#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan Monitoring Dashboard
========================
Scan Coordinator 모니터링: 정규스캔, 프리미엄풀, 마이크로버스트
"""

import streamlit as st
import json
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
from pathlib import Path


def render_scan_monitor():
    """스캔 모니터링 대시보드"""
    st.title("📊 Scan Monitoring")
    st.caption("Monitor Regular Scan, Premium Pool, and Micro Burst status")

    # Tabs
    tab1, tab2 = st.tabs(["🔄 Scan Status & Statistics", "⚙️ Coordinator Status"])

    with tab1:
        _render_scan_statistics()

    with tab2:
        _render_coordinator_status()


def _render_scan_statistics():
    """스캔 통계 및 현황"""
    st.subheader("📊 Scan Statistics")

    # Load statistics files
    regular_stats = _load_json_file('scan_history/latest.json')
    premium_stats = _load_json_file('premium_pool_stats.json')
    microburst_stats = _load_json_file('micro_burst_stats.json')

    # 1. Regular Scan (2-hour interval)
    st.markdown("### 🔄 Regular Scan (2-hour interval)")
    col1, col2, col3 = st.columns(3)

    with col1:
        if regular_stats:
            last_scan = regular_stats.get('timestamp', 'N/A')
            try:
                dt = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                ago = datetime.now(timezone.utc) - dt
                hours_ago = int(ago.total_seconds() / 3600)
                mins_ago = int((ago.total_seconds() % 3600) / 60)
                st.metric("Last Scan", f"{hours_ago}h {mins_ago}m ago")
            except:
                st.metric("Last Scan", "N/A")
        else:
            st.metric("Last Scan", "N/A")

    with col2:
        if regular_stats:
            tokens = regular_stats.get('tokens', [])
            st.metric("Tokens Scanned", len(tokens))
        else:
            st.metric("Tokens Scanned", "N/A")

    with col3:
        if regular_stats:
            # Count tokens by status
            status_counts = {}
            for token in regular_stats.get('tokens', []):
                status = token.get('lifecycle', {}).get('status', 'UNKNOWN')
                status_counts[status] = status_counts.get(status, 0) + 1
            st.metric("Main Board Tokens", status_counts.get('MAIN_BOARD', 0))
        else:
            st.metric("Main Board Tokens", "N/A")

    st.markdown("---")

    # 2. Premium Pool Collection (1-minute interval)
    st.markdown("### ⭐ Premium Pool Collection (1-minute interval)")
    col1, col2, col3 = st.columns(3)

    with col1:
        if premium_stats:
            last_collection = premium_stats.get('last_collection', 'N/A')
            try:
                dt = datetime.fromisoformat(last_collection.replace('Z', '+00:00'))
                ago = datetime.now(timezone.utc) - dt
                mins_ago = int(ago.total_seconds() / 60)
                secs_ago = int(ago.total_seconds() % 60)
                st.metric("Last Collection", f"{mins_ago}m {secs_ago}s ago")
            except:
                st.metric("Last Collection", "N/A")
        else:
            st.metric("Last Collection", "N/A")

    with col2:
        if premium_stats:
            collected = premium_stats.get('tokens_collected', 0)
            st.metric("Tokens Collected", collected)
        else:
            st.metric("Tokens Collected", "N/A")

    with col3:
        if premium_stats:
            rate = premium_stats.get('collection_rate', 0)
            st.metric("Success Rate", f"{rate:.1f}%")
        else:
            st.metric("Success Rate", "N/A")

    st.markdown("---")

    # 3. Micro Burst (5-minute interval)
    st.markdown("### ⚡ Micro Burst Analysis (5-minute interval)")
    col1, col2, col3 = st.columns(3)

    with col1:
        if microburst_stats:
            last_burst = microburst_stats.get('last_analysis', 'N/A')
            try:
                dt = datetime.fromisoformat(last_burst.replace('Z', '+00:00'))
                ago = datetime.now(timezone.utc) - dt
                mins_ago = int(ago.total_seconds() / 60)
                secs_ago = int(ago.total_seconds() % 60)
                st.metric("Last Analysis", f"{mins_ago}m {secs_ago}s ago")
            except:
                st.metric("Last Analysis", "N/A")
        else:
            st.metric("Last Analysis", "N/A")

    with col2:
        if microburst_stats:
            analyzed = microburst_stats.get('tokens_analyzed', 0)
            st.metric("Tokens Analyzed", analyzed)
        else:
            st.metric("Tokens Analyzed", "N/A")

    with col3:
        if microburst_stats:
            anomalies = microburst_stats.get('anomalies_detected', 0)
            st.metric("Anomalies Detected", anomalies)
        else:
            st.metric("Anomalies Detected", "N/A")

    # Refresh button
    st.markdown("---")
    if st.button("🔄 Refresh Statistics", use_container_width=True):
        st.rerun()

    # Visual scan history (last 24 hours for premium, 14 days for regular)
    st.markdown("---")
    st.markdown("### 📅 Scan History Visualization")

    # Show current time
    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc + timedelta(hours=9)
    st.caption(f"Current Time: {now_kst.strftime('%Y-%m-%d %H:%M KST')} ({now_utc.strftime('%H:%M UTC')})")

    # Side-by-side layout for Premium Pool and Regular Scan
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Premium Pool - Last 24 hours (1-minute intervals = 1440 data points)
        st.markdown("#### ⭐ Premium Pool (Last 24h)")
        st.caption("Each dot = 1 minute")
        _render_premium_pool_heatmap()

    with col_right:
        # Regular Scan - Last 14 days (2-hour intervals = 12 per day)
        st.markdown("#### 🔄 Regular Scan (Last 14 Days)")
        st.caption("Each box = 2 hours")
        _render_regular_scan_heatmap()


def _render_coordinator_status():
    """Scan Coordinator 상태"""
    st.subheader("⚙️ Scan Coordinator Status")

    # Coordinator가 실행 중인지 확인 (coordinator_status.json 또는 프로세스 체크)
    coordinator_running = _check_coordinator_running()

    if coordinator_running:
        st.success("✅ Scan Coordinator is RUNNING")
    else:
        st.error("❌ Scan Coordinator is NOT running")
        st.warning("Start coordinator with: `python scan_coordinator.py start`")

    st.markdown("---")

    # Scan intervals
    st.markdown("### ⏱️ Scan Intervals")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🔄 Regular Scan**")
        st.info("Every 2 hours")
        st.caption("Full scan of all tracked tokens")

    with col2:
        st.markdown("**⭐ Premium Pool**")
        st.info("Every 1 minute")
        st.caption("High-resolution premium token monitoring")

    with col3:
        st.markdown("**⚡ Micro Burst**")
        st.info("Every 5 minutes")
        st.caption("Quick anomaly detection for main board tokens")

    st.markdown("---")

    # Latest scan times
    st.markdown("### 🕐 Next Scheduled Scans")

    regular_stats = _load_json_file('scan_history/latest.json')
    premium_stats = _load_json_file('premium_pool_stats.json')
    microburst_stats = _load_json_file('micro_burst_stats.json')

    col1, col2, col3 = st.columns(3)

    with col1:
        if regular_stats:
            last_scan = regular_stats.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                next_scan = dt + timedelta(hours=2)
                remaining = next_scan - datetime.now(timezone.utc)

                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() / 3600)
                    mins = int((remaining.total_seconds() % 3600) / 60)
                    st.metric("Regular Scan", f"in {hours}h {mins}m")
                else:
                    st.metric("Regular Scan", "Overdue")
            except:
                st.metric("Regular Scan", "N/A")
        else:
            st.metric("Regular Scan", "N/A")

    with col2:
        if premium_stats:
            last_collection = premium_stats.get('last_collection', '')
            try:
                dt = datetime.fromisoformat(last_collection.replace('Z', '+00:00'))
                next_collection = dt + timedelta(minutes=1)
                remaining = next_collection - datetime.now(timezone.utc)

                if remaining.total_seconds() > 0:
                    secs = int(remaining.total_seconds())
                    st.metric("Premium Pool", f"in {secs}s")
                else:
                    st.metric("Premium Pool", "Overdue")
            except:
                st.metric("Premium Pool", "N/A")
        else:
            st.metric("Premium Pool", "N/A")

    with col3:
        if microburst_stats:
            last_burst = microburst_stats.get('last_analysis', '')
            try:
                dt = datetime.fromisoformat(last_burst.replace('Z', '+00:00'))
                next_burst = dt + timedelta(minutes=5)
                remaining = next_burst - datetime.now(timezone.utc)

                if remaining.total_seconds() > 0:
                    mins = int(remaining.total_seconds() / 60)
                    secs = int(remaining.total_seconds() % 60)
                    st.metric("Micro Burst", f"in {mins}m {secs}s")
                else:
                    st.metric("Micro Burst", "Overdue")
            except:
                st.metric("Micro Burst", "N/A")
        else:
            st.metric("Micro Burst", "N/A")

    st.markdown("---")

    # Coordinator statistics
    st.markdown("### 📊 Coordinator Statistics")

    # Scan coordinator가 통계를 저장한다면 여기서 표시
    try:
        tokens_file = "data/tokens_unified.json"
        if os.path.exists(tokens_file):
            with open(tokens_file, 'r', encoding='utf-8') as f:
                all_tokens = json.load(f)

            # Count by status
            status_counts = {}
            premium_count = 0

            for token_id, token_data in all_tokens.items():
                status = token_data.get('lifecycle', {}).get('status', 'UNKNOWN')
                status_counts[status] = status_counts.get(status, 0) + 1

                if token_data.get('premium_pool', {}).get('in_pool', False):
                    premium_count += 1

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Tokens", len(all_tokens))

            with col2:
                st.metric("Main Board", status_counts.get('MAIN_BOARD', 0))

            with col3:
                st.metric("Premium Pool", premium_count)

            with col4:
                st.metric("Assessment Zone", status_counts.get('ASSESSMENT_ZONE', 0))

    except Exception as e:
        st.error(f"Failed to load token statistics: {e}")


def _load_json_file(filepath):
    """JSON 파일 로드 헬퍼"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None


