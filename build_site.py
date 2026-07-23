"""
수집된 실적 데이터를 정적 웹페이지(docs/index.html)로 생성하는 모듈.

collect.py 가 매일 실행되면서 이 모듈을 호출해 docs/index.html 을 새로 씁니다.
저장소 Settings -> Pages 에서 "Deploy from a branch: main / docs" 로 지정하면
이 파일이 그대로 공개 웹 대시보드가 됩니다.
"""

import calendar as calendar_mod
import os
from datetime import datetime

from watchlist import TICKERS

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
HEADER_DAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]

SITE_DIR = "docs"

CSS = """
:root {
  color-scheme: dark;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Pretendard, sans-serif;
  background: #0b1120;
  color: #e2e8f0;
  line-height: 1.5;
}
.container {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 16px 60px;
}
.hero {
  background: linear-gradient(135deg, #0f172a, #1e293b);
  border: 1px solid #1e293b;
  border-radius: 14px;
  padding: 24px;
}
.eyebrow {
  font-size: 12px;
  letter-spacing: 2px;
  color: #93c5fd;
  font-weight: 600;
}
.hero h1 {
  font-size: 26px;
  margin: 6px 0 8px;
}
.meta {
  font-size: 13px;
  color: #94a3b8;
}
.section-title {
  font-size: 16px;
  margin: 28px 0 10px;
  color: #f1f5f9;
}
.card {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 12px;
  padding: 14px;
}
.muted { color: #94a3b8; }
.small { font-size: 12px; }

.briefing-card {
  background: #0f1e33;
  border: 1px solid #1e3a5f;
  border-radius: 12px;
  padding: 16px;
  margin-top: 20px;
}
.briefing-title { font-weight: 700; margin-bottom: 8px; font-size: 14px; }
.briefing-body { font-size: 14px; color: #cbd5e1; }

table.calendar {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
table.calendar th {
  padding: 6px 2px;
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}
.cal-cell {
  vertical-align: top;
  padding: 4px;
  border: 1px solid #1f2937;
  min-height: 44px;
  height: 44px;
}
.cal-cell-muted .cal-day { color: #334155; }
.cal-cell-today { background: #1e293b; }
.cal-day { font-size: 11px; color: #cbd5e1; margin-bottom: 2px; }
.cal-badges { display: flex; flex-wrap: wrap; gap: 2px; }

.badge {
  display: inline-block;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.badge-scheduled { background: #1e2a4a; color: #93c5fd; }
.badge-announced { background: #1f2937; color: #94a3b8; }

.list-row {
  padding: 8px 0;
  border-bottom: 1px solid #1f2937;
  font-size: 13px;
}
.list-row:last-child { border-bottom: none; }
.dday {
  display: inline-block;
  min-width: 46px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #3a2412;
  color: #fb923c;
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  margin-right: 6px;
}
.ticker-link { color: #e2e8f0; text-decoration: none; }
.ticker-link:hover { text-decoration: underline; }

.surprise-up { color: #f87171; font-weight: 600; }
.surprise-down { color: #60a5fa; font-weight: 600; }
.surprise-na { color: #94a3b8; }

.detail-date { font-size: 12px; color: #94a3b8; margin: 16px 0 4px; }
table.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 4px;
}
table.detail-table th {
  text-align: left;
  color: #64748b;
  font-weight: 500;
  padding: 6px;
  font-size: 11px;
}
table.detail-table td { padding: 6px; border-top: 1px solid #1f2937; }
table.detail-table a { color: #93c5fd; text-decoration: none; }

.footer {
  margin-top: 32px;
  font-size: 12px;
  color: #475569;
  text-align: center;
}

.market-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.market-tile {
  background: #0d1526;
  border: 1px solid #1f2937;
  border-radius: 10px;
  padding: 10px 12px;
}
.market-label { font-size: 11px; color: #94a3b8; margin-bottom: 4px; }
.market-value { font-size: 16px; font-weight: 700; color: #f1f5f9; }
.market-change { font-size: 12px; margin-top: 2px; }

.news-row {
  padding: 8px 0;
  border-bottom: 1px solid #1f2937;
  font-size: 13px;
}
.news-row:last-child { border-bottom: none; }
.news-row a { color: #e2e8f0; text-decoration: none; }
.news-row a:hover { text-decoration: underline; }
.news-publisher { color: #64748b; font-size: 11px; margin-left: 6px; }
"""


