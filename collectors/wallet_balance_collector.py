#!/usr/bin/env python3
"""
Automated Wallet Balance Collector
하루 12회 (2시간마다) 유저들의 추적 지갑 잔액을 수집
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import schedule
from onchain_data_collector import OnChainCollector

def load_all_user_wallets() -> Dict:
    """Load all users' tracked wallets"""
    user_data_dir = Path("user_data")
    if not user_data_dir.exists():
        return {}

    all_users = {}

    for user_dir in user_data_dir.iterdir():
        if user_dir.is_dir():
            user_id = user_dir.name
            wallet_file = user_dir / "tracked_wallets.json"

            if wallet_file.exists():
                try:
                    with open(wallet_file, 'r', encoding='utf-8') as f:
                        all_users[user_id] = json.load(f)
                except:
                    continue

    return all_users

def get_wallet_history_file(user_id: str, token_key: str, wallet_address: str) -> str:
    """Get wallet balance history file path"""
    user_dir = Path("user_data") / user_id / "wallet_history"
    user_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename from wallet address
    safe_address = wallet_address.replace('0x', '').lower()
    return str(user_dir / f"{token_key}_{safe_address}.jsonl")

def save_balance_to_history(history_file: str, balance: float):
    """Append balance to history file (JSONL format)"""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'balance': balance
    }

    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')

def collect_all_wallet_balances():
    """Collect wallet balances for all users"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting wallet balance collection...")
    print(f"{'='*60}")

    all_users = load_all_user_wallets()

    if not all_users:
        print("No users with tracked wallets found.")
        return

    print(f"Found {len(all_users)} users with tracked wallets.")

    collector = OnChainCollector()

    total_wallets = 0
    successful_collections = 0
    failed_collections = 0

    for user_id, user_wallet_config in all_users.items():
        print(f"\n--- Processing User: {user_id} ---")

        for token_key, tracking_config in user_wallet_config.items():
            contract_address = tracking_config.get('contract_address')
            chain = tracking_config.get('chain', 'ETH')
            tracked_wallets = tracking_config.get('tracked_wallets', [])
            monitoring_enabled = tracking_config.get('monitoring_enabled', True)

            if not monitoring_enabled:
                print(f"  ⏭️  {token_key}: Monitoring disabled, skipping...")
                continue

            if not contract_address or not contract_address.startswith('0x'):
                print(f"  ⚠️  {token_key}: Invalid contract address, skipping...")
                continue

            if not tracked_wallets:
                print(f"  ⏭️  {token_key}: No tracked wallets, skipping...")
                continue

            print(f"  📊 {token_key} ({chain}): {len(tracked_wallets)} wallets")

            for wallet in tracked_wallets:
                wallet_address = wallet.get('address')
                wallet_label = wallet.get('label', 'Unknown')

                total_wallets += 1

                try:
                    # Get balance
                    balance = collector.get_token_balance(
                        contract_address,
                        wallet_address,
                        chain
                    )

                    if balance is not None:
                        # Save to history
                        history_file = get_wallet_history_file(user_id, token_key, wallet_address)
                        save_balance_to_history(history_file, balance)

                        print(f"    ✅ {wallet_label}: {balance:,.8f} tokens")
                        successful_collections += 1
                    else:
                        print(f"    ❌ {wallet_label}: Failed to get balance")
                        failed_collections += 1

                    # Rate limiting: 4 calls per second (free tier = 5 calls/sec)
                    time.sleep(0.25)

                except Exception as e:
                    print(f"    ❌ {wallet_label}: Error - {str(e)}")
                    failed_collections += 1

    print(f"\n{'='*60}")
    print(f"Collection Summary:")
    print(f"  Total wallets processed: {total_wallets}")
    print(f"  Successful: {successful_collections}")
    print(f"  Failed: {failed_collections}")
    print(f"  Success rate: {(successful_collections/total_wallets*100) if total_wallets > 0 else 0:.1f}%")
    print(f"{'='*60}\n")

def detect_large_movements():
    """Detect large movements (>0.1% change) in wallet balances"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for large movements...")

    all_users = load_all_user_wallets()

    alerts = []

    for user_id, user_wallet_config in all_users.items():
        for token_key, tracking_config in user_wallet_config.items():
            tracked_wallets = tracking_config.get('tracked_wallets', [])

            for wallet in tracked_wallets:
                wallet_address = wallet.get('address')
                wallet_label = wallet.get('label', 'Unknown')

                history_file = get_wallet_history_file(user_id, token_key, wallet_address)

                if not os.path.exists(history_file):
                    continue

                # Read last 2 entries
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) < 2:
                            continue

                        prev_entry = json.loads(lines[-2])
                        curr_entry = json.loads(lines[-1])

                        prev_balance = prev_entry['balance']
                        curr_balance = curr_entry['balance']

                        if prev_balance == 0:
                            continue

                        change_pct = ((curr_balance - prev_balance) / prev_balance) * 100

                        if abs(change_pct) >= 0.1:
                            alerts.append({
                                'user_id': user_id,
                                'token': token_key,
                                'wallet': wallet_label,
                                'wallet_address': wallet_address,
                                'prev_balance': prev_balance,
                                'curr_balance': curr_balance,
                                'change_pct': change_pct,
                                'timestamp': curr_entry['timestamp']
                            })

                            print(f"  🚨 ALERT: {user_id} / {token_key} / {wallet_label}")
                            print(f"      Previous: {prev_balance:,.8f}")
                            print(f"      Current: {curr_balance:,.8f}")
                            print(f"      Change: {change_pct:+.2f}%")

                except Exception as e:
                    continue

    if alerts:
        # Save alerts to file
        alert_file = Path("alerts") / f"large_movements_{datetime.now().strftime('%Y%m%d')}.jsonl"
        alert_file.parent.mkdir(exist_ok=True)

        with open(alert_file, 'a', encoding='utf-8') as f:
            for alert in alerts:
                f.write(json.dumps(alert) + '\n')

        print(f"\n  💾 Saved {len(alerts)} alerts to {alert_file}")
    else:
        print("  ✅ No large movements detected.")

