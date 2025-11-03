# Render 배포 가이드

이 가이드는 Night Watch 프로젝트를 Render에 배포하는 방법을 단계별로 안내합니다.

---

## 📋 사전 준비

1. GitHub 레포지토리에 프로젝트 업로드 완료
2. Render 계정 생성 (https://render.com)
3. 필요한 환경 변수 목록 준비

---

## 🚀 단계별 배포 가이드

### 방법 1: render.yaml 사용 (권장)

#### Step 1: Render 대시보드 접속

1. https://render.com 접속
2. 로그인 또는 회원가입

#### Step 2: 새 Blueprint 생성

1. Dashboard에서 "New +" 버튼 클릭
2. "Blueprint" 선택
3. GitHub 레포지토리 연결:
   - GitHub 계정 연결 (처음 한 번만)
   - 레포지토리 선택: `night-watch`
4. "Apply" 클릭

#### Step 3: 서비스 자동 생성 확인

Render가 `render.yaml` 파일을 자동 감지하여 다음 5개 서비스를 생성합니다:

1. **night-watch-admin** (Web Service)
   - Admin Dashboard
   - URL: `https://night-watch-admin.onrender.com`

2. **night-watch-main** (Web Service)
   - Main Board
   - URL: `https://night-watch-main.onrender.com`

3. **night-watch-user** (Web Service)
   - User Dashboard
   - URL: `https://night-watch-user.onrender.com`

4. **night-watch-scanner** (Background Worker)
   - Scanner Scheduler
   - 백그라운드 실행

5. **night-watch-collector** (Background Worker)
   - Premium Pool Collector
   - 백그라운드 실행

#### Step 4: 환경 변수 설정

각 서비스의 Settings → Environment Variables에서 다음 변수를 추가하세요:

```
PYTHONIOENCODING=utf-8
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
```

**추가 환경 변수 (선택사항):**
- API 키들은 환경 변수로 설정 권장
- `EXCHANGE_API_KEY_GATEIO`
- `EXCHANGE_API_KEY_MEXC`
- `ETHERSCAN_API_KEY`

#### Step 5: 배포 확인

1. 각 서비스의 "Events" 탭에서 배포 진행 상황 확인
2. 배포 완료 후 서비스 URL 확인
3. 각 URL 접속하여 서비스 정상 작동 확인

---

### 방법 2: Procfile 사용

#### Step 1: 새 Web Service 생성

1. Dashboard에서 "New +" 버튼 클릭
2. "Web Service" 선택
3. GitHub 레포지토리 연결
4. 서비스 설정:
   - **Name**: `night-watch-admin`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m streamlit run apps/crypto_dashboard.py --server.port $PORT --server.address 0.0.0.0`
   - Render가 `Procfile`의 `web` 명령을 사용할 수도 있음

#### Step 2: 추가 서비스 생성

각 서비스를 별도로 생성:

1. **Main Board** (Web Service)
   - Start Command: `python -m streamlit run apps/night_watch_board.py --server.port $PORT --server.address 0.0.0.0`

2. **User Dashboard** (Web Service)
   - Start Command: `python -m streamlit run apps/simple_user_dashboard.py --server.port $PORT --server.address 0.0.0.0`

3. **Scanner Scheduler** (Background Worker)
   - Start Command: `python services/scanner_scheduler.py start`

4. **Premium Pool Collector** (Background Worker)
   - Start Command: `python services/premium_pool_collector.py --continuous`

---

## ⚙️ 환경 변수 설정

### 공통 환경 변수

모든 서비스에 추가:

```
PYTHONIOENCODING=utf-8
LANG=en_US.UTF-8
LC_ALL=en_US.UTF-8
```

### 선택적 환경 변수

실제 API 키를 사용하려면:

```
# Exchange API Keys
EXCHANGE_API_KEY_GATEIO=your_gateio_key
EXCHANGE_API_SECRET_GATEIO=your_gateio_secret
EXCHANGE_API_KEY_MEXC=your_mexc_key
EXCHANGE_API_SECRET_MEXC=your_mexc_secret

# Blockchain Explorer API Keys
ETHERSCAN_API_KEY=your_etherscan_key
BSCSCAN_API_KEY=your_bscscan_key
```

**코드에서 환경 변수 사용:**

```python
import os

api_key = os.getenv('EXCHANGE_API_KEY_GATEIO', '')
```

---

## 🔍 Render 무료 티어 제한사항

### 제한사항

1. **서비스 시간**
   - 750시간/월 (계정당)
   - 5개 서비스 = 각 150시간/월

2. **비활성화**
   - 15분간 요청이 없으면 서비스 일시 중지
   - 다음 요청 시 자동 재시작 (약 30초 소요)

3. **데이터 영속성**
   - 무료 티어는 데이터 영구 저장 안 됨
   - 서비스 재시작 시 데이터 초기화 가능

### 해결 방법

1. **데이터베이스 사용**
   - Render PostgreSQL 사용 (무료 티어)
   - 또는 외부 데이터베이스 (Supabase, MongoDB 등)

2. **Redis 사용**
   - Render Redis 사용 (무료 티어)
   - 캐시 데이터 저장

3. **정기적 활성화**
   - Cron Job으로 주기적 요청
   - 외부 서비스 사용 (UptimeRobot 등)

---

## 📊 서비스 모니터링

### Render Dashboard

1. **서비스 상태**
   - Dashboard에서 각 서비스 상태 확인
   - 배포 로그 확인

2. **로그 확인**
   - 각 서비스의 "Logs" 탭
   - 실시간 로그 스트리밍

3. **메트릭**
   - CPU, 메모리 사용량
   - 네트워크 트래픽

---

## 🔧 문제 해결

### 서비스가 시작되지 않음

**확인 사항:**
1. `requirements.txt` 확인
2. 시작 명령 확인
3. 로그에서 오류 메시지 확인
4. 환경 변수 확인

### Import 오류

**오류**: `ModuleNotFoundError: No module named 'modules'`

**해결:**
- Python 경로 확인
- `sys.path` 설정 확인
- 상대 경로 import 확인

### 데이터 파일 오류

**오류**: `FileNotFoundError: data/tokens_unified.json`

**해결:**
- 초기 데이터 파일 생성
- 데이터베이스 사용 고려
- 볼륨 마운트 사용 (유료 플랜)

---

## 📝 배포 체크리스트

### 배포 전

- [ ] GitHub 레포지토리에 프로젝트 업로드
- [ ] `render.yaml` 파일 확인
- [ ] `requirements.txt` 루트에 있는지 확인
- [ ] 민감 정보 제거 확인
- [ ] 환경 변수 목록 준비

### 배포 중

- [ ] Blueprint 생성
- [ ] 서비스 자동 생성 확인
- [ ] 환경 변수 설정
- [ ] 빌드 로그 확인

### 배포 후

- [ ] 각 서비스 URL 확인
- [ ] 서비스 접속 테스트
- [ ] 백그라운드 서비스 실행 확인
- [ ] 로그 모니터링 설정

---

## ✅ 완료

Render 배포가 완료되면:
- ✅ 5개 서비스 모두 실행 중
- ✅ 각 서비스 URL 접속 가능
- ✅ 백그라운드 서비스 정상 작동
- ✅ 로그 모니터링 가능

---

## 🔄 업데이트 방법

코드를 수정한 후:

1. **GitHub에 푸시**
   ```bash
   git add .
   git commit -m "Update description"
   git push
   ```

2. **Render 자동 배포**
   - Render가 GitHub 변경사항 자동 감지
   - 자동으로 재배포 시작

3. **수동 배포**
   - Render Dashboard → 서비스 → "Manual Deploy"
   - "Deploy latest commit" 선택

---

## 📞 다음 단계

Render 배포가 완료되면:
1. Vercel 배포 준비 (프론트엔드)
2. Railway 배포 준비 (전체 서비스)
3. 프로덕션 최적화