def _check_coordinator_running():
    """Scan Coordinator 실행 여부 확인"""
    # coordinator_status.json 파일 체크
    status_file = 'coordinator_status.json'
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
                last_heartbeat = status.get('last_heartbeat', '')

                if last_heartbeat:
                    dt = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                    ago = datetime.now(timezone.utc) - dt

                    # 5분 이내에 heartbeat가 있으면 실행 중
                    if ago.total_seconds() < 300:
                        return True
        except:
            pass

    # 프로세스 체크 (Windows)
    try:
        import subprocess
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if 'scan_coordinator.py' in result.stdout:
            return True
    except:
        pass

    return False


def _render_premium_pool_heatmap():
    """프리미엄 풀 수집 히트맵 (24시간, 1분 간격)"""
    now = datetime.now(timezone.utc)
    # Show from 24 hours ago (same hour yesterday) to current hour
    # Example: if now is 16:32, show yesterday 17:00 to today 16:59
    start_time = (now - timedelta(hours=23)).replace(minute=0, second=0, microsecond=0)

    # Check if coordinator is running
    coordinator_running = _check_coordinator_running()

    # 프리미엄 풀 토큰 중 하나를 샘플로 선택 (데이터 확인용)
    tokens_file = "data/tokens_unified.json"
    sample_token = None

    try:
        with open(tokens_file, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
            for token_id, token_data in tokens.items():
                if token_data.get('premium_pool', {}).get('in_pool', False):
                    sample_token = token_id
                    break
    except Exception as e:
        st.warning(f"Error loading premium pool tokens: {e}")
        return

    if not sample_token:
        st.warning("No premium pool tokens found")
        return

    # Check snapshot files for the sample token
    snapshots_dir = Path('premium_pool_snapshots') / sample_token

    if not snapshots_dir.exists():
        st.warning(f"No snapshot data for {sample_token}")
        return

    # 24시간을 24개 행으로 (각 행 = 1시간 = 60분)
    # Each entry: (status_code, tooltip_message, check_time)
    hours_grid = []
    last_scan_time = None
    next_scan_time = None

    for hour_offset in range(24):
        hour_start = start_time + timedelta(hours=hour_offset)
        hour_data = []

        for minute in range(60):
            check_time = hour_start + timedelta(minutes=minute)

            # Check if snapshot file exists for this minute
            date_str = check_time.strftime('%Y-%m-%d')
            snapshot_file = snapshots_dir / f"snapshots_{date_str}.jsonl"

            # Check if this is the current minute
            # Current minute = now's minute (floor to minute)
            now_minute = now.replace(second=0, microsecond=0)
            is_current_minute = (check_time == now_minute)

            # Check if this specific minute has data in the snapshot file
            has_data = False
            if snapshot_file.exists() and check_time <= now:
                # Only check past/current times - future times can't have data yet
                try:
                    # Format to match ISO timestamp format: 2025-11-03T08:17
                    check_time_iso = check_time.strftime('%Y-%m-%dT%H:%M')
                    with open(snapshot_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                data = json.loads(line.strip())
                                # Match ISO format timestamp (first 16 chars: YYYY-MM-DDTHH:MM)
                                if data.get('timestamp', '').startswith(check_time_iso):
                                    has_data = True
                                    break
                            except:
                                continue
                except:
                    pass

            # Priority: current minute > has data > future > past
            if is_current_minute:
                # Current minute - scan should be happening now
                if has_data:
                    last_scan_time = check_time
                    hour_data.append((1, '', check_time))  # Green (completed)
                else:
                    hour_data.append((3, '', check_time))  # Pink/Rose (in progress)
            elif has_data:
                last_scan_time = check_time
                hour_data.append((1, '', check_time))  # Green (exists)
            elif check_time > now:
                # Future - check if next scheduled minute
                time_diff = (check_time - now).total_seconds()
                if time_diff <= 120 and coordinator_running:  # Within 2 minutes
                    if next_scan_time is None:
                        next_scan_time = check_time
                    hour_data.append((2, '', check_time))  # Yellow blinking (next scheduled)
                else:
                    hour_data.append((-1, '', check_time))  # Future (gray filled)
            else:
                # Past minute without snapshot - failed scan
                time_str = check_time.strftime('%Y-%m-%d %H:%M UTC')
                tooltip = f'Scan failed at {time_str}\\nNo snapshot data collected'
                hour_data.append((0, tooltip, check_time))  # Red (failed)

        hours_grid.append(hour_data)

    # CSS for blinking animation
    blink_css = """
    <style>
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    .blinking {
        animation: blink 1s infinite;
    }
    </style>
    """

    # Display as a simple grid using HTML/CSS
    # Add header row with time markers (every 20 minutes)
    html_grid = blink_css + '<div style="display: flex; flex-direction: column; gap: 2px;">'

    # Header with timezone and time markers
    html_grid += '<div style="display: flex; align-items: center; gap: 5px; margin-bottom: 5px;">'
    html_grid += '<span style="width: 80px; font-size: 10px; font-weight: bold; color: #666;">KST</span>'
    html_grid += '<div style="display: flex; position: relative;">'

    # Time markers every 20 minutes (3 per hour, so 72 total markers for 24 hours)
    for i in range(0, 60, 20):
        marker_pos = i * 8 + (i * 1 / 60)  # 8px per minute + 1px gap adjustment
        html_grid += f'<div style="position: absolute; left: {marker_pos}px; width: 1px; height: 5px; background-color: #999;"></div>'

    html_grid += '</div></div>'

    for hour_idx, hour_data in enumerate(hours_grid):
        hour_time_utc = start_time + timedelta(hours=hour_idx)
        hour_time_kst = hour_time_utc + timedelta(hours=9)
        hour_label = hour_time_kst.strftime('%H:00')

        # Check if this is the current hour
        is_current_hour = (now >= hour_time_utc and now < hour_time_utc + timedelta(hours=1))
        now_marker = ' ← NOW' if is_current_hour else ''

        html_grid += f'<div style="display: flex; align-items: center; gap: 5px;">'
        html_grid += f'<span style="width: 80px; font-size: 10px; font-weight: {"bold" if is_current_hour else "normal"};">{hour_label}{now_marker}</span>'
        html_grid += '<div style="display: flex; gap: 1px; position: relative;">'

        for minute_idx, (status_code, tooltip, check_time) in enumerate(hour_data):
            # Add vertical grid line at 20 and 40 minutes (세로 수직선)
            if minute_idx == 20 or minute_idx == 40:
                html_grid += f'<div style="width: 3px; height: 12px; background-color: #333; margin: 0 3px;"></div>'
            # Check if this is the last scan or next scan
            is_last_scan = (last_scan_time and check_time == last_scan_time)
            is_next_scan = (next_scan_time and check_time == next_scan_time)

            # Add border for special scans
            border_style = ""
            if is_last_scan:
                border_style = "border: 2px solid #007bff;"  # Blue border for last scan
            elif is_next_scan:
                border_style = "border: 2px solid #ffc107;"  # Yellow border for next scan

            if status_code == 3:  # Current minute (pink/rose)
                html_grid += f'<div style="width: 8px; height: 12px; background-color: #ff69b4; border-radius: 2px; box-shadow: 0 1px 3px rgba(255,105,180,0.4); {border_style}"></div>'
            elif status_code == 2:  # Blinking (next scheduled)
                html_grid += f'<div class="blinking" style="width: 8px; height: 12px; background-color: #ffc107; border-radius: 2px; box-shadow: 0 1px 3px rgba(255,193,7,0.4); {border_style}"></div>'
            elif status_code == 1:  # Green (exists)
                html_grid += f'<div style="width: 8px; height: 12px; background-color: #28a745; border-radius: 2px; box-shadow: 0 1px 2px rgba(40,167,69,0.3); {border_style}"></div>'
            elif status_code == -1:  # Future (gray filled)
                html_grid += f'<div style="width: 8px; height: 12px; background-color: #e0e0e0; border-radius: 2px;"></div>'
            else:  # Red (failed) - with tooltip
                tooltip_escaped = tooltip.replace("'", "&apos;").replace('"', "&quot;")
                html_grid += f'<div title="{tooltip_escaped}" style="width: 8px; height: 12px; background-color: #dc3545; border-radius: 2px; box-shadow: 0 1px 3px rgba(220,53,69,0.4); cursor: help;"></div>'

        html_grid += '</div></div>'

    html_grid += '</div>'

    st.markdown(html_grid, unsafe_allow_html=True)

    # Legend and Summary
    st.caption("🟢 Collected | 🔴 Failed | 🌸 Current | 🟡 Next scheduled | ⬜ Future")

    total_minutes = sum(1 for hour in hours_grid for status, _, _ in hour if status == 1)
    failed_minutes = sum(1 for hour in hours_grid for status, _, _ in hour if status == 0)
    coverage_pct = (total_minutes / (24 * 60)) * 100
    st.caption(f"Coverage: {total_minutes}/1440 minutes ({coverage_pct:.1f}%) | Failed: {failed_minutes}")

    # Show last scan and next scan info
    if last_scan_time:
        time_since_last = (now - last_scan_time).total_seconds()
        if time_since_last < 60:
            last_scan_str = f"{int(time_since_last)}s ago"
        elif time_since_last < 3600:
            last_scan_str = f"{int(time_since_last / 60)}m ago"
        else:
            last_scan_str = f"{int(time_since_last / 3600)}h ago"
        st.caption(f"🔵 Last scan: {last_scan_str}")

    if coordinator_running and next_scan_time:
        time_until_next = (next_scan_time - now).total_seconds()
        if time_until_next < 60:
            next_scan_str = f"in {int(time_until_next)}s"
        else:
            next_scan_str = f"in {int(time_until_next / 60)}m"
        st.caption(f"🟡 Next scan: {next_scan_str}")
    elif not coordinator_running:
        st.caption("⚠️ Coordinator not running - no new collections scheduled")


def _render_regular_scan_heatmap():
    """정규 스캔 히트맵 (14일, 2시간 간격)"""
    now = datetime.now(timezone.utc)
    # Show past 13 days + today = 14 days total
    # Last row is today, showing all time slots including future (in gray)
    start_date = (now - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if coordinator is running
    coordinator_running = _check_coordinator_running()

    # Check scan_history files
    scan_history_dir = Path('scan_history')

    if not scan_history_dir.exists():
        st.warning("No scan history found")
        return

    # 14일 x 12개 (2시간 간격)
    # Each entry: (status_code, tooltip_message, check_time)
    days_grid = []
    last_scan_time = None
    next_scan_time = None

    for day_offset in range(14):
        day_start = start_date + timedelta(days=day_offset)
        day_data = []

        for slot in range(12):  # 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
            check_time = day_start + timedelta(hours=slot * 2)

            # Check if scan file exists
            # Format: scan_history/YYYYMMDD_HH.json
            date_str = check_time.strftime('%Y%m%d')
            hour_str = check_time.strftime('%H')
            scan_file = scan_history_dir / f"{date_str}_{hour_str}.json"

            # Check if this is the current slot
            # Current slot = the slot that should be running now or next
            # Scan runs at 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
            # Example: if now=16:32, current slot is 16:00
            current_slot_hour = (now.hour // 2) * 2
            is_current_slot = (check_time.hour == current_slot_hour and check_time.date() == now.date())

            # Priority: current slot > file exists > future > past
            if is_current_slot:
                # Current slot - scan should be happening now or will happen soon
                if scan_file.exists():
                    last_scan_time = check_time
                    day_data.append((1, '', check_time))  # Green (completed)
                else:
                    day_data.append((3, '', check_time))  # Pink/Rose (in progress)
            elif scan_file.exists():
                last_scan_time = check_time  # Track most recent successful scan
                day_data.append((1, '', check_time))  # Green (exists)
            elif check_time > now:
                # Future - check if next scheduled scan
                time_diff = (check_time - now).total_seconds()
                if time_diff <= 7200 and coordinator_running:  # Within 2 hours
                    if next_scan_time is None:
                        next_scan_time = check_time
                    day_data.append((2, '', check_time))  # Yellow blinking (next scheduled)
                else:
                    day_data.append((-1, '', check_time))  # Future (gray filled)
            else:
                # Past slot without scan file - failed scan
                time_str = check_time.strftime('%Y-%m-%d %H:%M UTC')
                tooltip = f'Scan failed at {time_str}\\nNo scan data found'
                day_data.append((0, tooltip, check_time))  # Red (failed)

        days_grid.append(day_data)

    # CSS for blinking animation
    blink_css = """
    <style>
    @keyframes blink-scan {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    .blinking-scan {
        animation: blink-scan 1s infinite;
    }
    </style>
    """

    # Display as grid
    html_grid = blink_css + '<div style="display: flex; flex-direction: column; gap: 2px;">'

    # Header with timezone indicator
    html_grid += '<div style="display: flex; align-items: center; gap: 5px; margin-bottom: 5px;">'
    html_grid += '<span style="width: 80px; font-size: 10px; font-weight: bold; color: #666;">UTC</span>'
    html_grid += '<div style="display: flex; gap: 3px;">'

    # Add time markers for every 8 hours (4 markers per day)
    for slot in range(12):
        hour = slot * 2
        if hour % 8 == 0:
            html_grid += f'<span style="font-size: 8px; color: #999; width: 20px; text-align: center;">{hour:02d}</span>'
        else:
            html_grid += f'<span style="width: 20px;"></span>'

    html_grid += '</div></div>'

    for day_idx, day_data in enumerate(days_grid):
        day_time_utc = start_date + timedelta(days=day_idx)
        day_date_utc = day_time_utc.strftime('%m/%d')

        # Check if this is today
        today_utc = now.date()
        is_today = (day_time_utc.date() == today_utc)
        today_marker = ' ← TODAY' if is_today else ''

        html_grid += f'<div style="display: flex; align-items: center; gap: 5px;">'
        html_grid += f'<span style="width: 80px; font-size: 10px; font-weight: {"bold" if is_today else "normal"};">{day_date_utc}{today_marker}</span>'
        html_grid += '<div style="display: flex; gap: 3px; position: relative;">'

        for slot_idx, (status_code, tooltip, check_time) in enumerate(day_data):
            # Add vertical grid line at 08:00 and 16:00 (slot 4 and slot 8) - 세로 수직선
            # Slot 0=00:00, 1=02:00, 2=04:00, 3=06:00, 4=08:00, 5=10:00, 6=12:00, 7=14:00, 8=16:00...
            if slot_idx == 4 or slot_idx == 8:
                html_grid += f'<div style="width: 3px; height: 20px; background-color: #333; margin: 0 5px;"></div>'
            # Check if this is the last scan or next scan
            is_last_scan = (last_scan_time and check_time == last_scan_time)
            is_next_scan = (next_scan_time and check_time == next_scan_time)

            # Add border for special scans
            border_style = ""
            if is_last_scan:
                border_style = "border: 3px solid #007bff;"  # Blue border for last scan
            elif is_next_scan:
                border_style = "border: 3px solid #ffc107;"  # Yellow border for next scan

            if status_code == 3:  # Current slot (pink/rose)
                html_grid += f'<div style="width: 20px; height: 20px; background-color: #ff69b4; border-radius: 3px; {border_style}"></div>'
            elif status_code == 2:  # Blinking (next scheduled)
                html_grid += f'<div class="blinking-scan" style="width: 20px; height: 20px; background-color: #ffc107; border-radius: 3px; {border_style}"></div>'
            elif status_code == 1:  # Green (exists)
                html_grid += f'<div style="width: 20px; height: 20px; background-color: #28a745; border-radius: 3px; {border_style}"></div>'
            elif status_code == -1:  # Future (gray filled)
                html_grid += f'<div style="width: 20px; height: 20px; background-color: #e0e0e0; border-radius: 3px;"></div>'
            else:  # Red (failed) - with tooltip
                tooltip_escaped = tooltip.replace("'", "&apos;").replace('"', "&quot;")
                html_grid += f'<div title="{tooltip_escaped}" style="width: 20px; height: 20px; background-color: #dc3545; border-radius: 3px; cursor: help;"></div>'

        html_grid += '</div></div>'

    html_grid += '</div>'

    st.markdown(html_grid, unsafe_allow_html=True)

    # Legend and Summary
    st.caption("🟢 Completed | 🔴 Failed | 🌸 Current | 🟡 Next scheduled | ⬜ Future")

    total_scans = sum(1 for day in days_grid for status, _, _ in day if status == 1)
    failed_scans = sum(1 for day in days_grid for status, _, _ in day if status == 0)
    expected_scans = 14 * 12
    coverage_pct = (total_scans / expected_scans) * 100
    st.caption(f"Completed: {total_scans}/{expected_scans} scans ({coverage_pct:.1f}%) | Failed: {failed_scans}")

    # Show last scan and next scan info
    if last_scan_time:
        time_since_last = (now - last_scan_time).total_seconds()
        if time_since_last < 60:
            last_scan_str = f"{int(time_since_last)}s ago"
        elif time_since_last < 3600:
            last_scan_str = f"{int(time_since_last / 60)}m ago"
        else:
            last_scan_str = f"{int(time_since_last / 3600)}h ago"
        st.caption(f"🔵 Last scan: {last_scan_str}")

    if coordinator_running and next_scan_time:
        time_until_next = (next_scan_time - now).total_seconds()
        if time_until_next < 60:
            next_scan_str = f"in {int(time_until_next)}s"
        else:
            next_scan_str = f"in {int(time_until_next / 60)}m"
        st.caption(f"🟡 Next scan: {next_scan_str}")
    elif not coordinator_running:
        st.caption("⚠️ Coordinator not running - no new scans scheduled")












