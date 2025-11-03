#!/usr/bin/env python3
"""
Shard Manager - Isolated Write Operations
각 스캐너가 독립된 파일에 쓰기를 수행
"""

import json
import os
from pathlib import Path
from filelock import FileLock
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class ShardManager:
    """
    각 스캔 타입별로 독립된 파일(shard)을 관리
    동시 쓰기 충돌 제거
    """

    # Shard 타입 정의
    SHARD_REGULAR_SCAN = "regular_scan"
    SHARD_PREMIUM_POOL = "premium_pool"

    def __init__(self, base_dir: str = "data/shards"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Shard 파일 경로
        self.shards = {
            self.SHARD_REGULAR_SCAN: self.base_dir / "regular_scan.json",
            self.SHARD_PREMIUM_POOL: self.base_dir / "premium_pool.json"
        }

        # 각 shard 초기화
        for shard_path in self.shards.values():
            if not shard_path.exists():
                self._save_shard(shard_path, {})

    def _load_shard(self, shard_path: Path) -> Dict:
        """Shard 파일 로드"""
        try:
            with open(shard_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_shard(self, shard_path: Path, data: Dict):
        """Shard 파일 저장 (atomic write)"""
        temp_path = shard_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(shard_path)

    def update_regular_scan(self, token_id: str, scan_data: Dict[str, Any]):
        """
        정규 스캔 데이터 업데이트
        batch_scanner.py에서 사용

        Args:
            token_id: 토큰 ID (e.g., "gateio_btc_usdt")
            scan_data: 스캔 결과 데이터
        """
        shard_path = self.shards[self.SHARD_REGULAR_SCAN]
        lock_path = str(shard_path) + ".lock"

        with FileLock(lock_path, timeout=10):
            data = self._load_shard(shard_path)

            # 기존 토큰 데이터 가져오기 or 새로 생성
            if token_id not in data:
                data[token_id] = {
                    'token_id': token_id,
                    'exchange': scan_data.get('exchange'),
                    'symbol': scan_data.get('symbol'),
                }

            # scan_aggregate 업데이트
            if 'scan_aggregate' not in data[token_id]:
                data[token_id]['scan_aggregate'] = {}

            data[token_id]['scan_aggregate'].update(scan_data.get('scan_aggregate', {}))
            data[token_id]['scan_aggregate']['last_updated'] = datetime.now(timezone.utc).isoformat()

            # 다른 필드도 업데이트
            for key, value in scan_data.items():
                if key not in ['token_id', 'exchange', 'symbol', 'scan_aggregate']:
                    data[token_id][key] = value

            self._save_shard(shard_path, data)

    def update_premium_pool(self, token_id: str, snapshot_data: Dict[str, Any]):
        """
        프리미엄 풀 스냅샷 업데이트
        premium_pool_collector.py에서 사용

        Args:
            token_id: 토큰 ID
            snapshot_data: 스냅샷 데이터
        """
        shard_path = self.shards[self.SHARD_PREMIUM_POOL]
        lock_path = str(shard_path) + ".lock"

        with FileLock(lock_path, timeout=10):
            data = self._load_shard(shard_path)

            if token_id not in data:
                data[token_id] = {
                    'token_id': token_id,
                    'exchange': snapshot_data.get('exchange'),
                    'symbol': snapshot_data.get('symbol'),
                }

            # current_snapshot 업데이트
            if 'current_snapshot' not in data[token_id]:
                data[token_id]['current_snapshot'] = {}

            data[token_id]['current_snapshot'].update(snapshot_data.get('current_snapshot', {}))
            data[token_id]['current_snapshot']['timestamp'] = datetime.now(timezone.utc).isoformat()

            # 다른 필드도 업데이트
            for key, value in snapshot_data.items():
                if key not in ['token_id', 'exchange', 'symbol', 'current_snapshot']:
                    data[token_id][key] = value

            self._save_shard(shard_path, data)

    def get_shard_data(self, shard_type: str) -> Dict:
        """특정 shard의 전체 데이터 읽기"""
        if shard_type not in self.shards:
            raise ValueError(f"Unknown shard type: {shard_type}")

        shard_path = self.shards[shard_type]
        lock_path = str(shard_path) + ".lock"

        with FileLock(lock_path, timeout=5):
            return self._load_shard(shard_path)

    def bulk_update_regular_scan(self, tokens_data: Dict[str, Dict]):
        """
        정규 스캔 대량 업데이트
        batch_scanner.py의 한 번의 스캔에서 모든 토큰 업데이트
        """
        shard_path = self.shards[self.SHARD_REGULAR_SCAN]
        lock_path = str(shard_path) + ".lock"

        with FileLock(lock_path, timeout=30):
            data = self._load_shard(shard_path)
            timestamp = datetime.now(timezone.utc).isoformat()

            for token_id, token_data in tokens_data.items():
                if token_id not in data:
                    data[token_id] = {
                        'token_id': token_id,
                        'exchange': token_data.get('exchange'),
                        'symbol': token_data.get('symbol'),
                    }

                # scan_aggregate 업데이트
                if 'scan_aggregate' not in data[token_id]:
                    data[token_id]['scan_aggregate'] = {}

                data[token_id]['scan_aggregate'].update(token_data.get('scan_aggregate', {}))
                data[token_id]['scan_aggregate']['last_updated'] = timestamp

                # 다른 필드
                for key, value in token_data.items():
                    if key not in ['token_id', 'exchange', 'symbol', 'scan_aggregate']:
                        data[token_id][key] = value

            self._save_shard(shard_path, data)
            print(f"[SHARD] Updated regular_scan shard: {len(tokens_data)} tokens")


# Singleton instance
_shard_manager_instance = None

def get_shard_manager() -> ShardManager:
    """ShardManager 싱글톤 인스턴스 반환"""
    global _shard_manager_instance
    if _shard_manager_instance is None:
        _shard_manager_instance = ShardManager()
    return _shard_manager_instance
