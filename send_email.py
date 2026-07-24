"""
Gmail SMTP로 이메일 발송하는 모듈 (HTML 캘린더 버전).

GitHub Actions Secrets에 등록된 환경변수를 사용합니다:
  - GMAIL_USER          : 보내는/받는 Gmail 주소
  - GMAIL_APP_PASSWORD  : Gmail 앱 비밀번호 (일반 로그인 비밀번호 아님)
  - RECIPIENT_EMAIL     : 받는 주소 (비워두면 GMAIL_USER와 동일하게 자기 자신에게 발송)
"""

import os
import calendar as calendar_mod
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

from watchlist import TICKERS

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
HEADER_DAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]


def _weekday_kr(d):
    return WEEKDAY_KR[d.weekday()]


def _yahoo_link(ticker):
    return f"https://finance.yahoo.com/quote/{ticker}"


def _fmt(value):
    return f"{value:.2f}" if value is not None else "N/A"


def _group_by_date(month_earnings):
    # [(ticker, report_date, eps_estimate, eps_actual, surprise_pct, status), ...] -> {report_date: [entry, ...]}
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


def _badge_html(ticker, status, date_str):
    if status == "announced":
        bg, color = "#e5e7eb", "#6b7280"
    else:
        bg, color = "#ffedd5", "#c2410c"
    return (
        f'<a href="{_yahoo_link(ticker)}" style="text-decoration:none;">'
        f'<span style="display:inline-block;margin:1px;padding:2px 6px;'
        f'border-radius:4px;background:{bg};color:{color};font-size:11px;'
        f'font-weight:600;white-space:nowrap;">{ticker}</span></a>'
    )


def build_calendar_html(month_earnings, today):
    grouped = _group_by_date(month_earnings)
    cal = calendar_mod.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdatescalendar(today.year, today.month)

    header_cells = "".join(
        f'<th style="padding:6px;font-size:12px;color:#6b7280;">{d}</th>'
        for d in HEADER_DAYS_KR
    )

    row_html = []
    for week in weeks:
        cells = []
        for day in week:
            date_str = day.isoformat()
            in_month = day.month == today.month
            entries = grouped.get(date_str, [])
            badges = "".join(_badge_html(e["ticker"], e["status"], date_str) for e in entries)
            day_color = "#111827" if in_month else "#d1d5db"
            bg = "#fdf2f8" if day == today else "transparent"
            cells.append(
                f'<td style="vertical-align:top;padding:4px;border:1px solid #f0f0f0;'
                f'background:{bg};min-width:70px;">'
                f'<div style="font-size:12px;color:{day_color};margin-bottom:2px;">{day.day}</div>'
                f'<div>{badges}</div></td>'
            )
        row_html.append(f"<tr>{''.join(cells)}</tr>")

    return (
        '<table style="width:100%;border-collapse:collapse;font-family:sans-serif;">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody></table>"
    )


def build_upcoming_html(upcoming, today):
    if not upcoming:
        return '<p style="color:#6b7280;font-size:13px;">이번 주 예정된 실적 발표 없음</p>'
    items = []
    for ticker, report_date, eps_estimate in upcoming:
        d = datetime.strptime(report_date, "%Y-%m-%d").date()
        d_day = (d - today).days
        d_label = "D-DAY" if d_day == 0 else f"D-{d_day}"
        est_str = f"${eps_estimate:.2f}" if eps_estimate is not None else "컨센서스 미공개"
        items.append(
            '<div style="padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px;">'
            '<span style="display:inline-block;min-width:52px;padding:2px 6px;'
            'border-radius:4px;background:#fff1e6;color:#c2410c;font-size:11px;'
            f'font-weight:700;text-align:center;">{d_label}</span> '
            f'<a href="{_yahoo_link(ticker)}" style="text-decoration:none;color:#111827;">'
            f'{report_date}({_weekday_kr(d)}) <b>{ticker}</b></a> '
            f'<span style="color:#6b7280;font-size:12px;">(컨센서스 EPS {est_str})</span>'
            '</div>'
        )
    return "".join(items)


