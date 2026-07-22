"""
Google Gemini API로 이번 주 실적 발표 브리핑 문단을 생성하는 모듈.

GEMINI_API_KEY 환경변수가 필요합니다 (https://aistudio.google.com/apikey 에서 발급).
키가 없거나 호출에 실패하면 None을 반환하고, collect.py/send_email.py는 이 경우
브리핑 없이 기존 메일을 그대로 발송합니다.
"""

import os

import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _build_prompt(upcoming, newly_announced):
    lines = ["다음은 이번 주 실적 발표 일정과 컨센서스 EPS다.", ""]
    for ticker, report_date, eps_estimate in upcoming:
        est = f"${eps_estimate:.2f}" if eps_estimate is not None else "미공개"
        lines.append(f"- {report_date} {ticker} (컨센서스 EPS {est})")

    if newly_announced:
        lines.append("")
        lines.append("최근 발표된 실적(컨센서스 대비 서프라이즈):")
        for item in newly_announced:
            surprise = item["surprise_pct"]
            surprise_str = f"{surprise:+.1f}%" if surprise is not None else "N/A"
            lines.append(f"- {item['ticker']}: 서프라이즈 {surprise_str}")

    lines.append("")
    lines.append(
        "위 내용을 바탕으로 국내 투자자를 위한 '이번 주 관전 포인트'를 "
        "3~5문장의 한국어 문단으로 작성해줘. 어떤 종목의 실적을 먼저 확인해야 하는지, "
        "주목할 만한 서프라이즈가 있었는지 위주로 간결하게 써줘. 과장하거나 투자 조언처럼 "
        "쓰지 말고 사실 위주로 요약해줘."
    )
    return "\n".join(lines)


def generate_briefing(upcoming, newly_announced):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    if not upcoming and not newly_announced:
        return None

    prompt = _build_prompt(upcoming, newly_announced)
    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"[경고] AI 브리핑 생성 실패: {e}")
        return None
