"""
주요 시장 지표(지수/금리/환율)와 경제 뉴스 헤드라인을 가져오는 모듈.

기존에 이미 쓰고 있는 yfinance 만 사용하므로 별도 API 키가 필요 없습니다.
"""

import yfinance as yf

# (야후 파이낸스 티커, 화면에 표시할 이름)
INDICATORS = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "나스닥"),
    ("^DJI", "다우"),
    ("^KS11", "코스피"),
    ("^VIX", "VIX(변동성)"),
    ("^TNX", "美 10년물 금리"),
    ("KRW=X", "원/달러 환율"),
    ("JPYKRW=X", "원/100엔 환율"),
    ("GC=F", "금(Gold)"),
    ("HG=F", "구리(Copper)"),
    ("CL=F", "WTI 유가"),
    ("BTC-USD", "비트코인"),
]

# 경제/시장 뉴스 헤드라인을 가져올 때 참고할 티커 (해당 종목의 관련 뉴스 피드를 사용)
NEWS_TICKER = "^GSPC"


def fetch_market_snapshot():
    # 지표별 최근 종가와 전일 대비 등락률을 조회
    snapshot = []
    for symbol, label in INDICATORS:
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            closes = hist["Close"].dropna()
            if len(closes) < 2:
                continue
            last = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            change_pct = (last - prev) / prev * 100
            # ^TNX/^FVX/^TYX 등 CBOE 금리 지수는 야후에서 (금리 x10) 값으로 제공됨
            if symbol == "^TNX":
                last = last / 10
            # JPYKRW=X는 "엔화 1엔당 원화"이므로, 한국에서 흔히 쓰는 "100엔당 원화" 기준으로 변환
            if symbol == "JPYKRW=X":
                last = last * 100
            snapshot.append(
                {
                    "symbol": symbol,
                    "label": label,
                    "value": last,
                    "change_pct": change_pct,
                }
            )
        except Exception as e:
            print(f"[경고] {symbol} 지표 조회 실패: {e}")
    return snapshot


def fetch_market_news(limit=10):
    # 시장/경제 관련 최신 뉴스 헤드라인 조회
    try:
        ticker = yf.Ticker(NEWS_TICKER)
        items = []
        for item in (ticker.news or [])[:limit]:
            content = item.get("content") if isinstance(item, dict) else None
            if content:
                title = content.get("title")
                link = (
                    (content.get("clickThroughUrl") or {}).get("url")
                    or (content.get("canonicalUrl") or {}).get("url")
                )
                publisher = (content.get("provider") or {}).get("displayName")
            else:
                title = item.get("title")
                link = item.get("link")
                publisher = item.get("publisher")
            if title and link:
                items.append({"title": title, "link": link, "publisher": publisher})
        return items
    except Exception as e:
        print(f"[경고] 시장 뉴스 조회 실패: {e}")
        return []
