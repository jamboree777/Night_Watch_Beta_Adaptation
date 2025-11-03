"""
NightWatch JSON Utilities
통합 JSON 로드/저장 모듈 - Thread-safe, Atomic writes

기존 모듈 통합:
- admin_utils.py → load_json_file(), save_json_file()
- safe_json_loader.py → safe_load_json()

특징:
- Atomic write (파일 손상 방지)
- File locking (동시 접근 방지)
- Automatic backup
- 강력한 에러 핸들링
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import contextmanager
import logging

# Windows에서는 fcntl이 없으므로 대체 구현
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

logger = logging.getLogger(__name__)


# ========================================
# JSONManager 클래스
# ========================================

class JSONManager:
    """
    Thread-safe JSON 파일 관리 클래스

    사용 예:
        # 기본 사용
        manager = JSONManager("data.json")
        data = manager.load()
        data['key'] = 'value'
        manager.save(data)

        # 백업 없이 저장
        manager.save(data, create_backup=False)
    """

    def __init__(
        self,
        file_path: str,
        auto_backup: bool = True,
        backup_suffix: str = ".backup"
    ):
        """
        Args:
            file_path: JSON 파일 경로
            auto_backup: 자동 백업 생성 여부
            backup_suffix: 백업 파일 접미사
        """
        self.file_path = Path(file_path)
        self.auto_backup = auto_backup
        self.backup_suffix = backup_suffix
        self.backup_path = Path(str(self.file_path) + backup_suffix)

    @contextmanager
    def _file_lock(self, file_handle):
        """
        파일 잠금 컨텍스트 매니저

        Unix: fcntl 사용
        Windows: 파일 존재 여부만 체크 (제한적)
        """
        try:
            if HAS_FCNTL:
                fcntl.flock(file_handle, fcntl.LOCK_EX)
            yield file_handle
        finally:
            if HAS_FCNTL:
                fcntl.flock(file_handle, fcntl.LOCK_UN)

    def load(self, default: Optional[Dict] = None) -> Dict[str, Any]:
        """
        JSON 파일 로드 (file locking 포함)

        Args:
            default: 파일이 없을 때 반환할 기본값

        Returns:
            로드된 데이터 (파일 없으면 default 또는 빈 dict)

        Raises:
            json.JSONDecodeError: JSON 파싱 실패
            IOError: 파일 읽기 실패
        """
        if default is None:
            default = {}

        if not self.file_path.exists():
            logger.warning(f"File not found: {self.file_path}, returning default")
            return default

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                with self._file_lock(f):
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data)} items from {self.file_path}")
                    return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {self.file_path}: {e}")
            # 백업이 있으면 백업에서 복구 시도
            if self.backup_path.exists():
                logger.info(f"Attempting to restore from backup: {self.backup_path}")
                return self._load_from_backup()
            raise
        except Exception as e:
            logger.error(f"Error loading {self.file_path}: {e}")
            raise

    def _load_from_backup(self) -> Dict[str, Any]:
        """백업 파일에서 복구"""
        try:
            with open(self.backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Successfully restored from backup")
                return data
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return {}

    def save(
        self,
        data: Dict[str, Any],
        create_backup: Optional[bool] = None,
        indent: int = 2
    ) -> bool:
        """
        JSON 파일 저장 (atomic write + 백업)

        Args:
            data: 저장할 데이터
            create_backup: 백업 생성 여부 (None이면 auto_backup 사용)
            indent: JSON indent 수준

        Returns:
            성공 여부

        Raises:
            IOError: 파일 쓰기 실패
        """
        create_backup = create_backup if create_backup is not None else self.auto_backup

        try:
            # 1. 백업 생성 (기존 파일이 있으면)
            if create_backup and self.file_path.exists():
                try:
                    shutil.copy2(self.file_path, self.backup_path)
                    logger.debug(f"Created backup: {self.backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")

            # 2. Atomic write: 임시 파일에 쓰고 rename
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json.tmp',
                dir=self.file_path.parent
            )

            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=indent, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # 디스크에 강제 write

                # Atomic rename (기존 파일 덮어쓰기)
                temp_path_obj = Path(temp_path)
                temp_path_obj.replace(self.file_path)

                logger.debug(f"Saved {len(data)} items to {self.file_path}")
                return True

            except Exception as e:
                # 실패 시 임시 파일 정리
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                raise

        except Exception as e:
            logger.error(f"Error saving {self.file_path}: {e}")
            return False

    def exists(self) -> bool:
        """파일 존재 여부"""
        return self.file_path.exists()

    def delete(self) -> bool:
        """파일 삭제"""
        try:
            if self.file_path.exists():
                self.file_path.unlink()
                logger.info(f"Deleted {self.file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {self.file_path}: {e}")
            return False

    def get_size(self) -> int:
        """파일 크기 (bytes)"""
        if self.file_path.exists():
            return self.file_path.stat().st_size
        return 0


# ========================================
# 편의 함수 (Convenience Functions)
# ========================================

def load_json(file_path: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    간단한 JSON 로드

    사용 예:
        data = load_json("config.json")
        data = load_json("config.json", default={'key': 'value'})
    """
    return JSONManager(file_path).load(default=default)


