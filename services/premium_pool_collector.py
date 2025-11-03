#!/usr/bin/env python3
"""
Premium Watch Pool Collector
200개 프리미엄 토큰 풀의 1분 스냅샷 수집
"""
import sys
import io
import os
import json
import time
import ccxt
from datetime import datetime, timezone
from pathlib import Path
import argparse

# UTF-8 인코딩 강제 (Windows cp949 문제 해결)
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class PremiumPoolCollector:
    """프리미엄 풀 1분 스냅샷 수집기"""
    
    def __init__(self):
        self.exchanges = self._init_exchanges()
        self.pool_file = "premium_watch_pool.json"
        self.snapshots_dir = Path("premium_pool_snapshots")
        self.snapshots_dir.mkdir(exist_ok=True)

        print("\n" + "="*60)
        print("[PREMIUM POOL COLLECTOR] Initialized")
        print("="*60)
    
    def _init_exchanges(self):
        """거래소 초기화"""
        return {
            'gateio': ccxt.gateio({'enableRateLimit': True}),
            'mexc': ccxt.mexc({'enableRateLimit': True}),
            'kucoin': ccxt.kucoin({'enableRateLimit': True}),
            'bitget': ccxt.bitget({'enableRateLimit': True}),
            'mexc_assessment': ccxt.mexc({'enableRateLimit': True})  # 동일한 MEXC 사용
        }
    
    def load_pool(self):
        """프리미엄 풀 로드 (tokens_unified.json에서)"""
        tokens_file = "data/tokens_unified.json"
        if not os.path.exists(tokens_file):
            return {}
        
        with open(tokens_file, 'r', encoding='utf-8') as f:
            all_tokens = json.load(f)
        
        # premium_pool.in_pool = True인 토큰만 필터링
        premium_tokens = {}
        for token_id, token_data in all_tokens.items():
            if token_data.get('premium_pool', {}).get('in_pool', False):
                exchange = token_data.get('exchange')
                symbol = token_data.get('symbol')
                
                premium_tokens[token_id] = {
                    'exchange': exchange,
                    'symbol': symbol,
                    'added_at': token_data.get('premium_pool', {}).get('added_at'),
                    'added_by': token_data.get('premium_pool', {}).get('added_by', 'unknown')
                }
        
        return premium_tokens
    
    def collect_snapshot(self, exchange_id, symbol):
        """단일 토큰의 스냅샷 수집"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                return None

            # Order book 가져오기 (모든 거래소 100개)
            orderbook = exchange.fetch_order_book(symbol, limit=100)
            ticker = exchange.fetch_ticker(symbol)
            
            # 스프레드 계산
            best_bid = orderbook['bids'][0][0] if orderbook['bids'] else 0
            best_ask = orderbook['asks'][0][0] if orderbook['asks'] else 0
            mid_price = (best_bid + best_ask) / 2 if (best_bid and best_ask) else 0
            spread_pct = ((best_ask - best_bid) / mid_price * 100) if mid_price else 0

            # Depth 계산 (±2%, ±5%, ±10%)
            depth_2pct = self._calculate_depth(orderbook, mid_price, 0.02)
            depth_5pct = self._calculate_depth(orderbook, mid_price, 0.05)
            depth_10pct = self._calculate_depth(orderbook, mid_price, 0.10)

            snapshot = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'exchange': exchange_id,
                'symbol': symbol,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'spread_pct': round(spread_pct, 3),
                'depth_2pct': round(depth_2pct, 2),
                'depth_5pct': round(depth_5pct, 2),
                'depth_10pct': round(depth_10pct, 2),
                'volume_24h': ticker.get('quoteVolume', 0),
                'last_price': ticker.get('last', 0)
            }

            return snapshot
        
        except Exception as e:
            print(f"[ERROR] {exchange_id} {symbol}: {e}")
            return None
    
    def _calculate_depth(self, orderbook, mid_price, threshold):
        """유동성 깊이 계산

        Args:
            orderbook: 호가 데이터
            mid_price: 중간 가격
            threshold: 가격 범위 (0.02 = ±2%, 0.05 = ±5%, 0.10 = ±10%)
        """
        if not mid_price:
            return 0

        lower_bound = mid_price * (1 - threshold)
        upper_bound = mid_price * (1 + threshold)

        bid_depth = sum(
            price * amount
            for price, amount in orderbook['bids']
            if price >= lower_bound
        )

        ask_depth = sum(
            price * amount
            for price, amount in orderbook['asks']
            if price <= upper_bound
        )

        return bid_depth + ask_depth
    
    def save_snapshot(self, snapshot):
        """스냅샷 저장"""
        if not snapshot:
            return
        
        exchange = snapshot['exchange']
        symbol = snapshot['symbol'].replace('/', '_')
        
        # 토큰별 디렉토리 생성
        token_dir = self.snapshots_dir / f"{exchange}_{symbol}"
        token_dir.mkdir(exist_ok=True)
        
        # 날짜별 파일 (하루에 1440개 스냅샷)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        snapshot_file = token_dir / f"snapshots_{today}.jsonl"
        
        # JSONL 형식으로 추가 (한 줄에 하나씩)
        with open(snapshot_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
        
        # Update tokens_unified.json with last_1min_snapshot
        self._update_unified_db(snapshot)
    
    def _update_unified_db(self, snapshot):
        """Update tokens_unified.json with 1-minute snapshot data"""
        try:
            tokens_file = "data/tokens_unified.json"
            if not os.path.exists(tokens_file):
                return
            
            # Load tokens
            with open(tokens_file, 'r', encoding='utf-8') as f:
                tokens = json.load(f)
            
            # Get token_id
            exchange = snapshot['exchange']
            symbol = snapshot['symbol']
            token_id = f"{exchange}_{symbol.replace('/', '_').lower()}"
            
            if token_id not in tokens:
                return
            
            # Update premium_pool data
            if 'premium_pool' not in tokens[token_id]:
                tokens[token_id]['premium_pool'] = {}
            
            tokens[token_id]['premium_pool']['last_1min_snapshot'] = snapshot['timestamp']
            tokens[token_id]['premium_pool']['last_1min_data'] = {
                'spread_pct': snapshot['spread_pct'],
                'depth_2pct': snapshot['depth_2pct'],
                'bid': snapshot.get('best_bid', 0),
                'ask': snapshot.get('best_ask', 0),
                'mid_price': snapshot.get('mid_price', 0),
                'volume_24h': snapshot.get('volume_24h', 0),
                'last_price': snapshot.get('last_price', 0)
            }
            
            # Save back
            with open(tokens_file, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[WARN] Failed to update tokens_unified.json: {e}")
    
    def collect_all(self):
        """전체 프리미엄 풀 수집"""
        pool_tokens = self.load_pool()
        
        if not pool_tokens:
            print("[INFO] Premium Pool is empty. Nothing to collect.")
            return
        
        print(f"\n[COLLECT] Starting 1-minute snapshot for {len(pool_tokens)} tokens...")
        
        collected = 0
        failed = 0
        
        for token_id, token_data in pool_tokens.items():
            exchange = token_data['exchange']
            symbol = token_data['symbol']
            
            snapshot = self.collect_snapshot(exchange, symbol)
            
            if snapshot:
                self.save_snapshot(snapshot)
                collected += 1
                print(f"  [OK] {exchange.upper()} {symbol} - Spread: {snapshot['spread_pct']:.2f}% | Depth: ${snapshot['depth_2pct']:,.0f}")
            else:
                failed += 1
            
            # Rate limit 준수
            time.sleep(0.5)
        
        print(f"\n[COLLECT] Complete: {collected} collected, {failed} failed")
        
        # 통계 업데이트
        self._update_statistics(collected, failed)
    
    def _update_statistics(self, collected, failed):
        """수집 통계 업데이트"""
        stats_file = "premium_pool_stats.json"
        
        stats = {
            'last_collection': datetime.now(timezone.utc).isoformat(),
            'tokens_collected': collected,
            'tokens_failed': failed,
            'collection_rate': round(collected / (collected + failed) * 100, 2) if (collected + failed) > 0 else 0
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    
    def run_continuous(self):
        """연속 수집 (1분 간격)"""
        print("\n" + "="*60)
        print("[PREMIUM POOL COLLECTOR] Starting continuous 1-minute collection")
        print("="*60)
        
        while True:
            try:
                start_time = time.time()
                
                self.collect_all()
                
                # 1분 간격 유지
                elapsed = time.time() - start_time
                sleep_time = max(0, 60 - elapsed)
                
                if sleep_time > 0:
                    print(f"\n[SLEEP] Next collection in {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                else:
                    print(f"\n[WARNING] Collection took {elapsed:.1f}s (> 60s)")
            
            except KeyboardInterrupt:
                print("\n[STOP] Premium Pool Collector stopped by user")
                break
            except Exception as e:
                print(f"\n[ERROR] Collection error: {e}")
                time.sleep(60)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Premium Watch Pool Collector')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous 1-minute collection')
    parser.add_argument('--once', action='store_true',
                       help='Collect once and exit')
    
    args = parser.parse_args()
    
    collector = PremiumPoolCollector()
    
    if args.continuous:
        collector.run_continuous()
    elif args.once:
        collector.collect_all()
    else:
        print("\nUsage:")
        print("  python premium_pool_collector.py --continuous  # Run continuously")
        print("  python premium_pool_collector.py --once        # Collect once")


if __name__ == '__main__':
    main()

