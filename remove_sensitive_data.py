#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
민감 정보 제거 스크립트
GitHub 업로드 전에 실제 API 키를 제거합니다.
"""

import json
import os
from pathlib import Path

def remove_sensitive_data():
    """민감 정보 제거"""
    
    print("=" * 60)
    print("[SECURITY] 민감 정보 제거 시작")
    print("=" * 60)
    print()
    
    # exchange_api_keys.json 비우기
    exchange_api_keys_path = Path("config/exchange_api_keys.json")
    if exchange_api_keys_path.exists():
        print("[INFO] exchange_api_keys.json 파일 확인 중...")
        
        # 백업 생성 (안전을 위해)
        backup_path = Path("config/exchange_api_keys.json.backup")
        if not backup_path.exists():
            import shutil
            shutil.copy2(exchange_api_keys_path, backup_path)
            print("[OK] 백업 생성: exchange_api_keys.json.backup")
        
        # 빈 구조로 교체
        empty_structure = {
            "gateio": {"keys": []},
            "mexc": {"keys": []},
            "kucoin": {"keys": []},
            "bitget": {"keys": []},
            "note": "실제 API 키는 Railway 환경 변수나 로컬 설정에서 관리하세요."
        }
        
        with open(exchange_api_keys_path, 'w', encoding='utf-8') as f:
            json.dump(empty_structure, f, indent=2, ensure_ascii=False)
        
        print("[OK] exchange_api_keys.json - 실제 키 제거 완료")
        print("     (예시 파일: exchange_api_keys.json.example 참조)")
    else:
        print("[WARNING] exchange_api_keys.json 파일이 없습니다.")
    
    print()
    
    # api_config.json 비우기
    api_config_path = Path("config/api_config.json")
    if api_config_path.exists():
        print("[INFO] api_config.json 파일 확인 중...")
        
        # 백업 생성
        backup_path = Path("config/api_config.json.backup")
        if not backup_path.exists():
            import shutil
            shutil.copy2(api_config_path, backup_path)
            print("[OK] 백업 생성: api_config.json.backup")
        
        # 빈 구조로 교체
        empty_structure = {
            "etherscan_api_key": "",
            "bscscan_api_key": "",
            "polygonscan_api_key": "",
            "note": "실제 API 키는 Railway 환경 변수나 로컬 설정에서 관리하세요."
        }
        
        with open(api_config_path, 'w', encoding='utf-8') as f:
            json.dump(empty_structure, f, indent=2, ensure_ascii=False)
        
        print("[OK] api_config.json - 실제 키 제거 완료")
        print("     (예시 파일: api_config.json.example 참조)")
    else:
        print("[WARNING] api_config.json 파일이 없습니다.")
    
    print()
    print("=" * 60)
    print("[SUCCESS] 민감 정보 제거 완료!")
    print("=" * 60)
    print()
    print("[INFO] 다음 단계:")
    print("  1. 백업 파일 확인 (필요시 복원)")
    print("  2. Git 커밋 및 푸시")
    print("  3. Railway에서 환경 변수로 실제 키 설정")
    print()
    print("[WARNING] 백업 파일(*.backup)도 .gitignore에 포함되어 있는지 확인하세요!")

if __name__ == "__main__":
    remove_sensitive_data()
