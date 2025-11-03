# GitHub 업로드 가이드

이 가이드는 Night Watch 프로젝트를 GitHub에 업로드하는 방법을 안내합니다.

## 📋 사전 준비

1. GitHub 계정이 있어야 합니다
2. Git이 설치되어 있어야 합니다
3. 배포 구조가 생성되어 있어야 합니다 (`night-watch-deploy/`)

---

## 🚀 단계별 가이드

### Step 1: Git 초기화

```bash
cd night-watch-deploy
git init
```

### Step 2: 파일 추가

```bash
git add .
```

### Step 3: 첫 커밋

```bash
git commit -m "Initial deployment structure"
```

### Step 4: GitHub 레포지토리 생성

1. GitHub 웹사이트 (https://github.com) 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭
4. "New repository" 선택
5. 레포지토리 정보 입력:
   - **Repository name**: `night-watch` (또는 원하는 이름)
   - **Description**: "Liquidity Threshold & Delisting Monitoring System"
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license**: 모두 체크 해제 (이미 있음)
6. "Create repository" 클릭

### Step 5: GitHub에 연결

GitHub에서 제공하는 명령어를 사용하거나:

```bash
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
```

**YOUR_USERNAME**을 실제 GitHub 사용자 이름으로 변경하세요.

### Step 6: 메인 브랜치 설정

```bash
git branch -M main
```

### Step 7: GitHub에 푸시

```bash
git push -u origin main
```

GitHub 로그인 정보를 입력하거나, Personal Access Token을 사용하세요.

---

## 🔐 Personal Access Token 설정

Git 2FA를 사용하는 경우 Personal Access Token이 필요합니다:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 설정:
   - `repo` (전체 권한)
4. 토큰 생성 후 복사
5. Git 푸시 시 비밀번호 대신 토큰 사용

---

## ✅ 확인

GitHub 레포지토리 페이지에서 파일들이 올라갔는지 확인하세요:
- ✅ `apps/` 폴더
- ✅ `services/` 폴더
- ✅ `modules/` 폴더
- ✅ `config/` 폴더
- ✅ `README.md`
- ✅ `.gitignore`
- ✅ `Procfile`
- ✅ `railway.json`

---

## ⚠️ 주의사항

### 민감 정보 제거

GitHub에 업로드하기 전에 다음 파일들을 확인하세요:

1. **`config/exchange_api_keys.json`**
   - 실제 API 키 제거
   - 예시 값만 포함

2. **`config/api_config.json`**
   - 실제 API 키 제거
   - 예시 값만 포함

3. **`.env` 파일**
   - `.gitignore`에 포함되어 있어야 함
   - 절대 업로드하지 마세요

### .gitignore 확인

`.gitignore` 파일이 다음을 포함하는지 확인:
- `data/tokens_unified.json`
- `data/users.json`
- `config/exchange_api_keys.json`
- `config/api_config.json`
- `*.log`
- `__pycache__/`

---

## 🔄 업데이트 방법

코드를 수정한 후:

```bash
git add .
git commit -m "Update description"
git push
```

---

## 📞 문제 해결

### 오류: "remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
```

### 오류: "failed to push"

- 인터넷 연결 확인
- GitHub 인증 확인
- Personal Access Token 확인

---

## ✅ 완료

GitHub에 업로드가 완료되면:
1. 레포지토리 페이지 확인
2. 파일들이 올라갔는지 확인
3. README.md가 제대로 표시되는지 확인

다음 단계: Railway 배포

