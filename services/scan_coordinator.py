#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Night Watch Scan Coordinator
모든 스캐너를 통합 관리하고 충돌 방지

- Regular Scan (2시간): 매 2시간마다 UTC
- Watchlist Scan (5분): 매 5분마다 (Pro tier standard)
- Premium Pool 1분 Snapshot: 매 1분마다 (4개 그룹 분할)
- Premium Pool Micro Burst: 매 5분마다 (조건부)
"""

import json
import os
import sys
import time
import threading
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess

# UTF-8 인코딩 강제 (Windows cp949 문제 해결)
if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ScanCoordinator:
    """전체 스캔 시스템 조율자"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='UTC')
        self.is_running = False
        
        # 스캔 상태 추적
        self.regular_scan_active = False
        self.watchlist_scan_active = False
        self.premium_1min_active = False
        self.microburst_active = False
        
        # API 건강 상태
        self.api_health = "good"  # good / slow / overload
        self.last_api_check = None
        
        # Premium Pool 그룹 (200개를 4개로 분할)
        self.premium_groups = {
            1: [],  # 0-49
            2: [],  # 50-99
            3: [],  # 100-149
            4: []   # 150-199
        }
        
        # 통계
        self.stats = {
            'regular_scans': 0,
            'watchlist_scans': 0,
            'premium_1min_scans': 0,
            'microburst_scans': 0,
            'conflicts_avoided': 0
        }
        
        # 상태 파일 (admin dashboard가 찾는 파일명과 일치)
        self.status_file = 'coordinator_status.json'
        
    def _sync_premium_pool(self):
        """모든 사용자 워치리스트를 Premium Pool에 동기화 (무료+유료)"""
        try:
            print(f"[COORDINATOR] Syncing Premium Pool from all users' watchlists...")

            # Step 1: 워치리스트 토큰 추가 (TokenManager 사용으로 안전)
            result = subprocess.run(
                ['python', 'force_add_watchlist_to_premium.py'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=60
            )

            if result.returncode == 0:
                print(f"[COORDINATOR] Premium Pool sync completed")
                # 출력 표시
                if result.stdout:
                    for line in result.stdout.strip().split('\n')[-5:]:  # 마지막 5줄만
                        print(f"  {line}")
            else:
                print(f"[COORDINATOR] WARNING: Premium Pool sync failed")
                if result.stderr:
                    print(f"  Error: {result.stderr[:200]}")

            # Step 2: 14일 경과 + 워치리스트에 없는 토큰 자동 정리
            print(f"[COORDINATOR] Running 14-day cleanup...")
            cleanup_result = subprocess.run(
                ['python', 'cleanup_premium_pool.py'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=60
            )

            if cleanup_result.returncode == 0:
                print(f"[COORDINATOR] Premium Pool cleanup completed")
                # 출력 표시
                if cleanup_result.stdout:
                    for line in cleanup_result.stdout.strip().split('\n')[-5:]:  # 마지막 5줄만
                        print(f"  {line}")
            else:
                print(f"[COORDINATOR] WARNING: Premium Pool cleanup failed")
                if cleanup_result.stderr:
                    print(f"  Error: {cleanup_result.stderr[:200]}")

        except Exception as e:
            print(f"[COORDINATOR] Error syncing premium pool: {e}")
    
    def _load_premium_pool(self):
        """Premium Pool 토큰 로드 및 4개 그룹으로 분할"""
        try:
            from safe_json_loader import load_tokens_unified
            tokens = load_tokens_unified(default={})

            # premium_pool.in_pool == True인 토큰들만 필터링
            premium_tokens = []
            for token_id, data in tokens.items():
                if data.get('premium_pool', {}).get('in_pool', False):
                    premium_tokens.append(token_id)

            print(f"[COORDINATOR] Premium Pool loaded: {len(premium_tokens)} tokens")

            # 4개 그룹으로 분할 (마이크로 버스트용)
            group_size = max(1, len(premium_tokens) // 4)
            for i in range(4):
                start = i * group_size
                end = start + group_size if i < 3 else len(premium_tokens)
                self.premium_groups[i] = premium_tokens[start:end]
                print(f"[COORDINATOR]   Group {i}: {len(self.premium_groups[i])} tokens")

        except Exception as e:
            print(f"[COORDINATOR] Error loading premium pool: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_status(self):
        """상태 파일 업데이트 (Heartbeat 포함)"""
        now = datetime.now(timezone.utc).isoformat()
        status_data = {
            'timestamp': now,
            'last_heartbeat': now,  # Admin dashboard가 찾는 heartbeat 필드
            'is_running': self.is_running,
            'scans_active': {
                'regular_scan': self.regular_scan_active,
                'watchlist_scan': self.watchlist_scan_active,
                'premium_1min': self.premium_1min_active,
                'microburst': self.microburst_active
            },
            'api_health': self.api_health,
            'last_api_check': self.last_api_check,
            'premium_pool_groups': {
                str(k): len(v) for k, v in self.premium_groups.items()
            },
            'stats': self.stats
        }
        
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[COORDINATOR] Error updating status: {e}")
    
    def can_run_premium_1min(self):
        """1분 스냅샷 실행 가능 여부"""
        if self.regular_scan_active:
            # 정규 스캔 중에는 건너뛰기
            return False
        return True
    
    def can_run_microburst(self):
        """Micro Burst 실행 가능 여부"""
        if self.regular_scan_active:
            print(f"[COORDINATOR] ⏸ Micro Burst paused (Regular scan active)")
            return False
        
        if self.premium_1min_active:
            print(f"[COORDINATOR] ⏸ Micro Burst paused (1min snapshot active)")
            return False
        
        if self.api_health != "good":
            print(f"[COORDINATOR] ⏸ Micro Burst paused (API health: {self.api_health})")
            return False
        
        return True
    
    # ========== Regular Scan (2시간) ==========
    def _run_regular_scan(self):
        """정규 스캔 실행 (2시간마다)"""
        if self.regular_scan_active:
            print(f"[COORDINATOR] Regular scan already running, skipping")
            return
        
        self.regular_scan_active = True
        self._update_status()
        
        now = datetime.now(timezone.utc)
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] 🔴 REGULAR SCAN STARTED")
        print(f"  Time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  All other scans will be paused")
        print(f"{'='*60}\n")
        
        try:
            # batch_scanner.py 실행 (UTF-8 인코딩 명시 - Windows cp949 문제 해결)
            result = subprocess.run(
                ['python', 'batch_scanner.py', '--exchanges', 'gateio', 'mexc', 'kucoin', 'bitget'],
                capture_output=True,
                text=True,
                encoding='utf-8',  # UTF-8 인코딩 명시
                errors='replace',  # 디코딩 에러 무시
                timeout=3600  # 1시간 타임아웃
            )

            elapsed = (datetime.now(timezone.utc) - now).total_seconds()

            if result.returncode == 0:
                print(f"\n[COORDINATOR] ✅ Market scan completed ({elapsed:.1f}s)")
                print(f"[COORDINATOR] 📊 Starting post-scan calculations...")

                # 스캔 완료 후 평균 계산 실행
                calc_start = datetime.now(timezone.utc)
                calc_result = subprocess.run(
                    ['python', 'batch_scanner.py', '--calculate-average'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=300  # 5분 타임아웃
                )

                calc_elapsed = (datetime.now(timezone.utc) - calc_start).total_seconds()

                if calc_result.returncode == 0:
                    total_elapsed = (datetime.now(timezone.utc) - now).total_seconds()
                    print(f"[COORDINATOR] ✅ Average calculation completed ({calc_elapsed:.1f}s)")
                    print(f"\n{'='*60}")
                    print(f"[COORDINATOR] ✅ REGULAR SCAN COMPLETED")
                    print(f"  Market Scan: {elapsed:.1f}s ({elapsed/60:.1f}min)")
                    print(f"  Calculations: {calc_elapsed:.1f}s")
                    print(f"  Total: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
                    print(f"{'='*60}\n")
                    self.stats['regular_scans'] += 1
                else:
                    print(f"[COORDINATOR] ⚠️ Average calculation failed (returncode={calc_result.returncode})")
                    print(f"  Market scan succeeded, but post-processing incomplete")
                    if calc_result.stderr:
                        print(f"  Error: {calc_result.stderr[:500]}")
            else:
                print(f"\n[COORDINATOR] ❌ Regular scan failed (returncode={result.returncode}):")
                print(result.stderr if result.stderr else "No error output")
                
        except subprocess.TimeoutExpired:
            print(f"\n[COORDINATOR] ⏱ Regular scan timeout (>1 hour)")
        except Exception as e:
            print(f"\n[COORDINATOR] ❌ Regular scan error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.regular_scan_active = False
            self._update_status()
            print(f"[COORDINATOR] 🟢 Other scans resumed\n")
    
    # ========== Watchlist Scan 제거 ==========
    # 모든 유저 워치리스트는 프리미엄 풀로 통합되어 1분 스캔으로 처리됨

    # ========== Premium Pool 1분 Snapshot ==========
    def _run_premium_1min(self):
        """Premium Pool 1분 스냅샷 (전체 실행)"""
        if not self.can_run_premium_1min():
            return

        # Count total tokens in premium pool
        total_tokens = sum(len(tokens) for tokens in self.premium_groups.values())
        if total_tokens == 0:
            return

        self.premium_1min_active = True
        self._update_status()

        now = datetime.now(timezone.utc)
        print(f"[COORDINATOR] 💎 Premium 1min scan started ({total_tokens} tokens)")

        try:
            # premium_pool_collector.py --once 실행
            result = subprocess.run(
                ['python', 'premium_pool_collector.py', '--once'],
                capture_output=True,
                text=True,
                timeout=120  # 2분 타임아웃
            )

            elapsed = (datetime.now(timezone.utc) - now).total_seconds()

            if result.returncode == 0:
                print(f"[COORDINATOR] ✅ Premium 1min scan completed ({elapsed:.1f}s)")
                self.stats['premium_1min_scans'] += 1
            else:
                print(f"[COORDINATOR] ❌ Premium 1min scan failed")
                if result.stderr:
                    print(f"  Error: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            print(f"[COORDINATOR] ⏱ Premium 1min scan timeout")
        except Exception as e:
            print(f"[COORDINATOR] ❌ Premium 1min scan error: {e}")
        finally:
            self.premium_1min_active = False
            self._update_status()
    
    # ========== Premium Pool Micro Burst (5분) ==========
    def _run_microburst(self):
        """Micro Burst 분석 (5분마다, 조건부)"""
        if not self.can_run_microburst():
            self.stats['conflicts_avoided'] += 1
            return
        
        self.microburst_active = True
        self._update_status()
        
        now = datetime.now(timezone.utc)
        total_tokens = sum(len(tokens) for tokens in self.premium_groups.values())
        
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] 🔬 MICRO BURST ANALYSIS STARTED")
        print(f"  Time: {now.strftime('%H:%M:%S')} UTC")
        print(f"  Tokens: {total_tokens}")
        print(f"{'='*60}\n")
        
        try:
            # premium_pool_microburst_scanner.py 실행
            result = subprocess.run(
                ['python', 'premium_pool_microburst_scanner.py'],
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )
            
            elapsed = (datetime.now(timezone.utc) - now).total_seconds()
            
            if result.returncode == 0:
                print(f"\n{'='*60}")
                print(f"[COORDINATOR] ✅ MICRO BURST COMPLETED")
                print(f"  Elapsed: {elapsed:.1f}s ({elapsed/60:.1f}min)")
                print(f"{'='*60}\n")
                self.stats['microburst_scans'] += 1
            else:
                print(f"\n[COORDINATOR] ❌ Micro Burst failed")
                if result.stderr:
                    print(f"  Error: {result.stderr[:500]}")
            
        except subprocess.TimeoutExpired:
            print(f"\n[COORDINATOR] ⏱ Micro Burst timeout (>10min)")
        except Exception as e:
            print(f"[COORDINATOR] ❌ Micro Burst error: {e}")
        finally:
            self.microburst_active = False
            self._update_status()
    
    def start(self):
        """코디네이터 시작"""
        if self.is_running:
            print("[COORDINATOR] Already running")
            return False
        
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] 🚀 NIGHT WATCH SCAN COORDINATOR")
        print(f"{'='*60}\n")
        
        # Premium Pool 로드 및 그룹 분할
        self._load_premium_pool()
        
        # ===== 정규 스캔 (2시간) =====
        # Note: scanner_scheduler.py + scanner_config.json도 2시간으로 설정됨
        regular_trigger = CronTrigger(
            hour='0,2,4,6,8,10,12,14,16,18,20,22',
            minute='0',
            second='0',
            timezone='UTC'
        )
        self.scheduler.add_job(
            self._run_regular_scan,
            trigger=regular_trigger,
            id='regular_scan',
            name='Regular Scan (2h)',
            replace_existing=True
        )
        
        # ===== 워치리스트 스캔 제거 =====
        # 모든 유저 워치리스트는 프리미엄 풀로 통합되어 1분 스캔으로 처리됨

        # ===== Premium Pool 1분 스냅샷 =====
        premium_1min_trigger = CronTrigger(
            minute='*',
            second='0',
            timezone='UTC'
        )
        self.scheduler.add_job(
            self._run_premium_1min,
            trigger=premium_1min_trigger,
            id='premium_1min',
            name='Premium 1min Snapshot',
            replace_existing=True
        )
        
        # ===== Micro Burst (5분) =====
        microburst_trigger = CronTrigger(
            minute='*/5',
            second='0',
            timezone='UTC'
        )
        self.scheduler.add_job(
            self._run_microburst,
            trigger=microburst_trigger,
            id='microburst',
            name='Micro Burst (5min)',
            replace_existing=True
        )
        
        # 스케줄러 시작
        self.scheduler.start()
        self.is_running = True
        self._update_status()
        
        # 스케줄 출력
        print(f"{'='*60}")
        print(f"[COORDINATOR] 📅 SCHEDULE")
        print(f"{'='*60}")
        
        jobs = self.scheduler.get_jobs()
        for job in sorted(jobs, key=lambda x: x.next_run_time):
            print(f"  {job.name:30} → {job.next_run_time}")
        
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] ✅ All scanners are now coordinated!")
        print(f"{'='*60}\n")
        
        # 백그라운드에서 계속 실행
        print(f"[COORDINATOR] Running... (Press Ctrl+C to stop)\n")
        try:
            while self.is_running:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            print(f"\n[COORDINATOR] Received stop signal...")
            self.stop()
        
        return True
    
    def stop(self):
        """코디네이터 중지"""
        if not self.is_running:
            print("[COORDINATOR] Not running")
            return False
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        self._update_status()
        
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] 🛑 STOPPED")
        print(f"  Regular Scans: {self.stats['regular_scans']}")
        print(f"  Watchlist Scans: {self.stats['watchlist_scans']}")
        print(f"  Premium 1min Scans: {self.stats['premium_1min_scans']}")
        print(f"  Micro Burst Scans: {self.stats['microburst_scans']}")
        print(f"  Conflicts Avoided: {self.stats['conflicts_avoided']}")
        print(f"{'='*60}\n")
        
        return True
    
    def status(self):
        """현재 상태 출력"""
        print(f"\n{'='*60}")
        print(f"[COORDINATOR] STATUS")
        print(f"{'='*60}")
        print(f"  Running: {self.is_running}")
        print(f"  API Health: {self.api_health}")
        print(f"\n  Active Scans:")
        print(f"    Regular Scan: {'🔴 YES' if self.regular_scan_active else '🟢 No'}")
        print(f"    Watchlist Scan: {'🔴 YES' if self.watchlist_scan_active else '🟢 No'}")
        print(f"    Premium 1min: {'🔴 YES' if self.premium_1min_active else '🟢 No'}")
        print(f"    Micro Burst: {'🔴 YES' if self.microburst_active else '🟢 No'}")
        print(f"\n  Premium Pool Groups:")
        for group_id, tokens in self.premium_groups.items():
            print(f"    Group {group_id}: {len(tokens)} tokens")
        print(f"\n  Statistics:")
        print(f"    Regular Scans: {self.stats['regular_scans']}")
        print(f"    Watchlist Scans: {self.stats['watchlist_scans']}")
        print(f"    Premium 1min Scans: {self.stats['premium_1min_scans']}")
        print(f"    Micro Burst Scans: {self.stats['microburst_scans']}")
        print(f"    Conflicts Avoided: {self.stats['conflicts_avoided']}")
        
        if self.is_running:
            print(f"\n  Next Runs:")
            jobs = self.scheduler.get_jobs()
            for job in sorted(jobs, key=lambda x: x.next_run_time)[:5]:
                print(f"    {job.name:30} → {job.next_run_time}")
        
        print(f"{'='*60}\n")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Night Watch Scan Coordinator')
    parser.add_argument('action', choices=['start', 'stop', 'status'], help='Action to perform')

    args = parser.parse_args()

    # 🔒 Process Lock: Coordinator 중복 실행 방지
    LOCK_FILE = '.scan_coordinator.lock'

    if args.action == 'start':
        if os.path.exists(LOCK_FILE):
            # Lock 파일 생성 시간 확인
            lock_age = time.time() - os.path.getmtime(LOCK_FILE)
            if lock_age < 7200:  # 2시간 이내
                print(f"❌ Scan Coordinator is already running!")
                print(f"   Lock file: {LOCK_FILE} (age: {lock_age:.0f}s)")
                print(f"   If this is a stale lock, delete the file manually.")
                sys.exit(1)
            else:
                # 2시간 이상 된 lock은 stale로 간주
                print(f"⚠️  Removing stale lock file (age: {lock_age:.0f}s)")
                os.remove(LOCK_FILE)

        # Lock 파일 생성
        with open(LOCK_FILE, 'w') as f:
            f.write(f"PID: {os.getpid()}\nStarted: {datetime.now()}\n")

        try:
            coordinator = ScanCoordinator()
            coordinator.start()
        finally:
            # Lock 파일 삭제
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                print(f"\n🔓 Released coordinator lock: {LOCK_FILE}")
    else:
        coordinator = ScanCoordinator()
        if args.action == 'status':
            coordinator.status()
        elif args.action == 'stop':
            coordinator.stop()


if __name__ == '__main__':
    main()

























