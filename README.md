# 주식 실적 캘린더 시스템 (MVP)

매일 아침(KST 08:00, 평일) 미국 주식 20개 종목의 실적 발표 일정과 컨센서스 대비
서프라이즈를 자동으로 수집해서 HTML 캘린더 메일로 보내주는 시스템입니다.
Gemini API 키를 등록하면 이번 주 관전 포인트를 요약하는 AI 브리핑도 함께 발송됩니다.
주요 지수(S&P 500·나스닥·다우·코스피), VIX, 美 10년물 금리, 원/달러·원/100엔 환율,
금·구리·WTI 유가, 비트코인 같은 시장 지표와 경제/시장 뉴스 헤드라인(10건)도 함께
수집해서 이메일과 웹 대시보드에 표시합니다.
같은 데이터로 `docs/index.html` 웹 대시보드도 매일 자동 생성되며, GitHub Pages로
공개 웹사이트처럼 확인할 수 있습니다.

## 남은 설정

1. Gmail 앱 비밀번호 발급: https://myaccount.google.com/apppasswords
   (2단계 인증 필요, 발급된 16자리 값을 아래 Secrets에 등록)
2. (선택) Gemini API 키 발급: https://aistudio.google.com/apikey
   (AI 실적 브리핑 기능에 사용. 등록하지 않으면 브리핑 없이 캘린더 메일만 발송됩니다)
3. 이 저장소 Settings → Secrets and variables → Actions 에서 등록:
   - GMAIL_USER: 발송할 Gmail 주소
   - GMAIL_APP_PASSWORD: 1번에서 발급받은 앱 비밀번호
   - RECIPIENT_EMAIL: 받을 주소 (자기 자신이면 GMAIL_USER와 동일하게)
   - GEMINI_API_KEY: 2번에서 발급받은 키 (선택)
4. Actions 탭 → Daily Stock Earnings Update → Run workflow 로 수동 테스트
5. 종목 추가/삭제는 watchlist.py 의 TICKERS 리스트만 수정
   - 시장 지표(지수/금리/환율) 추가/삭제는 market_snapshot.py 의 INDICATORS 리스트만 수정
     (yfinance 티커 기준이며 별도 API 키가 필요 없습니다)
6. 웹 대시보드 공개(GitHub Pages, 최초 1회만 설정):
   - 이 저장소 Settings → Pages 로 이동
   - Build and deployment → Source: "Deploy from a branch" 선택
   - Branch: `main` / 폴더: `/docs` 선택 후 저장
   - 잠시 후 `https://<GitHub 사용자명>.github.io/stock-info-system/` 에서 대시보드 확인 가능
   - 이후 워크플로우가 실행될 때마다 `docs/index.html` 이 갱신되며 사이트도 자동으로 최신화됩니다
