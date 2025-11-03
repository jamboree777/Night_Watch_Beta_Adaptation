"""
Data Access Layer for Night Watch
=================================
사용자 티어별 데이터 접근 권한 및 가공 로직
"""

from datetime import datetime, timezone, timedelta
from modules.token_manager import TokenManager
from pathlib import Path
import json
import os

class DataAccessLayer:
    """티어별 데이터 접근 제어"""

    def __init__(self):
        self.token_manager = TokenManager()
        self.snapshots_dir = Path("premium_pool_snapshots")

    def _get_latest_premium_snapshot(self, token_id, exchange, symbol):
        """프리미엄 풀의 최신 1분 스냅샷 가져오기"""
        snapshot_dir = self.snapshots_dir / token_id
        if not snapshot_dir.exists():
            return None

        # 오늘 스냅샷 파일
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        snapshot_file = snapshot_dir / f"snapshots_{today}.jsonl"

        if not snapshot_file.exists():
            # 어제 파일도 체크
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
            snapshot_file = snapshot_dir / f"snapshots_{yesterday}.jsonl"
            if not snapshot_file.exists():
                return None

        # 파일의 마지막 줄 읽기 (최신 스냅샷)
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    if last_line:
                        snapshot = json.loads(last_line)

                        # 필드명 매핑: 프리미엄 풀 스냅샷 → 표준 current_snapshot 형식
                        mapped_snapshot = {
                            'timestamp': snapshot.get('timestamp'),
                            'spread_pct': snapshot.get('spread_pct'),
                            'depth_2pct': snapshot.get('depth_2pct'),
                            'volume_24h': snapshot.get('volume_24h'),
                            'bid': snapshot.get('best_bid'),
                            'ask': snapshot.get('best_ask'),
                            'mid_price': snapshot.get('mid_price'),
                            'last_scanned': snapshot.get('timestamp'),  # last_scanned와 timestamp 동일
                            'last_price': snapshot.get('last_price')
                        }
                        return mapped_snapshot
        except Exception as e:
            print(f"[ERROR] Failed to read premium snapshot for {token_id}: {e}")

        return None
    
    def get_main_board_data(self, user_tier='free'):
        """
        Main Board 데이터 반환 (V2 Schema)
        - 모든 티어: Main Board 토큰 전체 표시
        - 업데이트 주기는 표시만 다름 (실제 데이터는 동일)
        - Single Source: tokens_unified.json만 사용
        """
        all_tokens = self.token_manager.get_all_tokens()
        main_board_tokens = {}
        
        # tokens_unified.json에서 MAIN_BOARD 토큰 로드
        for token_id, token_data in all_tokens.items():
            # lifecycle.status가 MAIN_BOARD 또는 MONITORING인 토큰만 필터링
            lifecycle_status = token_data.get('lifecycle', {}).get('status')
            if lifecycle_status in ['MAIN_BOARD', 'MONITORING']:
                # 기본 정보
                lifecycle = token_data.get('lifecycle', {})
                api_info = token_data.get('api_info', {})
                
                display_data = {
                    'exchange': token_data.get('exchange'),
                    'symbol': token_data.get('symbol'),
                    'added_at': lifecycle.get('main_board_entry') or token_data.get('retention', {}).get('created_at'),
                    'requires_api_key': api_info.get('requires_special_api', False),
                    'api_available': api_info.get('admin_api_available', True)
                }
                
                # 스캔 데이터 추가 (V2 Schema: scan_aggregate 우선)
                scan_aggregate = token_data.get('scan_aggregate', {})
                current_snapshot = token_data.get('current_snapshot', {})
                
                if scan_aggregate:
                    display_data.update({
                        'spread_pct': scan_aggregate.get('avg_spread_pct'),
                        'depth_2pct_usd': scan_aggregate.get('avg_depth_2pct'),
                        'volume_24h_usd': scan_aggregate.get('avg_volume_24h'),
                        'grade': current_snapshot.get('grade') or scan_aggregate.get('grade'),  # 마지막 스캔의 실제 grade 우선
                        'average_risk': scan_aggregate.get('average_risk'),
                        'violation_rate': scan_aggregate.get('violation_rate'),
                        'st_tagged': token_data.get('tags', {}).get('st_tagged', False),
                        # last_scanned는 current_snapshot에서 가져옴
                        'last_scanned': current_snapshot.get('last_scanned')
                    })
                else:
                    # Fallback to current_snapshot
                    display_data.update({
                        'spread_pct': current_snapshot.get('spread_pct'),
                        'depth_2pct_usd': current_snapshot.get('depth_2pct'),
                        'volume_24h_usd': current_snapshot.get('volume_24h'),
                        'last_scanned': current_snapshot.get('last_scanned')
                    })
                
                # Manual inputs 추가 (V2: admin_manual_data)
                admin_manual = token_data.get('admin_manual_data', {})
                if admin_manual and any(admin_manual.values()):
                    display_data['manual_inputs'] = admin_manual
                
                main_board_tokens[token_id] = display_data
        
        return main_board_tokens
    
    def get_watchlist_data(self, user_id, user_tier='free'):
        """
        사용자 Watchlist 데이터 반환
        - 모든 티어: 데이터는 항상 표시 (Main Board와 동일)
        - 티어별 차이: 업데이트 주기 표시만 다름
        - Free: "30분마다 업데이트" 표시
        - Pro: "5분마다 업데이트" 표시
        - Premium: "실시간 (1분)" 표시
        """
        # 티어별 데이터 신선도 설정 (표시용)
        freshness_limits = {
            'free': timedelta(hours=24),  # 24시간 이내면 표시 (Main Board와 동일)
            'pro': timedelta(hours=24),
            'premium': timedelta(hours=24)
        }
        max_age = freshness_limits.get(user_tier, freshness_limits['free'])
        now = datetime.now(timezone.utc)
        
        # 사용자 watchlist 토큰 가져오기
        user_data = self._load_user_data(user_id)
        watchlist_tokens = user_data.get('watchlist', [])
        
        watchlist_data = {}
        for token_info in watchlist_tokens:
            token_id = f"{token_info['exchange']}_{token_info['symbol']}".replace('/', '_').lower()
            token = self.token_manager.get_token_by_id(token_id)
            
            if token:
                # V2 Schema 적용
                api_info = token.get('api_info', {})
                
                display_data = {
                    'exchange': token.get('exchange'),
                    'symbol': token.get('symbol'),
                    'requires_api_key': api_info.get('requires_special_api', False),
                    'api_available': api_info.get('admin_api_available', True)
                }

                # 프리미엄 풀 토큰은 최신 1분 스냅샷 사용, 아니면 regular scan의 current_snapshot 사용
                is_premium_pool = token.get('premium_pool', {}).get('in_pool', False)

                # Check if token is in premium pool
                if is_premium_pool:
                    # Premium pool: use latest 1min snapshot
                    premium_snapshot = self._get_latest_premium_snapshot(token_id, token.get('exchange'), token.get('symbol'))
                    if premium_snapshot:
                        current_snapshot = premium_snapshot
                        # Mark as premium pool data for later use
                        display_data['is_premium_pool'] = True
                    else:
                        # Fallback to current_snapshot
                        current_snapshot = token.get('current_snapshot', {})
                        display_data['is_premium_pool'] = False
                else:
                    # Regular token: use current_snapshot (2hr regular scan)
                    current_snapshot = token.get('current_snapshot', {})
                    display_data['is_premium_pool'] = False
                if current_snapshot:
                    last_updated = current_snapshot.get('timestamp')
                    
                    if last_updated:
                        try:
                            update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            data_age = now - update_time
                            
                            # 티어별 데이터 신선도 체크
                            if data_age <= max_age:
                                display_data.update({
                                    'spread_pct': current_snapshot.get('spread_pct'),
                                    'depth_2pct_usd': current_snapshot.get('depth_2pct'),
                                    'volume_24h_usd': current_snapshot.get('volume_24h'),
                                    'bid': current_snapshot.get('bid'),
                                    'ask': current_snapshot.get('ask'),
                                    'last_updated': last_updated,
                                    'last_scanned': current_snapshot.get('last_scanned', last_updated),  # last_scanned 추가
                                    'data_fresh': True
                                })
                            else:
                                # 데이터가 오래됨
                                display_data.update({
                                    'spread_pct': current_snapshot.get('spread_pct'),
                                    'depth_2pct_usd': current_snapshot.get('depth_2pct'),
                                    'volume_24h_usd': current_snapshot.get('volume_24h'),
                                    'bid': current_snapshot.get('bid'),
                                    'ask': current_snapshot.get('ask'),
                                    'last_updated': last_updated,
                                    'last_scanned': current_snapshot.get('last_scanned', last_updated),  # last_scanned 추가
                                    'data_fresh': False,
                                    'data_age_minutes': int(data_age.total_seconds() / 60)
                                })
                        except Exception as e:
                            # 날짜 파싱 실패해도 데이터는 보여줌
                            display_data.update({
                                'spread_pct': current_snapshot.get('spread_pct'),
                                'depth_2pct_usd': current_snapshot.get('depth_2pct'),
                                'volume_24h_usd': current_snapshot.get('volume_24h'),
                                'bid': current_snapshot.get('bid'),
                                'ask': current_snapshot.get('ask'),
                                'last_scanned': current_snapshot.get('last_scanned', last_updated),  # last_scanned 추가
                                'last_updated': last_updated,
                                'data_fresh': False
                            })
                
                # Scan data (Grade info) - V2 Schema
                scan_aggregate = token.get('scan_aggregate', {})
                if scan_aggregate:
                    grade_data = {
                        'grade': current_snapshot.get('grade') or scan_aggregate.get('grade'),  # Latest scan grade takes priority
                        'average_risk': scan_aggregate.get('average_risk'),
                        'violation_rate': scan_aggregate.get('violation_rate'),
                        'st_tagged': token.get('tags', {}).get('st_tagged', False)
                    }
                    # For premium pool tokens, don't override last_updated from snapshot
                    if not display_data.get('is_premium_pool'):
                        grade_data['last_updated'] = scan_aggregate.get('last_updated')

                    display_data.update(grade_data)
                    # Watchlist에서도 평균값 사용 (현재 스냅샷보다 안정적)
                    if 'spread_pct' not in display_data or display_data['spread_pct'] is None:
                        display_data['spread_pct'] = scan_aggregate.get('avg_spread_pct')
                    if 'depth_2pct_usd' not in display_data or display_data['depth_2pct_usd'] is None:
                        display_data['depth_2pct_usd'] = scan_aggregate.get('avg_depth_2pct')
                    if 'volume_24h_usd' not in display_data or display_data['volume_24h_usd'] is None:
                        display_data['volume_24h_usd'] = scan_aggregate.get('avg_volume_24h')
                
                watchlist_data[token_id] = display_data
        
        return watchlist_data
    
    def get_analytics_data(self, token_id, user_tier='free'):
        """
        Liquidity Analytics 데이터 반환
        - Free: 기본 분석만
        - Pro: 상세 분석 + Custom Monitoring
        - Premium: 전체 기능 + AI 분석
        """
        token = self.token_manager.get_token_by_id(token_id)
        if not token:
            return None
        
        analytics_data = {
            'basic_info': {
                'exchange': token.get('exchange'),
                'symbol': token.get('symbol'),
                'requires_api_key': token.get('requires_api_key', False)
            }
        }
        
        # 기본 분석 (모든 티어)
        if token.get('current_snapshot'):
            analytics_data['current_metrics'] = token['current_snapshot']
        
        if token.get('scan_data'):
            analytics_data['risk_assessment'] = {
                'grade': token['scan_data'].get('grade'),
                'average_risk': token['scan_data'].get('average_risk'),
                'violation_rate': token['scan_data'].get('violation_rate')
            }
        
        # Pro 이상: 상세 분석
        if user_tier in ['pro', 'premium']:
            # Scan history (5일 데이터)
            analytics_data['historical_analysis'] = self._get_historical_analysis(token_id)
            
            # Custom monitoring targets
            if token.get('manual_inputs'):
                analytics_data['custom_targets'] = token['manual_inputs']
        
        # Premium: AI 분석
        if user_tier == 'premium':
            analytics_data['ai_insights'] = self._get_ai_insights(token_id)
            analytics_data['micro_burst_available'] = True
        
        return analytics_data
    
    def _load_user_data(self, user_id):
        """사용자 데이터 로드"""
        users_file = "data/users.json"
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
                    return users.get(user_id, {})
            except:
                pass
        return {}
    
    def _get_historical_analysis(self, token_id):
        """과거 데이터 분석 (Pro/Premium)"""
        # TODO: scan_history에서 5일 데이터 분석
        return {
            'trend': 'improving',
            'volatility': 'moderate',
            'recommendation': 'monitor_closely'
        }
    
    def _get_ai_insights(self, token_id):
        """AI 인사이트 (Premium only)"""
        # TODO: AI 분석 로직
        return {
            'manipulation_risk': 'low',
            'liquidity_quality': 'fair',
            'action_plan': 'Consider adding liquidity at ±1.5% range'
        }
