#!/usr/bin/env python3
"""
Subscription Manager for Night Watch
무료/유료 구독 관리
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

class SubscriptionManager:
    def __init__(self, config_file: str = "config/subscription_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """구독 설정 로드"""
        default_config = {
            "subscription_type": "free",  # "free" or "premium"
            "subscription_start": None,
            "subscription_end": None,
            "last_free_update": None,
            "free_update_interval_hours": 1,  # 무료: 1시간마다
            "users": {}
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception:
                pass
        
        return default_config
    
    def _save_config(self):
        """구독 설정 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def is_premium(self) -> bool:
        """프리미엄 구독 여부 확인"""
        if self.config.get("subscription_type") != "premium":
            return False
        
        # 구독 만료일 확인
        end_date = self.config.get("subscription_end")
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > end:
                    # 구독 만료됨
                    self.config["subscription_type"] = "free"
                    self._save_config()
                    return False
            except Exception:
                return False
        
        return True
    
    def can_update_free(self) -> bool:
        """무료 사용자의 업데이트 가능 여부 확인 (1시간 제한)"""
        if self.is_premium():
            return True
        
        last_update = self.config.get("last_free_update")
        if not last_update:
            return True
        
        try:
            last = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            interval_hours = self.config.get("free_update_interval_hours", 1)
            next_update = last + timedelta(hours=interval_hours)
            
            return datetime.now(timezone.utc) >= next_update
        except Exception:
            return True
    
    def get_next_free_update_time(self) -> Optional[str]:
        """다음 무료 업데이트 가능 시간"""
        if self.is_premium():
            return None
        
        last_update = self.config.get("last_free_update")
        if not last_update:
            return "Now"
        
        try:
            last = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            interval_hours = self.config.get("free_update_interval_hours", 1)
            next_update = last + timedelta(hours=interval_hours)
            
            now = datetime.now(timezone.utc)
            if now >= next_update:
                return "Now"
            
            time_left = next_update - now
            minutes_left = int(time_left.total_seconds() / 60)
            
            if minutes_left < 60:
                return f"{minutes_left} min"
            else:
                hours_left = minutes_left // 60
                mins_left = minutes_left % 60
                return f"{hours_left}h {mins_left}m"
        except Exception:
            return "Now"
    
    def record_free_update(self):
        """무료 업데이트 기록"""
        self.config["last_free_update"] = datetime.now(timezone.utc).isoformat()
        self._save_config()
    
    def upgrade_to_premium(self, duration_days: int = 30):
        """프리미엄으로 업그레이드"""
        now = datetime.now(timezone.utc)
        self.config["subscription_type"] = "premium"
        self.config["subscription_start"] = now.isoformat()
        self.config["subscription_end"] = (now + timedelta(days=duration_days)).isoformat()
        self._save_config()
    
    def get_subscription_info(self) -> Dict:
        """구독 정보 반환"""
        is_premium = self.is_premium()
        
        info = {
            "type": "Premium" if is_premium else "Free",
            "is_premium": is_premium,
            "features": []
        }
        
        if is_premium:
            end_date = self.config.get("subscription_end")
            if end_date:
                try:
                    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    days_left = (end - datetime.now(timezone.utc)).days
                    info["days_left"] = days_left
                    info["end_date"] = end_date[:10]
                except Exception:
                    pass
            
            info["features"] = [
                "Real-time monitoring",
                "Full User Dashboard access",
                "Unlimited updates",
                "Advanced analytics",
                "Priority support"
            ]
        else:
            next_update = self.get_next_free_update_time()
            info["next_update"] = next_update
            info["features"] = [
                "1-hour update interval",
                "Basic monitoring",
                "Limited features"
            ]
        
        return info

def main():
    """테스트"""
    manager = SubscriptionManager()
    print(f"Is Premium: {manager.is_premium()}")
    print(f"Can Update (Free): {manager.can_update_free()}")
    print(f"Next Free Update: {manager.get_next_free_update_time()}")
    print(f"Subscription Info: {manager.get_subscription_info()}")

if __name__ == "__main__":
    main()



