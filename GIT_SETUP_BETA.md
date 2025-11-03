# Night Watch Beta Adaptation - GitHub 업로드 가이드

**레포지토리 이름**: `night-watch-beta-adaptation`  
**제목**: 나이트와치 베타아답션

---

## 📋 단계별 명령어

### Step 1: 배포 디렉토리로 이동

```powershell
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
```

### Step 2: 민감 정보 제거 (중요!)

```powershell
python remove_sensitive_data.py
```

### Step 3: Git 초기화

```powershell
git init
```

### Step 4: 파일 추가

```powershell
git add .
```

### Step 5: 첫 커밋

```powershell
git commit -m "Initial deployment structure - Night Watch Beta Adaptation"
```

### Step 6: GitHub 레포지토리 생성 (웹 브라우저)

1. https://github.com 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭
4. "New repository" 선택
5. 레포지토리 정보 입력:
   - **Repository name**: `night-watch-beta-adaptation`
   - **Description**: `나이트와치 베타아답션 - Liquidity Threshold & Delisting Monitoring System`
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license**: 모두 체크 해제 (이미 있음)
6. "Create repository" 클릭

### Step 7: GitHub 연결

```powershell
# YOUR_USERNAME을 실제 GitHub 사용자 이름으로 변경
git remote add origin https://github.com/YOUR_USERNAME/night-watch-beta-adaptation.git
```

### Step 8: 메인 브랜치 설정

```powershell
git branch -M main
```

### Step 9: GitHub에 푸시

```powershell
git push -u origin main
```

GitHub 로그인 정보를 입력하거나, Personal Access Token을 사용하세요.

---

## 🔐 Personal Access Token 사용

Git 2FA를 사용하는 경우:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 설정: `repo` (전체 권한) 체크
4. 토큰 생성 후 복사
5. `git push` 시 비밀번호 대신 토큰 사용

---

## 📝 전체 명령어 (한 번에 복사)

```powershell
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
python remove_sensitive_data.py
git init
git add .
git commit -m "Initial deployment structure - Night Watch Beta Adaptation"
git remote add origin https://github.com/YOUR_USERNAME/night-watch-beta-adaptation.git
git branch -M main
git push -u origin main
```

**⚠️ 중요**: `YOUR_USERNAME`을 실제 GitHub 사용자 이름으로 변경하세요!

---

## ✅ 확인

GitHub 레포지토리 페이지에서 다음이 표시되는지 확인:
- ✅ `apps/` 폴더
- ✅ `services/` 폴더
- ✅ `modules/` 폴더
- ✅ `config/` 폴더
- ✅ `README.md` (제목: "Night Watch Beta Adaptation")
- ✅ `.gitignore`
- ✅ `render.yaml`
- ✅ `vercel.json`
- ✅ `railway.json`

레포지토리 주소: `https://github.com/YOUR_USERNAME/night-watch-beta-adaptation`

---

## 🔄 업데이트 방법

코드를 수정한 후:

```powershell
git add .
git commit -m "Update description"
git push
```

---

## 🐛 문제 해결

### 오류: "remote origin already exists"

```powershell
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/night-watch-beta-adaptation.git
```

### 오류: "failed to push"

- 인터넷 연결 확인
- GitHub 인증 확인
- Personal Access Token 확인

---

## 📞 다음 단계

GitHub 업로드가 완료되면:
1. Render 배포 준비
2. Vercel 배포 준비 (다음 단계)
3. Railway 배포 준비 (다음 단계)

