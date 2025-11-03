# 배포 플랫폼별 가이드

이 문서는 Render, Vercel, Railway 등 다양한 플랫폼에 배포하는 방법을 안내합니다.

---

## 🎯 현재 지원 플랫폼

### ✅ Render (현재 사용 예정)
- **설정 파일**: `render.yaml` 또는 `Procfile`
- **추천**: `render.yaml` 사용 (여러 서비스 관리 용이)

### ⏳ Vercel (다음 단계)
- **설정 파일**: `vercel.json`
- **주의**: Streamlit 앱은 Vercel에서 제한적 지원

### ⏳ Railway (다음 단계)
- **설정 파일**: `railway.json` 또는 `Procfile`
- **추천**: `railway.json` 사용

---

## 🚀 Render 배포 가이드

### 방법 1: render.yaml 사용 (권장)

1. **Render 대시보드 접속**
   - https://render.com 접속
   - 로그인

2. **새 Blueprint 생성**
   - Dashboard → "New +" → "Blueprint"
   - GitHub 레포지토리 연결
   - `render.yaml` 파일 자동 감지

3. **서비스 확인**
   - 5개 서비스가 자동 생성됨:
     - `night-watch-admin` (Admin Dashboard)
     - `night-watch-main` (Main Board)
     - `night-watch-user` (User Dashboard)
     - `night-watch-scanner` (Worker)
     - `night-watch-collector` (Worker)

4. **환경 변수 설정**
   - 각 서비스의 Settings → Environment Variables
   - 다음 변수 추가:
     ```
     PYTHONIOENCODING=utf-8
     LANG=en_US.UTF-8
     LC_ALL=en_US.UTF-8
     ```

5. **배포 확인**
   - 각 서비스의 URL 확인
   - 서비스 상태 확인

### 방법 2: Procfile 사용

1. **Render 대시보드 접속**
2. **새 Web Service 생성**
   - "New +" → "Web Service"
   - GitHub 레포지토리 연결
   - Render가 `Procfile` 자동 감지

3. **서비스별 생성**
   - Web Service: `web` 명령 사용
   - Background Worker: `worker` 명령 사용 (별도 서비스)
   - Background Worker: `worker2` 명령 사용 (별도 서비스)

---

## ⚡ Vercel 배포 가이드 (다음 단계)

### 주의사항

Vercel은 서버리스 플랫폼이므로:
- ✅ 정적 사이트 및 API 서버에 최적화
- ⚠️ Streamlit 앱은 제한적 지원
- ⚠️ 백그라운드 서비스 (Worker)는 별도 서버 필요

### 배포 방법

1. **Vercel CLI 설치**
   ```bash
   npm i -g vercel
   ```

2. **Vercel 로그인**
   ```bash
   vercel login
   ```

3. **프로젝트 배포**
   ```bash
   cd night-watch-deploy
   vercel
   ```

4. **환경 변수 설정**
   - Vercel Dashboard → Project Settings → Environment Variables
   - 필요한 변수 추가

5. **프로덕션 배포**
   ```bash
   vercel --prod
   ```

### Vercel 제한사항

- ❌ 백그라운드 서비스 지원 안 함 (Worker 필요)
- ❌ 장시간 실행 프로세스 제한
- ✅ 정적 사이트 및 API 서버에 적합

**권장**: Vercel은 프론트엔드만 배포하고, 백그라운드 서비스는 Render 또는 Railway 사용

---

## 🚂 Railway 배포 가이드 (다음 단계)

### 배포 방법

1. **Railway 대시보드 접속**
   - https://railway.app 접속
   - 로그인

2. **새 프로젝트 생성**
   - "New Project" 클릭
   - "Deploy from GitHub repo" 선택
   - GitHub 레포지토리 연결

3. **자동 설정**
   - Railway가 `railway.json` 자동 감지
   - 설정 적용

4. **환경 변수 설정**
   - Project Settings → Variables
   - 다음 변수 추가:
     ```
     PYTHONIOENCODING=utf-8
     LANG=en_US.UTF-8
     LC_ALL=en_US.UTF-8
     ```

5. **서비스 추가**
   - 메인 웹 서비스: `web` (railway.json)
   - 백그라운드 서비스: `worker`, `worker2` (별도 서비스로 생성)

6. **도메인 설정**
   - Settings → Networking
   - Generate Domain 클릭

---

## 📋 플랫폼별 비교

