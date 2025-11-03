"""
Report Helpers for User Board Detailed Token Analysis
Provides data loading and calculation functions for token reports
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Tuple


def load_grade_history(exchange: str, symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Load grade history for a token from scan_history files

    Args:
        exchange: Exchange ID (e.g., 'gateio', 'mexc')
        symbol: Trading symbol (e.g., 'BTC/USDT')
        days: Number of days to load (default 30)

    Returns:
        DataFrame with columns: timestamp, grade, grade_numeric
        grade_numeric maps: F=0.5, D-=1.0, D=1.5, D+=2.0, C-=2.0, C=2.5, C+=3.0,
                           B-=3.0, B=3.5, B+=4.0, A-=4.0, A=4.5, A+=5.0
    """
    scan_history_dir = Path('scan_history')
    if not scan_history_dir.exists():
        scan_history_dir = Path('data/scan_history')

    if not scan_history_dir.exists():
        return pd.DataFrame(columns=['timestamp', 'grade', 'grade_numeric'])

    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Token identifier
    token_id = f"{exchange}_{symbol}".replace('/', '_').lower()

    history_data = []

    # Iterate through scan history files
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')

        # Check files for each 2-hour interval (00, 02, 04, ..., 22)
        for hour in range(0, 24, 2):
            filename = f"{date_str}_{hour:02d}.json"
            filepath = scan_history_dir / filename

            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        scan_data = json.load(f)

                    # Find token in scan results
                    tokens = scan_data.get('tokens', [])
                    for token in tokens:
                        # Match by exchange and symbol
                        if (token.get('exchange', '').lower() == exchange.lower() and
                            token.get('symbol', '') == symbol):

                            timestamp = scan_data.get('timestamp', current_date.isoformat())
                            grade = token.get('grade', 'N/A')
                            grade_numeric = grade_to_numeric(grade)

                            history_data.append({
                                'timestamp': timestamp,
                                'grade': grade,
                                'grade_numeric': grade_numeric
                            })
                            break

                except (json.JSONDecodeError, IOError):
                    pass  # Skip corrupted or unreadable files

        current_date += timedelta(days=1)

    # Convert to DataFrame
    df = pd.DataFrame(history_data)

    if not df.empty:
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

    return df


def grade_to_numeric(grade: str) -> float:
    """
    Convert letter grade to numeric value for plotting (5-point system)

    Mapping:
    - F: 1.0
    - D: 2.0, D+: 2.33
    - C-: 2.67, C: 3.0, C+: 3.33
    - B-: 3.67, B: 4.0, B+: 4.33
    - A-: 4.67, A: 5.0
    - N/A: None (excluded from calculations)
    """
    grade_map = {
        'F': 1.0,
        'D': 2.0, 'D+': 2.33,
        'C-': 2.67, 'C': 3.0, 'C+': 3.33,
        'B-': 3.67, 'B': 4.0, 'B+': 4.33,
        'A-': 4.67, 'A': 5.0
    }
    return grade_map.get(grade, None)  # Return None for N/A grades