def save_json(
    file_path: str,
    data: Dict[str, Any],
    create_backup: bool = True,
    indent: int = 2
) -> bool:
    """
    간단한 JSON 저장

    사용 예:
        save_json("config.json", data)
        save_json("config.json", data, create_backup=False)
    """
    return JSONManager(file_path, auto_backup=create_backup).save(data, indent=indent)


def load_json_safe(file_path: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    안전한 JSON 로드 (에러 발생 시 default 반환)

    사용 예:
        data = load_json_safe("config.json")  # 에러 무시
    """
    try:
        return load_json(file_path, default=default)
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return default or {}


# ========================================
# 호환성 함수 (Backward Compatibility)
# ========================================

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    admin_utils.py 호환 함수

    ⚠️ Deprecated: load_json() 사용 권장
    """
    return load_json(file_path)


def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    admin_utils.py 호환 함수

    ⚠️ Deprecated: save_json() 사용 권장
    """
    return save_json(file_path, data)


def safe_load_json(
    file_path: str,
    default: Optional[Dict] = None,
    create_if_missing: bool = False
) -> Dict[str, Any]:
    """
    safe_json_loader.py 호환 함수

    ⚠️ Deprecated: load_json_safe() 사용 권장
    """
    data = load_json_safe(file_path, default=default)

    # 파일이 없고 생성 요청 시
    if create_if_missing and not Path(file_path).exists() and default:
        save_json(file_path, default)

    return data


# ========================================
# 유틸리티 함수
# ========================================

def validate_json_file(file_path: str) -> bool:
    """
    JSON 파일 유효성 검사

    Returns:
        True: 유효한 JSON
        False: 유효하지 않음
    """
    try:
        load_json(file_path)
        return True
    except:
        return False


def get_json_size_mb(file_path: str) -> float:
    """JSON 파일 크기 (MB)"""
    size_bytes = JSONManager(file_path).get_size()
    return size_bytes / (1024 * 1024)


def backup_json(file_path: str, backup_dir: str = "backups") -> bool:
    """
    JSON 파일 백업 생성

    Args:
        file_path: 원본 파일
        backup_dir: 백업 디렉토리

    Returns:
        성공 여부
    """
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return False

        backup_dir_obj = Path(backup_dir)
        backup_dir_obj.mkdir(exist_ok=True)

        # 타임스탬프 포함 백업 파일명
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path_obj.stem}_{timestamp}{file_path_obj.suffix}"
        backup_path = backup_dir_obj / backup_name

        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to backup {file_path}: {e}")
        return False


# ========================================
# 사용 예제
# ========================================

if __name__ == "__main__":
    # 기본 사용
    print("=== JSON Utils Test ===")

    # 1. 간단한 저장/로드
    test_data = {"name": "NightWatch", "version": "1.0.0", "tokens": 5791}
    save_json("test.json", test_data)
    loaded = load_json("test.json")
    print(f"Loaded: {loaded}")

    # 2. JSONManager 사용
    manager = JSONManager("test.json", auto_backup=True)
    data = manager.load()
    data['updated'] = True
    manager.save(data)

    # 3. 백업 생성
    backup_json("test.json")

    # 4. 유효성 검사
    is_valid = validate_json_file("test.json")
    print(f"Valid: {is_valid}")

    # 5. 파일 크기
    size_mb = get_json_size_mb("test.json")
    print(f"Size: {size_mb:.2f} MB")

    print("✓ All tests passed!")
