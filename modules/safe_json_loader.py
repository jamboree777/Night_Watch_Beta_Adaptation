#!/usr/bin/env python3
"""
Safe JSON Loader with File Locking
모든 JSON 읽기/쓰기를 안전하게 처리
"""
import json
import os
from filelock import FileLock, Timeout
from typing import Dict, Any, Optional

def safe_load_json(filepath: str, default: Any = None, timeout: int = 10) -> Any:
    """
    파일 락을 사용하여 안전하게 JSON 파일 로드

    Args:
        filepath: JSON 파일 경로
        default: 파일이 없거나 손상된 경우 반환할 기본값
        timeout: 락 대기 시간 (초)

    Returns:
        로드된 JSON 데이터 또는 default 값
    """
    if not os.path.exists(filepath):
        return default if default is not None else {}

    lock_file = f"{filepath}.lock"

    try:
        with FileLock(lock_file, timeout=timeout):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Timeout:
        print(f"[WARN] Timeout acquiring lock for {filepath}")
        # Timeout 발생 시 락 없이 읽기 시도 (읽기 전용이므로 상대적으로 안전)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON decode error in {filepath}: {e}")
            return default if default is not None else {}
        except Exception as e:
            print(f"[ERROR] Failed to load {filepath}: {e}")
            return default if default is not None else {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON decode error in {filepath}: {e}")
        return default if default is not None else {}
    except Exception as e:
        print(f"[ERROR] Failed to load {filepath}: {e}")
        return default if default is not None else {}


def safe_save_json(filepath: str, data: Any, indent: int = 2, timeout: int = 30) -> bool:
    """
    파일 락을 사용하여 안전하게 JSON 파일 저장 (Atomic write)

    Args:
        filepath: JSON 파일 경로
        data: 저장할 데이터
        indent: JSON 들여쓰기
        timeout: 락 대기 시간 (초)

    Returns:
        성공 여부
    """
    lock_file = f"{filepath}.lock"
    temp_file = f"{filepath}.tmp"

    try:
        with FileLock(lock_file, timeout=timeout):
            # 1. 임시 파일에 먼저 저장
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)

            # 2. 임시 파일을 원본으로 교체 (atomic operation)
            os.replace(temp_file, filepath)

            return True
    except Timeout:
        print(f"[ERROR] Timeout acquiring lock for {filepath}")
        # 임시 파일 정리
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False
    except Exception as e:
        print(f"[ERROR] Failed to save {filepath}: {e}")
        # 임시 파일 정리
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False


# Convenience function for tokens_unified.json
def load_tokens_unified(default: Optional[Dict] = None) -> Dict:
    """
    tokens_unified.json을 안전하게 로드

    Returns:
        토큰 데이터 딕셔너리
    """
    return safe_load_json('tokens_unified.json', default=default if default is not None else {})


def save_tokens_unified(data: Dict) -> bool:
    """
    tokens_unified.json을 안전하게 저장

    Args:
        data: 저장할 토큰 데이터

    Returns:
        성공 여부
    """
    return safe_save_json('tokens_unified.json', data, indent=2)
