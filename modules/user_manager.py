"""
Night Watch - User Management System
Handles user data, watchlists, and subscription tiers
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from modules.token_manager import TokenManager

class UserManager:
    """Manage user data and settings"""
    
    def __init__(self, users_dir="users"):
        self.users_dir = users_dir
        self.ensure_users_directory()
        self.token_manager = TokenManager()
    
    def ensure_users_directory(self):
        """Create users directory structure if it doesn't exist"""
        os.makedirs(self.users_dir, exist_ok=True)
    
    def get_user_dir(self, user_id: str) -> str:
        """Get user's data directory path"""
        user_dir = os.path.join(self.users_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile and subscription info"""
        user_dir = self.get_user_dir(user_id)
        profile_path = os.path.join(user_dir, "profile.json")
        
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Default profile for new users
        default_profile = {
            "user_id": user_id,
            "subscription": "free",  # or "premium"
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "theme": "dark",
                "notifications_enabled": True,
                "telegram_chat_id": None
            }
        }
        
        # Save default profile
        self.save_user_profile(user_id, default_profile)
        return default_profile
    
    def save_user_profile(self, user_id: str, profile: Dict):
        """Save user profile"""
        user_dir = self.get_user_dir(user_id)
        profile_path = os.path.join(user_dir, "profile.json")
        
        profile["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
    
    def get_user_watchlist(self, user_id: str) -> List[Dict]:
        """Get user's watchlist from users.json"""
        users_file = "data/users.json"
        
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
                
                # Find user (case-insensitive)
                user_data = users.get(user_id) or users.get(user_id.lower())
                
                if user_data:
                    return user_data.get('watchlist', [])
            except Exception as e:
                print(f"[ERROR] Failed to load watchlist for {user_id}: {e}")
        
        # Fallback: Check old system (users/<user_id>/watchlist.json)
        user_dir = self.get_user_dir(user_id)
        watchlist_path = os.path.join(user_dir, "watchlist.json")
        
        if os.path.exists(watchlist_path):
            try:
                with open(watchlist_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return []
    
    def save_user_watchlist(self, user_id: str, watchlist: List[Dict]):
        """Save user's watchlist to users.json"""
        # Don't save watchlist for guest users
        if user_id in ('guest', 'demo_free'):
            return
        
        users_file = "data/users.json"
        
        # Load users
        users = {}
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        
        # Find user (case-insensitive)
        user_key = None
        for key in users.keys():
            if key.lower() == user_id.lower():
                user_key = key
                break
        
        if not user_key:
            # User doesn't exist - create new user entry
            print(f"[INFO] Creating new user entry for {user_id}")
            user_key = user_id
            users[user_key] = {
                "telegram_id": user_id,
                "username": user_id,
                "tier": "free",
                "watchlist": [],
                "api_keys": {},
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Update watchlist
        users[user_key]['watchlist'] = watchlist
        
        # Save
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    
    def add_to_watchlist(self, user_id: str, exchange: str, symbol: str) -> bool:
        """Add token to user's watchlist"""
        print(f"[DEBUG] add_to_watchlist called: user_id={user_id}, exchange={exchange}, symbol={symbol}")
        
        watchlist = self.get_user_watchlist(user_id)
        profile = self.get_user_profile(user_id)
        
        # Get tier-specific limit from subscription_config.json
        max_tokens = self.get_watchlist_limit(user_id)
        print(f"[DEBUG] Current watchlist size: {len(watchlist)}, Max: {max_tokens}")
        
        # Check if already in watchlist
        token_id = f"{exchange}_{symbol.replace('/', '_').lower()}"
        for item in watchlist:
            if item.get("token_id") == token_id:
                print(f"[DEBUG] Token {token_id} already in watchlist")
                return False  # Already exists
        
        # Check limit
        if len(watchlist) >= max_tokens:
            print(f"[DEBUG] Watchlist limit reached: {len(watchlist)}/{max_tokens}")
            return False  # Limit reached
        
        # Add to watchlist
        new_item = {
            "exchange": exchange,
            "symbol": symbol,
            "token_id": token_id,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        watchlist.append(new_item)
        print(f"[DEBUG] Adding token to watchlist: {new_item}")
        
        self.save_user_watchlist(user_id, watchlist)
        print(f"[DEBUG] Watchlist saved successfully for {user_id}")
        
        # Update watchers in tokens_unified.json
        try:
            self.token_manager.add_watcher(exchange, symbol, user_id)
            print(f"[DEBUG] Added watcher {user_id} to token {token_id} in tokens_unified.json")
        except Exception as e:
            print(f"[WARN] Failed to update watchers in tokens_unified.json: {e}")
        
        # Auto-add to Premium Pool for Pro/Premium users
        user_tier = profile.get('tier', 'free')
        if user_tier in ['pro', 'premium']:
            try:
                self.token_manager.add_to_premium_pool(exchange, symbol)
                print(f"[DEBUG] Auto-added {token_id} to Premium Pool for {user_tier} user {user_id}")
            except Exception as e:
                print(f"[WARN] Failed to add to Premium Pool: {e}")
        
        return True
    
    def remove_from_watchlist(self, user_id: str, token_id: str) -> bool:
        """Remove token from user's watchlist"""
        watchlist = self.get_user_watchlist(user_id)
        
        # Find the token to get exchange and symbol
        token_item = None
        for item in watchlist:
            if item.get("token_id") == token_id:
                token_item = item
                break
        
        # Filter out the token
        new_watchlist = [item for item in watchlist if item.get("token_id") != token_id]
        
        if len(new_watchlist) < len(watchlist):
            self.save_user_watchlist(user_id, new_watchlist)
            
            # Update watchers in tokens_unified.json
            if token_item:
                try:
                    exchange = token_item.get("exchange")
                    symbol = token_item.get("symbol")
                    self.token_manager.remove_watcher(exchange, symbol, user_id)
                    print(f"[DEBUG] Removed watcher {user_id} from token {token_id} in tokens_unified.json")
                    
                    # Check if any Pro/Premium users still have this token in watchlist
                    # If not, remove from Premium Pool
                    profile = self.get_user_profile(user_id)
                    user_tier = profile.get('tier', 'free')
                    if user_tier in ['pro', 'premium']:
                        # Check if other pro/premium users have this token
                        has_other_premium_watchers = False
                        users_file = os.path.join(self.users_dir, "..", "data/users.json")
                        if os.path.exists(users_file):
                            with open(users_file, 'r', encoding='utf-8') as f:
                                all_users = json.load(f)
                            for uid, udata in all_users.items():
                                if uid != user_id and udata.get('tier') in ['pro', 'premium']:
                                    for item in udata.get('watchlist', []):
                                        if item.get('token_id') == token_id:
                                            has_other_premium_watchers = True
                                            break
                                if has_other_premium_watchers:
                                    break
                        
                        if not has_other_premium_watchers:
                            try:
                                self.token_manager.remove_from_premium_pool(exchange, symbol)
                                print(f"[DEBUG] Removed {token_id} from Premium Pool (no more premium watchers)")
                            except Exception as e:
                                print(f"[WARN] Failed to remove from Premium Pool: {e}")
                
                except Exception as e:
                    print(f"[WARN] Failed to update watchers in tokens_unified.json: {e}")
            
            return True
        
        return False
    
    def clear_watchlist(self, user_id: str):
        """Clear user's entire watchlist"""
        watchlist = self.get_user_watchlist(user_id)
        
        # Remove watcher from all tokens in tokens_unified.json
        for item in watchlist:
            try:
                exchange = item.get("exchange")
                symbol = item.get("symbol")
                token_id = item.get("token_id")
                self.token_manager.remove_watcher(exchange, symbol, user_id)
                print(f"[DEBUG] Removed watcher {user_id} from token {token_id} in tokens_unified.json")
            except Exception as e:
                print(f"[WARN] Failed to remove watcher for {item.get('token_id')}: {e}")
        
        self.save_user_watchlist(user_id, [])
    
    def is_premium(self, user_id: str) -> bool:
        """Check if user has premium subscription"""
        profile = self.get_user_profile(user_id)
        return profile.get("subscription") == "premium"
    
    def get_watchlist_limit(self, user_id: str) -> int:
        """Get max watchlist size for user based on tier from subscription_config.json"""
        # Load subscription config
        config_file = "config/subscription_config.json"
        default_limits = {
            'free': 4,
            'pro': 20,
            'premium': 100
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_limits['free'] = config.get('free', {}).get('watchlist_limit', 4)
                    default_limits['pro'] = config.get('pro', {}).get('watchlist_limit', 20)
                    default_limits['premium'] = config.get('premium', {}).get('watchlist_limit', 100)
            except:
                pass
        
        # users.json에서 tier 확인
        users_file = "data/users.json"
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
                
                # Find user with @ symbol handling
                clean_user_id = user_id.lstrip('@')
                user_data = None
                
                # Try different variations
                if user_id in users:
                    user_data = users[user_id]
                elif clean_user_id in users:
                    user_data = users[clean_user_id]
                elif f"@{clean_user_id}" in users:
                    user_data = users[f"@{clean_user_id}"]
                elif user_id.lower() in users:
                    user_data = users[user_id.lower()]
                elif clean_user_id.lower() in users:
                    user_data = users[clean_user_id.lower()]
                
                if user_data:
                    tier = user_data.get('tier', 'free')
                    return default_limits.get(tier, default_limits['free'])
            except:
                pass
        
        # Default: Free tier
        return default_limits['free']
    
    def upgrade_to_premium(self, user_id: str):
        """Upgrade user to premium"""
        profile = self.get_user_profile(user_id)
        profile["subscription"] = "premium"
        profile["subscription_upgraded_at"] = datetime.now(timezone.utc).isoformat()
        self.save_user_profile(user_id, profile)
    
    def downgrade_to_free(self, user_id: str):
        """Downgrade user to free tier"""
        profile = self.get_user_profile(user_id)
        profile["subscription"] = "free"
        self.save_user_profile(user_id, profile)
        
        # No need to trim watchlist - both tiers get 10 tokens
        # Difference is in update speed and features
    
    def get_all_users(self) -> List[str]:
        """Get list of all user IDs"""
        if not os.path.exists(self.users_dir):
            return []
        
        return [d for d in os.listdir(self.users_dir) 
                if os.path.isdir(os.path.join(self.users_dir, d))]
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics"""
        profile = self.get_user_profile(user_id)
        watchlist = self.get_user_watchlist(user_id)
        
        return {
            "user_id": user_id,
            "subscription": profile.get("subscription", "free"),
            "watchlist_count": len(watchlist),
            "watchlist_limit": self.get_watchlist_limit(user_id),
            "created_at": profile.get("created_at"),
            "last_login": profile.get("last_login")
        }


# Global instance
_user_manager = None

def get_user_manager() -> UserManager:
    """Get global UserManager instance"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


# Demo users setup
def setup_demo_users():
    """Create demo users for testing"""
    um = get_user_manager()
    
    # Demo Free User
    free_profile = {
        "user_id": "demo_free",
        "subscription": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "theme": "dark",
            "notifications_enabled": True,
            "telegram_chat_id": None
        }
    }
    um.save_user_profile("demo_free", free_profile)
    
    # Demo Premium User
    premium_profile = {
        "user_id": "demo_premium",
        "subscription": "premium",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat(),
        "subscription_upgraded_at": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "theme": "dark",
            "notifications_enabled": True,
            "telegram_chat_id": "123456789"
        }
    }
    um.save_user_profile("demo_premium", premium_profile)
    
    print("✅ Demo users created:")
    print("  - demo_free (Free tier: 5min updates, 3 burst/day)")
    print("  - demo_premium (Premium tier: 1min updates, unlimited burst)")


if __name__ == "__main__":
    # Test the system
    setup_demo_users()
    
    um = get_user_manager()
    
    # Test free user
    print("\n📊 Demo Free User:")
    print(json.dumps(um.get_user_stats("demo_free"), indent=2))
    
    # Test premium user
    print("\n💎 Demo Premium User:")
    print(json.dumps(um.get_user_stats("demo_premium"), indent=2))

