"""
NightWatch Data Manager
Central data access layer with thread-safe operations

This module wraps TokenManager with core module integration
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import sys
import os

# Add parent directory to path for TokenManager import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.token_manager import TokenManager as _TokenManager
from core.config import FilePaths, TokenStatus


class DataManager(_TokenManager):
    """
    Enhanced TokenManager with core module integration

    Features:
    - All TokenManager features (thread-safe, auto-backup, recovery)
    - Integrated with core.config constants
    - Simplified API for common operations
    """

    def __init__(self, db_path: str = None):
        """Initialize with default path from core.config"""
        if db_path is None:
            db_path = FilePaths.TOKENS_UNIFIED
        super().__init__(db_path)

    def get_main_board_tokens(self) -> Dict[str, Any]:
        """Get all tokens in MAIN_BOARD status"""
        db = self._load_db()
        return {
            token_id: token_data
            for token_id, token_data in db.items()
            if token_data.get('lifecycle', {}).get('status') == TokenStatus.MAIN_BOARD
        }

    def get_archived_tokens(self) -> Dict[str, Any]:
        """Get all tokens in ARCHIVED status"""
        db = self._load_db()
        return {
            token_id: token_data
            for token_id, token_data in db.items()
            if token_data.get('lifecycle', {}).get('status') == TokenStatus.ARCHIVED
        }

    def get_tokens_by_status(self, status: str) -> Dict[str, Any]:
        """Get all tokens with given status"""
        db = self._load_db()
        return {
            token_id: token_data
            for token_id, token_data in db.items()
            if token_data.get('lifecycle', {}).get('status') == status
        }

    def get_premium_pool_tokens(self) -> Dict[str, Any]:
        """Get all tokens in premium pool"""
        db = self._load_db()
        return {
            token_id: token_data
            for token_id, token_data in db.items()
            if token_data.get('premium_pool', {}).get('in_pool', False)
        }

    def count_by_status(self) -> Dict[str, int]:
        """Count tokens by lifecycle status"""
        db = self._load_db()
        counts = {}
        for token_data in db.values():
            status = token_data.get('lifecycle', {}).get('status', 'UNKNOWN')
            counts[status] = counts.get(status, 0) + 1
        return counts


# Singleton instance
_data_manager_instance = None

def get_data_manager() -> DataManager:
    """Get or create singleton DataManager instance"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance


if __name__ == "__main__":
    # Test
    dm = get_data_manager()

    print("\n=== DataManager Test ===")
    print(f"Database: {dm.db_path}")

    # Count by status
    counts = dm.count_by_status()
    print(f"\nToken counts by status:")
    for status, count in counts.items():
        print(f"  {status}: {count}")

    # Premium pool
    premium = dm.get_premium_pool_tokens()
    print(f"\nPremium pool tokens: {len(premium)}")

    print("\n✓ DataManager working!")
