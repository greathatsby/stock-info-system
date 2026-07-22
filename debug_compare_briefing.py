"""
(임시 진단용) 뉴스 헤드라인 유무에 따라 AI 브리핑이 실제로 달라지는지 비교.
확인 후 이 파일과 관련 워크플로우는 삭제할 예정입니다.
"""

import sqlite3

from collect import get_upcoming, fetch_company_context
from ai_briefing import generate_briefing

DB_PATH = "stocks.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    upcoming = get_upcoming(conn)
    conn.close()

    tickers = {t for t, _, _ in upcoming}
    context_with_news = {t: fetch_company_context(t) for t in tickers}
    context_without_news = {t: {**ctx, "news": []} for t, ctx in context_with_news.items()}

    print("===== [A] 뉴스 헤드라인 포함 =====")
    print(generate_briefing(upcoming, [], context_with_news))
    print()
    print("===== [B] 뉴스 헤드라인 제외 (섬터/사업개요만) =====")
    print(generate_briefing(upcoming, [], context_without_news))


if __name__ == "__main__":
    main()
