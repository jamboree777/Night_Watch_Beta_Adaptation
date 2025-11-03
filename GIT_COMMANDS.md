# Git 초기화 및 GitHub 업로드 명령어

GitHub에 업로드하기 위한 단계별 명령어입니다.

---

## 📋 단계별 명령어

### Step 1: 배포 디렉토리로 이동

```bash
cd night-watch-deploy
```

### Step 2: Git 초기화

```bash
git init
```

### Step 3: 파일 추가

```bash
git add .
```

### Step 4: 첫 커밋

```bash
git commit -m "Initial deployment structure"
```

### Step 5: GitHub 레포지토리 생성 (웹 브라우저)

1. https://github.com 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭
4. "New repository" 선택
5. 레포지토리 정보 입력:
   - **Repository name**: `night-watch` (또는 원하는 이름)
   - **Description**: "Liquidity Threshold & Delisting Monitoring System"
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license**: 모두 체크 해제 (이미 있음)
6. "Create repository" 클릭

### Step 6: GitHub 연결

```bash
# YOUR_USERNAME을 실제 GitHub 사용자 이름으로 변경
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
```

**GitHub 사용자 이름 확인 방법:**
- GitHub 웹사이트에서 프로필 페이지 확인
- 또는 GitHub 설정에서 확인

### Step 7: 메인 브랜치 설정

```bash
git branch -M main
```

### Step 8: GitHub에 푸시

```bash
git push -u origin main
```

GitHub 로그인 정보를 입력하거나, Personal Access Token을 사용하세요.

---

## ⚠️ 중요: 업로드 전 확인

### 민감 정보 제거 (필수!)

```bash
# 배포 디렉토리에서 실행
python remove_sensitive_data.py
```

이 스크립트는:
- `config/exchange_api_keys.json`의 실제 API 키 제거
- `config/api_config.json`의 실제 API 키 제거
- 백업 파일 생성

---

## 🔐 Personal Access Token 사용

Git 2FA를 사용하는 경우 Personal Access Token이 필요합니다:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 설정: `repo` (전체 권한) 체크
4. 토큰 생성 후 복사
5. `git push` 시 비밀번호 대신 토큰 사용

---

## 📝 전체 명령어 (한 번에 복사)

```bash
cd night-watch-deploy
python remove_sensitive_data.py
git init
git add .
git commit -m "Initial deployment structure"
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
git branch -M main
git push -u origin main
```

**YOUR_USERNAME**을 실제 GitHub 사용자 이름으로 변경하세요!

---

## ✅ 확인

GitHub 레포지토리 페이지에서 다음이 표시되는지 확인:
- ✅ `apps/` 폴더
- ✅ `services/` 폴더
- ✅ `modules/` 폴더
- ✅ `config/` 폴더
- ✅ `README.md`
- ✅ `.gitignore`

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

- 인터넷 연결 확인
- GitHub 인증 확인
- Personal Access Token 확인

---

## 📞 참고

자세한 내용은 다음 파일을 참조하세요:
- `GITHUB_UPLOAD_STEPS.md` - 상세 가이드
- `QUICK_START.md` - 빠른 시작 가이드