def scheduled_collection():
    """Combined scheduled task: collect balances and detect movements"""
    try:
        collect_all_wallet_balances()
        detect_large_movements()
    except Exception as e:
        print(f"❌ Error during scheduled collection: {str(e)}")

def run_scheduler():
    """Run the scheduler - 12 times per day (every 2 hours)"""
    print("="*60)
    print("Wallet Balance Collector - Starting Scheduler")
    print("="*60)
    print("Collection schedule: Every 2 hours (12 times per day)")
    print("Schedule times: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00,")
    print("                12:00, 14:00, 16:00, 18:00, 20:00, 22:00")
    print("="*60)

    # Schedule 12 times per day (every 2 hours)
    schedule.every().day.at("00:00").do(scheduled_collection)
    schedule.every().day.at("02:00").do(scheduled_collection)
    schedule.every().day.at("04:00").do(scheduled_collection)
    schedule.every().day.at("06:00").do(scheduled_collection)
    schedule.every().day.at("08:00").do(scheduled_collection)
    schedule.every().day.at("10:00").do(scheduled_collection)
    schedule.every().day.at("12:00").do(scheduled_collection)
    schedule.every().day.at("14:00").do(scheduled_collection)
    schedule.every().day.at("16:00").do(scheduled_collection)
    schedule.every().day.at("18:00").do(scheduled_collection)
    schedule.every().day.at("20:00").do(scheduled_collection)
    schedule.every().day.at("22:00").do(scheduled_collection)

    # Run once immediately on startup
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running initial collection...")
    scheduled_collection()

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler is running. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\n⏹️  Scheduler stopped by user.")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
