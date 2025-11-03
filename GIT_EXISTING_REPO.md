# 기존 레포지토리 업데이트 가이드

이미 GitHub에 레포지토리가 있는 경우 업데이트하는 방법입니다.

---

## 📋 상황 확인

현재 `night-watch-deploy` 디렉토리는 상위 디렉토리의 Git 저장소에 포함되어 있습니다.

배포 디렉토리만 별도로 GitHub에 업로드하려면:

---

## 🚀 방법 1: 새 레포지토리로 업로드 (권장)

배포 디렉토리를 **새로운 GitHub 레포지토리**로 업로드합니다.

### Step 1: 배포 디렉토리로 이동

```bash
cd night-watch-deploy
```

### Step 2: Git 초기화 (새로)

```bash
git init
```

### Step 3: 민감 정보 제거

```bash
python remove_sensitive_data.py
```

### Step 4: 파일 추가

```bash
git add .
```

### Step 5: 첫 커밋

```bash
git commit -m "Initial deployment structure"
```

### Step 6: GitHub 레포지토리 생성 (웹 브라우저)

1. https://github.com 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭
4. "New repository" 선택
5. 레포지토리 정보 입력:
   - **Repository name**: `night-watch-deploy` (또는 원하는 이름)
   - **Description**: "Night Watch - Deployment Structure"
   - **Visibility**: Public 또는 Private 선택
   - **README, .gitignore, license**: 모두 체크 해제 (이미 있음)
6. "Create repository" 클릭

### Step 7: GitHub 연결

```bash
# YOUR_USERNAME을 실제 GitHub 사용자 이름으로 변경
git remote add origin https://github.com/YOUR_USERNAME/night-watch-deploy.git
```

### Step 8: 메인 브랜치 설정 및 푸시

```bash
git branch -M main
git push -u origin main
```

---

## 🔄 방법 2: 기존 레포지토리에 추가

기존 레포지토리에 배포 디렉토리를 추가하려면:

### Step 1: 기존 레포지토리 확인

```bash
# 상위 디렉토리에서
cd ..
git remote -v
```

### Step 2: 기존 레포지토리에 배포 디렉토리 추가

```bash
# 상위 디렉토리에서
cd ..
git add night-watch-deploy/
git commit -m "Add deployment structure"
git push
```

---

## ⚠️ 주의사항

### 방법 1 (새 레포지토리) 사용 시

- ✅ 배포 파일만 깔끔하게 관리
- ✅ 배포 전용 레포지토리로 운영
- ⚠️ 두 개의 레포지토리 관리 필요

### 방법 2 (기존 레포지토리) 사용 시

- ✅ 하나의 레포지토리로 통합 관리
- ⚠️ 개발 파일과 배포 파일이 섞임
- ⚠️ 레포지토리가 커짐

---

## 📝 권장 방법

**방법 1 (새 레포지토리)**을 권장합니다:
- 배포 전용으로 관리하기 쉬움
- Render, Vercel, Railway 배포에 적합
- 깔끔한 구조 유지

---

## ✅ 전체 명령어 (방법 1)

```bash
cd night-watch-deploy
python remove_sensitive_data.py
git init
git add .
git commit -m "Initial deployment structure"
git remote add origin https://github.com/YOUR_USERNAME/night-watch-deploy.git
git branch -M main
git push -u origin main
```

**YOUR_USERNAME**을 실제 GitHub 사용자 이름으로 변경하세요!

