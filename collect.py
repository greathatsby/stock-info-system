"""
주식 실적 발표 캘린더 수집 스크립트.

동작 순서:
1) watchlist.py 에 정의된 종목들의 실적 발표일/컨센서스/실제치를 야후 파이낸스에서 수집
2) SQLite(stocks.db)에 저장 (이미 있으면 갱신, 없으면 추가 - upsert)
3) '방금 발표됨(scheduled -> announced)'으로 바뀐 종목과 '이번 주 예정' 종목,
   그리고 이번 달 캘린더용 데이터를 모아 이메일 발송
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import yfinance as yf

from watchlist import TICKERS
from send_email import send_email
from ai_briefing import generate_briefing
from build_site import build_site
from market_snapshot import fetch_market_snapshot, fetch_market_news

DB_PATH = "stocks.db"


def init_db(conn):
    # 실적 정보를 저장할 테이블 생성 (이미 있으면 그대로 둠)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS earnings (
            ticker TEXT NOT NULL,
            report_date TEXT NOT NULL,
            eps_estimate REAL,
            eps_actual REAL,
            surprise_pct REAL,
            status TEXT,
            updated_at TEXT,
            PRIMARY KEY (ticker, report_date)
        )
        """
    )
    conn.commit()


def fetch_ticker_earnings(ticker_symbol):
    # 종목 하나의 최근 + 예정 실적 발표 일정을 가져옴 (최대 8건)
    ticker = yf.Ticker(ticker_symbol)
    try:
        df = ticker.get_earnings_dates(limit=8)
    except Exception as e:
        print(f"[경고] {ticker_symbol} 조회 실패: {e}")
        return None
    return df


def _clean(value):
    # pandas 결측치(NaN)를 None으로, 나머지는 float로 변환
    if value is None:
        return None
    try:
        if value != value:  # NaN 체크
            return None
        return float(value)
    except TypeError:
        return None


def upsert_earnings(conn, ticker_symbol, df):
    # DB에 저장하면서, 이전에는 '예정'이었다가 이번에 '발표완료'로 바뀐 건을 찾아 반환
    newly_announced = []
    now_str = datetime.now(timezone.utc).isoformat()

    for report_date, row in df.iterrows():
        date_str = report_date.strftime("%Y-%m-%d")
        eps_estimate = _clean(row.get("EPS Estimate"))
        eps_actual = _clean(row.get("Reported EPS"))
        surprise_pct = _clean(row.get("Surprise(%)"))

        new_status = "announced" if eps_actual is not None else "scheduled"

        cur = conn.execute(
            "SELECT status FROM earnings WHERE ticker=? AND report_date=?",
            (ticker_symbol, date_str),
        )
        existing = cur.fetchone()
        old_status = existing[0] if existing else None

        conn.execute(
            """
            INSERT INTO earnings (ticker, report_date, eps_estimate, eps_actual, surprise_pct, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, report_date) DO UPDATE SET
                eps_estimate=excluded.eps_estimate,
                eps_actual=excluded.eps_actual,
                surprise_pct=excluded.surprise_pct,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (ticker_symbol, date_str, eps_estimate, eps_actual, surprise_pct, new_status, now_str),
        )

        if old_status == "scheduled" and new_status == "announced":
            newly_announced.append(
                {
                    "ticker": ticker_symbol,
                    "date": date_str,
                    "eps_estimate": eps_estimate,
                    "eps_actual": eps_actual,
                    "surprise_pct": surprise_pct,
                }
            )

    conn.commit()
    return newly_announced


def get_upcoming(conn, days_ahead=7):
    # 오늘부터 N일 이내 예정된 실적 발표 목록을 날짜순으로 조회
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=days_ahead)
    cur = conn.execute(
        """
        SELECT ticker, report_date, eps_estimate
        FROM earnings
        WHERE status='scheduled' AND report_date BETWEEN ? AND ?
        ORDER BY report_date
        """,
        (today.isoformat(), end.isoformat()),
    )
    return cur.fetchall()


def fetch_company_context(ticker_symbol):
    # AI 브리핑에 참고할 섹터/업종/사업개요/최근 뉴스를 야후 파이낸스에서 수집
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}
    except Exception as e:
        print(f"[경고] {ticker_symbol} 기업 정보 조회 실패: {e}")
        return {}

    headlines = []
    try:
        for item in (ticker.news or [])[:3]:
            content = item.get("content") if isinstance(item, dict) else None
            title = (content or {}).get("title") if content else item.get("title")
            if title:
                headlines.append(title)
    except Exception as e:
        print(f"[경고] {ticker_symbol} 뉴스 조회 실패: {e}")

    return {
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "summary": info.get("longBusinessSummary"),
        "news": headlines,
    }


def get_month_earnings(conn, today):
    # 이번 달 캘린더 그리드(앞뒤 다른 달 날짜 포함)에 표시할 실적 일정을 모두 조회
    first_of_month = today.replace(day=1)
    if today.month == 12:
        next_month_first = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_first = today.replace(month=today.month + 1, day=1)
    start = first_of_month - timedelta(days=7)
    end = next_month_first + timedelta(days=7)

    cur = conn.execute(
        """
        SELECT ticker, report_date, eps_estimate, eps_actual, surprise_pct, status
        FROM earnings
        WHERE report_date BETWEEN ? AND ?
        ORDER BY report_date, ticker
        """,
        (start.isoformat(), end.isoformat()),
    )
    return cur.fetchall()


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    all_newly_announced = []

    for ticker_symbol in TICKERS:
        df = fetch_ticker_earnings(ticker_symbol)
        if df is None or df.empty:
            continue
        newly_announced = upsert_earnings(conn, ticker_symbol, df)
        all_newly_announced.extend(newly_announced)

    today = datetime.now(timezone.utc).date()
    upcoming = get_upcoming(conn)
    month_earnings = get_month_earnings(conn, today)
    conn.close()

    briefing_tickers = {t for t, _, _ in upcoming} | {item["ticker"] for item in all_newly_announced}
    company_context = {t: fetch_company_context(t) for t in briefing_tickers}

    ai_briefing = generate_briefing(upcoming, all_newly_announced, company_context)

    market_snapshot = fetch_market_snapshot()
    market_news = fetch_market_news()

    send_email(
        upcoming=upcoming,
        newly_announced=all_newly_announced,
        month_earnings=month_earnings,
        ai_briefing=ai_briefing,
        market_snapshot=market_snapshot,
        market_news=market_news,
    )

    build_site(
        upcoming=upcoming,
        newly_announced=all_newly_announced,
        month_earnings=month_earnings,
        ai_briefing=ai_briefing,
        today=today,
        market_snapshot=market_snapshot,
        market_news=market_news,
    )


if __name__ == "__main__":
    main()
