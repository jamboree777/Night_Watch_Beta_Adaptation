# 🚀 빠른 시작 가이드

GitHub 업로드를 위한 빠른 명령어입니다.

## 📋 필수 명령어

### 1. Git 초기화
```bash
cd night-watch-deploy
git init
```

### 2. 파일 추가
```bash
git add .
```

### 3. 커밋
```bash
git commit -m "Initial deployment structure"
```

### 4. GitHub 레포지토리 생성
웹 브라우저에서:
1. https://github.com 접속
2. 로그인
3. 우측 상단 "+" 버튼 클릭
4. "New repository" 선택
5. 레포지토리 이름 입력 (예: `night-watch`)
6. "Create repository" 클릭

### 5. GitHub 연결 및 푸시
```bash
# YOUR_USERNAME을 실제 GitHub 사용자 이름으로 변경
git remote add origin https://github.com/YOUR_USERNAME/night-watch.git
git branch -M main
git push -u origin main
```

**참고**: GitHub 사용자 이름을 모르면 GitHub 웹사이트에서 프로필 페이지를 확인하세요.

---

## ⚠️ 업로드 전 확인사항

### 민감 정보 제거 확인

다음 파일들을 확인하세요:

1. **`config/exchange_api_keys.json`**
   ```bash
   # 파일 열어서 실제 API 키 제거 또는 예시 값으로 변경
   ```

2. **`config/api_config.json`**
   ```bash
   # 파일 열어서 실제 API 키 제거 또는 예시 값으로 변경
   ```

3. **`.gitignore` 확인**
   ```bash
   # .gitignore 파일이 민감 파일들을 제외하는지 확인
   ```

---

## 🔍 확인

GitHub 레포지토리 페이지에서 다음이 표시되는지 확인:
- ✅ `apps/` 폴더
- ✅ `services/` 폴더  
- ✅ `modules/` 폴더
- ✅ `config/` 폴더
- ✅ `README.md`
- ✅ `.gitignore`
- ✅ `Procfile`

---

## ❓ 문제가 발생하면

1. **GitHub 로그인 오류**
   - Personal Access Token 사용
   - GitHub → Settings → Developer settings → Personal access tokens

2. **푸시 오류**
   - 인터넷 연결 확인
   - Git 인증 확인

3. **파일이 보이지 않음**
   - `.gitignore` 확인
   - `git status` 명령으로 확인

---

## 📞 다음 단계

GitHub 업로드가 완료되면:
1. Railway 배포 준비
2. 환경 변수 설정
3. 배포 테스트

자세한 내용은 `GITHUB_SETUP.md` 파일을 참조하세요.

