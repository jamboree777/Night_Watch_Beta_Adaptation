"""
Time-Series Data Helper for 1-Minute Snapshots
================================================
Handles loading and aggregating premium pool 1-minute snapshot data
for various time ranges: 8h, 48h, 7w, 30d
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class TimeSeriesHelper:
    """Helper for loading and aggregating time-series snapshot data"""

    def __init__(self, snapshots_dir='premium_pool_snapshots'):
        self.snapshots_dir = Path(snapshots_dir)

    def load_snapshots(self, exchange: str, symbol: str, hours_back: int) -> List[Dict]:
        """
        Load snapshots for given time range

        Args:
            exchange: Exchange ID (e.g., 'gateio')
            symbol: Trading pair (e.g., 'BTC/USDT')
            hours_back: How many hours to look back

        Returns:
            List of snapshot dictionaries, sorted by timestamp
        """
        token_dir = self.snapshots_dir / f"{exchange}_{symbol.replace('/', '_')}"

        if not token_dir.exists():
            return []

        snapshots = []
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours_back)

        # Calculate which date files to read
        days_to_check = (hours_back // 24) + 2  # Extra day for safety

        for days_ago in range(days_to_check):
            check_date = now - timedelta(days=days_ago)
            date_str = check_date.strftime('%Y-%m-%d')
            snapshot_file = token_dir / f"snapshots_{date_str}.jsonl"

            if not snapshot_file.exists():
                continue

            # Read JSONL file
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue

                        snapshot = json.loads(line)
                        snapshot_time = datetime.fromisoformat(
                            snapshot['timestamp'].replace('Z', '+00:00')
                        )

                        if snapshot_time >= cutoff_time:
                            snapshots.append(snapshot)
            except Exception as e:
                print(f"[WARN] Failed to read {snapshot_file}: {e}")
                continue

        # Sort by timestamp
        snapshots.sort(key=lambda x: x['timestamp'])
        return snapshots

    def aggregate_snapshots(self, snapshots: List[Dict], interval_minutes: int) -> List[Dict]:
        """
        Aggregate snapshots into larger time intervals

        Args:
            snapshots: List of snapshot dictionaries
            interval_minutes: Aggregation interval (5, 15, 60)

        Returns:
            List of aggregated data points
        """
        if not snapshots:
            return []

        aggregated = []
        current_bucket = []
        bucket_start_time = None

        for snapshot in snapshots:
            snap_time = datetime.fromisoformat(
                snapshot['timestamp'].replace('Z', '+00:00')
            )

            # Determine bucket start time (round down to interval)
            bucket_time = snap_time.replace(
                minute=(snap_time.minute // interval_minutes) * interval_minutes,
                second=0,
                microsecond=0
            )

            if bucket_start_time is None:
                bucket_start_time = bucket_time

            # If we've moved to a new bucket, aggregate the previous one
            if bucket_time != bucket_start_time:
                if current_bucket:
                    aggregated.append(self._aggregate_bucket(current_bucket, bucket_start_time))
                current_bucket = [snapshot]
                bucket_start_time = bucket_time
            else:
                current_bucket.append(snapshot)

        # Don't forget the last bucket
        if current_bucket:
            aggregated.append(self._aggregate_bucket(current_bucket, bucket_start_time))

        return aggregated

    def _aggregate_bucket(self, bucket: List[Dict], timestamp: datetime) -> Dict:
        """Aggregate a bucket of snapshots into single data point"""
        if not bucket:
            return {}

        # Calculate averages
        spread_pcts = [s.get('spread_pct', 0) for s in bucket if s.get('spread_pct')]
        depth_2pcts = [s.get('depth_2pct', 0) for s in bucket if s.get('depth_2pct')]
        volumes = [s.get('volume_24h', 0) for s in bucket if s.get('volume_24h')]

        return {
            'timestamp': timestamp.isoformat(),
            'spread_pct': sum(spread_pcts) / len(spread_pcts) if spread_pcts else 0,
            'depth_2pct': sum(depth_2pcts) / len(depth_2pcts) if depth_2pcts else 0,
            'volume_24h': sum(volumes) / len(volumes) if volumes else 0,
            'sample_count': len(bucket),
            'min_spread': min(spread_pcts) if spread_pcts else 0,
            'max_spread': max(spread_pcts) if spread_pcts else 0,
            'min_depth': min(depth_2pcts) if depth_2pcts else 0,
            'max_depth': max(depth_2pcts) if depth_2pcts else 0,
        }

    def get_timeseries_data(self, exchange: str, symbol: str, range_name: str) -> Dict:
        """
        Get time-series data for specified range

        Args:
            exchange: Exchange ID
            symbol: Trading pair
            range_name: '8h', '48h', '7w', or '30d'

        Returns:
            Dictionary with timestamps, spreads, depths, volumes
        """
        # Define range parameters
        range_config = {
            '24h': {'hours': 24, 'interval_minutes': 1},      # 24 hours, 1-min interval
            '72h': {'hours': 72, 'interval_minutes': 5},      # 72 hours (3 days), 5-min interval
            '7d': {'hours': 7 * 24, 'interval_minutes': 15},  # 7 days, 15-min interval
            '30d': {'hours': 30 * 24, 'interval_minutes': 60} # 30 days, 1-hour interval
        }

        if range_name not in range_config:
            return {'error': f'Invalid range: {range_name}'}

        config = range_config[range_name]

        # Load snapshots
        snapshots = self.load_snapshots(exchange, symbol, config['hours'])

        if not snapshots:
            return {
                'range': range_name,
                'data_points': 0,
                'timestamps': [],
                'spreads': [],
                'depths': [],
                'volumes': [],
                'error': 'No snapshot data available'
            }

        # Aggregate if needed
        if config['interval_minutes'] > 1:
            data_points = self.aggregate_snapshots(snapshots, config['interval_minutes'])
        else:
            data_points = snapshots

        # Extract arrays for charting
        timestamps = []
        spreads = []
        depths = []
        volumes = []

        for point in data_points:
            timestamps.append(point['timestamp'])
            spreads.append(point.get('spread_pct', 0))
            depths.append(point.get('depth_2pct', 0))
            volumes.append(point.get('volume_24h', 0))

        # Calculate statistics
        valid_spreads = [s for s in spreads if s > 0]
        valid_depths = [d for d in depths if d > 0]
        valid_volumes = [v for v in volumes if v > 0]

        return {
            'range': range_name,
            'data_points': len(data_points),
            'timestamps': timestamps,
            'spreads': spreads,
            'depths': depths,
            'volumes': volumes,
            'stats': {
                'spread': {
                    'current': spreads[-1] if spreads else 0,
                    'avg': sum(valid_spreads) / len(valid_spreads) if valid_spreads else 0,
                    'min': min(valid_spreads) if valid_spreads else 0,
                    'max': max(valid_spreads) if valid_spreads else 0
                },
                'depth': {
                    'current': depths[-1] if depths else 0,
                    'avg': sum(valid_depths) / len(valid_depths) if valid_depths else 0,
                    'min': min(valid_depths) if valid_depths else 0,
                    'max': max(valid_depths) if valid_depths else 0
                },
                'volume': {
                    'current': volumes[-1] if volumes else 0,
                    'avg': sum(valid_volumes) / len(valid_volumes) if valid_volumes else 0,
                    'min': min(valid_volumes) if valid_volumes else 0,
                    'max': max(valid_volumes) if valid_volumes else 0
                }
            }
        }


def format_timestamp_for_chart(timestamp_str: str, range_name: str) -> str:
    """
    Format timestamp for chart display based on range

    Args:
        timestamp_str: ISO format timestamp
        range_name: '24h', '72h', '7d', or '30d'

    Returns:
        Formatted time string
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        if range_name == '24h':
            return dt.strftime('%H:%M')  # "14:30"
        elif range_name == '72h':
            return dt.strftime('%m/%d %H:%M')  # "10/28 14:30"
        elif range_name == '7d':
            return dt.strftime('%m/%d %H:%M')  # "10/28 14:30"
        elif range_name == '30d':
            return dt.strftime('%m/%d')  # "10/28"
        else:
            return dt.strftime('%H:%M')
    except:
        return timestamp_str
