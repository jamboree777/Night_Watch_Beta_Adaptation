# Render 서비스 업데이트 - Scan Coordinator 추가

스캔 코디네이터가 추가되었습니다.

---

## ✅ 추가된 서비스

### Scan Coordinator (새로 추가)

- **이름**: `night-watch-coordinator`
- **타입**: Background Worker
- **시작 명령**: `python services/scan_coordinator.py start`
- **역할**: 모든 스캔을 통합 관리 (Regular Scan, Watchlist Scan, Premium Pool 등)

---

## 📋 현재 Render 서비스 구성

### Web Services (3개)

1. **night-watch-admin** - Admin Dashboard
2. **night-watch-main** - Main Board  
3. **night-watch-user** - User Dashboard

### Background Workers (3개)

4. **night-watch-coordinator** ⭐ (새로 추가)
   - Scan Coordinator
   - 통합 스캔 관리

5. **night-watch-scanner**
   - Scanner Scheduler
   - ⚠️ **참고**: `scanner_scheduler.py` 파일이 없을 수 있음

6. **night-watch-collector**
   - Premium Pool Collector

---

## ⚠️ 주의사항

### scanner_scheduler.py 파일 확인

현재 `render.yaml`에 `scanner_scheduler.py`가 포함되어 있지만, 실제 파일이 없을 수 있습니다.

**옵션 1**: `scan_coordinator.py`가 모든 스캔을 관리한다면, `scanner_scheduler.py` 서비스는 제거 가능

**옵션 2**: `scanner_scheduler.py`가 필요하다면, 백업 파일(`scanner_scheduler.py.backup`)을 복사

---

## 🔧 해결 방법

### Option 1: scanner_scheduler.py 서비스 제거 (권장)

`scan_coordinator.py`가 모든 스캔을 통합 관리한다면:

```yaml
# render.yaml에서 다음 서비스 제거
- type: worker
  name: night-watch-scanner
  ...
```

### Option 2: scanner_scheduler.py 파일 복사

백업 파일이 있다면:

```powershell
# 백업 파일을 복사
Copy-Item "scanner_scheduler.py.backup" -Destination "night-watch-deploy\services\scanner_scheduler.py"
```

---

## 📝 업데이트된 render.yaml

현재 `render.yaml`에는 다음 6개 서비스가 포함되어 있습니다:

1. night-watch-admin (Web)
2. night-watch-main (Web)
3. night-watch-user (Web)
4. night-watch-coordinator (Worker) ⭐ 새로 추가
5. night-watch-scanner (Worker) ⚠️ 파일 확인 필요
6. night-watch-collector (Worker)

---

## ✅ 다음 단계

1. **GitHub에 커밋 및 푸시**
   ```powershell
   cd C:\Users\robin\Desktop\NightWatch_v1.0_beta\night-watch-deploy
   git add .
   git commit -m "Add scan coordinator service"
   git push
   ```

2. **Render에서 Blueprint 업데이트**
   - Render Dashboard에서 기존 Blueprint 업데이트
   - 또는 새로 생성

3. **서비스 확인**
   - 6개 서비스가 모두 생성되는지 확인
   - `scanner_scheduler.py` 파일이 없으면 빌드 오류 발생 가능

---

## 🎯 권장 사항

`scan_coordinator.py`가 모든 스캔을 통합 관리한다면, `scanner_scheduler.py` 서비스는 제거하는 것을 권장합니다.

**확인 사항:**
- `scan_coordinator.py`가 Regular Scan, Watchlist Scan, Premium Pool을 모두 관리하는가?
- `scanner_scheduler.py`가 별도로 필요한가?

