# admin_modules/admin_tokens.py
"""
Token Management Module for Admin Dashboard
Manages Main Board token posting, removal, and suspension
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# Add parent directory to path for core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Core modules
from core.config import FilePaths, TokenStatus
from core.data_manager import get_data_manager


def load_monitoring_configs():
    """Load monitoring configs (Main Board tokens from tokens_unified.json)"""
    # ✅ MIGRATION: Use DataManager from core
    try:
        dm = get_data_manager()
        main_board_tokens = dm.get_main_board_tokens()
        return main_board_tokens
    except Exception as e:
        # Streamlit-safe error handling
        if hasattr(st, 'session_state'):
            st.error(f"❌ Error loading tokens: {e}")
        return {}
    
    # Fallback to old monitoring_configs.json
    config_file = 'monitoring_configs.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                normalized = {}
                for key, value in data.items():
                    normalized[key.lower()] = value
                return normalized
        except json.JSONDecodeError as e:
            # Streamlit-safe error handling
            pass
            return {}
    return {}


def save_monitoring_configs(configs):
    """Save monitoring configs"""
    with open('monitoring_configs.json', 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)


# load_high_risk_tokens() 삭제됨 - tokens_unified.json 사용


def load_scan_history():
    """Load scan history for detailed violation tracking"""
    history_dir = 'scan_history'
    if not os.path.exists(history_dir):
        return {}
    
    # Load scanner config to get history days
    scanner_config_file = 'config/scanner_config.json'
    history_days = 2  # default
    scan_interval_hours = 4  # default
    
    if os.path.exists(scanner_config_file):
        try:
            with open(scanner_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                history_days = config.get('global', {}).get('default_history_days', 2)
                scan_interval_hours = config.get('scheduler', {}).get('scan_interval_hours', 4)
        except:
            pass
    
    # Calculate max scans based on config
    max_scans = int((history_days * 24) / scan_interval_hours)
    
    all_history = {}
    try:
        # Get all scan history files (sorted by date), excluding latest.json
        files = sorted([
            f for f in os.listdir(history_dir)
            if f.endswith('.json') and f != 'latest.json'
        ])

        # Load recent data based on config
        for filename in files[-max_scans:]:
            file_path = os.path.join(history_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    scan_data = json.load(f)
                    
                    for token in scan_data.get('tokens', []):
                        exchange = token.get('exchange', '')
                        symbol = token.get('symbol', '').replace('/', '_').lower()
                        key = f"{exchange}_{symbol}"
                        
                        if key not in all_history:
                            all_history[key] = {
                                'depth_violations': 0,
                                'spread_violations': 0,
                                'volume_violations': 0,
                                'simultaneous_violations': 0,  # depth AND spread
                                'total_scans': 0,
                                'scan_records': []
                            }
                        
                        # Track violations
                        depth_violated = token.get('depth_2pct', 99999) < token.get('depth_threshold', 500)
                        spread_violated = token.get('spread_pct', 0) > token.get('spread_threshold', 1.0)
                        volume_violated = token.get('quote_volume', 99999) < token.get('volume_threshold', 10000)
                        
                        all_history[key]['total_scans'] += 1
                        
                        if depth_violated:
                            all_history[key]['depth_violations'] += 1
                        if spread_violated:
                            all_history[key]['spread_violations'] += 1
                        if volume_violated:
                            all_history[key]['volume_violations'] += 1
                        if depth_violated and spread_violated:
                            all_history[key]['simultaneous_violations'] += 1
                        
                        # Store recent record
                        all_history[key]['scan_records'].append({
                            'time': scan_data.get('timestamp', ''),
                            'depth': token.get('depth_2pct', 0),
                            'spread': token.get('spread_pct', 0),
                            'volume': token.get('quote_volume', 0),
                            'depth_violated': depth_violated,
                            'spread_violated': spread_violated,
                            'volume_violated': volume_violated
                        })
            except Exception as e:
                continue
    except Exception as e:
        # Streamlit-safe error handling
        pass
    
    return all_history


def calculate_grade_from_stats(violation_rate, avg_risk):
    """Calculate grade from violation rate and average risk"""
    if violation_rate >= 0.40 or avg_risk >= 0.50:
        return 'F'
    elif violation_rate >= 0.30 or avg_risk >= 0.40:
        return 'D'
    elif violation_rate >= 0.20 or avg_risk >= 0.30:
        return 'C'
    elif violation_rate >= 0.10 or avg_risk >= 0.20:
        return 'B'
    else:
        return 'A'


def load_period_averages():
    """Load 7-day, 14-day averages and latest scan data"""
    history_dir = 'scan_history'
    if not os.path.exists(history_dir):
        return {}

    # Load config
    scanner_config_file = 'config/scanner_config.json'
    scan_interval_hours = 2
    if os.path.exists(scanner_config_file):
        try:
            with open(scanner_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                scan_interval_hours = config.get('scheduler', {}).get('scan_interval_hours', 2)
        except:
            pass

    # Calculate number of scans for each period
    scans_7day = int((7 * 24) / scan_interval_hours)   # 84 scans
    scans_14day = int((14 * 24) / scan_interval_hours)  # 168 scans

    period_data = {}

    try:
        # Get all scan history files (excluding latest.json)
        files = sorted([
            f for f in os.listdir(history_dir)
            if f.endswith('.json') and f != 'latest.json'
        ])

        if not files:
            return {}

        # Load 14-day data (includes 7-day)
        for filename in files[-scans_14day:]:
            file_path = os.path.join(history_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    scan_data = json.load(f)

                    for token in scan_data.get('tokens', []):
                        exchange = token.get('exchange', '')
                        symbol = token.get('symbol', '').replace('/', '_').lower()
                        key = f"{exchange}_{symbol}"

                        if key not in period_data:
                            period_data[key] = {
                                '7day': {'violations': 0, 'total': 0, 'risk_sum': 0},
                                '14day': {'violations': 0, 'total': 0, 'risk_sum': 0},
                                'latest': {}
                            }

                        # Check violations
                        depth_violated = token.get('depth_2pct', 99999) < token.get('depth_threshold', 500)
                        spread_violated = token.get('spread_pct', 0) > token.get('spread_threshold', 1.0)
                        violated = depth_violated or spread_violated

                        # Calculate risk score (0-1)
                        risk = 0
                        if depth_violated:
                            risk += 0.5
                        if spread_violated:
                            risk += 0.5

                        # Add to 14day
                        period_data[key]['14day']['total'] += 1
                        if violated:
                            period_data[key]['14day']['violations'] += 1
                        period_data[key]['14day']['risk_sum'] += risk
            except:
                continue

        # Load 7-day data (last 7 days from 14-day)
        for filename in files[-scans_7day:]:
            file_path = os.path.join(history_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    scan_data = json.load(f)

                    for token in scan_data.get('tokens', []):
                        exchange = token.get('exchange', '')
                        symbol = token.get('symbol', '').replace('/', '_').lower()
                        key = f"{exchange}_{symbol}"

                        if key not in period_data:
                            period_data[key] = {
                                '7day': {'violations': 0, 'total': 0, 'risk_sum': 0},
                                '14day': {'violations': 0, 'total': 0, 'risk_sum': 0},
                                'latest': {}
                            }

                        # Check violations
                        depth_violated = token.get('depth_2pct', 99999) < token.get('depth_threshold', 500)
                        spread_violated = token.get('spread_pct', 0) > token.get('spread_threshold', 1.0)
                        violated = depth_violated or spread_violated

                        # Calculate risk score
                        risk = 0
                        if depth_violated:
                            risk += 0.5
                        if spread_violated:
                            risk += 0.5

                        # Add to 7day
                        period_data[key]['7day']['total'] += 1
                        if violated:
                            period_data[key]['7day']['violations'] += 1
                        period_data[key]['7day']['risk_sum'] += risk
            except:
                continue

        # Load latest scan
        if files:
            latest_file = os.path.join(history_dir, files[-1])
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    scan_data = json.load(f)

                    for token in scan_data.get('tokens', []):
                        exchange = token.get('exchange', '')
                        symbol = token.get('symbol', '').replace('/', '_').lower()
                        key = f"{exchange}_{symbol}"

                        if key not in period_data:
                            period_data[key] = {
                                '7day': {'violations': 0, 'total': 0, 'risk_sum': 0},
                                '14day': {'violations': 0, 'total': 0, 'risk_sum': 0},
                                'latest': {}
                            }

                        # Check violations
                        depth_violated = token.get('depth_2pct', 99999) < token.get('depth_threshold', 500)
                        spread_violated = token.get('spread_pct', 0) > token.get('spread_threshold', 1.0)

                        # Calculate risk score
                        risk = 0
                        if depth_violated:
                            risk += 0.5
                        if spread_violated:
                            risk += 0.5

                        period_data[key]['latest'] = {
                            'risk': risk,
                            'violated': depth_violated or spread_violated
                        }
            except:
                pass

        # Calculate grades for each period
        for key, data in period_data.items():
            # 7-day grade
            if data['7day']['total'] > 0:
                violation_rate_7 = data['7day']['violations'] / data['7day']['total']
                avg_risk_7 = data['7day']['risk_sum'] / data['7day']['total']
                data['7day']['grade'] = calculate_grade_from_stats(violation_rate_7, avg_risk_7)
                data['7day']['violation_rate'] = violation_rate_7
                data['7day']['avg_risk'] = avg_risk_7
            else:
                data['7day']['grade'] = 'N/A'

            # 14-day grade
            if data['14day']['total'] > 0:
                violation_rate_14 = data['14day']['violations'] / data['14day']['total']
                avg_risk_14 = data['14day']['risk_sum'] / data['14day']['total']
                data['14day']['grade'] = calculate_grade_from_stats(violation_rate_14, avg_risk_14)
                data['14day']['violation_rate'] = violation_rate_14
                data['14day']['avg_risk'] = avg_risk_14
            else:
                data['14day']['grade'] = 'N/A'

            # Latest grade
            if 'risk' in data['latest']:
                # Latest is single scan, so violation_rate is 0 or 1
                violation_rate_latest = 1.0 if data['latest']['violated'] else 0.0
                data['latest']['grade'] = calculate_grade_from_stats(violation_rate_latest, data['latest']['risk'])
            else:
                data['latest']['grade'] = 'N/A'

    except Exception as e:
        pass

    return period_data


def load_suspended_tokens():
    """Load suspended tokens list"""
    suspended_file = 'suspended_tokens.json'
    if os.path.exists(suspended_file):
        with open(suspended_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_suspended_tokens(suspended):
    """Save suspended tokens list"""
    with open('suspended_tokens.json', 'w', encoding='utf-8') as f:
        json.dump(suspended, f, indent=2, ensure_ascii=False)


def render_token_management():
    """Render Token Management section"""
    
    st.markdown("## 🎯 Token Management")
    st.markdown("메인보드에 게시된 토큰을 관리합니다.")
    
    # Load scanner config for dynamic settings
    scanner_config_file = 'config/scanner_config.json'
    history_days = 2  # default
    scan_interval_hours = 4  # default
    
    if os.path.exists(scanner_config_file):
        try:
            with open(scanner_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                history_days = config.get('global', {}).get('default_history_days', 2)
                scan_interval_hours = config.get('scheduler', {}).get('scan_interval_hours', 4)
        except:
            pass
    
    max_scans_window = int((history_days * 24) / scan_interval_hours)
    
    # Load data (tokens_unified.json만 사용)
    monitoring_configs = load_monitoring_configs()
    suspended_tokens = load_suspended_tokens()
    scan_history = load_scan_history()
    period_averages = load_period_averages()  # 7-day, 14-day, latest grades
    
    # Debug info with refresh functionality
    col_info, col_refresh = st.columns([3, 1])

    with col_info:
        now = datetime.now(timezone.utc)
        debug_msg = f"📊 Main Board Tokens: {len(monitoring_configs)}, Suspended: {len(suspended_tokens)}"
        debug_msg += f"\n⏰ Last Updated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        debug_msg += f"\n📁 Scan History Loaded: {len(scan_history)} tokens"

        if monitoring_configs:
            sample_token_id = list(monitoring_configs.keys())[0]
            sample_grade = monitoring_configs[sample_token_id].get('scan_aggregate', {}).get('grade', 'N/A')
            sample_scans = scan_history.get(sample_token_id, {}).get('total_scans', 0)
            debug_msg += f"\n**Sample**: `{sample_token_id}` (Grade: {sample_grade}, Scans: {sample_scans})"

        st.info(debug_msg)

    with col_refresh:
        st.markdown("") # spacing
        if st.button("🔄 Refresh Data", use_container_width=True, help="Reload token data from database"):
            st.cache_data.clear()
            st.rerun()
    
    # Filter options (moved closer to table)
    filter_exchange = "All"
    filter_grade = "All"
    filter_status = "All"
    
    # Prepare table data
    table_data = []
    for token_id, token_data in monitoring_configs.items():
        # Extract exchange and symbol from token_id (e.g., "gateio_btc_usdt")
        parts = token_id.split('_')
        if len(parts) < 3:
            continue
        
        exchange = parts[0]
        symbol = f"{parts[1].upper()}/{parts[2].upper()}"
        
        # Apply filters
        if filter_exchange != "All" and exchange != filter_exchange.lower():
            continue
        
        # Get grade from scan_aggregate
        scan_aggregate = token_data.get('scan_aggregate', {})
        grade = scan_aggregate.get('grade', 'N/A')
        
        if filter_grade != "All" and grade != filter_grade:
            continue
        
        # Check suspension status
        is_suspended = token_id in suspended_tokens
        suspension_info = suspended_tokens.get(token_id, {})
        
        if filter_status == "Active" and is_suspended:
            continue
        if filter_status == "Suspended" and not is_suspended:
            continue
        
        # Calculate suspension remaining days
        suspension_days_left = 0
        suspension_end_date = ""
        if is_suspended:
            end_date_str = suspension_info.get('suspension_end_date')
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_left = (end_date - now).days
                suspension_days_left = max(0, days_left)
                suspension_end_date = end_date.strftime('%Y-%m-%d')
        
        # Get violation history (5일간)
        history = scan_history.get(token_id, {})
        depth_violations = history.get('depth_violations', 0)
        spread_violations = history.get('spread_violations', 0)
        volume_violations = history.get('volume_violations', 0)
        simultaneous_violations = history.get('simultaneous_violations', 0)
        total_scans = history.get('total_scans', 0)
        
        # Calculate Safety status based on config (history_days)
        current_violation_rate = scan_aggregate.get('violation_rate', 0)
        current_average_risk = scan_aggregate.get('average_risk', 0)
        target_violation_rate = 0.20  # 20% (Grade C 미만)
        target_average_risk = 0.30  # Grade D 미만
        
        safety_text = ""
        
        if total_scans < max_scans_window:
            # 데이터 수집 중
            safety_text = f"Collecting data ({total_scans}/{max_scans_window})"
        else:
            # 충분한 데이터 수집 완료
            if grade in ['D', 'F']:
                # 위험 - 개선 필요
                violation_gap = current_violation_rate - target_violation_rate
                risk_gap = current_average_risk - target_average_risk
                safety_text = f"개선 필요\n  • 위반율: {current_violation_rate:.0%} → {target_violation_rate:.0%} 이하로 {violation_gap:.0%}p ↓\n  • 위험도: {current_average_risk:.2f} → {target_average_risk:.2f} 이하로 {risk_gap:.2f} ↓"
            elif grade == 'C':
                # 경고 - 주의 관찰
                violation_gap = current_violation_rate - target_violation_rate
                risk_gap = current_average_risk - 0.25  # Grade C → B 경계
                safety_text = f"주의 관찰\n  • 위반율: {current_violation_rate:.0%} → {target_violation_rate:.0%} 이하로 {violation_gap:.0%}p ↓\n  • 위험도: {current_average_risk:.2f} → 0.25 이하로 {risk_gap:.2f} ↓"
            else:  # A, B
                # 안전
                safety_text = f"안전 ✓ (위반율 {current_violation_rate:.0%}, 위험도 {current_average_risk:.2f})"
        
        # 오버레이 마크 감지
        overlay_marks = []
        
        # 1. 상폐 확인 (데이터 1일+ 없음)
        current_snapshot = token_data.get('current_snapshot', {})
        last_scanned = current_snapshot.get('last_scanned', '')
        if last_scanned:
            try:
                last_scan_time = datetime.fromisoformat(last_scanned.replace('Z', '+00:00'))
                hours_since_scan = (datetime.now(timezone.utc) - last_scan_time).total_seconds() / 3600
                if hours_since_scan > 24:
                    overlay_marks.append("⚠️상폐")
            except:
                pass
        
        # 2. ST 확인
        tags = token_data.get('tags', {})
        if tags.get('st_tagged', False):
            overlay_marks.append("🔴ST")
        
        # 3. 평가존 확인 (exchange 이름에 assessment/evaluation 포함)
        if 'assessment' in exchange or 'evaluation' in exchange or 'innovation' in exchange:
            overlay_marks.append("📊평가존")
        
        overlay_text = " ".join(overlay_marks) if overlay_marks else ""
        
        # Get lifecycle info
        lifecycle = token_data.get('lifecycle', {})
        main_board_entry = lifecycle.get('main_board_entry', 'N/A')

        # Get period grades
        period_data = period_averages.get(token_id, {})
        grade_14day = period_data.get('14day', {}).get('grade', 'N/A')
        grade_7day = period_data.get('7day', {}).get('grade', 'N/A')
        grade_latest = period_data.get('latest', {}).get('grade', 'N/A')

        # Get scan counts for 14-day and 7-day periods
        scans_14day = period_data.get('14day', {}).get('total', 0)
        scans_7day = period_data.get('7day', {}).get('total', 0)

        # Calculate Main Board entry date and next evaluation date
        entry_date_display = 'N/A'
        next_eval_display = 'N/A'

        if main_board_entry and main_board_entry != 'N/A':
            try:
                entry_dt = datetime.fromisoformat(main_board_entry.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                days_since_entry = (now - entry_dt).days

                # Show entry date if within last 14 days
                if days_since_entry <= 14:
                    entry_date_display = entry_dt.strftime('%Y-%m-%d')
                    # Next evaluation is at 14 days
                    eval_date = entry_dt + timedelta(days=14)
                    next_eval_display = eval_date.strftime('%Y-%m-%d')
                else:
                    # Been on board > 14 days
                    entry_date_display = entry_dt.strftime('%Y-%m-%d')
                    next_eval_display = '수시'  # Continuous evaluation
            except Exception as e:
                pass

        table_data.append({
            'key': token_id,
            'exchange': exchange.upper(),
            'symbol': symbol,
            'overlay_marks': overlay_text,
            'grade': grade,
            'avg_risk': current_average_risk,
            'violation_rate': current_violation_rate,
            # Period grades
            'grade_14day': grade_14day,
            'grade_7day': grade_7day,
            'grade_latest': grade_latest,
            'is_suspended': is_suspended,
            'suspension_days_left': suspension_days_left,
            'suspension_end_date': suspension_end_date,
            'added_at': main_board_entry,
            # Main Board tracking (NEW)
            'entry_date': entry_date_display,
            'next_eval': next_eval_display,
            'scans_14day': scans_14day,
            'scans_7day': scans_7day,
            # Safety evaluation
            'safety': safety_text
        })
    
    # Sort by grade (F > D > C > B > A) and then by violation rate
    grade_order = {'F': 0, 'D': 1, 'C': 2, 'B': 3, 'A': 4, 'N/A': 5}
    table_data.sort(key=lambda x: (grade_order.get(x['grade'], 5), -x['violation_rate']))
    
    # Calculate matching stats
    matched_count = sum(1 for t in table_data if t['grade'] != 'N/A')
    match_rate = (matched_count / len(table_data) * 100) if table_data else 0
    
    st.markdown(f"### 📊 Total: {len(table_data)} tokens")
    st.caption(f"Grade matched: {matched_count}/{len(table_data)} ({match_rate:.1f}%)")
    
    if not table_data:
        st.info("📭 No tokens found matching the filters.")
        return
    
    # Convert to DataFrame for display
    import pandas as pd
    
    df_display = pd.DataFrame([
        {
            '🔴': '☑' if t['is_suspended'] else '',  # Suspended 체크박스
            '#': idx + 1,
            'Exchange': t['exchange'],
            'Symbol': t['symbol'],
            'Grade': t['grade'],
            # 기간별 평점
            '14일': t['grade_14day'],
            '7일': t['grade_7day'],
            '최신': t['grade_latest'],
            'Avg Risk': f"{t['avg_risk']:.3f}",
            'Violation %': f"{t['violation_rate']*100:.1f}%",
            # 메인보드 추적 (NEW - replaces violation history)
            '진입일': t['entry_date'],
            '다음평가일': t['next_eval'],
            '14일스캔': t['scans_14day'],
            '7일스캔': t['scans_7day'],
            # 안전도 평가
            'Safety': t['safety'],
            'Susp. Days': t['suspension_days_left'] if t['is_suspended'] else '',
            'Susp. End': t['suspension_end_date'] if t['is_suspended'] and t['suspension_end_date'] else '',
        }
        for idx, t in enumerate(table_data)
    ])
    
    # Filters and Batch actions (moved closer to table)
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_exchange_display = st.selectbox(
            "Exchange Filter",
            ["All"] + sorted(list(set([k.split('_')[0] for k in monitoring_configs.keys()]))),
            key="token_mgmt_exchange_display"
        )
    
    with col2:
        filter_grade_display = st.selectbox(
            "Grade Filter",
            ["All", "F", "D", "C", "B", "A"],
            key="token_mgmt_grade_display"
        )
    
    with col3:
        filter_status_display = st.selectbox(
            "Status Filter",
            ["All", "Active", "Suspended"],
            key="token_mgmt_status_display"
        )
    
    # Apply display filters to DataFrame
    df_filtered = df_display.copy()
    if filter_exchange_display != "All":
        df_filtered = df_filtered[df_filtered['Exchange'] == filter_exchange_display.upper()]
    if filter_grade_display != "All":
        df_filtered = df_filtered[df_filtered['Grade'] == filter_grade_display]
    if filter_status_display == "Active":
        df_filtered = df_filtered[df_filtered['🔴'] == '']
    elif filter_status_display == "Suspended":
        df_filtered = df_filtered[df_filtered['🔴'] == '☑']
    
    # Batch actions (compact)
    with st.expander("🔧 Batch Actions", expanded=False):
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        
        with col1:
            batch_action = st.selectbox(
                "Action",
                ["Remove from Main Board", "Suspend (Temp)", "Suspend (Permanent)"],
                key="batch_action_select"
            )
        
        with col2:
            start_row = st.number_input("Start #", min_value=1, max_value=len(table_data), value=1, key="batch_start_row")
        
        with col3:
            end_row = st.number_input("End #", min_value=1, max_value=len(table_data), value=min(10, len(table_data)), key="batch_end_row")
        
        with col4:
            if batch_action == "Suspend (Temp)":
                batch_suspend_days = st.number_input("Days", min_value=1, max_value=365, value=7, key="batch_suspend_days")
            else:
                batch_suspend_days = None
        
        with col5:
            if st.button("Apply", key="apply_batch_action", type="primary"):
                st.session_state['confirm_batch_action'] = True
    
    # Batch action confirmation
    if st.session_state.get('confirm_batch_action', False):
        if start_row and end_row and start_row <= end_row:
            selected_tokens = table_data[start_row-1:end_row]
            
            action_type = batch_action
            if batch_action == "Suspend (Temp)":
                action_desc = f"Suspend for {batch_suspend_days} days"
            elif batch_action == "Suspend (Permanent)":
                action_desc = "Suspend permanently"
            else:
                action_desc = batch_action
            
            st.warning(f"⚠️ You are about to **{action_desc}** for {len(selected_tokens)} tokens (Row {start_row} to {end_row})")
            
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("✅ Confirm", key="confirm_batch_yes", type="primary"):
                    # Execute batch action
                    success_count = 0
                    
                    for token in selected_tokens:
                        key = token['key']
                        
                        if batch_action == "Remove from Main Board":
                            # Remove from monitoring_configs
                            if key in monitoring_configs:
                                del monitoring_configs[key]
                                success_count += 1
                            
                            # Remove from suspended if exists
                            if key in suspended_tokens:
                                del suspended_tokens[key]
                        
                        elif batch_action in ["Suspend (Temp)", "Suspend (Permanent)"]:
                            # Add to suspended_tokens
                            now = datetime.now(timezone.utc)
                            
                            if batch_action == "Suspend (Permanent)":
                                suspend_days = 36500  # 100 years
                            else:
                                suspend_days = batch_suspend_days
                            
                            end_date = now + timedelta(days=suspend_days)
                            
                            suspended_tokens[key] = {
                                'suspended_at': now.isoformat(),
                                'suspension_end_date': end_date.isoformat(),
                                'suspension_days': suspend_days,
                                'suspension_type': 'permanent' if suspend_days >= 36500 else 'temporary',
                                'reason': 'Admin batch suspension'
                            }
                            success_count += 1
                    
                    # Save changes
                    save_monitoring_configs(monitoring_configs)
                    save_suspended_tokens(suspended_tokens)
                    
                    st.success(f"✅ Successfully processed {success_count} tokens!")
                    st.session_state['confirm_batch_action'] = False
                    st.rerun()
            
            with confirm_col2:
                if st.button("❌ Cancel", key="confirm_batch_no"):
                    st.session_state['confirm_batch_action'] = False
                    st.rerun()
        else:
            st.error("Please enter valid row numbers (start ≤ end)")
            if st.button("Close", key="close_batch_error"):
                st.session_state['confirm_batch_action'] = False
                st.rerun()
    
    # Display tokens table
    st.markdown(f"#### 📑 Token List ({len(df_filtered)} tokens)")
    
    # Style configuration for DataFrame
    def color_grade(val):
        colors = {
            'F': 'background-color: #ff4757; color: white; font-weight: bold',
            'D': 'background-color: #ff6348; color: white; font-weight: bold',
            'C': 'background-color: #ffa502; color: white; font-weight: bold',
            'B': 'background-color: #1e90ff; color: white; font-weight: bold',
            'A': 'background-color: #2ed573; color: white; font-weight: bold',
        }
        return colors.get(val, '')
    
    def color_status(val):
        if '🔴' in val:
            return 'color: #ff4757; font-weight: bold'
        elif '🟢' in val:
            return 'color: #2ed573; font-weight: bold'
        return ''
    
    # Apply styling (removed - styling breaks with hidden index and filters)
    
    # Display dataframe with sorting and filtering
    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            '🔴': st.column_config.TextColumn('🔴', width='small', help='☑ = Suspended (게시 중단)'),
            '#': st.column_config.NumberColumn('#', width='small'),
            'Exchange': st.column_config.TextColumn('Exchange', width='small'),
            'Symbol': st.column_config.TextColumn('Symbol', width='small'),
            'Grade': st.column_config.TextColumn('Grade', width='small', help='현재 scan_aggregate Grade'),
            # 기간별 평점
            '14일': st.column_config.TextColumn('14일', width='small', help='최근 14일 평균 평점 (퇴출 기준)'),
            '7일': st.column_config.TextColumn('7일', width='small', help='최근 7일 평균 평점 (진입 기준)'),
            '최신': st.column_config.TextColumn('최신', width='small', help='마지막 스캔 평점'),
            'Avg Risk': st.column_config.TextColumn('Avg Risk', width='small'),
            'Violation %': st.column_config.TextColumn('Violation %', width='small'),
            # 메인보드 추적 (NEW - replaces violation history)
            '진입일': st.column_config.TextColumn('진입일', width='small', help='메인보드 진입 날짜'),
            '다음평가일': st.column_config.TextColumn('다음평가일', width='small', help='다음 퇴출 평가일 (14일 의무 게시 후 "수시" 평가)'),
            '14일스캔': st.column_config.NumberColumn('14일스캔', width='small', help='최근 14일 총 스캔 수'),
            '7일스캔': st.column_config.NumberColumn('7일스캔', width='small', help='최근 7일 총 스캔 수'),
            # 안전도 평가
            'Safety': st.column_config.TextColumn('Safety', width='medium', help=f'{history_days}일 데이터 기반 안전도 평가'),
            'Susp. Days': st.column_config.NumberColumn('Susp. Days', width='small', help='남은 중단 일수 (0 = 만료됨)'),
            'Susp. End': st.column_config.TextColumn('Susp. End', width='small', help='중단 종료 날짜'),
        }
    )
    
    st.info("💡 **Tip**: Click on column headers to sort. Use filters above to narrow down results, then select row range for batch actions.")
    
    # Individual token actions (optional - kept for manual operations)
    with st.expander("🔧 Individual Token Actions", expanded=False):
        st.markdown("**Manual token management:**")
        st.caption("⚠️ **How to use**: Type a symbol in the search box below to find and manage individual tokens. Action buttons will appear after searching.")

        token_search = st.text_input("Search Symbol", placeholder="e.g., CRE/USDT, BTC/USDT", key="individual_token_search", help="Type symbol name to search, buttons will appear below")
        
        if token_search:
            matching_tokens = [t for t in table_data if token_search.upper() in t['symbol'].upper()]
            
            if matching_tokens:
                for idx, token in enumerate(matching_tokens[:5]):  # Show max 5 results
                    st.markdown(f"**{token['exchange'].upper()} {token['symbol']}** - Grade {token['grade']}")
                    
                    action_col1, action_col2 = st.columns([1, 1])
                    
                    with action_col1:
                        if not token['is_suspended']:
                            if st.button("⏸️ Suspend", key=f"ind_suspend_{token['key']}_{idx}"):
                                st.session_state[f'show_suspend_modal_ind_{token["key"]}'] = True
                                st.rerun()
                        else:
                            if st.button("🟢 Reactivate", key=f"ind_reactivate_{token['key']}_{idx}"):
                                if token['key'] in suspended_tokens:
                                    del suspended_tokens[token['key']]
                                    save_suspended_tokens(suspended_tokens)
                                    st.success(f"✅ Reactivated {token['symbol']}")
                                    st.rerun()
                    
                    with action_col2:
                        if st.button("🗑️ Remove", key=f"ind_remove_{token['key']}_{idx}"):
                            if token['key'] in monitoring_configs:
                                del monitoring_configs[token['key']]
                                save_monitoring_configs(monitoring_configs)
                            if token['key'] in suspended_tokens:
                                del suspended_tokens[token['key']]
                                save_suspended_tokens(suspended_tokens)
                            st.success(f"✅ Removed {token['symbol']}")
                            st.rerun()
                    
                    st.markdown("---")
            else:
                st.info("No matching tokens found")
    
    # Auto-cleanup expired suspensions
    st.markdown("---")
    st.markdown("#### 🔧 Maintenance")

    # Calculate expired suspensions
    now = datetime.now(timezone.utc)
    expired_count = 0
    expired_list = []

    for key, info in suspended_tokens.items():
        end_date_str = info.get('suspension_end_date')
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if now >= end_date:
                    expired_count += 1
                    # Get token display name
                    parts = key.split('_')
                    if len(parts) >= 3:
                        symbol = f"{parts[1].upper()}/{parts[2].upper()}"
                        expired_list.append(f"{parts[0].upper()} {symbol}")
            except:
                pass

    # Display info about expired suspensions
    if expired_count > 0:
        st.warning(f"⚠️ **{expired_count} expired suspension(s) found**")
        st.caption("**Expired tokens** (suspension end date has passed, days remaining = 0):")
        for token in expired_list[:10]:  # Show max 10
            st.caption(f"  • {token}")
        if len(expired_list) > 10:
            st.caption(f"  ... and {len(expired_list) - 10} more")
        st.caption("**Note**: Batch Actions 'Remove from Main Board' will also remove suspensions.")
    else:
        st.info("✅ No expired suspensions found")

    # Cleanup button
    if st.button("🧹 Clean Up Expired Suspensions", key="cleanup_suspended", disabled=(expired_count == 0)):
        cleaned = 0

        for key, info in list(suspended_tokens.items()):
            end_date_str = info.get('suspension_end_date')
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    if now >= end_date:
                        del suspended_tokens[key]
                        cleaned += 1
                except:
                    pass

        if cleaned > 0:
            save_suspended_tokens(suspended_tokens)
            st.success(f"✅ Cleaned up {cleaned} expired suspensions")
        else:
            st.info("No expired suspensions found")

        st.rerun()
