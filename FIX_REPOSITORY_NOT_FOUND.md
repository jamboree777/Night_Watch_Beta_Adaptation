# Repository Not Found 오류 해결 가이드

"repository not found" 오류가 발생했을 때 해결하는 방법입니다.

---

## 🔍 현재 설정 확인

현재 remote 설정:
```
origin: https://github.com/jamboree777/night-watch-beta-adaptation.git
```

---

## 🚨 문제 해결 방법

### 방법 1: GitHub 레포지토리가 없을 때

**문제**: GitHub에 레포지토리를 아직 생성하지 않았습니다.

**해결**:
1. https://github.com 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭
4. "New repository" 선택
5. 레포지토리 정보 입력:
   - **Repository name**: `night-watch-beta-adaptation` (정확히!)
   - **Description**: `나이트와치 베타아답션`
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license**: 모두 체크 해제
6. "Create repository" 클릭

### 방법 2: 레포지토리 이름이 틀렸을 때

**문제**: 레포지토리 이름이 다릅니다.

**확인**:
- GitHub에서 실제 레포지토리 이름 확인
- `night-watch-beta-adaptation` vs `night-watch-beta-adoption` 등

**해결**:
```powershell
# 현재 remote 제거
git remote remove origin

# 올바른 이름으로 다시 추가 (실제 레포지토리 이름으로 변경)
git remote add origin https://github.com/jamboree777/실제레포지토리이름.git
```

### 방법 3: 인증 문제

**문제**: Personal Access Token이 필요합니다.

**해결**:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 설정: `repo` (전체 권한) 체크
4. 토큰 생성 후 복사
5. 푸시 시:
   - Username: `jamboree777`
   - Password: `생성한토큰` (비밀번호가 아님!)

### 방법 4: 레포지토리가 Private일 때

**문제**: Private 레포지토리는 인증이 필요합니다.

**해결**:
- Personal Access Token 사용 (방법 3 참조)

---

## 🔧 빠른 해결 방법

### Step 1: GitHub 레포지토리 확인/생성

1. https://github.com/jamboree777 접속
2. 레포지토리 목록 확인
3. `night-watch-beta-adaptation` 레포지토리가 있는지 확인
4. 없으면 생성

### Step 2: Remote 설정 확인

```powershell
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
git remote -v
```

현재 설정:
```
origin: https://github.com/jamboree777/night-watch-beta-adaptation.git
```

### Step 3: 레포지토리 이름 확인

GitHub에서 실제 레포지토리 이름을 확인하고, 다르면 remote를 수정:

```powershell
# remote 제거
git remote remove origin

# 올바른 이름으로 다시 추가
git remote add origin https://github.com/jamboree777/실제레포지토리이름.git
```

### Step 4: Personal Access Token 사용

```powershell
git push -u origin main
# Username: jamboree777
# Password: [Personal Access Token 입력]
```

---

## ✅ 확인 체크리스트

- [ ] GitHub 레포지토리가 생성되었는지 확인
- [ ] 레포지토리 이름이 정확한지 확인 (`night-watch-beta-adaptation`)
- [ ] GitHub 사용자 이름이 정확한지 확인 (`jamboree777`)
- [ ] Personal Access Token이 생성되었는지 확인
- [ ] Remote URL이 올바른지 확인

---

## 🔄 다시 시도

레포지토리를 생성하고 Personal Access Token을 준비한 후:

```powershell
cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
git push -u origin main
```

---

## 📞 추가 도움

여전히 문제가 발생하면:
1. GitHub 레포지토리 페이지에서 Settings → General → Repository name 확인
2. GitHub 사용자 이름이 `jamboree777`가 맞는지 확인
3. Personal Access Token 권한 확인 (`repo` 권한 필요)