| 기능 | Render | Vercel | Railway |
|------|--------|--------|---------|
| Streamlit 앱 | ✅ 지원 | ⚠️ 제한적 | ✅ 지원 |
| 백그라운드 서비스 | ✅ 지원 | ❌ 미지원 | ✅ 지원 |
| 무료 티어 | ✅ 있음 | ✅ 있음 | ✅ 있음 |
| 설정 파일 | `render.yaml` | `vercel.json` | `railway.json` |
| 여러 서비스 | ✅ 쉬움 | ⚠️ 제한적 | ✅ 쉬움 |
| 데이터베이스 | ✅ 제공 | ✅ 제공 | ✅ 제공 |

---

## 🔧 설정 파일 설명

### render.yaml
- Render 전용 설정 파일
- 여러 서비스를 하나의 파일에서 관리
- 각 서비스별 빌드/시작 명령 설정

### vercel.json
- Vercel 전용 설정 파일
- 서버리스 함수 라우팅 설정
- 환경 변수 설정

### railway.json
- Railway 전용 설정 파일
- 빌드/배포 설정
- 환경 변수 설정

### Procfile
- Render, Railway 모두 지원
- 간단한 서비스 시작 명령 정의

---

## ⚠️ 주의사항

### Render

1. **무료 티어 제한**
   - 750시간/월 (계정당)
   - 서비스가 15분간 비활성화되면 일시 중지
   - 트래픽 발생 시 자동 재시작

2. **환경 변수**
   - 각 서비스별로 개별 설정 필요
   - 공유 환경 변수 사용 가능

3. **데이터 영속성**
   - 무료 티어는 데이터 영구 저장 안 됨
   - Redis, PostgreSQL 등 별도 서비스 필요

### Vercel

1. **Streamlit 제한**
   - Streamlit 앱은 Vercel에 적합하지 않음
   - API 서버만 배포 권장

2. **백그라운드 서비스**
   - Worker 서비스 지원 안 함
   - 별도 서버 필요 (Render/Railway 사용)

### Railway

1. **무료 티어 제한**
   - $5 크레딧/월
   - 사용량에 따라 과금

2. **데이터 영속성**
   - 볼륨 마운트 지원
   - 데이터 영구 저장 가능

---

## 🎯 권장 배포 전략

### 현재 단계 (Render)

```
Render에서:
- Admin Dashboard (Web Service)
- Main Board (Web Service)
- User Dashboard (Web Service)
- Scanner Scheduler (Background Worker)
- Premium Pool Collector (Background Worker)
```

### 다음 단계 (Vercel + Railway)

```
Vercel:
- 프론트엔드 정적 사이트 (향후)

Railway:
- Admin Dashboard (Web Service)
- Main Board (Web Service)
- User Dashboard (Web Service)
- Scanner Scheduler (Background Worker)
- Premium Pool Collector (Background Worker)
```

---

## 📝 배포 체크리스트

### Render 배포 전

- [ ] `render.yaml` 파일 확인
- [ ] `requirements.txt` 루트에 있는지 확인
- [ ] 환경 변수 목록 준비
- [ ] 민감 정보 제거 확인
- [ ] GitHub 레포지토리 준비

### Vercel 배포 전

- [ ] `vercel.json` 파일 확인
- [ ] Streamlit 앱 대신 API 서버로 전환 고려
- [ ] 백그라운드 서비스는 다른 플랫폼 사용 계획

### Railway 배포 전

- [ ] `railway.json` 파일 확인
- [ ] `Procfile` 확인
- [ ] 환경 변수 목록 준비
- [ ] 데이터 볼륨 설정 계획

---

## 🔍 문제 해결

### Render 배포 오류

**오류**: "Build failed"
- `requirements.txt` 확인
- Python 버전 확인
- 빌드 로그 확인

**오류**: "Service not found"
- `render.yaml` 파일 경로 확인
- 서비스 이름 확인

### Vercel 배포 오류

**오류**: "Function timeout"
- Streamlit 앱은 Vercel에 적합하지 않음
- API 서버로 전환 고려

### Railway 배포 오류

**오류**: "Deployment failed"
- `railway.json` 문법 확인
- 빌드 로그 확인
- 환경 변수 확인

---

## ✅ 완료

각 플랫폼별 배포가 완료되면:
- ✅ 서비스 URL 확인
- ✅ 각 서비스 접속 테스트
- ✅ 백그라운드 서비스 실행 확인
- ✅ 로그 모니터링 설정