def build_announced_html(newly_announced):
    if not newly_announced:
        return ""
    items = []
    for item in newly_announced:
        est, act, surprise = item["eps_estimate"], item["eps_actual"], item["surprise_pct"]
        surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
        if surprise is None:
            surprise_color = "#6b7280"
        else:
            surprise_color = "#dc2626" if surprise >= 0 else "#2563eb"
        items.append(
            '<div style="padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px;">'
            f'<b>{item["ticker"]}</b>: 실제 {_fmt(act)} / 컨센서스 {_fmt(est)} '
            f'(서프라이즈 <span style="color:{surprise_color};">{surprise_str}</span>)</div>'
        )
    return (
        '<h3 style="margin:20px 0 8px;font-size:15px;">방금 발표된 실적</h3>'
        f"{''.join(items)}"
    )


def build_detail_html(month_earnings):
    grouped = _group_by_date(month_earnings)
    if not grouped:
        return '<p style="color:#6b7280;font-size:13px;">이번 달 등록된 실적 일정이 없습니다.</p>'

    sections = []
    for date_str in sorted(grouped.keys()):
        rows = []
        for e in grouped[date_str]:
            surprise = e["surprise_pct"]
            surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
            if surprise is None:
                surprise_color = "#6b7280"
            else:
                surprise_color = "#dc2626" if surprise >= 0 else "#2563eb"
            rows.append(
                "<tr>"
                f'<td style="padding:6px;font-weight:600;">{e["ticker"]}</td>'
                f'<td style="padding:6px;">{_fmt(e["eps_estimate"])}</td>'
                f'<td style="padding:6px;">{_fmt(e["eps_actual"])}</td>'
                f'<td style="padding:6px;color:{surprise_color};">{surprise_str}</td>'
                f'<td style="padding:6px;"><a href="{_yahoo_link(e["ticker"])}">링크</a></td>'
                "</tr>"
            )
        sections.append(
            f'<h4 style="margin:14px 0 4px;font-size:13px;color:#111827;">{date_str}</h4>'
            '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
            '<tr style="color:#6b7280;text-align:left;">'
            "<th style=\"padding:6px;\">종목</th><th style=\"padding:6px;\">컨센서스 EPS</th>"
            "<th style=\"padding:6px;\">실제 EPS</th><th style=\"padding:6px;\">서프라이즈</th>"
            "<th style=\"padding:6px;\"></th></tr>"
            f"{''.join(rows)}</table>"
        )
    return "".join(sections)


def _format_market_value(symbol, value):
    if symbol in ("KRW=X", "JPYKRW=X"):
        return f"{value:,.1f}원"
    if symbol == "^TNX":
        return f"{value:.2f}%"
    if symbol in ("CL=F", "GC=F"):
        return f"${value:,.2f}"
    if symbol == "HG=F":
        return f"${value:,.3f}"
    if symbol == "BTC-USD":
        return f"${value:,.0f}"
    return f"{value:,.2f}"


def build_market_html(market_snapshot):
    if not market_snapshot:
        return ""
    cells = []
    for item in market_snapshot:
        change = item["change_pct"]
        color = "#dc2626" if change >= 0 else "#2563eb"
        value_str = _format_market_value(item["symbol"], item["value"])
        cells.append(
            '<td style="padding:6px 10px;vertical-align:top;">'
            f'<div style="font-size:11px;color:#6b7280;">{item["label"]}</div>'
            f'<div style="font-size:14px;font-weight:700;">{value_str}</div>'
            f'<div style="font-size:12px;color:{color};">{change:+.2f}%</div>'
            "</td>"
        )
    # 4개씩 줄바꿈
    rows = []
    for i in range(0, len(cells), 4):
        rows.append(f"<tr>{''.join(cells[i:i + 4])}</tr>")
    return (
        '<h3 style="margin:20px 0 8px;font-size:15px;">주요 시장 지표</h3>'
        '<table style="width:100%;border-collapse:collapse;">' + "".join(rows) + "</table>"
    )


def build_news_html(market_news):
    if not market_news:
        return ""
    items = []
    for item in market_news:
        publisher = f' <span style="color:#9ca3af;font-size:11px;">({item["publisher"]})</span>' if item.get("publisher") else ""
        items.append(
            '<div style="padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px;">'
            f'<a href="{item["link"]}" style="text-decoration:none;color:#111827;">{item["title"]}</a>{publisher}'
            "</div>"
        )
    return (
        '<h3 style="margin:20px 0 8px;font-size:15px;">경제/시장 뉴스</h3>'
        f"{''.join(items)}"
    )