def load_spread_volume_history(exchange: str, symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Load spread and volume history for dual-axis chart

    For premium pool tokens, loads 1-minute resolution data from premium_pool_snapshots.
    For other tokens, loads 2-hour resolution data from scan_history.

    Returns:
        DataFrame with columns: timestamp, spread_pct, volume_24h
    """
    # Try premium pool snapshots first (1-minute resolution)
    snapshots_dir = Path('premium_pool_snapshots')
    token_id = f"{exchange}_{symbol}".replace('/', '_')
    token_dir = snapshots_dir / token_id

    if token_dir.exists():
        # Premium pool token - use 1-minute snapshots
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        history_data = []

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            filename = f"snapshots_{date_str}.jsonl"
            filepath = token_dir / filename

            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            if not line.strip():
                                continue

                            snapshot = json.loads(line)
                            timestamp = snapshot.get('timestamp')

                            # Parse timestamp to check if in range
                            try:
                                snap_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                if snap_time < start_date or snap_time > end_date:
                                    continue
                            except:
                                continue

                            spread_pct = snapshot.get('spread_pct', 0)
                            volume_24h = snapshot.get('volume_24h', 0)

                            # Ensure values are non-negative
                            spread_pct = max(0, spread_pct) if spread_pct else 0
                            volume_24h = max(0, volume_24h) if volume_24h else 0

                            history_data.append({
                                'timestamp': timestamp,
                                'spread_pct': spread_pct,
                                'volume_24h': volume_24h
                            })

                except (json.JSONDecodeError, IOError):
                    pass

            current_date += timedelta(days=1)

        if history_data:
            df = pd.DataFrame(history_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            return df

    # Fallback to scan_history (2-hour resolution)
    scan_history_dir = Path('scan_history')
    if not scan_history_dir.exists():
        scan_history_dir = Path('data/scan_history')

    if not scan_history_dir.exists():
        return pd.DataFrame(columns=['timestamp', 'spread_pct', 'volume_24h'])

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    history_data = []

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')

        for hour in range(0, 24, 2):
            filename = f"{date_str}_{hour:02d}.json"
            filepath = scan_history_dir / filename

            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        scan_data = json.load(f)

                    tokens = scan_data.get('tokens', [])
                    for token in tokens:
                        if (token.get('exchange', '').lower() == exchange.lower() and
                            token.get('symbol', '') == symbol):

                            timestamp = scan_data.get('timestamp', current_date.isoformat())
                            spread_pct = token.get('spread_pct', 0)
                            volume_24h = token.get('volume_24h', 0)

                            # Ensure values are non-negative
                            spread_pct = max(0, spread_pct)
                            volume_24h = max(0, volume_24h)

                            history_data.append({
                                'timestamp': timestamp,
                                'spread_pct': spread_pct,
                                'volume_24h': volume_24h
                            })
                            break

                except (json.JSONDecodeError, IOError):
                    pass

        current_date += timedelta(days=1)

    df = pd.DataFrame(history_data)

    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

    return df


def load_depth_history(exchange: str, symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Load depth history (2%, 5%, 10%) from premium pool snapshots for area chart

    Premium pool tokens have 1-minute snapshot data stored in JSONL format.
    Structure: premium_pool_snapshots/{exchange}_{symbol}/snapshots_{YYYY-MM-DD}.jsonl

    Returns:
        DataFrame with columns: timestamp, depth_2pct, depth_5pct, depth_10pct
    """
    snapshots_dir = Path('premium_pool_snapshots')
    if not snapshots_dir.exists():
        return pd.DataFrame(columns=['timestamp', 'depth_2pct', 'depth_5pct', 'depth_10pct'])

    # Token identifier for directory name
    token_id = f"{exchange}_{symbol}".replace('/', '_')
    token_dir = snapshots_dir / token_id

    if not token_dir.exists():
        return pd.DataFrame(columns=['timestamp', 'depth_2pct', 'depth_5pct', 'depth_10pct'])

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    history_data = []

    # Iterate through dates in range
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        filename = f"snapshots_{date_str}.jsonl"
        filepath = token_dir / filename

        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue

                        snapshot = json.loads(line)
                        timestamp = snapshot.get('timestamp')

                        # Parse timestamp to check if in range
                        try:
                            snap_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            if snap_time < start_date or snap_time > end_date:
                                continue
                        except:
                            continue

                        depth_2pct = snapshot.get('depth_2pct', 0)
                        depth_5pct = snapshot.get('depth_5pct', 0)
                        depth_10pct = snapshot.get('depth_10pct', 0)

                        # Ensure depth values are non-negative
                        depth_2pct = max(0, depth_2pct) if depth_2pct else 0
                        depth_5pct = max(0, depth_5pct) if depth_5pct else 0
                        depth_10pct = max(0, depth_10pct) if depth_10pct else 0

                        history_data.append({
                            'timestamp': timestamp,
                            'depth_2pct': depth_2pct,
                            'depth_5pct': depth_5pct,
                            'depth_10pct': depth_10pct
                        })

            except (json.JSONDecodeError, IOError):
                pass

        current_date += timedelta(days=1)

    df = pd.DataFrame(history_data)

    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

    return df


def calculate_score(actual_value: float, target_value: float,
                    is_lower_better: bool = False) -> int:
    """
    Calculate score (0-100) based on actual vs target value

    Args:
        actual_value: Current measured value
        target_value: Target/threshold value
        is_lower_better: True if lower values are better (e.g., spread)
                        False if higher values are better (e.g., depth, volume)

    Returns:
        Score from 0 to 100
    """
    if target_value == 0:
        return 0

    if is_lower_better:
        # Lower is better (spread)
        # If actual <= target, score = 100
        # If actual > target, score decreases
        if actual_value <= target_value:
            return 100
        else:
            # Exponential decay: score drops quickly as actual exceeds target
            ratio = actual_value / target_value
            score = max(0, 100 - (ratio - 1) * 50)
            return int(score)
    else:
        # Higher is better (depth, volume)
        # If actual >= target, score = 100
        # If actual < target, score = (actual/target) * 100
        if actual_value >= target_value:
            return 100
        else:
            score = (actual_value / target_value) * 100
            return int(min(100, score))


def calculate_violation_rate(scan_aggregate: Dict) -> float:
    """
    Calculate violation rate from scan_aggregate data

    Args:
        scan_aggregate: Aggregate data containing violation_rate field

    Returns:
        Violation rate as percentage (0-100)
    """
    violation_rate = scan_aggregate.get('violation_rate', 0)
    return round(violation_rate * 100, 1)


def get_token_data(exchange: str, symbol: str) -> Optional[Dict]:
    """
    Get token data from tokens_unified.json

    Args:
        exchange: Exchange ID
        symbol: Trading symbol

    Returns:
        Token data dictionary or None if not found
    """
    token_id = f"{exchange}_{symbol}".replace('/', '_').lower()

    # Try multiple file locations
    file_paths = [
        'data/tokens_unified.json',
        'data/tokens_unified.json',
        Path('..') / 'data/tokens_unified.json'
    ]

    for filepath in file_paths:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_tokens = json.load(f)
                return all_tokens.get(token_id)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    return None


def get_thresholds(exchange: str) -> Dict[str, float]:
    """
    Get thresholds for an exchange from scanner_config.json

    Args:
        exchange: Exchange ID

    Returns:
        Dictionary with spread_threshold, depth_threshold, volume_threshold
    """
    default_thresholds = {
        'spread_threshold': 2.0,
        'depth_threshold': 500.0,
        'volume_threshold': 10000.0
    }

    file_paths = [
        'config/scanner_config.json',
        'data/scanner_config.json',
        Path('..') / 'config/scanner_config.json'
    ]

    for filepath in file_paths:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
                exchange_config = config.get('exchanges', {}).get(exchange.lower(), {})

                return {
                    'spread_threshold': exchange_config.get('spread_threshold', default_thresholds['spread_threshold']),
                    'depth_threshold': exchange_config.get('depth_threshold', default_thresholds['depth_threshold']),
                    'volume_threshold': exchange_config.get('volume_threshold', default_thresholds['volume_threshold'])
                }
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    return default_thresholds


def load_deposit_history(exchange: str, symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Load deposit balance history from deposit_history files

    Args:
        exchange: Exchange ID (e.g., 'gateio', 'mexc')
        symbol: Trading symbol (e.g., 'BTC/USDT')
        days: Number of days to load (default 30)

    Returns:
        DataFrame with columns: timestamp, balance, market_cap_usd, movement_pct
    """
    deposit_history_dir = Path('deposit_history')
    if not deposit_history_dir.exists():
        return pd.DataFrame(columns=['timestamp', 'balance', 'market_cap_usd', 'movement_pct'])

    # Token identifier for file name
    token_id = f"{exchange}_{symbol}".replace('/', '_').lower()
    history_file = deposit_history_dir / f"{token_id}_deposit_history.jsonl"

    if not history_file.exists():
        return pd.DataFrame(columns=['timestamp', 'balance', 'market_cap_usd', 'movement_pct'])

    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    history_data = []

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                record = json.loads(line)
                timestamp_str = record.get('timestamp')

                # Parse timestamp to check if in range
                try:
                    record_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if record_time < start_date or record_time > end_date:
                        continue
                except:
                    continue

                history_data.append({
                    'timestamp': timestamp_str,
                    'balance': record.get('balance', 0),
                    'market_cap_usd': record.get('market_cap_usd', 0),
                    'movement_pct': record.get('movement_pct', 0),
                    'movement_detected': record.get('movement_detected', False)
                })

    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to read deposit history: {e}")

    df = pd.DataFrame(history_data)

    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

    return df


def calculate_deposit_score(token_data: Dict, target_deposit: Optional[float] = None) -> Tuple[int, float]:
    """
    Calculate deposit market cap score (0-100) for Phase 3

    Score Logic:
    - If deposit data is unavailable: Return (0, 0)
    - If deposit is within 10% of target: Score 100
    - If deposit deviates >10%: Score decreases
    - Violation rate = average deviation percentage over last 30 days

    Args:
        token_data: Token data from tokens_unified.json
        target_deposit: Optional target deposit balance (from custom_monitoring)

    Returns:
        Tuple of (score, violation_rate)
    """
    exchange_deposit = token_data.get('exchange_deposit', {})
    current_balance = exchange_deposit.get('current_balance')

    if current_balance is None:
        return (0, 0.0)

    # Use custom target or default to current balance as baseline
    custom_monitoring = token_data.get('custom_monitoring', {})
    if custom_monitoring.get('enabled') and custom_monitoring.get('target_deposit_balance'):
        target = custom_monitoring['target_deposit_balance']
    elif target_deposit:
        target = target_deposit
    else:
        # If no target, score based on percentage of supply
        percentage = exchange_deposit.get('percentage_of_supply', 0)
        # Ideal range: 5-15% of supply on exchange
        # Too low = illiquid, too high = centralization risk
        if 5 <= percentage <= 15:
            score = 100
        elif percentage < 5:
            score = int(percentage / 5 * 100)
        else:
            # Penalty for >15%
            score = max(0, int(100 - (percentage - 15) * 3))

        # For violation rate, use movement percentage
        violation_rate = exchange_deposit.get('movement_pct', 0)
        return (score, min(violation_rate, 100.0))

    # Calculate deviation from target
    deviation_pct = abs(current_balance - target) / target * 100 if target > 0 else 0

    if deviation_pct <= 10:
        score = 100
    elif deviation_pct <= 20:
        score = 90 - int((deviation_pct - 10) * 2)
    elif deviation_pct <= 50:
        score = 70 - int((deviation_pct - 20) * 1.5)
    else:
        score = max(0, 25 - int((deviation_pct - 50) / 2))

    # Calculate violation rate from historical data
    # Load last 30 days of deposit history to calculate average deviation
    exchange = token_data.get('exchange', '')
    symbol = token_data.get('symbol', '')

    if exchange and symbol:
        deposit_history = load_deposit_history(exchange, symbol, days=30)

        if not deposit_history.empty and target > 0:
            # Calculate deviation for each historical record
            deposit_history['deviation_pct'] = (
                (deposit_history['balance'] - target).abs() / target * 100
            )
            # Violation rate = % of time deviation > 10%
            violations = (deposit_history['deviation_pct'] > 10).sum()
            total_records = len(deposit_history)
            violation_rate = (violations / total_records * 100) if total_records > 0 else deviation_pct
        else:
            violation_rate = deviation_pct
    else:
        violation_rate = deviation_pct

    return (score, min(violation_rate, 100.0))


def calculate_summary_scores(token_data: Dict, thresholds: Dict) -> Dict[str, Tuple[int, float]]:
    """
    Calculate all summary scores for the top summary box

    Args:
        token_data: Token data from tokens_unified.json
        thresholds: Threshold values from scanner_config.json

    Returns:
        Dictionary with keys: depth_score, spread_score, volume_score, deposit_score
        Each value is a tuple of (score, violation_rate)
    """
    scan_aggregate = token_data.get('scan_aggregate', {})
    current_snapshot = token_data.get('current_snapshot', {})

    # Get current values (prefer current_snapshot, fallback to aggregate)
    avg_depth = current_snapshot.get('depth_2pct') or scan_aggregate.get('avg_depth_2pct', 0)
    avg_spread = current_snapshot.get('spread_pct') or scan_aggregate.get('avg_spread_pct', 0)
    avg_volume = current_snapshot.get('volume_24h') or scan_aggregate.get('avg_volume_24h', 0)

    # Calculate scores
    depth_score = calculate_score(avg_depth, thresholds['depth_threshold'], is_lower_better=False)
    spread_score = calculate_score(avg_spread, thresholds['spread_threshold'], is_lower_better=True)
    volume_score = calculate_score(avg_volume, thresholds['volume_threshold'], is_lower_better=False)

    # Phase 3: Calculate deposit score
    deposit_score_tuple = calculate_deposit_score(token_data)

    # Get violation rate
    violation_rate = calculate_violation_rate(scan_aggregate)

    return {
        'depth_score': (depth_score, violation_rate),
        'spread_score': (spread_score, violation_rate),
        'volume_score': (volume_score, violation_rate),
        'deposit_score': deposit_score_tuple  # (score, violation_rate) already included
    }
