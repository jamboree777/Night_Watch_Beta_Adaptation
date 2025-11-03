"""
Admin Honeymoon Management System
관리자용 전역 허니문 설정 (마켓 캐싱에 반영)
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List


class AdminHoneymoonManager:
    """관리자용 전역 허니문 관리 시스템"""
    
    def __init__(self, config_file='admin_honeymoon_config.json'):
        self.config_file = config_file
        self.default_config = {
            'global_threshold_days': 240,  # 8개월 (240일)
            'global_price_drop_threshold_pct': 1.0,  # 1% 이하
            'tokens': {},  # 전역 토큰 설정 (마켓 캐싱에 반영)
            'last_updated': None
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """설정 파일 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"관리자 설정 파일 로드 실패: {e}")
        
        # 기본 설정으로 초기화
        self.save_config(self.default_config)
        return self.default_config.copy()
    
    def save_config(self, config: Dict = None):
        """설정 파일 저장"""
        if config is None:
            config = self.config
        
        config['last_updated'] = datetime.now(timezone.utc).isoformat()
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def set_global_token_listing(self, exchange: str, symbol: str, listing_date: str, listing_price: float):
        """
        전역 토큰 상장 정보 설정 (마켓 캐싱에 반영)
        
        Args:
            exchange: 거래소 (gateio, mexc, kucoin, bitget)
            symbol: 심볼 (BTC/USDT)
            listing_date: 상장일 (YYYY-MM-DD)
            listing_price: 상장가격 (USDT)
        """
        token_key = f"{exchange}_{symbol.replace('/', '_')}"
        
        try:
            # 날짜 파싱
            listing_dt = datetime.fromisoformat(listing_date)
            if listing_dt.tzinfo is None:
                listing_dt = listing_dt.replace(tzinfo=timezone.utc)
            
            # 전역 토큰 정보 저장
            self.config['tokens'][token_key] = {
                'exchange': exchange,
                'symbol': symbol,
                'listing_date': listing_dt.isoformat(),
                'listing_price': listing_price,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.save_config()
            return True
            
        except Exception as e:
            print(f"전역 토큰 상장 정보 설정 실패: {e}")
            return False
    
    def get_global_token_honeymoon_status(self, exchange: str, symbol: str, current_price: float = None) -> Dict:
        """
        전역 토큰 허니문 상태 확인 (스캔 최적화용)
        
        Args:
            exchange: 거래소
            symbol: 심볼
            current_price: 현재 가격 (선택적)
        
        Returns:
            {
                'is_in_honeymoon': bool,
                'days_since_listing': int,
                'days_remaining': int,
                'price_drop_pct': float,
                'threshold_days': int,
                'threshold_price_pct': float,
                'status': str
            }
        """
        token_key = f"{exchange}_{symbol.replace('/', '_')}"
        token_info = self.config['tokens'].get(token_key)
        
        if not token_info:
            return {
                'is_in_honeymoon': False,
                'days_since_listing': 0,
                'days_remaining': 0,
                'price_drop_pct': 0,
                'threshold_days': self.config['global_threshold_days'],
                'threshold_price_pct': self.config['global_price_drop_threshold_pct'],
                'status': 'not_configured',
                'error': '전역 토큰 정보가 설정되지 않음'
            }
        
        try:
            # 상장일 파싱
            listing_dt = datetime.fromisoformat(token_info['listing_date'])
            if listing_dt.tzinfo is None:
                listing_dt = listing_dt.replace(tzinfo=timezone.utc)
            
            # 현재 시간
            now = datetime.now(timezone.utc)
            
            # 상장 후 경과 일수
            days_since_listing = (now - listing_dt).days
            
            # 허니문 임계값
            threshold_days = self.config['global_threshold_days']
            threshold_price_pct = self.config['global_price_drop_threshold_pct']
            
            # 허니문 여부 판단
            is_in_honeymoon = days_since_listing <= threshold_days
            
            # 남은 허니문 일수
            days_remaining = max(0, threshold_days - days_since_listing)
            
            # 가격 하락률 계산
            price_drop_pct = 0
            if current_price and token_info['listing_price']:
                price_drop_pct = ((token_info['listing_price'] - current_price) / token_info['listing_price']) * 100
            
            # 상태 결정
            if not is_in_honeymoon:
                status = 'honeymoon_ended'
            elif price_drop_pct >= threshold_price_pct:
                status = 'honeymoon_high_risk'
            else:
                status = 'honeymoon_normal'
            
            return {
                'is_in_honeymoon': is_in_honeymoon,
                'days_since_listing': days_since_listing,
                'days_remaining': days_remaining,
                'price_drop_pct': price_drop_pct,
                'threshold_days': threshold_days,
                'threshold_price_pct': threshold_price_pct,
                'listing_price': token_info['listing_price'],
                'status': status,
                'error': None
            }
            
        except Exception as e:
            return {
                'is_in_honeymoon': False,
                'days_since_listing': 0,
                'days_remaining': 0,
                'price_drop_pct': 0,
                'threshold_days': self.config['global_threshold_days'],
                'threshold_price_pct': self.config['global_price_drop_threshold_pct'],
                'status': 'error',
                'error': str(e)
            }
    
    def update_global_thresholds(self, threshold_days: int = None, price_drop_threshold_pct: float = None):
        """전역 허니문 임계값 업데이트"""
        if threshold_days is not None:
            self.config['global_threshold_days'] = threshold_days
        
        if price_drop_threshold_pct is not None:
            self.config['global_price_drop_threshold_pct'] = price_drop_threshold_pct
        
        self.save_config()
    
    def get_all_global_tokens_status(self) -> List[Dict]:
        """모든 전역 토큰의 허니문 상태 조회"""
        results = []
        
        for token_key, token_info in self.config['tokens'].items():
            exchange = token_info['exchange']
            symbol = token_info['symbol']
            
            status = self.get_global_token_honeymoon_status(exchange, symbol)
            status['token_key'] = token_key
            status['exchange'] = exchange
            status['symbol'] = symbol
            
            results.append(status)
        
        return results
    
    def delete_global_token(self, exchange: str, symbol: str) -> bool:
        """전역 토큰 정보 삭제"""
        token_key = f"{exchange}_{symbol.replace('/', '_')}"
        
        if token_key in self.config['tokens']:
            del self.config['tokens'][token_key]
            self.save_config()
            return True
        
        return False
    
    def get_config_summary(self) -> Dict:
        """설정 요약 정보"""
        return {
            'total_tokens': len(self.config['tokens']),
            'global_threshold_days': self.config['global_threshold_days'],
            'global_price_drop_threshold_pct': self.config['global_price_drop_threshold_pct'],
            'config_file': self.config_file,
            'last_updated': self.config['last_updated']
        }
    
    def get_all_user_tokens(self) -> Dict[str, List[Dict]]:
        """모든 사용자의 토큰 설정 조회 (관리자용)"""
        user_tokens = {}
        
        # 사용자별 허니문 설정 파일에서 모든 사용자 데이터 수집
        user_config_file = 'honeymoon_config.json'
        if os.path.exists(user_config_file):
            try:
                with open(user_config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                for user_id, tokens in user_config.get('users', {}).items():
                    user_tokens[user_id] = []
                    for token_key, token_info in tokens.items():
                        user_tokens[user_id].append({
                            'token_key': token_key,
                            'exchange': token_info['exchange'],
                            'symbol': token_info['symbol'],
                            'listing_date': token_info['listing_date'],
                            'listing_price': token_info['listing_price'],
                            'created_at': token_info['created_at'],
                            'updated_at': token_info['updated_at']
                        })
            except Exception as e:
                print(f"사용자 토큰 설정 조회 실패: {e}")
        
        return user_tokens


# 전역 인스턴스
_admin_honeymoon_manager = None

def get_admin_honeymoon_manager() -> AdminHoneymoonManager:
    """AdminHoneymoonManager 싱글톤 인스턴스"""
    global _admin_honeymoon_manager
    if _admin_honeymoon_manager is None:
        _admin_honeymoon_manager = AdminHoneymoonManager()
    return _admin_honeymoon_manager
