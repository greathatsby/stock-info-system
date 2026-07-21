"""
Gmail SMTP로 이메일 발송하는 모듈.

GitHub Actions Secrets에 등록된 환경변수를 사용합니다:
  - GMAIL_USER          : 보내는/받는 Gmail 주소
  - GMAIL_APP_PASSWORD  : Gmail 앱 비밀번호 (일반 로그인 비밀번호 아님)
  - RECIPIENT_EMAIL     : 받는 주소 (비워두면 GMAIL_USER와 동일하게 자기 자신에게 발송)
"""

import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone


def format_email_body(upcoming, newly_announced):
    # 이메일 본문을 일반 텍스트로 조립
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"국내외 실적 캘린더 ({today_str})", ""]

    if newly_announced:
        lines.append("■ 방금 발표된 실적 (컨센서스 대비)")
        for item in newly_announced:
            est = item["eps_estimate"]
            act = item["eps_actual"]
            surprise = item["surprise_pct"]
            surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
            est_str = f"{est:.2f}" if est is not None else "N/A"
            act_str = f"{act:.2f}" if act is not None else "N/A"
            lines.append(
                f"- {item['ticker']}: 실제 {act_str} / 컨센서스 {est_str} (서프라이즈 {surprise_str})"
            )
        lines.append("")

    if upcoming:
        lines.append("■ 이번 주 예정된 실적 발표")
        for ticker_symbol, report_date, eps_estimate in upcoming:
            est_str = f"${eps_estimate:.2f}" if eps_estimate is not None else "컨센서스 미공개"
            lines.append(f"- {report_date} {ticker_symbol} (컨센서스 EPS {est_str})")
    else:
        lines.append("■ 이번 주 예정된 실적 발표 없음")

    return "\n".join(lines)


def send_email(upcoming, newly_announced):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL") or gmail_user

    body = format_email_body(upcoming, newly_announced)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"국내외 IR 캘린더 ({today_str})"
    msg["From"] = gmail_user
    msg["To"] = recipient

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, [recipient], msg.as_string())

    print("메일 발송 완료:", recipient)
