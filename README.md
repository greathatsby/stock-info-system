# 주식 실적 캘린더 시스템 (MVP)

매일 아침(KST 08:00, 평일) 미국 주식 20개 종목의 실적 발표 일정과 컨센서스 대비
서프라이즈를 자동으로 수집해서 메일로 보내주는 시스템입니다.

## 남은 설정

1. Gmail 앱 비밀번호 발급: https://myaccount.google.com/apppasswords
   (2단계 인증 필요, 발급된 16자리 값을 아래 Secrets에 등록)
2. 이 저장소 Settings → Secrets and variables → Actions 에서 등록:
   - GMAIL_USER: 발송할 Gmail 주소
   - GMAIL_APP_PASSWORD: 1번에서 발급받은 앱 비밀번호
   - RECIPIENT_EMAIL: 받을 주소 (자기 자신이면 GMAIL_USER와 동일하게)
3. Actions 탭 → Daily Stock Earnings Update → Run workflow 로 수동 테스트
4. 종목 추가/삭제는 watchlist.py 의 TICKERS 리스트만 수정
