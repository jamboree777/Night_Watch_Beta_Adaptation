# Private 레포지토리 푸시 문제 해결

Private 레포지토리에서 "repository not found" 오류가 발생하는 경우 해결 방법입니다.

---

## 🔍 문제 원인

Private 레포지토리는 인증이 필요합니다:
- Personal Access Token 필요
- 또는 GitHub 인증 설정 필요

---

## 🚀 해결 방법 1: Personal Access Token 사용 (권장)

### Step 1: Personal Access Token 생성

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 설정:
   - ✅ `repo` (전체 권한) 체크
   - ✅ `workflow` (선택사항)
4. "Generate token" 클릭
5. 생성된 토큰 복사 (한 번만 표시됨!)

### Step 2: 푸시 시 토큰 사용

```powershell
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
git push -u origin main
```

입력 시:
- **Username**: `jamboree777`
- **Password**: `생성한 Personal Access Token` (비밀번호가 아님!)

---

## 🔄 해결 방법 2: Public으로 변경 (선택사항)

Private이 불편하다면 Public으로 변경할 수 있습니다.

### Step 1: GitHub에서 레포지토리 설정 변경

1. https://github.com/jamboree777/night-watch-beta-adaptation 접속
2. Settings → General → Danger Zone
3. "Change repository visibility" 클릭
4. "Change visibility" → "Make public" 선택
5. 레포지토리 이름 입력하여 확인

### Step 2: 다시 푸시

```powershell
git push -u origin main
```

Public으로 변경하면 Personal Access Token 없이도 푸시할 수 있습니다.

---

## 🔐 해결 방법 3: Git Credential Manager 설정

Windows에서 Git Credential Manager를 사용하여 자동 인증:

### Step 1: Credential Manager 확인

```powershell
git config --global credential.helper manager-core
```

### Step 2: Personal Access Token 저장

```powershell
git push -u origin main
# Username: jamboree777
# Password: [Personal Access Token]
```

이후부터는 자동으로 인증됩니다.

---

## ⚠️ Private vs Public 선택 가이드

### Private 레포지토리
- ✅ 코드가 공개되지 않음
- ✅ 민감 정보 보호
- ⚠️ Personal Access Token 필요
- ⚠️ 배포 시 인증 필요

### Public 레포지토리
- ✅ Personal Access Token 불필요
- ✅ 배포가 쉬움 (Render, Vercel 등)
- ⚠️ 코드가 공개됨
- ⚠️ 민감 정보 노출 위험 (주의!)

---

## 🎯 권장 사항

### 배포용 레포지토리라면

**Public 권장**:
- 배포 파일만 포함 (민감 정보 제거됨)
- Render, Vercel, Railway 연동이 쉬움
- Personal Access Token 불필요

**Private 유지 시**:
- Personal Access Token 반드시 생성
- 배포 시 인증 설정 필요

---

## 📝 빠른 해결

### 방법 A: Personal Access Token 사용 (Private 유지)

```powershell
# 1. Personal Access Token 생성 (위 방법 참조)

# 2. 푸시
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
git push -u origin main
# Username: jamboree777
# Password: [Personal Access Token]
```

### 방법 B: Public으로 변경 (간단)

1. GitHub → Settings → General → Danger Zone → "Change repository visibility"
2. "Make public" 선택
3. 다시 푸시:

```powershell
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
git push -u origin main
```

---

## ✅ 확인

푸시가 성공하면:
```
Enumerating objects: X, done.
Counting objects: 100% (X/X), done.
Writing objects: 100% (X/X), done.
To https://github.com/jamboree777/night-watch-beta-adaptation.git
 * [new branch]      main -> main
```

---

## 🔍 문제 해결

### 여전히 "repository not found" 오류

1. 레포지토리 이름 확인: `night-watch-beta-adaptation`
2. GitHub 사용자 이름 확인: `jamboree777`
3. Personal Access Token 권한 확인: `repo` 권한 필요
4. Remote URL 확인:

```powershell
git remote -v
```

올바른 URL:
```
origin  https://github.com/jamboree777/night-watch-beta-adaptation.git
```

---

## 💡 추천

배포용 레포지토리이므로 **Public으로 변경**하는 것을 권장합니다:
- 배포 파일만 포함 (민감 정보 제거됨)
- Render, Vercel, Railway 연동이 쉬움
- Personal Access Token 관리 불필요

