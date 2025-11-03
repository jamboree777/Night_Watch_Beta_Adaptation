# Night Watch Beta Adaptation - 배포용 README

**나이트와치 베타아답션**  
**Liquidity Threshold & Delisting Monitoring System**

Streamlit 기반의 암호화폐 유동성 모니터링 및 상장폐지 방어 시스템입니다.

---

## 📋 요구사항

- Python 3.9 이상
- Railway 계정 (또는 다른 클라우드 호스팅 서비스)

---

## 🚀 배포 방법

### 1. Railway에 배포

1. GitHub에 레포지토리 푸시
2. Railway 대시보드에서 "New Project" 클릭
3. GitHub 레포지토리 연결
4. 자동 배포 시작

### 2. 환경 변수 설정

Railway 대시보드에서 다음 환경 변수를 설정하세요:

```
PYTHONIOENCODING=utf-8
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
```

### 3. 필수 설정 파일

`config/` 디렉토리에 다음 파일들을 설정하세요:

- `exchange_api_keys.json` - 거래소 API 키 (선택사항)
- `scanner_config.json` - 스캐너 설정
- `subscription_config.json` - 구독 설정
- `api_config.json` - 기타 API 키 (선택사항)

---

## 📁 프로젝트 구조

```
night-watch-deploy/
├── apps/                    # Streamlit 앱들
│   ├── night_watch_board.py      # 메인보드
│   ├── simple_user_dashboard.py  # 유저 대시보드
│   └── crypto_dashboard.py       # 관리자 대시보드
│
├── services/                # 백그라운드 서비스
│   ├── batch_scanner.py           # 정규 스캔
│   ├── scanner_scheduler.py       # 스캔 스케줄러
│   ├── premium_pool_collector.py # 프리미엄 풀 수집기
│   └── detect_missing_tokens.py  # 누락 토큰 감지
│
├── modules/                 # 핵심 모듈
├── helpers/                 # 헬퍼 함수들
├── collectors/              # 데이터 수집기
├── config/                  # 설정 파일들
├── data/                    # 데이터 디렉토리
└── logs/                    # 로그 디렉토리
```

---

## 🔧 주요 기능

### 메인보드 (Main Board)
- 실시간 유동성 모니터링
- 위험 토큰 알림
- 등급별 분류

### 유저 대시보드
- 개인화된 토큰 모니터링
- 상세 분석 리포트
- 프리미엄 풀 데이터

### 관리자 대시보드
- 시스템 제어
- 토큰 관리
- 스캔 모니터링

---

## 📝 설정 가이드

### Exchange API Keys

`config/exchange_api_keys.json` 파일을 생성하세요:

```json
{
  "gateio": {
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  },
  "mexc": {
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }
}
```

### Scanner Config

`config/scanner_config.json` 파일을 확인하고 필요시 수정하세요.

---

## 🛠️ 개발

### 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 메인보드 실행
streamlit run apps/night_watch_board.py --server.port 8501

# 유저 대시보드 실행
streamlit run apps/simple_user_dashboard.py --server.port 8506

# 관리자 대시보드 실행
streamlit run apps/crypto_dashboard.py --server.port 8503
```

### 백그라운드 서비스

```bash
# 스캐너 스케줄러
python services/scanner_scheduler.py start

# 프리미엄 풀 수집기
python services/premium_pool_collector.py --continuous
```

---

## 📄 라이선스

이 프로젝트는 비공개 프로젝트입니다.

---

## 🆘 지원

문제가 발생하면 GitHub Issues에 문의하세요.