def build_briefing_html(ai_briefing):
    if not ai_briefing:
        return ""
    return (
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:16px;margin:20px 0;">'
        '<div style="font-size:13px;font-weight:700;margin-bottom:6px;">🤖 AI 실적 브리핑</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.6;">{ai_briefing}</div>'
        "</div>"
    )


def format_email_html(upcoming, newly_announced, month_earnings, today, ai_briefing=None, market_snapshot=None, market_news=None):
    return f"""
    <div style="font-family:-apple-system,Helvetica,sans-serif;max-width:640px;margin:0 auto;color:#111827;">
      <div style="background:#0f172a;color:#fff;border-radius:10px;padding:20px;">
        <div style="font-size:12px;letter-spacing:1px;color:#fdba74;">GLOBAL IR & ECONOMY</div>
        <div style="font-size:20px;font-weight:700;margin-top:4px;">국내외 IR·경제 캘린더</div>
        <div style="font-size:13px;color:#cbd5e1;margin-top:6px;">
          {today.isoformat()}({_weekday_kr(today)}) · 평일 아침 8시 발행 · {len(TICKERS)}개 기업 감시
        </div>
      </div>

      {build_market_html(market_snapshot or [])}

      {build_briefing_html(ai_briefing)}

      {build_news_html(market_news or [])}

      <h3 style="margin:20px 0 8px;font-size:15px;">실적발표 캘린더</h3>
      {build_calendar_html(month_earnings, today)}

      <h3 style="margin:20px 0 8px;font-size:15px;">이번 주 실적발표 일정</h3>
      {build_upcoming_html(upcoming, today)}

      {build_announced_html(newly_announced)}

      <h3 style="margin:20px 0 8px;font-size:15px;">상세 일정</h3>
      {build_detail_html(month_earnings)}
    </div>
    """


def format_email_text(upcoming, newly_announced, ai_briefing=None, market_snapshot=None, market_news=None):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"국내외 실적 캘린더 ({today_str})", ""]

    if market_snapshot:
        lines.append("■ 주요 시장 지표")
        for item in market_snapshot:
            value_str = _format_market_value(item["symbol"], item["value"])
            lines.append(f"- {item['label']}: {value_str} ({item['change_pct']:+.2f}%)")
        lines.append("")

    if ai_briefing:
        lines.append("■ AI 실적 브리핑")
        lines.append(ai_briefing)
        lines.append("")

    if market_news:
        lines.append("■ 경제/시장 뉴스")
        for item in market_news:
            lines.append(f"- {item['title']} ({item['link']})")
        lines.append("")

    if newly_announced:
        lines.append("■ 방금 발표된 실적 (컨센서스 대비)")
        for item in newly_announced:
            est, act, surprise = item["eps_estimate"], item["eps_actual"], item["surprise_pct"]
            surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
            lines.append(
                f"- {item['ticker']}: 실제 {_fmt(act)} / 컨센서스 {_fmt(est)} (서프라이즈 {surprise_str})"
            )
        lines.append("")

    if upcoming:
        lines.append("■ 이번 주 예정된 실적 발표")
        for ticker, report_date, eps_estimate in upcoming:
            est_str = f"${eps_estimate:.2f}" if eps_estimate is not None else "컨센서스 미공개"
            lines.append(f"- {report_date} {ticker} (컨센서스 EPS {est_str})")
    else:
        lines.append("■ 이번 주 예정된 실적 발표 없음")

    lines.append("")
    lines.append("(이 메일은 HTML 형식으로 보시면 캘린더와 링크가 함께 표시됩니다.)")

    return "\n".join(lines)


def send_email(upcoming, newly_announced, month_earnings, ai_briefing=None, market_snapshot=None, market_news=None):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL") or gmail_user

    today = datetime.now(timezone.utc).date()
    text_body = format_email_text(upcoming, newly_announced, ai_briefing, market_snapshot, market_news)
    html_body = format_email_html(upcoming, newly_announced, month_earnings, today, ai_briefing, market_snapshot, market_news)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"국내외 IR·경제 캘린더 ({today.isoformat()})"
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, [recipient], msg.as_string())

    print("메일 발송 완료:", recipient)
