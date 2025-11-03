# GitHub 업로드 단계별 가이드

이 가이드는 Night Watch 프로젝트를 GitHub에 업로드하는 방법을 단계별로 안내합니다.

---

## ⚠️ 중요: 업로드 전 확인사항

### 1. 민감 정보 제거

**실행 필수:**
```bash
cd night-watch-deploy
python remove_sensitive_data.py
```

이 스크립트는:
- `config/exchange_api_keys.json`의 실제 API 키 제거
- `config/api_config.json`의 실제 API 키 제거
- 백업 파일 생성 (필요시 복원 가능)

**또는 수동으로:**
- `config/exchange_api_keys.json` 파일 열기
- 실제 API 키를 빈 값 또는 예시 값으로 변경
- `config/api_config.json` 파일 열기
- 실제 API 키를 빈 값 또는 예시 값으로 변경

---

## 📋 단계별 실행

### Step 1: 디렉토리 이동

```bash
cd night-watch-deploy
```

### Step 2: 민감 정보 제거

```bash
python remove_sensitive_data.py
```

### Step 3: Git 초기화

```bash
git init
```

### Step 4: 파일 추가

```bash
git add .
```

### Step 5: 첫 커밋

```bash
git commit -m "Initial deployment structure"
```

### Step 6: GitHub 레포지토리 생성

1. 웹 브라우저에서 https://github.com 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭 → "New repository" 선택
4. 레포지토리 정보 입력:
   - **Repository name**: `night-watch` (또는 원하는 이름)
   - **Description**: "Liquidity Threshold & Delisting Monitoring System"
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license**: 모두 체크 해제 (이미 있음)
5. "Create repository" 클릭

### Step 7: GitHub 연결

```bash
# YOUR_USERNAME을 실제 GitHub 사용자 이름으로 변경
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
```

**GitHub 사용자 이름 확인 방법:**
- GitHub 웹사이트에서 프로필 페이지 확인
- 또는 GitHub 설정에서 확인

### Step 8: 메인 브랜치 설정

```bash
git branch -M main
```

### Step 9: GitHub에 푸시

```bash
git push -u origin main
```

**로그인 정보 입력:**
- GitHub 사용자 이름
- 비밀번호 또는 Personal Access Token

---

## 🔐 Personal Access Token 사용

Git 2FA를 사용하는 경우 Personal Access Token이 필요합니다:

### Token 생성 방법

1. GitHub 웹사이트 접속
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token (classic)" 클릭
4. 권한 설정:
   - `repo` (전체 권한) 체크
5. "Generate token" 클릭
6. 생성된 토큰 복사 (한 번만 표시됨!)

### Token 사용

```bash
git push -u origin main
# Username: YOUR_USERNAME
# Password: YOUR_PERSONAL_ACCESS_TOKEN (비밀번호가 아님!)
```

---

## ✅ 업로드 확인

GitHub 레포지토리 페이지에서 다음이 표시되는지 확인:

- ✅ `apps/` 폴더
- ✅ `services/` 폴더
- ✅ `modules/` 폴더
- ✅ `helpers/` 폴더
- ✅ `collectors/` 폴더
- ✅ `config/` 폴더
- ✅ `core/` 폴더
- ✅ `admin_modules/` 폴더
- ✅ `README.md`
- ✅ `.gitignore`
- ✅ `Procfile`
- ✅ `railway.json`

**확인 사항:**
- ❌ `config/exchange_api_keys.json`에 실제 API 키가 없어야 함
- ❌ `config/api_config.json`에 실제 API 키가 없어야 함
- ✅ `.gitignore`에 민감 파일들이 포함되어 있어야 함

---

## 🔄 업데이트 방법

코드를 수정한 후:

```bash
git add .
git commit -m "Update description"
git push
```

---

## 🐛 문제 해결

### 오류: "remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
```

### 오류: "failed to push"

**해결 방법:**
1. 인터넷 연결 확인
2. GitHub 인증 확인
3. Personal Access Token 확인
4. 레포지토리 권한 확인

### 오류: "Authentication failed"

**해결 방법:**
1. Personal Access Token 사용
2. Token 권한 확인 (`repo` 권한 필요)
3. Token 만료 확인

### 파일이 보이지 않음

**확인 사항:**
1. `.gitignore` 확인 (파일이 제외되어 있는지)
2. `git status` 명령으로 확인
3. `git add .` 명령 실행

---

## 📝 다음 단계

GitHub 업로드가 완료되면:

1. **Railway 배포 준비**
   - Railway 대시보드에서 새 프로젝트 생성
   - GitHub 레포지토리 연결

2. **환경 변수 설정**
   - Railway에서 실제 API 키를 환경 변수로 설정
   - `config/` 파일은 예시 값으로 유지

3. **배포 테스트**
   - 메인보드 접속 확인
   - 유저 대시보드 접속 확인
   - 관리자 대시보드 접속 확인

---

## ⚠️ 보안 주의사항

### 절대 하지 말아야 할 것

- ❌ 실제 API 키를 GitHub에 커밋
- ❌ `.env` 파일을 Git에 추가
- ❌ 실제 사용자 데이터를 GitHub에 업로드
- ❌ 민감한 설정 파일을 공개

### 권장 사항

- ✅ 환경 변수 사용
- ✅ `.gitignore` 확인
- ✅ 예시 파일 사용 (`.example`)
- ✅ Private 레포지토리 사용 (선택사항)

---

## ✅ 완료

GitHub 업로드가 완료되면:
- ✅ 레포지토리 페이지 확인
- ✅ 파일들이 올라갔는지 확인
- ✅ README.md가 제대로 표시되는지 확인

**축하합니다! 🎉**