def _weekday_kr(d):
    return WEEKDAY_KR[d.weekday()]


def _yahoo_link(ticker):
    return f"https://finance.yahoo.com/quote/{ticker}"


def _fmt(value):
    return f"{value:.2f}" if value is not None else "N/A"


def _group_by_date(month_earnings):
    grouped = {}
    for ticker, report_date, eps_estimate, eps_actual, surprise_pct, status in month_earnings:
        grouped.setdefault(report_date, []).append(
            {
                "ticker": ticker,
                "eps_estimate": eps_estimate,
                "eps_actual": eps_actual,
                "surprise_pct": surprise_pct,
                "status": status,
            }
        )
    return grouped


def _badge_html(ticker, status):
    css_class = "badge-announced" if status == "announced" else "badge-scheduled"
    return f'<a href="{_yahoo_link(ticker)}" class="badge {css_class}">{ticker}</a>'


def _build_calendar_html(month_earnings, today):
    grouped = _group_by_date(month_earnings)
    cal = calendar_mod.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdatescalendar(today.year, today.month)

    header_cells = "".join(f"<th>{d}</th>" for d in HEADER_DAYS_KR)

    rows = []
    for week in weeks:
        cells = []
        for day in week:
            date_str = day.isoformat()
            in_month = day.month == today.month
            entries = grouped.get(date_str, [])
            badges = "".join(_badge_html(e["ticker"], e["status"]) for e in entries)
            classes = "cal-cell"
            if not in_month:
                classes += " cal-cell-muted"
            if day == today:
                classes += " cal-cell-today"
            cells.append(
                f'<td class="{classes}"><div class="cal-day">{day.day}</div>'
                f'<div class="cal-badges">{badges}</div></td>'
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")

    return (
        '<table class="calendar">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _build_upcoming_html(upcoming, today):
    if not upcoming:
        return '<p class="muted small">이번 주 예정된 실적 발표가 없습니다.</p>'
    items = []
    for ticker, report_date, eps_estimate in upcoming:
        d = datetime.strptime(report_date, "%Y-%m-%d").date()
        d_day = (d - today).days
        d_label = "D-DAY" if d_day == 0 else f"D-{d_day}"
        est_str = f"${eps_estimate:.2f}" if eps_estimate is not None else "컨센서스 미공개"
        items.append(
            '<div class="list-row">'
            f'<span class="dday">{d_label}</span>'
            f'<a href="{_yahoo_link(ticker)}" class="ticker-link">{report_date}({_weekday_kr(d)}) <b>{ticker}</b></a> '
            f'<span class="muted small">(컨센서스 EPS {est_str})</span>'
            "</div>"
        )
    return "".join(items)


def _build_announced_html(newly_announced):
    if not newly_announced:
        return ""
    items = []
    for item in newly_announced:
        est, act, surprise = item["eps_estimate"], item["eps_actual"], item["surprise_pct"]
        surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
        if surprise is None:
            surprise_class = "surprise-na"
        else:
            surprise_class = "surprise-up" if surprise >= 0 else "surprise-down"
        items.append(
            '<div class="list-row">'
            f'<b>{item["ticker"]}</b> 실제 {_fmt(act)} / 컨센서스 {_fmt(est)} '
            f'<span class="{surprise_class}">{surprise_str}</span></div>'
        )
    return (
        '<h2 class="section-title">방금 발표된 실적</h2>'
        f'<div class="card">{"".join(items)}</div>'
    )


def _build_detail_html(month_earnings):
    grouped = _group_by_date(month_earnings)
    if not grouped:
        return '<p class="muted small">이번 달 등록된 실적 일정이 없습니다.</p>'

    sections = []
    for date_str in sorted(grouped.keys()):
        rows = []
        for e in grouped[date_str]:
            surprise = e["surprise_pct"]
            surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
            if surprise is None:
                surprise_class = "surprise-na"
            else:
                surprise_class = "surprise-up" if surprise >= 0 else "surprise-down"
            rows.append(
                "<tr>"
                f'<td><a href="{_yahoo_link(e["ticker"])}">{e["ticker"]}</a></td>'
                f'<td>{_fmt(e["eps_estimate"])}</td>'
                f'<td>{_fmt(e["eps_actual"])}</td>'
                f'<td class="{surprise_class}">{surprise_str}</td>'
                "</tr>"
            )
        sections.append(
            f'<h3 class="detail-date">{date_str}</h3>'
            '<table class="detail-table">'
            "<tr><th>종목</th><th>컨센서스 EPS</th><th>실제 EPS</th><th>서프라이즈</th></tr>"
            f"{''.join(rows)}</table>"
        )
    return "".join(sections)


def _format_market_value(symbol, value):
    if symbol == "KRW=X":
        return f"{value:,.1f}원"
    if symbol == "^TNX":
        return f"{value:.2f}%"
    if symbol == "CL=F":
        return f"${value:,.2f}"
    if symbol == "BTC-USD":
        return f"${value:,.0f}"
    return f"{value:,.2f}"


def _build_market_html(market_snapshot):
    if not market_snapshot:
        return ""
    tiles = []
    for item in market_snapshot:
        change = item["change_pct"]
        change_class = "surprise-up" if change >= 0 else "surprise-down"
        value_str = _format_market_value(item["symbol"], item["value"])
        tiles.append(
            '<div class="market-tile">'
            f'<div class="market-label">{item["label"]}</div>'
            f'<div class="market-value">{value_str}</div>'
            f'<div class="market-change {change_class}">{change:+.2f}%</div>'
            "</div>"
        )
    return (
        '<h2 class="section-title">주요 시장 지표</h2>'
        f'<div class="market-grid">{"".join(tiles)}</div>'
    )


def _build_news_html(market_news):
    if not market_news:
        return ""
    items = []
    for item in market_news:
        publisher = f'<span class="news-publisher">{item["publisher"]}</span>' if item.get("publisher") else ""
        items.append(
            '<div class="news-row">'
            f'<a href="{item["link"]}" target="_blank" rel="noopener">{item["title"]}</a>{publisher}'
            "</div>"
        )
    return (
        '<h2 class="section-title">경제/시장 뉴스</h2>'
        f'<div class="card">{"".join(items)}</div>'
    )


def _build_briefing_html(ai_briefing):
    if not ai_briefing:
        return ""
    return (
        '<div class="briefing-card">'
        '<div class="briefing-title">🤖 AI 실적 브리핑</div>'
        f'<div class="briefing-body">{ai_briefing}</div>'
        "</div>"
    )


def build_site(
    upcoming,
    newly_announced,
    month_earnings,
    ai_briefing,
    today,
    market_snapshot=None,
    market_news=None,
    out_dir=SITE_DIR,
):
    os.makedirs(out_dir, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>국내외 IR 캘린더</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <header class="hero">
    <div class="eyebrow">GLOBAL IR CALENDAR</div>
    <h1>국내외 IR 캘린더</h1>
    <div class="meta">{today.isoformat()}({_weekday_kr(today)}) 기준 · 평일 아침 자동 갱신 · {len(TICKERS)}개 기업 감시</div>
  </header>

  {_build_market_html(market_snapshot or [])}

  {_build_briefing_html(ai_briefing)}

  {_build_news_html(market_news or [])}

  <h2 class="section-title">실적발표 캘린더</h2>
  <div class="card">{_build_calendar_html(month_earnings, today)}</div>

  <h2 class="section-title">이번 주 실적발표 일정</h2>
  <div class="card">{_build_upcoming_html(upcoming, today)}</div>

  {_build_announced_html(newly_announced)}

  <h2 class="section-title">상세 일정</h2>
  <div class="card">{_build_detail_html(month_earnings)}</div>

  <div class="footer">Data via Yahoo Finance · Generated by GitHub Actions</div>
</div>
</body>
</html>
"""

    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("웹사이트 생성 완료:", path)
    return path
