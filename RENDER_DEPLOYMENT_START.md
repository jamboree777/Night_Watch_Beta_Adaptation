# Render 배포 시작 가이드

GitHub 업로드가 완료되었으니 이제 Render에 배포합니다.

---

## 🎉 GitHub 업로드 완료!

레포지토리: https://github.com/jamboree777/Night_Watch_Beta_Adaptation

---

## 🚀 Render 배포 단계

### Step 1: Render 계정 생성/로그인

1. https://render.com 접속
2. "Get Started for Free" 클릭
3. GitHub 계정으로 로그인 (권장)

### Step 2: 새 Blueprint 생성

1. Render Dashboard에서 "New +" 버튼 클릭
2. "Blueprint" 선택
3. GitHub 레포지토리 연결:
   - "Connect GitHub" 클릭 (처음 한 번만)
   - 레포지토리 선택: `Night_Watch_Beta_Adaptation`
   - "Connect" 클릭

### Step 3: Blueprint 적용

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

### Step 4: 환경 변수 설정

각 서비스의 Settings → Environment Variables에서 다음 변수를 추가:

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

### Step 5: 배포 확인

1. 각 서비스의 "Events" 탭에서 배포 진행 상황 확인
2. 배포 완료 후 서비스 URL 확인
3. 각 URL 접속하여 서비스 정상 작동 확인

---

## 📋 Render 배포 체크리스트

### 배포 전

- [x] GitHub 레포지토리 업로드 완료
- [ ] Render 계정 생성/로그인
- [ ] GitHub 레포지토리 연결

### 배포 중

- [ ] Blueprint 생성
- [ ] 5개 서비스 자동 생성 확인
- [ ] 환경 변수 설정
- [ ] 빌드 로그 확인

### 배포 후

- [ ] 각 서비스 URL 확인
- [ ] 서비스 접속 테스트
- [ ] 백그라운드 서비스 실행 확인
- [ ] 로그 모니터링 설정

---

## ⚠️ Render 무료 티어 제한사항

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

## 🔍 문제 해결

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

## 📝 다음 단계

Render 배포가 완료되면:

1. **Vercel 배포 준비** (다음 단계)
2. **Railway 배포 준비** (다음 단계)
3. **프로덕션 최적화**

---

## ✅ 완료

Render 배포가 완료되면:
- ✅ 5개 서비스 모두 실행 중
- ✅ 각 서비스 URL 접속 가능
- ✅ 백그라운드 서비스 정상 작동
- ✅ 로그 모니터링 가능

**축하합니다! 🎉**

---

## 📞 참고 문서

자세한 내용은 다음 파일을 참조하세요:
- `RENDER_DEPLOYMENT.md` - Render 배포 상세 가이드
- `DEPLOYMENT_PLATFORMS.md` - 플랫폼별 비교 및 가이드

