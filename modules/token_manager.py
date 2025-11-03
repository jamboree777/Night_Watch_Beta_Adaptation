#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Manager - Unified Token Database Management
단일 진실의 원천 (Single Source of Truth)
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock
from filelock import FileLock, Timeout

def safe_print(*args, **kwargs):
    """Streamlit-safe print that won't crash on closed stdout"""
    try:
        print(*args, **kwargs)
    except (ValueError, OSError):
        # stdout is closed (Streamlit context), silently ignore
        pass

class TokenManager:
    """
    모든 토큰 데이터를 통합 관리하는 중앙 관리자
    
    Features:
    - 단일 통합 DB (tokens_unified.json)
    - Thread-safe 업데이트
    - 자동 생명주기 관리
    - 데이터 우선순위 처리
    """
    
    def __init__(self, db_path: str = "data/unified/tokens_unified.json"):
        self.db_path = db_path
        self.lock = Lock()  # Thread-level lock
        self.file_lock = FileLock(f"{db_path}.lock", timeout=30)  # Process-level file lock

        # 필수 필드 정의
        self.REQUIRED_FIELDS = ['token_id', 'exchange', 'symbol', 'lifecycle', 'retention']
        self.REQUIRED_LIFECYCLE_FIELDS = ['status']
        self.REQUIRED_RETENTION_FIELDS = ['created_at', 'last_updated', 'delete_after']
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """DB 파일이 없으면 초기화"""
        if not os.path.exists(self.db_path):
            self._save_db({})
    
    def _load_db(self) -> Dict:
        """
        DB 로드 (손상 감지 및 자동 복구 포함)
        """
        try:
            with self.file_lock:  # Acquire file lock across processes
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)

                # 데이터 무결성 검증
                if not isinstance(db, dict):
                    safe_print(f"[ERROR] DB is not a dictionary, attempting recovery")
                    return self._recover_from_backup()

                # MAIN_BOARD 토큰 수 확인 (급감 감지)
                mb_count = sum(1 for t in db.values() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD')

                # 백업 파일과 비교
                backup_mb_count = self._get_backup_mb_count()
                if backup_mb_count > 0 and mb_count < backup_mb_count * 0.3:
                    safe_print(f"[CRITICAL] MAIN_BOARD tokens dropped from {backup_mb_count} to {mb_count}")
                    safe_print(f"[RECOVERY] Attempting to recover from backup")
                    return self._recover_from_backup()

                return db
            
        except json.JSONDecodeError as e:
            safe_print(f"[ERROR] DB file is corrupted: {e}")
            safe_print(f"[RECOVERY] Attempting to recover from backup")
            return self._recover_from_backup()
        except FileNotFoundError:
            safe_print(f"[WARNING] DB file not found, creating new one")
            return {}
        except Exception as e:
            safe_print(f"[ERROR] Unexpected error loading DB: {e}")
            return self._recover_from_backup()
    
    def _get_backup_mb_count(self) -> int:
        """백업 파일의 MAIN_BOARD 토큰 수 확인"""
        import glob
        backup_files = sorted(glob.glob(f"{self.db_path}.backup_*"), reverse=True)
        
        for backup_file in backup_files[:3]:  # 최근 3개 백업 확인
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_db = json.load(f)
                mb_count = sum(1 for t in backup_db.values() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD')
                if mb_count > 0:
                    return mb_count
            except:
                continue
        return 0
    
    def _create_smart_backup(self):
        """
        스마트 백업 생성 전략:
        1. 시간당 최대 1개 백업만 생성 (불필요한 백업 방지)
        2. 최신 20개 백업만 유지 (디스크 공간 절약)
        3. 중요한 이벤트 백업은 별도 보관
        """
        import shutil
        import glob

        now = datetime.now()
        current_hour = now.strftime("%Y%m%d_%H")

        # 1. 같은 시간대의 백업이 이미 있는지 확인
        hourly_backup_pattern = f"{self.db_path}.backup_{current_hour}*"
        existing_hourly = glob.glob(hourly_backup_pattern)

        if existing_hourly:
            # 이미 이번 시간대 백업이 있으면 생성하지 않음
            return

        # 2. 새 백업 생성
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.db_path}.backup_{timestamp}"

        try:
            shutil.copy2(self.db_path, backup_path)
            # 조용히 백업 (로그 줄이기)
        except Exception as e:
            safe_print(f"[WARNING] Backup failed: {e}")

        # 3. 오래된 백업 정리 (최신 20개만 유지)
        self._cleanup_old_backups(keep_count=20)

    def _cleanup_old_backups(self, keep_count: int = 20):
        """오래된 백업 파일 정리"""
        import glob

        # backup_before_fix 같은 특수 백업은 제외
        backup_pattern = f"{self.db_path}.backup_[0-9]*"
        all_backups = sorted(glob.glob(backup_pattern), reverse=True)

        # 최신 keep_count개를 제외한 나머지 삭제
        backups_to_delete = all_backups[keep_count:]

        for backup_file in backups_to_delete:
            try:
                os.remove(backup_file)
            except Exception as e:
                pass  # 조용히 실패

    def _recover_from_backup(self) -> Dict:
        """
        백업에서 복구 (개선된 로직)
        1. 시간순 역순으로 백업 탐색
        2. 각 백업의 유효성 검증 (JSON 파싱 + MAIN_BOARD 개수)
        3. 가장 최신의 유효한 백업 복구
        """
        import glob
        import shutil

        # 최근 백업 파일 찾기 (숫자로 시작하는 것만 - 시간순)
        backup_pattern = f"{self.db_path}.backup_[0-9]*"
        backup_files = sorted(glob.glob(backup_pattern), reverse=True)

        safe_print(f"[RECOVERY] Found {len(backup_files)} backup files, checking from most recent...")

        for i, backup_file in enumerate(backup_files, 1):
            try:
                if i <= 5 or i % 10 == 0:  # 처음 5개와 10개마다 로그
                    safe_print(f"[RECOVERY] ({i}/{len(backup_files)}) Trying: {os.path.basename(backup_file)}")

                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_db = json.load(f)

                # 백업 검증
                if isinstance(backup_db, dict) and len(backup_db) > 100:  # 최소 100개 토큰 필요
                    mb_count = sum(1 for t in backup_db.values() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD')

                    # MAIN_BOARD가 최소 100개는 있어야 유효한 백업으로 간주
                    if mb_count >= 100:
                        safe_print(f"[RECOVERY] [SUCCESS] Found valid backup #{i}: {os.path.basename(backup_file)}")
                        safe_print(f"[RECOVERY]    Total: {len(backup_db)} tokens, MAIN_BOARD: {mb_count}")

                        # 손상된 파일을 .corrupted로 이동
                        if os.path.exists(self.db_path):
                            corrupted_path = f"{self.db_path}.corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            shutil.move(self.db_path, corrupted_path)
                            safe_print(f"[RECOVERY] Moved corrupted file to: {corrupted_path}")

                        # 백업에서 복구
                        shutil.copy2(backup_file, self.db_path)
                        safe_print(f"[RECOVERY] Successfully recovered from backup!")
                        return backup_db
                    else:
                        if i <= 5:
                            safe_print(f"[RECOVERY] [WARNING] Backup has only {mb_count} MAIN_BOARD tokens, skipping...")
            except Exception as e:
                if i <= 5:
                    safe_print(f"[RECOVERY] [ERROR] Failed: {e}")
                continue
        
        safe_print(f"[RECOVERY] No valid backup found, returning empty DB")
        return {}
    
    def _restore_lifecycle_from_backup(self, token_id: str) -> Optional[Dict]:
        """
        백업 파일에서 특정 토큰의 lifecycle 정보 복원
        
        Returns:
            lifecycle dict if found in backup, None otherwise
        """
        import glob
        
        backup_files = sorted(glob.glob(f"{self.db_path}.backup_*"), reverse=True)
        
        for backup_file in backup_files[:5]:  # 최근 5개 백업 확인
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_db = json.load(f)
                
                if token_id in backup_db:
                    lifecycle = backup_db[token_id].get('lifecycle')
                    if lifecycle and lifecycle.get('status') in ['MAIN_BOARD', 'MONITORING']:
                        # MAIN_BOARD나 MONITORING 상태인 경우만 복원
                        return lifecycle
            except:
                continue
        
        return None
    
    def _save_db(self, db: Dict):
        """
        DB 저장 (자동 백업 + 데이터 무결성 검증 포함)

        CRITICAL: 이 메소드만이 tokens_unified.json을 수정할 수 있습니다!
        """
        import shutil

        with self.file_lock:  # Acquire file lock across processes
            # 1. 데이터 무결성 검증 - MAIN_BOARD 토큰 수 급감 감지
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, 'r', encoding='utf-8') as f:
                        old_db = json.load(f)

                    old_mb_count = sum(1 for t in old_db.values() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD')
                    new_mb_count = sum(1 for t in db.values() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD')

                    # MAIN_BOARD 토큰이 50개 이상 감소하면 경고 및 저장 중단
                    if old_mb_count > 0 and new_mb_count < old_mb_count * 0.5:
                        safe_print(f"[CRITICAL ERROR] MAIN_BOARD token count dropped drastically!")
                        safe_print(f"  Old: {old_mb_count} → New: {new_mb_count}")
                        safe_print(f"  Aborting save to prevent data loss!")
                        safe_print(f"  Please investigate before proceeding.")
                        raise ValueError(f"Data integrity check failed: MAIN_BOARD tokens dropped from {old_mb_count} to {new_mb_count}")
                except json.JSONDecodeError:
                    safe_print(f"[WARNING] Existing DB file is corrupted, proceeding with save")

            # 2. 스마트 백업 생성 (시간별 백업 + 롤링 정책)
            if os.path.exists(self.db_path):
                self._create_smart_backup()

            # 3. 임시 파일에 먼저 쓰기 (atomic write)
            temp_path = f"{self.db_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)

            # 4. 임시 파일을 실제 파일로 이동 (원자적 작업)
            shutil.move(temp_path, self.db_path)
    
    def _make_token_id(self, exchange: str, symbol: str) -> str:
        """토큰 ID 생성"""
        return f"{exchange}_{symbol}".replace('/', '_').lower()
    
    def _validate_token_schema(self, token: Dict) -> bool:
        """토큰 스키마 검증"""
        # 최상위 필수 필드 확인
        for field in self.REQUIRED_FIELDS:
            if field not in token:
                safe_print(f"[WARNING] Schema validation failed: Missing field '{field}'")
                return False
        
        # lifecycle 필수 필드 확인
        if 'lifecycle' in token:
            for field in self.REQUIRED_LIFECYCLE_FIELDS:
                if field not in token['lifecycle']:
                    safe_print(f"[WARNING] Schema validation failed: Missing lifecycle.{field}")
                    return False
        
        # retention 필수 필드 확인
        if 'retention' in token:
            for field in self.REQUIRED_RETENTION_FIELDS:
                if field not in token['retention']:
                    safe_print(f"[WARNING] Schema validation failed: Missing retention.{field}")
                    return False
        
        return True
    
    def update_token(self, 
                    exchange: str, 
                    symbol: str, 
                    data: Dict[str, Any],
                    source: str = "unknown"):
        """
        토큰 데이터 업데이트 (Thread-safe)
        
        Args:
            exchange: 거래소 (e.g., "mexc_assessment", "gateio")
            symbol: 심볼 (e.g., "CREPE/USDT")
            data: 업데이트할 데이터
            source: 데이터 소스 (main_scanner, priority_scanner, watchlist_collector, premium_pool, user_input)
        """
        with self.lock:
            db = self._load_db()
            token_id = self._make_token_id(exchange, symbol)
            now = datetime.now(timezone.utc).isoformat()
            
            # 토큰이 없으면 초기화
            if token_id not in db:
                db[token_id] = self._create_new_token(exchange, symbol)
            
            token = db[token_id]
            
            # 데이터 소스별 업데이트
            if source in ["main_scanner", "priority_scanner"]:
                self._update_scan_data(token, data, source)
            elif source in ["watchlist_collector", "premium_pool"]:
                self._update_snapshot_data(token, data, source)
            elif source == "user_input":
                self._update_admin_manual_data(token, data)
            
            # 마지막 업데이트 시간 (retention 필드 체크)
            if "retention" not in token:
                token["retention"] = {
                    "delete_after": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
                    "last_updated": now
                }
            else:
                token["retention"]["last_updated"] = now
            
            db[token_id] = token
            self._save_db(db)
    
    def _create_new_token(self, exchange: str, symbol: str) -> Dict:
        """
        새 토큰 초기화 (백업에서 lifecycle 정보 복원 시도)
        
        CRITICAL: 백업에 해당 토큰의 lifecycle 정보가 있으면 복원합니다!
        """
        now = datetime.now(timezone.utc).isoformat()
        delete_after = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        token_id = self._make_token_id(exchange, symbol)
        
        # 백업에서 lifecycle 정보 복원 시도
        lifecycle_data = self._restore_lifecycle_from_backup(token_id)
        if lifecycle_data:
            safe_print(f"[RESTORE] Recovered lifecycle for {token_id}: status={lifecycle_data.get('status')}")
        
        return {
            "exchange": exchange,
            "symbol": symbol,
            "token_id": token_id,
            
            "lifecycle": lifecycle_data if lifecycle_data else {
                "status": "NORMAL",
                "main_board_entry": None,
                "main_board_exit": None,
                "archive_entry": None,
                "is_chronic": False,
                "chronic_count": 0
            },
            
            "current_snapshot": {
                "spread_pct": None,
                "depth_2pct": None,
                "volume_24h": None,
                "timestamp": None,
                "source": None,
                "data_quality": "public_api"
            },
            
            "scan_aggregate": {
                "avg_spread_pct": None,
                "avg_depth_2pct": None,
                "avg_volume_24h": None,
                "grade": "N/A",
                "average_risk": 0,
                "violation_rate": 0,
                "last_main_scan": None,
                "last_priority_scan": None,
                "scan_count_120h": 0,
                "violation_count_120h": 0
            },
            
            "tags": {
                "st_tagged": False,
                "innovation_zone": False,
                "assessment_zone": exchange in ("mexc_assessment", "mexc_evaluation"),
                "delisting_risk": False
            },
            
            "premium_pool": {
                "in_pool": False,
                "added_at": None,
                "added_by": None,
                "user_count": 0,
                "last_accessed": None
            },
            
            "watchers": [],
            "watcher_count": 0,
            
            "api_info": {
                "requires_special_api": exchange in ("mexc_assessment", "mexc_evaluation"),
                "admin_api_available": False,
                "public_api_available": True
            },
            
            "admin_manual_data": {},
            
            "retention": {
                "created_at": now,
                "last_updated": now,
                "delete_after": delete_after
            }
        }
    
    def _update_scan_data(self, token: Dict, data: Dict, source: str):
        """스캔 데이터 업데이트 (Main/Priority Scanner)"""
        now = datetime.now(timezone.utc).isoformat()
        
        # 스냅샷 업데이트 (개별 스캔 결과)
        if "spread_pct" in data:
            token["current_snapshot"]["spread_pct"] = data["spread_pct"]
        if "depth_2pct" in data:
            token["current_snapshot"]["depth_2pct"] = data["depth_2pct"]
        if "volume_24h" in data:
            token["current_snapshot"]["volume_24h"] = data["volume_24h"]
        if "grade" in data:
            token["current_snapshot"]["grade"] = data["grade"]  # 마지막 스캔의 실제 grade
        
        token["current_snapshot"]["timestamp"] = now
        token["current_snapshot"]["source"] = source
        token["current_snapshot"]["last_scanned"] = now  # last_scanned도 업데이트
        
        # 집계 데이터 업데이트 (평균)
        scan_agg = token["scan_aggregate"]
        
        if "avg_spread_pct" in data:
            scan_agg["avg_spread_pct"] = data["avg_spread_pct"]
        if "avg_depth_2pct" in data:
            scan_agg["avg_depth_2pct"] = data["avg_depth_2pct"]
        if "avg_volume_24h" in data:
            scan_agg["avg_volume_24h"] = data["avg_volume_24h"]
        if "grade" in data:
            scan_agg["grade"] = data["grade"]
        if "average_risk" in data:
            scan_agg["average_risk"] = data["average_risk"]
        if "violation_rate" in data:
            scan_agg["violation_rate"] = data["violation_rate"]
        
        if source == "main_scanner":
            scan_agg["last_main_scan"] = now
        elif source == "priority_scanner":
            scan_agg["last_priority_scan"] = now
        
        # ST Tag 업데이트
        if "st_tagged" in data:
            token["tags"]["st_tagged"] = data["st_tagged"]
    
    def _update_snapshot_data(self, token: Dict, data: Dict, source: str):
        """스냅샷 데이터 업데이트 (Watchlist/Premium Collector)"""
        now = datetime.now(timezone.utc).isoformat()
        
        token["current_snapshot"]["spread_pct"] = data.get("spread_pct")
        token["current_snapshot"]["depth_2pct"] = data.get("depth_2pct")
        token["current_snapshot"]["volume_24h"] = data.get("volume_24h", 0)
        token["current_snapshot"]["timestamp"] = now
        token["current_snapshot"]["last_scanned"] = now  # 🔧 FIX: last_scanned 추가
        token["current_snapshot"]["source"] = source
        
        # API 품질 표시
        if data.get("used_user_api"):
            token["current_snapshot"]["data_quality"] = "user_api"
        elif data.get("used_admin_api"):
            token["current_snapshot"]["data_quality"] = "admin_api"
        else:
            token["current_snapshot"]["data_quality"] = "public_api"
    
    def _update_admin_manual_data(self, token: Dict, data: Dict):
        """관리자 수동 입력 업데이트"""
        # lifecycle과 monitoring 필드를 직접 업데이트
        if "lifecycle" in data:
            if "lifecycle" not in token:
                token["lifecycle"] = {}
            token["lifecycle"].update(data["lifecycle"])
        
        if "monitoring" in data:
            if "monitoring" not in token:
                token["monitoring"] = {}
            token["monitoring"].update(data["monitoring"])
        
        # 기존 admin_manual_data도 업데이트
        if "admin_manual_data" not in token:
            token["admin_manual_data"] = {}
        token["admin_manual_data"].update(data)
    
    def get_token(self, exchange: str, symbol: str) -> Optional[Dict]:
        """토큰 정보 조회 (exchange와 symbol로)"""
        with self.lock:
            db = self._load_db()
            token_id = self._make_token_id(exchange, symbol)
            return db.get(token_id)
    
    def get_token_by_id(self, token_id: str) -> Optional[Dict]:
        """토큰 정보 조회 (token_id로 직접)"""
        with self.lock:
            db = self._load_db()
            return db.get(token_id)
    
    def get_all_tokens(self, filter_status: Optional[str] = None) -> Dict[str, Dict]:
        """모든 토큰 조회"""
        with self.lock:
            db = self._load_db()
            
            if filter_status:
                return {
                    k: v for k, v in db.items()
                    if v["lifecycle"]["status"] == filter_status
                }
            
            return db
    
    def add_watcher(self, exchange: str, symbol: str, user_id: str):
        """와치리스트에 사용자 추가"""
        with self.lock:
            db = self._load_db()
            token_id = self._make_token_id(exchange, symbol)
            
            if token_id not in db:
                db[token_id] = self._create_new_token(exchange, symbol)
            
            token = db[token_id]
            
            if user_id not in token["watchers"]:
                token["watchers"].append(user_id)
                token["watcher_count"] = len(token["watchers"])
            
            self._save_db(db)
    
    def remove_watcher(self, exchange: str, symbol: str, user_id: str):
        """와치리스트에서 사용자 제거"""
        with self.lock:
            db = self._load_db()
            token_id = self._make_token_id(exchange, symbol)
            
            if token_id in db:
                token = db[token_id]
                if user_id in token["watchers"]:
                    token["watchers"].remove(user_id)
                    token["watcher_count"] = len(token["watchers"])
                
                self._save_db(db)
    
    def update_lifecycle_status(self, exchange: str, symbol: str, new_status: str, reason: str = ""):
        """생명주기 상태 변경"""
        with self.lock:
            db = self._load_db()
            token_id = self._make_token_id(exchange, symbol)
            
            if token_id not in db:
                return
            
            token = db[token_id]
            now = datetime.now(timezone.utc).isoformat()
            lifecycle = token["lifecycle"]
            old_status = lifecycle["status"]
            
            lifecycle["status"] = new_status
            
            # 상태별 타임스탬프 업데이트
            if new_status == "MAIN_BOARD" and old_status != "MAIN_BOARD":
                lifecycle["main_board_entry"] = now
            elif new_status == "ARCHIVED":
                lifecycle["main_board_exit"] = now
                lifecycle["archive_entry"] = now
                
                # Chronic 체크 (90일 이내 재진입)
                if lifecycle["main_board_entry"]:
                    try:
                        entry_time = datetime.fromisoformat(lifecycle["main_board_entry"].replace('Z', '+00:00'))
                        if (datetime.now(timezone.utc) - entry_time).days <= 90:
                            lifecycle["is_chronic"] = True
                            lifecycle["chronic_count"] += 1
                    except:
                        pass
            
            self._save_db(db)
    
    def add_to_premium_pool(self, token_id: str, added_by: str = "admin"):
        """프리미엄 풀에 추가 (token_id 사용)"""
        with self.lock:
            db = self._load_db()
            
            if token_id not in db:
                safe_print(f"[WARN] Token {token_id} not found in database, cannot add to premium pool")
                return False
            
            token = db[token_id]
            now = datetime.now(timezone.utc).isoformat()
            
            token["premium_pool"]["in_pool"] = True
            token["premium_pool"]["added_at"] = now
            token["premium_pool"]["added_by"] = added_by
            token["premium_pool"]["last_accessed"] = now
            
            self._save_db(db)
            return True
    
    def remove_from_premium_pool(self, token_id: str):
        """프리미엄 풀에서 제거 (token_id 사용)"""
        with self.lock:
            db = self._load_db()
            
            if token_id in db:
                token = db[token_id]
                token["premium_pool"]["in_pool"] = False
                
                self._save_db(db)
                return True
            return False
    
    def get_premium_pool_tokens(self) -> Dict[str, Dict]:
        """프리미엄 풀 토큰 목록 (token_id: token_data 형식)"""
        with self.lock:
            db = self._load_db()
            return {
                token_id: token_data
                for token_id, token_data in db.items()
                if token_data.get("premium_pool", {}).get("in_pool", False)
            }
    
    def get_watchlist_stats(self) -> Dict[str, int]:
        """와치리스트 통계 (token_id: watcher_count)"""
        with self.lock:
            db = self._load_db()
            stats = {}
            for token_id, token_data in db.items():
                watchers = token_data.get('watchers', [])
                if watchers:
                    stats[token_id] = len(watchers)
            return stats
    
    def cleanup_old_tokens(self):
        """오래된 토큰 삭제 (90일 이상)"""
        with self.lock:
            db = self._load_db()
            now = datetime.now(timezone.utc)
            to_delete = []
            
            for token_id, token in db.items():
                try:
                    delete_after = datetime.fromisoformat(token["retention"]["delete_after"].replace('Z', '+00:00'))
                    
                    # 삭제 조건: 
                    # 1. 90일 경과
                    # 2. 와치리스트에 없음
                    # 3. 프리미엄 풀에 없음
                    if (now > delete_after and 
                        token["watcher_count"] == 0 and 
                        not token["premium_pool"]["in_pool"]):
                        to_delete.append(token_id)
                except:
                    continue
            
            for token_id in to_delete:
                del db[token_id]
            
            if to_delete:
                self._save_db(db)
                safe_print(f"[TOKEN MANAGER] [CLEANUP] Cleaned up {len(to_delete)} old tokens")
            
            return len(to_delete)


# Global instance
_token_manager = None

def get_token_manager() -> TokenManager:
    """싱글톤 인스턴스 반환"""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager

