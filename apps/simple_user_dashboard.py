#!/usr/bin/env python3
"""
Simple User Dashboard - Night Watch
Card-based layout with bottom panel for details
"""

import streamlit as st
import json
import os
from pathlib import Path
import ccxt
import time
import math
from datetime import datetime, timezone, timedelta
import pandas as pd

st.set_page_config(
    page_title="📊 Liquidity Analytics Pro",
    page_icon="🌙",
    layout="wide"
)

# Import Telegram login
from modules.telegram_login import init_session_state, render_sidebar_login
from modules.data_access_layer import DataAccessLayer
try:
    import altair as alt
except ImportError:
    alt = None  # Altair는 선택사항

# Import report helpers and charts for Phase 1
from helpers.report_helpers import (
    load_grade_history,
    load_spread_volume_history,
    load_depth_history,
    get_token_data,
    get_thresholds,
    calculate_summary_scores
)
from modules.honeymoon_manager import get_honeymoon_manager
from helpers.report_charts import (
    create_grade_chart,
    create_spread_volume_chart,
    create_depth_area_chart,
    create_summary_box_html,
    create_basic_info_html
)
from helpers.timeseries_helper import TimeSeriesHelper, format_timestamp_for_chart

# Initialize session state
init_session_state()

# Sidebar navigation (before render_sidebar_login to check page first)
st.sidebar.title("🌙 Night Watch")
page = st.sidebar.radio(
    "Navigation",
    ["📊 Liquidity Analytics", "✏️ Custom Token Data", "🔑 My API Keys"],
    key="user_nav"
)

# Render sidebar login
render_sidebar_login()

# Add logout button if logged in
if st.session_state.logged_in:
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="user_dashboard_logout_btn"):
        from modules.telegram_login import logout_user
        logout_user()
        st.rerun()
        st.stop()

st.sidebar.markdown("---")

# On-Chain Wallet Tracking (Sidebar)
if st.session_state.logged_in and 'selected_token_id' in st.session_state:
    with st.sidebar.expander("🔗 Wallet Tracking", expanded=False):
        try:
            from user_modules.user_wallet_tracking import render_wallet_tracking_ui
            user_id = st.session_state.get('telegram_username', 'unknown')
            render_wallet_tracking_ui(user_id, st.session_state.selected_token_id)
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Page routing (handle non-main pages first to avoid duplicate renders)
if page == "✏️ Custom Token Data":
    # Check if logged in
    if not st.session_state.logged_in:
        st.warning("⚠️ Please login to add custom token data")
        st.info("👈 Use the sidebar to login with Telegram")
    else:
        # Import and render manual input page
        from user_manual_inputs import render_manual_input_ui
        user_id = st.session_state.telegram_username
        render_manual_input_ui(user_id)
    st.stop()

elif page == "🔑 My API Keys":
    # Check if logged in
    if not st.session_state.logged_in:
        st.warning("⚠️ Please login to manage your API keys")
        st.info("👈 Use the sidebar to login with Telegram")
    else:
        # Import and render API keys page
        from user_api_keys import render_user_api_keys
        user_id = st.session_state.telegram_username
        user_tier = st.session_state.user_tier
        render_user_api_keys(user_id, user_tier)
    st.stop()

# Main page: Liquidity Analytics
# Header
st.markdown("""
<div style='background: #1a1a1a; border: 3px solid #667eea; padding: 14px 18px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);'>
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div style='flex: 1;'>
            <div style='display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px;'>
                <span style='font-size: 28px; filter: drop-shadow(0 2px 4px rgba(102, 126, 234, 0.5));'>🌙</span>
                <h1 style='color: white; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 1px;'>NIGHT WATCH | LIQUIDITY ANALYTICS</h1>
            </div>
            <p style='color: #b8c5ff; margin: 0 0 0 38px; font-size: 18px; font-weight: 600; line-height: 1.3;'>Advanced Multi-Exchange Analysis & Delisting Risk Assessment</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Check login for main page
if not st.session_state.logged_in:
    st.warning("⚠️ Please login to access your watchlist")
    st.info("👈 Use the sidebar to login with Telegram")
    st.stop()

# Load user watchlist
user_id = st.session_state.telegram_username
user_tier = st.session_state.get('user_tier', 'free')

configs = {}

if os.path.exists('data/users.json'):
    with open('data/users.json', 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    user_data = users.get(user_id, {})
    
    # Try to find user with both @ and without @ versions if not found
    if not user_data:
        clean_user_id = user_id.lstrip('@')
        if clean_user_id in users:
            user_data = users[clean_user_id]
        elif f"@{clean_user_id}" in users:
            user_data = users[f"@{clean_user_id}"]
    
    # Force update user_tier from users.json (in case session state is stale)
    actual_tier = user_data.get('tier', 'free')
    if actual_tier != user_tier:
        st.session_state.user_tier = actual_tier
        user_tier = actual_tier
    
    user_watchlist = user_data.get('watchlist', [])
    
    # Load tokens_unified.json to get token data (safe loading with file lock)
    from modules.safe_json_loader import load_tokens_unified
    all_tokens = load_tokens_unified(default={})
    
    for watchlist_item in user_watchlist:
        exchange = watchlist_item.get('exchange', '').lower()
        symbol = watchlist_item.get('symbol', '')
        
        if exchange and symbol:
            token_id = f"{exchange}_{symbol.replace('/', '_').lower()}"
            token_data = all_tokens.get(token_id, {})
            token_key = f"{exchange}_{symbol}".replace('/', '_').lower()
            
            # Check if in Premium Pool (for Pro/Premium users)
            is_premium_pool = token_data.get('premium_pool', {}).get('in_pool', False) if user_tier in ['pro', 'premium'] else False
            
            if is_premium_pool:
                # Premium Pool token - enhanced data
                current_snapshot = token_data.get('current_snapshot', {})
                micro_burst = token_data.get('premium_pool', {}).get('micro_burst', {})
                
                configs[token_key] = {
                    'exchange': exchange,
                    'symbol': symbol,
                    'from_premium_pool': True,
                    'current_snapshot': current_snapshot,
                    'micro_burst': micro_burst,
                    'last_1min_snapshot': token_data.get('premium_pool', {}).get('last_1min_snapshot'),
                    'last_microburst': token_data.get('premium_pool', {}).get('last_microburst')
                }
            else:
                # Regular watchlist token - basic data
                configs[token_key] = {
                    'exchange': exchange,
                    'symbol': symbol,
                    'from_watchlist': True,
                    'snapshot_data': token_data.get('current_snapshot', {})
                }

if not configs:
    st.warning(f"""
    ## No Active Monitoring Found

    **User:** {user_id}
    **Tier:** {user_tier}
    **Watchlist items:** {len(user_watchlist) if 'user_watchlist' in locals() else 'N/A'}

    Add tokens to your watchlist on the Main Board.
    """)
    st.stop()

# Enhanced surveillance status bar
st.markdown(f"""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 10px; 
            padding: 20px; 
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);'>
    <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 15px;'>
        <span style='font-size: 24px;'>🔍</span>
        <h3 style='color: white; margin: 0; font-size: 20px; font-weight: 700;'>SURVEILLANCE STATUS</h3>
    </div>
    <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;'>
        <div style='background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 12px; backdrop-filter: blur(10px);'>
            <div style='color: rgba(255, 255, 255, 0.8); font-size: 11px; font-weight: 600; margin-bottom: 4px;'>ACTIVE TOKENS</div>
            <div style='color: white; font-size: 24px; font-weight: 700;'>{len(configs)}</div>
        </div>
        <div style='background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 12px; backdrop-filter: blur(10px);'>
            <div style='color: rgba(255, 255, 255, 0.8); font-size: 11px; font-weight: 600; margin-bottom: 4px;'>EXCHANGES</div>
            <div style='color: white; font-size: 24px; font-weight: 700;'>{len(set(cfg.get('exchange', '').upper() for cfg in configs.values()))}</div>
        </div>
        <div style='background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 12px; backdrop-filter: blur(10px);'>
            <div style='color: rgba(255, 255, 255, 0.8); font-size: 11px; font-weight: 600; margin-bottom: 4px;'>OPERATION</div>
            <div style='color: #4ade80; font-size: 18px; font-weight: 700;'>24/7</div>
        </div>
        <div style='background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 12px; backdrop-filter: blur(10px);'>
            <div style='color: rgba(255, 255, 255, 0.8); font-size: 11px; font-weight: 600; margin-bottom: 4px;'>ALERT SYSTEM</div>
            <div style='color: #4ade80; font-size: 18px; font-weight: 700;'>● ACTIVE</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state for selected token
if 'selected_token_id' not in st.session_state:
    st.session_state.selected_token_id = None

# Add token to watchlist
st.markdown("---")
st.markdown("### ➕ Add Token to Watchlist")

col_add1, col_add2, col_add3 = st.columns([2, 2, 1])
with col_add1:
    add_exchange = st.selectbox("Exchange", ["gateio", "mexc", "kucoin", "bitget"], key="add_exchange")
with col_add2:
    add_symbol = st.text_input("Symbol (e.g., BTC/USDT)", key="add_symbol", placeholder="BTC/USDT")
with col_add3:
    st.write("")  # Spacing
    st.write("")  # Spacing
    if st.button("➕ Add", type="primary", use_container_width=True):
        if add_symbol:
            from modules.user_manager import get_user_manager
            user_manager = get_user_manager()
            
            added = user_manager.add_to_watchlist(user_id, add_exchange, add_symbol.upper())
            if added:
                st.toast(f"✅ {add_symbol} added to watchlist!", icon="⭐")
                st.rerun()
            else:
                st.toast(f"ℹ️ {add_symbol} already in watchlist", icon="ℹ️")

# Display token cards in grid layout (메인보드 스타일)
st.markdown("---")
st.markdown("### 📊 Your Watchlist")

# CSS for cards (same as mainboard)
st.markdown("""
<style>
    .user-nw-card { 
        border: 1px solid #e6e9ef; 
        border-radius: 6px; 
        padding: 4px 6px 4px 14px; 
        margin-bottom: 10px; 
        background:#fff; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
        position: relative;
        min-height: 96px;
        height: 96px;
        overflow: hidden;
        cursor: pointer;
    }
    .user-nw-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 8px;
        border-radius: 6px 0 0 6px;
    }
    .user-nw-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-2px);
        background: #fafbfc;
    }
    .user-nw-card.selected {
        border: 2px solid #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    .user-nw-header { display:flex; justify-content:space-between; align-items:center; font-weight:600; color:#222; margin-bottom:5px; }
    .user-nw-sub { color:#666; font-size:9.5px; line-height:1.3; }
    .user-pair { 
        font-size:15px; 
        font-weight:700; 
        letter-spacing:0.2px; 
        color:#1a1a1a;
        padding: 4px 8px;
        border-radius: 6px;
        display: inline-block;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    .user-exch { 
        font-size:11px; 
        font-weight:600; 
        color:white; 
        padding:1px 5px; 
        border-radius:3px; 
        margin-left:5px; 
    }
    .user-exch-gateio { background:#667eea; }
    .user-exch-mexc { background:#1abc9c; }
    .user-exch-kucoin { background:#16a085; }
    .user-exch-bitget { background:#3498db; }
    .user-exch-mexc_assessment,
    .user-exch-mexc_evaluation { background:#e91e63; }
    
    /* Grade colors */
    .user-nw-card.grade-F::before { background: #dc3545 !important; }
    .user-grade-F .user-pair { border-color: #dc3545 !important; }
    .user-nw-card.grade-D::before { background: #fd7e14 !important; }
    .user-grade-D .user-pair { border-color: #fd7e14 !important; }
    .user-nw-card.grade-C-::before,
    .user-nw-card.grade-C::before,
    .user-nw-card.grade-C-plus::before { background: #ffc107 !important; }
    .user-grade-C- .user-pair,
    .user-grade-C .user-pair,
    .user-grade-C-plus .user-pair { border-color: #ffc107 !important; }
    .user-nw-card.grade-B-::before,
    .user-nw-card.grade-B::before,
    .user-nw-card.grade-B-plus::before { background: #20c997 !important; }
    .user-grade-B- .user-pair,
    .user-grade-B .user-pair,
    .user-grade-B-plus .user-pair { border-color: #20c997 !important; }
    .user-nw-card.grade-A-::before,
    .user-nw-card.grade-A::before { background: #0dcaf0 !important; }
    .user-grade-A- .user-pair,
    .user-grade-A .user-pair { border-color: #0dcaf0 !important; }
    .user-nw-card.grade-NA::before { background: #6c757d !important; }
    .user-grade-NA .user-pair { border-color: #6c757d !important; }
    
    /* Card action buttons (same as mainboard) */
    .card-action-btn {
        background: rgba(255,255,255,0.95);
        border: 1px solid #ddd;
        border-radius: 3px;
        padding: 4px 8px;
        font-size: 14px;
        text-decoration: none;
        color: #333;
        transition: all 0.2s ease;
        opacity: 0;
        pointer-events: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        line-height: 1;
    }
    .card-action-btn:hover {
        background: #fff;
        border-color: #3498db;
        transform: scale(1.1);
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
    .user-nw-card:hover .card-action-btn {
        opacity: 1;
        pointer-events: auto;
    }
    
    /* 3-color flags (same as mainboard) */
    .status-flags {
        position: absolute;
        bottom: 6px;
        right: 6px;
        display: flex;
        flex-direction: column;
        gap: 1px;
        width: 20px;
        height: 30px;
        border: 1px solid #ddd;
        border-radius: 2px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .flag-bar {
        flex: 1;
        transition: all 0.3s ease;
    }
    .flag-excellent { background: #4caf50; }
    .flag-moderate { background: #ffd700; }
    .flag-poor { background: #f44336; }
    
    /* 7-tier status system (same as mainboard) */
    .status-excellent .pair { border-color: #00bfff; animation: blink-excellent 4s ease-in-out infinite; }
    .status-good .pair { border-color: #00ced1; animation: blink-good 3.5s ease-in-out infinite; }
    .status-fair .pair { border-color: #32cd32; animation: blink-fair 3s ease-in-out infinite; }
    .status-warning .pair { border-color: #ffd700; animation: blink-warning 2.5s ease-in-out infinite; }
    .status-caution .pair { border-color: #ff8c00; animation: blink-caution 2s ease-in-out infinite; }
    .status-danger .pair { border-color: #ff6347; animation: blink-danger 1.5s ease-in-out infinite; }
    .status-critical .pair { border-color: #dc143c; animation: blink-critical 1s ease-in-out infinite; }
    
    @keyframes blink-excellent {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0, 191, 255, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(0, 191, 255, 0.6); }
    }
    @keyframes blink-good {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0, 206, 209, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(0, 206, 209, 0.6); }
    }
    @keyframes blink-fair {
        0%, 100% { box-shadow: 0 0 0 0 rgba(50, 205, 50, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(50, 205, 50, 0.6); }
    }
    @keyframes blink-warning {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(255, 215, 0, 0.6); }
    }
    @keyframes blink-caution {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 140, 0, 0.3); }
        50% { box-shadow: 0 0 8px 2px rgba(255, 140, 0, 0.7); }
    }
    @keyframes blink-danger {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 99, 71, 0.3); }
        50% { box-shadow: 0 0 8px 2px rgba(255, 99, 71, 0.7); }
    }
    @keyframes blink-critical {
        0%, 100% { box-shadow: 0 0 0 0 rgba(220, 20, 60, 0.4); }
        50% { box-shadow: 0 0 10px 3px rgba(220, 20, 60, 0.8); }
    }
</style>
""", unsafe_allow_html=True)

# Load all tokens DB directly (same as My Watch List in mainboard) - using safe loader
from modules.safe_json_loader import safe_load_json
try:
    all_tokens_db = safe_load_json('data/tokens_unified.json', default={})
except:
    try:
        all_tokens_db = safe_load_json('data/tokens_unified.json', default={})
    except:
        all_tokens_db = {}

# Create grid layout for token cards (same as mainboard watchlist)
tokens_list = list(configs.items())
cols_per_row = 4

for row_idx in range(0, len(tokens_list), cols_per_row):
    cols = st.columns(cols_per_row)
    
    for col_idx, col in enumerate(cols):
        token_idx = row_idx + col_idx
        if token_idx < len(tokens_list):
            config_id, config = tokens_list[token_idx]
            
            with col:
                # Get token info (same as mainboard)
                ex_id = config.get('exchange', '').lower()
                sym = config.get('symbol', '')
                
                # Normalize exchange for token_id
                normalized_exchange = ex_id
                if normalized_exchange.startswith('mexc_'):
                    normalized_exchange = 'mexc'
                
                token_id = f"{normalized_exchange}_{sym}".replace('/', '_').lower()

                # Get token data from all_tokens_db directly (same as My Watch List)
                if token_id in all_tokens_db:
                    m = all_tokens_db[token_id]

                    # Extract data from unified DB structure (same as My Watch List)
                    current_snapshot = m.get('current_snapshot', {})
                    scan_aggregate = m.get('scan_aggregate', {})

                    # Display current snapshot if available, otherwise use aggregates
                    spread_pct = current_snapshot.get('spread_pct') or scan_aggregate.get('avg_spread_pct')
                    total_2 = current_snapshot.get('depth_2pct') or scan_aggregate.get('avg_depth_2pct')
                    avg_volume = current_snapshot.get('volume_24h') or scan_aggregate.get('avg_volume_24h', 0)

                    # Grade and risk from aggregates (calculated by main scanner)
                    grade = scan_aggregate.get('grade') or current_snapshot.get('grade', 'N/A')
                    average_risk = scan_aggregate.get('average_risk', 0)
                    violation_rate = scan_aggregate.get('violation_rate', 0)

                    # Tags
                    st_tagged = m.get('tags', {}).get('st_tagged', False)
                else:
                    # Token not found in database
                    spread_pct = None
                    total_2 = None
                    avg_volume = 0
                    grade = 'N/A'
                    average_risk = 0
                    violation_rate = 0
                    st_tagged = False
                    m = {}
                    current_snapshot = {}
                    scan_aggregate = {}
                
                # ST/AZ badges (same as mainboard)
                is_assessment_zone = ex_id in ["mexc_assessment"]
                badges_html = ""
                if st_tagged:
                    badges_html += "<span style='background:#000; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-left:8px; line-height:1.4; vertical-align:middle;'>ST</span>"
                if is_assessment_zone:
                    badges_html += "<span style='background:#000; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-left:8px; line-height:1.4; vertical-align:middle;'>AZ</span>"
                
                # Format display values
                spread_html = "N/A" if spread_pct is None else f"{spread_pct:.2f}%"
                depth_html = "N/A" if total_2 is None else f"${total_2:,.0f}"
                volume_html = "N/A" if avg_volume is None or avg_volume == 0 else f"${avg_volume:,.0f}"
                
                # 7-tier status system and 3-color flags (same as mainboard)
                spread_threshold = 1.0
                spread_target = 0.5
                depth_threshold = 500
                depth_target = 2000
                volume_threshold = 10000
                volume_target = 50000
                
                current_spread = spread_pct if spread_pct else 0
                current_depth = total_2 if total_2 else 0
                current_volume = avg_volume if avg_volume else 0
                
                spread_level = 0
                if current_spread <= spread_threshold:
                    spread_level = 1
                    if current_spread <= spread_target:
                        spread_level = 2
                
                depth_level = 0
                if current_depth >= depth_threshold:
                    depth_level = 1
                    if current_depth >= depth_target:
                        depth_level = 2
                
                volume_level = 0
                if current_volume >= volume_threshold:
                    volume_level = 1
                    if current_volume >= volume_target:
                        volume_level = 2
                
                target_count = sum([1 for level in [spread_level, depth_level, volume_level] if level == 2])
                threshold_count = sum([1 for level in [spread_level, depth_level, volume_level] if level >= 1])
                
                grade_class = f"grade-{grade.replace('+', '-plus').replace('/', '-')}" if grade and grade != 'N/A' else "grade-NA"
                css = f"user-nw-card exchange-{ex_id} {grade_class}"
                if target_count == 3:
                    css += " status-excellent"
                elif target_count == 2 and threshold_count == 3:
                    css += " status-good"
                elif target_count == 1 and threshold_count == 3:
                    css += " status-fair"
                elif target_count == 0 and threshold_count == 3:
                    css += " status-warning"
                elif threshold_count == 2:
                    css += " status-caution"
                elif threshold_count == 1:
                    css += " status-danger"
                else:
                    css += " status-critical"
                
                # 3-color flags
                spread_flag = "flag-excellent" if spread_level == 2 else ("flag-moderate" if spread_level == 1 else "flag-poor")
                depth_flag = "flag-excellent" if depth_level == 2 else ("flag-moderate" if depth_level == 1 else "flag-poor")
                volume_flag = "flag-excellent" if volume_level == 2 else ("flag-moderate" if volume_level == 1 else "flag-poor")
                
                flags_html = f"""<div class='status-flags' title='Top to Bottom: Spread | Depth | Volume&#10;🟢 Green: Target met&#10;🟡 Yellow: Threshold met&#10;🔴 Red: Below threshold'><div class='flag-bar {spread_flag}'></div><div class='flag-bar {depth_flag}'></div><div class='flag-bar {volume_flag}'></div></div>"""
                
                # Exchange display name
                ex_display = "MEXC_AZ" if ex_id in ("mexc_assessment", "mexc_evaluation") else ex_id.upper()

                # Calculate timestamp for "Updated: Xm ago" (same as My Watch List)
                # Try multiple possible timestamp field names
                timestamp_str = (current_snapshot.get('timestamp') or
                                current_snapshot.get('last_scanned') or
                                scan_aggregate.get('timestamp') or
                                scan_aggregate.get('last_scanned'))
                updated_ago = "N/A"
                if timestamp_str:
                    try:
                        # Parse ISO timestamp
                        if isinstance(timestamp_str, str):
                            ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            ts = timestamp_str
                        now = datetime.now(timezone.utc)
                        diff_mins = int((now - ts).total_seconds() / 60)
                        if diff_mins < 1:
                            updated_ago = "now"
                        elif diff_mins < 60:
                            updated_ago = f"{diff_mins}m"
                        else:
                            hours = diff_mins // 60
                            updated_ago = f"{hours}h"
                    except Exception:
                        updated_ago = "N/A"

                # Grade info from token data
                grade_info = m.get('grade_info', {})
                gpa_14d_str = str(grade_info.get('avg_14d_gpa', 'N/A')) if grade_info.get('avg_14d_gpa') else 'N/A'
                gpa_14d_grade = grade_info.get('avg_14d_grade', grade if grade != 'N/A' else 'N/A')
                
                # 허니문 상태 확인 (사용자별)
                user_id = st.session_state.get('telegram_username')
                honeymoon_manager = get_honeymoon_manager(user_id)
                honeymoon_status = honeymoon_manager.get_token_honeymoon_status(ex_id, sym)
                
                # Grade and risk info HTML with honeymoon info
                grade_html = ""
                if grade != 'N/A':
                    # 허니문 정보 추가
                    honeymoon_info = ""
                    if honeymoon_status['status'] not in ['not_configured', 'error']:
                        if honeymoon_status['is_in_honeymoon']:
                            days_remaining = honeymoon_status['days_remaining']
                            price_drop = honeymoon_status['price_drop_pct']
                            if price_drop >= honeymoon_status['threshold_price_pct']:
                                honeymoon_info = f"<span style='color:#dc3545; font-weight:bold;'>⚠️ 허니문 {days_remaining}일 남음 ({price_drop:.1f}%↓)</span>"
                            else:
                                honeymoon_info = f"<span style='color:#20c997;'>💎 허니문 {days_remaining}일 남음 ({price_drop:.1f}%↓)</span>"
                        else:
                            honeymoon_info = f"<span style='color:#6c757d;'>✅ 허니문 종료 ({honeymoon_status['days_since_listing']}일)</span>"
                    
                    grade_html = f"<div class='nw-sub' style='margin-top:4px; display:flex; gap:8px; font-size:10px;'><span>14dGPA: <b>{gpa_14d_str}/{gpa_14d_grade}</b></span><span>Risk: <b>{int(average_risk*100)}%</b></span><span>Viol.: <b>{int(violation_rate*100)}%</b></span></div>"
                    if honeymoon_info:
                        grade_html += f"<div class='nw-sub' style='margin-top:2px; font-size:9px;'>{honeymoon_info}</div>"
                else:
                    grade_html = "<div class='nw-sub' style='margin-top:4px; padding:3px 6px; background:#fff3cd; border:1px dashed #ffc107; border-radius:4px; font-size:9.5px;'><b>⏳ Awaiting First Scan</b><br/>This token will be scanned in the next Main Scanner cycle (every 2 hours at 00:00, 02:00, 04:00... UTC)</div>"
                
                # Grade watermark
                grade_watermark_html = ""
                if grade and grade != 'N/A':
                    base_grade = grade[0]
                    modifier = grade[1] if len(grade) > 1 else ''
                    grade_colors = {
                        'F': '#dc3545',
                        'D': '#fd7e14',
                        'C': '#ffc107',
                        'B': '#20c997',
                        'A': '#0dcaf0'
                    }
                    grade_color = grade_colors.get(base_grade, '#000000')
                    if modifier:
                        grade_watermark_html = f"<div class='grade-watermark' style='position:absolute; right:50px; bottom:0px; font-size:52px; font-weight:700; color:{grade_color}; opacity:0.08; line-height:1; pointer-events:none; user-select:none; z-index:2; transition: all 0.3s ease;'>{base_grade}<span style='font-size:28px; vertical-align:super; margin-left:2px;'>{modifier}</span></div>"
                    else:
                        grade_watermark_html = f"<div class='grade-watermark' style='position:absolute; right:50px; bottom:0px; font-size:52px; font-weight:700; color:{grade_color}; opacity:0.08; line-height:1; pointer-events:none; user-select:none; z-index:2; transition: all 0.3s ease;'>{base_grade}</div>"
                
                # Generate 14-day history chart (using separate chart_helpers module)
                from helpers.chart_helpers import get_token_history_14days, generate_mini_chart_html

                current_snapshot_data = {
                    'grade': grade,
                    'avg_volume_24h': m.get('scan_aggregate', {}).get('avg_volume_24h', 0),
                    'avg_spread_pct': m.get('scan_aggregate', {}).get('avg_spread_pct', 0),
                    'avg_depth_2pct': m.get('scan_aggregate', {}).get('avg_depth_2pct', 0)
                }
                history_data = get_token_history_14days(token_id, ex_id, sym, current_snapshot_data)
                inline_chart_html = generate_mini_chart_html(history_data, inline=True)
                
                # Symbol display
                if '/' in sym:
                    token_part, quote_part = sym.split('/', 1)
                    if len(token_part) > 5:
                        display_sym = f"{token_part[:5]}./{quote_part}"
                    else:
                        display_sym = sym
                else:
                    display_sym = sym[:5] + '.' if len(sym) > 5 else sym
                
                # Selected state
                selected_class = "selected" if st.session_state.selected_token_id == config_id else ""
                
                # Card ID and remove link (same as My Watch List)
                card_id = f"watchcard_{token_id.replace('_', '-')}"
                remove_link = f"?remove_exchange={ex_id}&remove_symbol={sym}"

                # Card HTML (same as My Watch List in mainboard)
                st.markdown(
f"""<style>
.user-nw-card:hover .grade-watermark {{
opacity: 0.5 !important;
}}
.user-nw-card:hover .mini-chart-container {{
opacity: 0.8 !important;
}}
</style>
<div class='{css} {selected_class}' id='{card_id}' style='position:relative; overflow:hidden; min-height:96px; height:96px;'>
{grade_watermark_html}
{flags_html}
<a href='{remove_link}' class='card-action-btn' title='Remove from Watchlist' style='position:absolute; top:8px; right:8px; z-index:11;'>🗑️</a>
<div style='position:relative; z-index:10;'>
<div class='user-nw-header' style='display:flex; align-items:flex-start; gap:8px;'>
<div style='display:flex; align-items:center; gap:6px; flex:1;'>
<span class='user-pair' title='{sym}'>{display_sym}</span>{badges_html}
<span class='user-exch user-exch-{ex_id}'>{ex_display}</span>{inline_chart_html}
</div>
</div>
<div class='user-nw-sub' style='margin-top:4px; display:flex; gap:8px; font-size:10px; justify-content:space-between; align-items:center;'>
<div style='display:flex; gap:8px;'>
<span>Spread: <b>{spread_html}</b></span>
<span>2%Dep: <b>{depth_html}</b></span>
<span>24Vol: <b>{volume_html}</b></span>
</div>
<span style='font-size:8.5px; color:#888; white-space:nowrap;'>⏱ {updated_ago}</span>
</div>
{grade_html}
</div>
</div>""",
unsafe_allow_html=True
                )
                
                # Card click button
                if st.button(f"📊 View Analysis", key=f"card_{config_id}", use_container_width=True,
                            type="primary" if selected_class else "secondary"):
                    st.session_state.selected_token_id = config_id
                    st.rerun()

# Note: Token details display moved to end of file (after function definitions)

# Minimal UI styles for liquidity quality cards
st.markdown(
    """
    <style>
      .u-card { border:1px solid #e5e7eb; border-radius:8px; padding:10px 12px; margin-bottom:8px; background:#fff; }
      .u-label { font-size:12px; color:#555; display:flex; align-items:center; gap:6px; }
      .u-value { font-size:18px; font-weight:700; color:#111; margin-top:4px; }
      .u-ok { color:#0b7a3b; }
      .u-warn { color:#b36b00; }
      .u-err { color:#b91c1c; }
      .qmark { display:inline-block; width:16px; height:16px; border-radius:50%; background:#eef; color:#336; text-align:center; line-height:16px; font-size:11px; cursor:help; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load monitoring data (functions for main page)
def load_monitoring_data():
    config_file = "monitoring_configs.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Load user watchlist snapshots
def load_user_watchlist_data(user_id):
    """Load watchlist data using Data Access Layer"""
    # Get user tier
    users_file = "data/users.json"
    user_tier = 'free'
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                user_tier = users.get(user_id, {}).get('tier', 'free')
        except:
            pass
    
    # Use Data Access Layer
    dal = DataAccessLayer()
    watchlist_data = dal.get_watchlist_data(user_id, user_tier=user_tier)
    
    # Convert to format expected by dashboard (latest snapshot format)
    if watchlist_data:
        tokens = []
        for token_id, data in watchlist_data.items():
            tokens.append({
                'exchange': data.get('exchange'),
                'symbol': data.get('symbol'),
                'spread_pct': data.get('spread_pct'),
                'depth_2pct': data.get('depth_2pct_usd'),
                'volume_24h': data.get('volume_24h_usd'),
                'bid': data.get('bid'),
                'ask': data.get('ask'),
                'timestamp': data.get('last_updated')
            })
        return {'timestamp': datetime.now().isoformat(), 'tokens': tokens}
    return None

# Load Night Watch selection
def load_night_watch_selection():
    selection_file = "night_watch_selection.json"
    if os.path.exists(selection_file):
        with open(selection_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # migrate old single-board format
            if isinstance(data, dict) and "selected_tokens" in data:
                return {"boards": {"default": data.get("selected_tokens", [])}, "active_board": "default"}
            return data
    return {"boards": {"default": []}, "active_board": "default"}


# CCXT helpers
def _get_exchange_instance(exchange_id: str, api_key: str | None = None, api_secret: str | None = None):
    """Return a public CCXT exchange instance for read-only endpoints."""
    mapped = exchange_id
    # Map special labels to ccxt ids
    if exchange_id in ("mexc_evaluation", "mexc_assessment"):
        mapped = "mexc"
    try:
        ex_class = getattr(ccxt, mapped)
        params = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
        # attach credentials for assessment if present
        if mapped == "mexc" and (api_key and api_secret):
            params.update({
                "apiKey": api_key,
                "secret": api_secret,
                "headers": {"x-mexc-apikey": api_key},
                "urls": {"api": {"public": "https://api.mexc.com/api/v3", "private": "https://api.mexc.com/api/v3"}}
            })
        return ex_class(params)
    except Exception:
        return None

def _fetch_market_snapshot(exchange_id: str, symbol: str, api_key: str | None = None, api_secret: str | None = None):
    """Fetch ticker and orderbook (up to 150) with safe fallbacks."""
    ex = _get_exchange_instance(exchange_id, api_key, api_secret)
    if ex is None:
        return None
    ticker = {}
    orderbook = {"bids": [], "asks": []}
    market_info = {}
    try:
        try:
            ex.load_markets()
            market_info = ex.markets.get(symbol, {})
        except Exception:
            market_info = {}
        try:
            ticker = ex.fetch_ticker(symbol)
        except Exception:
            ticker = {}
        try:
            # 거래소별 최적 limit 설정 (각 거래소의 최대값부터 시도)
            if exchange_id == 'kucoin':
                limits = [100, 20]  # KuCoin: 20 또는 100만 허용
            elif exchange_id == 'bitget':
                limits = [150, 100, 50]  # Bitget: 최대 150
            elif exchange_id == 'gateio':
                limits = [100, 50, 20]  # Gate.io: 최대 100
            elif exchange_id == 'mexc':
                limits = [200, 100, 50]  # MEXC: 최대 200
            else:
                limits = [150, 100, 50, 20]  # 기본값
            
            for lim in limits:
                try:
                    orderbook = ex.fetch_order_book(symbol, limit=lim)
                    if orderbook:
                        break
                except Exception:
                    continue
        except Exception:
            orderbook = {"bids": [], "asks": []}
    except Exception:
        # CCXT failed; try direct MEXC V3 public endpoints if possible (only if not requiring auth)
        pass
    
    # If exchange is mexc_assessment and private data might be required, try signed private endpoints for depth/ticker
    if (not ticker or not orderbook) and exchange_id in ("mexc_assessment", "mexc_evaluation") and api_key and api_secret:
        try:
            import requests
            base = "https://api.mexc.com/api/v3"
            # Public endpoints (should work with assessment but some symbols hidden without key); we pass header anyway
            headers = {"x-mexc-apikey": api_key}
            # Ticker price
            r1 = requests.get(f"{base}/ticker/24hr", params={"symbol": symbol.replace("/", "")}, headers=headers, timeout=5)
            if r1.ok:
                jd = r1.json()
                # normalize fields similar to ccxt
                try:
                    last = float(jd.get("lastPrice")) if isinstance(jd, dict) else None
                    bidp = float(jd.get("bidPrice")) if isinstance(jd, dict) else None
                    askp = float(jd.get("askPrice")) if isinstance(jd, dict) else None
                    qv = float(jd.get("quoteVolume")) if isinstance(jd, dict) else None
                    ticker = {"last": last, "bid": bidp, "ask": askp, "quoteVolume": qv}
                except Exception:
                    pass
            # Order book depth
            r2 = requests.get(f"{base}/depth", params={"symbol": symbol.replace("/", ""), "limit": 150}, headers=headers, timeout=5)
            if r2.ok:
                ob = r2.json()
                bids = ob.get("bids") or []
                asks = ob.get("asks") or []
                # ensure float conversion
                orderbook = {
                    "bids": [[float(p), float(a)] for p, a in bids],
                    "asks": [[float(p), float(a)] for p, a in asks],
                }
        except Exception:
            pass
    return {"ticker": ticker, "orderbook": orderbook, "market_info": market_info}

def _get_decimal_places(precision):
    """Convert price precision to decimal places"""
    if precision is None:
        return 8  # Default fallback
    
    # Handle scientific notation (e.g., 1e-06)
    if isinstance(precision, (int, float)):
        if precision == 0:
            return 0
        elif precision >= 1:
            return 0
        else:
            # Convert to string to count decimal places
            precision_str = f"{precision:.10f}".rstrip('0').rstrip('.')
            if '.' in precision_str:
                return len(precision_str.split('.')[1])
            else:
                return 0
    
    # Handle string precision
    if isinstance(precision, str):
        if 'e-' in precision.lower():
            # Scientific notation
            exp = int(precision.lower().split('e-')[1])
            return exp
        elif '.' in precision:
            return len(precision.split('.')[1])
        else:
            return 0
    
    return 8  # Default fallback

def _format_price(v: float, decimal_places: int = 6) -> str:
    if v is None or v == 0:
        return "N/A"
    return f"${v:.{decimal_places}f}"

def _calc_liquidity_depth(bids, asks, bid, ask, pct: float):
    """Return (bid_usdt, ask_usdt, total_usdt, net_usdt, weighted_bid, weighted_ask, spread_abs, spread_pct).
    
    NOTE: bid/ask are from ticker (real-time best prices for spread calculation)
          bids/asks are from orderbook (for liquidity depth calculation)
          
    For ±X% liquidity:
    1. Calculate range based on ticker bid/ask midpoint
    2. Sum all orderbook orders within that range
    3. If ticker bid/ask themselves are not in orderbook, include them as single orders
    """
    try:
        if not bid or not ask:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
        mid = (bid + ask) / 2.0
        low = mid * (1 - pct/100.0)
        high = mid * (1 + pct/100.0)
        
        bid_usdt = 0.0
        ask_usdt = 0.0
        wb_num = 0.0
        wb_den = 0.0
        wa_num = 0.0
        wa_den = 0.0
        
        # Check if ticker bid is in orderbook
        ticker_bid_in_ob = False
        ticker_ask_in_ob = False
        
        # Bids: sum all orderbook orders within [low, high] range
        for p, a in bids or []:
            try:
                p = float(p); a = float(a)
            except Exception:
                continue
            if abs(p - bid) < 0.00000001:  # Check if this is ticker bid
                ticker_bid_in_ob = True
            if low <= p <= high:
                notional = p * a
                bid_usdt += notional
                wb_num += p * a
                wb_den += a
        
        # If ticker bid is in range but not in orderbook, add it with estimated volume
        if low <= bid <= high and not ticker_bid_in_ob:
            # Estimate volume from nearby orderbook levels
            est_vol = 0
            if bids:
                est_vol = sum(float(a) for p, a in bids[:3]) / 3  # Average of top 3
            if est_vol == 0:
                est_vol = 1000  # Default fallback
            notional = bid * est_vol
            bid_usdt += notional
            wb_num += notional
            wb_den += est_vol
        
        # Asks: sum all orderbook orders within [low, high] range
        for p, a in asks or []:
            try:
                p = float(p); a = float(a)
            except Exception:
                continue
            if abs(p - ask) < 0.00000001:  # Check if this is ticker ask
                ticker_ask_in_ob = True
            if low <= p <= high:
                notional = p * a
                ask_usdt += notional
                wa_num += p * a
                wa_den += a
        
        # If ticker ask is in range but not in orderbook, add it with estimated volume
        if low <= ask <= high and not ticker_ask_in_ob:
            # Estimate volume from nearby orderbook levels
            est_vol = 0
            if asks:
                est_vol = sum(float(a) for p, a in asks[:3]) / 3  # Average of top 3
            if est_vol == 0:
                est_vol = 1000  # Default fallback
            notional = ask * est_vol
            ask_usdt += notional
            wa_num += notional
            wa_den += est_vol
        
        weighted_bid = (wb_num / wb_den) if wb_den > 0 else 0.0
        weighted_ask = (wa_num / wa_den) if wa_den > 0 else 0.0
        spread_abs = ask - bid if (ask and bid) else 0.0
        spread_pct = (spread_abs / bid * 100.0) if bid else 0.0
        net = bid_usdt - ask_usdt
        return bid_usdt, ask_usdt, (bid_usdt + ask_usdt), net, weighted_bid, weighted_ask, spread_abs, spread_pct
    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

# ---------------------- Micro Burst (User) ----------------------
def _capture_burst_frames(ex, symbol: str, frames: int = 10, sleep_s: float = 0.2, limit: int = 50, exchange_id: str = ""):
    data = []
    if ex is None:
        return data
    
    # 거래소별 최적 limit 설정
    if exchange_id == 'kucoin':
        limit = min(limit, 100)  # KuCoin: 최대 100
    elif exchange_id == 'bitget':
        limit = min(limit, 150)  # Bitget: 최대 150
    elif exchange_id == 'gateio':
        limit = min(limit, 100)  # Gate.io: 최대 100
    elif exchange_id == 'mexc':
        limit = min(limit, 200)  # MEXC: 최대 200
    
    for _ in range(max(1, frames)):
        try:
            ob = ex.fetch_order_book(symbol, limit=limit) or {"bids": [], "asks": []}
        except Exception:
            ob = {"bids": [], "asks": []}
        # normalize
        try:
            bids = [[float(p), float(a)] for p, a in (ob.get("bids") or [])]
            asks = [[float(p), float(a)] for p, a in (ob.get("asks") or [])]
        except Exception:
            bids, asks = [], []
        data.append({"bids": bids, "asks": asks})
        time.sleep(max(0.05, sleep_s))
    return data

def _best_prices(frame):
    bids = frame.get("bids") or []
    asks = frame.get("asks") or []
    best_bid = bids[0][0] if bids else 0.0
    best_ask = asks[0][0] if asks else 0.0
    return best_bid, best_ask

def _within_range(entries, low: float, high: float):
    return [(p, a) for p, a in entries if low <= p <= high]

def _compute_micro_burst_metrics(frames: list):
    metrics = {
        "valid_frames": 0,
        "quote_persistence": None,
        "concentration_hhi": None,
        "imbalance_vol": None,
        "layering_gap_std": None,
        "touch_flip_count": 0,
    }
    if not frames or len(frames) < 2:
        return metrics

    # Midpoint from first valid frame
    first = None
    for fr in frames:
        b, a = _best_prices(fr)
        if b > 0 and a > 0:
            first = fr
            break
    if first is None:
        return metrics

    b0, a0 = _best_prices(first)
    mid0 = (b0 + a0) / 2.0 if (b0 and a0) else 0.0
    if mid0 <= 0:
        return metrics

    low2 = mid0 * 0.98
    high2 = mid0 * 1.02

    # Quote Persistence: Jaccard of price-level sets between first and last frame within ±2%
    def level_set(frame):
        bids = _within_range(frame.get("bids") or [], low2, mid0)
        asks = _within_range(frame.get("asks") or [], mid0, high2)
        lv = set([round(p, 12) for p, _ in bids[:50]] + [round(p, 12) for p, _ in asks[:50]])
        return lv

    last = frames[-1]
    s_first = level_set(first)
    s_last = level_set(last)
    inter = len(s_first & s_last)
    union = max(1, len(s_first | s_last))
    metrics["quote_persistence"] = inter / union

    # Concentration HHI: notional share across buckets within ±2%
    def notional(frame):
        bids = _within_range(frame.get("bids") or [], low2, mid0)
        asks = _within_range(frame.get("asks") or [], mid0, high2)
        tot = 0.0
        for p, a in bids:
            tot += p * a
        for p, a in asks:
            tot += p * a
        return tot, bids, asks

    tot_notional, bids_f, asks_f = notional(first)
    if tot_notional > 0:
        # Bucket by rounding to 0.1% bands around mid
        buckets = {}
        for p, a in bids_f + asks_f:
            key = int(((p - mid0) / mid0) * 1000)  # 0.1% band
            buckets[key] = buckets.get(key, 0.0) + (p * a)
        shares = [(v / tot_notional) for v in buckets.values() if v > 0]
        hhi = sum([s * s for s in shares])  # 0..1
        metrics["concentration_hhi"] = hhi

    # Imbalance Volatility: CV of imbalance across frames within ±2%
    imbalances = []
    touch_flip = 0
    last_best = None
    gaps_rel = []
    for fr in frames:
        b, a = _best_prices(fr)
        if b > 0 and a > 0:
            metrics["valid_frames"] += 1
            # touch flip
            cur_best = (b, a)
            if last_best and (cur_best != last_best):
                touch_flip += 1
            last_best = cur_best

            # imbalance
            bids = _within_range(fr.get("bids") or [], low2, mid0)
            asks = _within_range(fr.get("asks") or [], mid0, high2)
            bid_usdt = sum([p * a for p, a in bids])
            ask_usdt = sum([p * a for p, a in asks])
            denom = (bid_usdt + ask_usdt)
            if denom > 0:
                imbalances.append(abs(bid_usdt - ask_usdt) / denom)

            # layering gaps (relative)
            # bids descending by price, asks ascending
            bid_prices = [p for p, _ in bids]
            ask_prices = [p for p, _ in asks]
            for side_prices in (bid_prices, ask_prices):
                side_prices = sorted(side_prices, reverse=True) if side_prices == bid_prices else sorted(side_prices)
                for i in range(1, len(side_prices)):
                    gap = abs(side_prices[i-1] - side_prices[i]) / mid0
                    if gap > 0:
                        gaps_rel.append(gap)

    metrics["touch_flip_count"] = touch_flip
    if imbalances:
        mean_imb = sum(imbalances) / len(imbalances)
        if mean_imb > 0:
            var = sum([(x - mean_imb) ** 2 for x in imbalances]) / len(imbalances)
            std = math.sqrt(var)
            metrics["imbalance_vol"] = std / mean_imb
        else:
            metrics["imbalance_vol"] = None
    if gaps_rel:
        mean_g = sum(gaps_rel) / len(gaps_rel)
        var_g = sum([(x - mean_g) ** 2 for x in gaps_rel]) / len(gaps_rel)
        metrics["layering_gap_std"] = math.sqrt(var_g)
    return metrics

# Persistent auto-burst state/metrics
def _load_json_safe(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def _save_json_safe(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# Permissions for micro burst timeframes per board
def _load_mb_permissions():
    path = "mb_permissions.json"
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"boards": {}}
    return {"boards": {}}

def _allowed_timeframes_for_board(board_name: str):
    perms = _load_mb_permissions()
    boards = perms.get("boards", {})
    allowed = boards.get(board_name, {}).get("allowed_timeframes")
    if isinstance(allowed, list) and allowed:
        return allowed
    # default: only 15 min
    return ["15 min"]

# ---------------------- Daily report helpers ----------------------
def _report_file_path(exchange_id: str, symbol: str):
    date = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.join("reports", date)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{exchange_id}_{symbol.replace('/', '-')}.json")

def _append_report_record(exchange_id: str, symbol: str, record: dict):
    path = _report_file_path(exchange_id, symbol)
    data = []
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(record)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return len(data)

def _load_report_records(exchange_id: str, symbol: str):
    path = _report_file_path(exchange_id, symbol)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _compute_daily_summary(records: list, targets: dict):
    """Compute comprehensive summary statistics from 1-minute snapshot records"""
    if not records:
        return {}
    
    import statistics as stats
    
    try:
        # Extract all metrics from snapshots
        spread_arr = [r.get('spread_pct') for r in records if isinstance(r.get('spread_pct'), (int, float))]
        bid_liq_arr = [r.get('bid_liq_2') for r in records if isinstance(r.get('bid_liq_2'), (int, float))]
        ask_liq_arr = [r.get('ask_liq_2') for r in records if isinstance(r.get('ask_liq_2'), (int, float))]
        total_liq_arr = [r.get('total_liq_2') for r in records if isinstance(r.get('total_liq_2'), (int, float))]
        total_liq_5_arr = [r.get('total_liq_5_usdt') for r in records if isinstance(r.get('total_liq_5_usdt'), (int, float))]
        total_liq_10_arr = [r.get('total_liq_10_usdt') for r in records if isinstance(r.get('total_liq_10_usdt'), (int, float))]
        vol_arr = [r.get('qv') for r in records if isinstance(r.get('qv'), (int, float))]
        
        # Micro Burst metrics
        qp_arr = [r.get('mb_quote_persistence') for r in records if isinstance(r.get('mb_quote_persistence'), (int, float))]
        hhi_arr = [r.get('mb_hhi') for r in records if isinstance(r.get('mb_hhi'), (int, float))]
        iv_arr = [r.get('mb_imbalance_vol') for r in records if isinstance(r.get('mb_imbalance_vol'), (int, float))]
        gap_arr = [r.get('mb_layering_gap_std') for r in records if isinstance(r.get('mb_layering_gap_std'), (int, float))]
        flip_arr = [r.get('mb_touch_flip') for r in records if isinstance(r.get('mb_touch_flip'), (int, float))]
        
        # Thresholds
        spread_thr = targets.get('spread_threshold', 2.0)
        depth_thr = targets.get('depth_threshold', 500)
        
        summary = {
            'count': len(records),
            
            # === SPREAD STATISTICS ===
            'avg_spread_pct': stats.mean(spread_arr) if spread_arr else None,
            'median_spread_pct': stats.median(spread_arr) if spread_arr else None,
            'min_spread_pct': min(spread_arr) if spread_arr else None,
            'max_spread_pct': max(spread_arr) if spread_arr else None,
            'stdev_spread_pct': stats.stdev(spread_arr) if len(spread_arr) > 1 else None,
            'spread_violations_pct': (sum(1 for s in spread_arr if s > spread_thr) / len(spread_arr) * 100) if spread_arr else 0,
            
            # === LIQUIDITY STATISTICS (±2%) ===
            'avg_bid_liq_2': stats.mean(bid_liq_arr) if bid_liq_arr else None,
            'avg_ask_liq_2': stats.mean(ask_liq_arr) if ask_liq_arr else None,
            'avg_total_liq_2': stats.mean(total_liq_arr) if total_liq_arr else None,
            'median_total_liq_2': stats.median(total_liq_arr) if total_liq_arr else None,
            'min_total_liq_2': min(total_liq_arr) if total_liq_arr else None,
            'max_total_liq_2': max(total_liq_arr) if total_liq_arr else None,
            'stdev_total_liq_2': stats.stdev(total_liq_arr) if len(total_liq_arr) > 1 else None,
            'depth_violations_pct': (sum(1 for d in total_liq_arr if d < depth_thr) / len(total_liq_arr) * 100) if total_liq_arr else 0,
            
            # === LIQUIDITY STATISTICS (±5%, ±10%) ===
            'avg_total_liq_5': stats.mean(total_liq_5_arr) if total_liq_5_arr else None,
            'avg_total_liq_10': stats.mean(total_liq_10_arr) if total_liq_10_arr else None,
            
            # === VOLUME STATISTICS ===
            'avg_volume': stats.mean(vol_arr) if vol_arr else None,
            'median_volume': stats.median(vol_arr) if vol_arr else None,
            'total_volume': sum(vol_arr) if vol_arr else None,
            
            # === BID/ASK IMBALANCE ===
            'avg_bid_ask_ratio': (stats.mean([b/max(1,a) for b,a in zip(bid_liq_arr, ask_liq_arr)]) if (bid_liq_arr and ask_liq_arr) else None),
            'ask_dominated_minutes_pct': (sum(1 for b,a in zip(bid_liq_arr, ask_liq_arr) if a > b) / min(len(bid_liq_arr), len(ask_liq_arr)) * 100) if (bid_liq_arr and ask_liq_arr) else 0,
            
            # === MICRO BURST AVERAGES ===
            'avg_quote_persistence': stats.mean(qp_arr) if qp_arr else None,
            'avg_concentration_hhi': stats.mean(hhi_arr) if hhi_arr else None,
            'avg_imbalance_vol': stats.mean(iv_arr) if iv_arr else None,
            'avg_layering_gap_std': stats.mean(gap_arr) if gap_arr else None,
            'avg_touch_flip': stats.mean(flip_arr) if flip_arr else None,
            
            # === CAPITAL REQUIREMENTS ===
            'cap_needed_usdt': 0,
            'actions': []
        }
        
        # Calculate capital needed to meet depth target
        if total_liq_arr:
            avg_liq = stats.mean(total_liq_arr)
            if avg_liq < depth_thr:
                deficit = depth_thr - avg_liq
                summary['cap_needed_usdt'] = deficit
        
        # Generate quick action items
        if summary.get('avg_spread_pct') and summary['avg_spread_pct'] > spread_thr:
            summary['actions'].append(f"Reduce spread from {summary['avg_spread_pct']:.2f}% to <{spread_thr}%")
        if summary.get('avg_total_liq_2') and summary['avg_total_liq_2'] < depth_thr:
            summary['actions'].append(f"Increase ±2% depth from ${summary['avg_total_liq_2']:,.0f} to ${depth_thr:,.0f}")
        if summary.get('ask_dominated_minutes_pct') and summary['ask_dominated_minutes_pct'] > 60:
            summary['actions'].append(f"Balance bid/ask ratio (currently {summary['ask_dominated_minutes_pct']:.0f}% ask-dominated)")
        
        return summary
        
    except Exception as e:
        return {'count': len(records), 'error': str(e)}

def _load_report_records_hours(exchange_id: str, symbol: str, hours: int):
    try:
        from datetime import timedelta
        now = datetime.utcnow()
        out = []
        # search today and up to previous 3 days
        for d in range(0, 4):
            date = (now - timedelta(days=d)).strftime("%Y-%m-%d")
            base = os.path.join("reports", date)
            path = os.path.join(base, f"{exchange_id}_{symbol.replace('/', '-')}.json")
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        arr = json.load(f)
                        out.extend(arr)
                except Exception:
                    continue
        # filter by last N hours
        cutoff = now.timestamp() - hours * 3600
        filtered = []
        for r in out:
            try:
                ts = r.get('ts')
                if not ts:
                    continue
                # parse ISO
                tsv = ts.replace('Z','').replace('T',' ')
                from datetime import datetime as _dt
                epoch = _dt.fromisoformat(tsv).timestamp()
                if epoch >= cutoff:
                    filtered.append(r)
            except Exception:
                continue
        # sort by ts
        filtered.sort(key=lambda x: x.get('ts',''))
        return filtered
    except Exception:
        return []

def _median_safe(values: list):
    try:
        vals = [v for v in values if isinstance(v, (int, float))]
        if not vals:
            return None
        vals.sort()
        n = len(vals)
        mid = n // 2
        if n % 2 == 1:
            return vals[mid]
        return (vals[mid-1] + vals[mid]) / 2.0
    except Exception:
        return None

def _generate_anomalies(records: list, targets: dict):
    notes = []
    if not records:
        return notes
    try:
        # Build series
        b_arr = [r.get('bid_liq_2') for r in records if isinstance(r.get('bid_liq_2'), (int, float))]
        a_arr = [r.get('ask_liq_2') for r in records if isinstance(r.get('ask_liq_2'), (int, float))]
        qv_arr = [r.get('qv') for r in records if isinstance(r.get('qv'), (int, float))]
        # volume deltas as proxy for trade bursts
        vol_delta = []
        for i in range(1, len(qv_arr)):
            dv = qv_arr[i] - qv_arr[i-1]
            if dv >= 0:
                vol_delta.append(dv)
        # thresholds
        depth_target = float(targets.get('depth_target', 1000) or 1000)
        side_target = depth_target / 2.0
        med_b = _median_safe(b_arr) or 0.0
        med_a = _median_safe(a_arr) or 0.0
        big_bid_th = max(side_target, med_b * 1.5)
        big_ask_th = max(side_target, med_a * 1.5)
        # Identify large trade bursts (top decile of vol_delta)
        if vol_delta:
            vd_sorted = sorted(vol_delta)
            idx = max(0, int(len(vd_sorted) * 0.9) - 1)
            top_vd = vd_sorted[idx] if idx < len(vd_sorted) else vd_sorted[-1]
            # Map to record indices (shift by 1 due to diff)
            for i in range(1, len(qv_arr)):
                dv = qv_arr[i] - qv_arr[i-1]
                if dv >= top_vd and top_vd > 0:
                    # lookback 5 minutes for elevated side liquidity
                    lb = max(0, i-5)
                    prev_bigs_bid = any(((records[j].get('bid_liq_2') or 0) >= big_bid_th) for j in range(lb, i))
                    prev_bigs_ask = any(((records[j].get('ask_liq_2') or 0) >= big_ask_th) for j in range(lb, i))
                    if prev_bigs_bid:
                        notes.append("Large trade burst followed by prior elevated bid liquidity in the last 5 minutes (accumulation signal).")
                    if prev_bigs_ask:
                        notes.append("Large trade burst followed by prior elevated ask liquidity in the last 5 minutes (distribution signal).")
                    if not (prev_bigs_bid or prev_bigs_ask):
                        notes.append("Large trade burst without preceding side build-up (news/impulse likely).")
                    # limit notes volume
                    if len(notes) >= 5:
                        break
        # Detect persistent walls
        if med_a > 0 and med_a >= big_ask_th:
            notes.append("Persistent sell-side wall detected within ±2% (median ask depth elevated).")
        if med_b > 0 and med_b >= big_bid_th:
            notes.append("Persistent buy-side wall detected within ±2% (median bid depth elevated).")
    except Exception:
        pass
    return notes

def _compute_exposure_stats(records: list, targets: dict):
    try:
        spread_thr = float(targets.get('spread_threshold', 2.0) or 2.0)
        depth_thr = float(targets.get('depth_threshold', 500) or 500)
        # exposures per minute
        spread_exposed = []
        liq_exposed = []
        both_exposed = []
        # longest streaks (by order of records)
        cur_spread = longest_spread = 0
        cur_liq = longest_liq = 0
        for r in records:
            sp = r.get('spread_pct'); tot = r.get('total_liq_2'); b = r.get('bid_liq_2'); a = r.get('ask_liq_2')
            is_spread = isinstance(sp, (int, float)) and sp > spread_thr
            is_liq = isinstance(tot, (int, float)) and tot < depth_thr
            spread_exposed.append(1 if is_spread else 0)
            liq_exposed.append(1 if is_liq else 0)
            both_exposed.append(1 if (is_spread and is_liq) else 0)
            # streaks
            if is_spread:
                cur_spread += 1
                longest_spread = max(longest_spread, cur_spread)
            else:
                cur_spread = 0
            if is_liq:
                cur_liq += 1
                longest_liq = max(longest_liq, cur_liq)
            else:
                cur_liq = 0
        n = max(1, len(records))
        return {
            'exposure_spread_pct': sum(spread_exposed) * 100.0 / n,
            'exposure_liq_pct': sum(liq_exposed) * 100.0 / n,
            'exposure_both_pct': sum(both_exposed) * 100.0 / n,
            'longest_spread_streak_min': longest_spread,
            'longest_liq_streak_min': longest_liq,
        }
    except Exception:
        return {}

def _comprehensive_market_analysis(records: list, targets: dict):
    """Comprehensive analysis using all ST thresholds and Micro Burst data"""
    import statistics as stats
    
    analysis = {
        'delisting_risk_score': 0,  # 0-100
        'market_manipulation_score': 0,  # 0-100
        'liquidity_quality_grade': 'N/A',  # A+ to F
        'immediate_actions': [],
        'strategic_recommendations': [],
        'risk_factors': [],
        'positive_signals': [],
        'micro_burst_insights': {},
        'st_compliance': {}
    }
    
    try:
        # Extract all metrics
        spread_arr = [r.get('spread_pct') for r in records if isinstance(r.get('spread_pct'), (int, float))]
        bid_arr = [r.get('bid_liq_2') for r in records if isinstance(r.get('bid_liq_2'), (int, float))]
        ask_arr = [r.get('ask_liq_2') for r in records if isinstance(r.get('ask_liq_2'), (int, float))]
        total_liq_arr = [r.get('total_liq_2') for r in records if isinstance(r.get('total_liq_2'), (int, float))]
        vol_arr = [r.get('qv') for r in records if isinstance(r.get('qv'), (int, float))]
        
        # Micro Burst metrics
        qp_arr = [r.get('mb_quote_persistence') for r in records if isinstance(r.get('mb_quote_persistence'), (int, float))]
        hhi_arr = [r.get('mb_hhi') for r in records if isinstance(r.get('mb_hhi'), (int, float))]
        iv_arr = [r.get('mb_imbalance_vol') for r in records if isinstance(r.get('mb_imbalance_vol'), (int, float))]
        gap_arr = [r.get('mb_layering_gap_std') for r in records if isinstance(r.get('mb_layering_gap_std'), (int, float))]
        flip_arr = [r.get('mb_touch_flip') for r in records if isinstance(r.get('mb_touch_flip'), (int, float))]
        
        # ST Thresholds
        spread_thr = targets.get('spread_threshold', 2.0)
        depth_thr = targets.get('depth_threshold', 500)
        vol_thr = targets.get('volume_target', 50000)
        
        # === DELISTING RISK SCORING (0-100) ===
        risk_score = 0
        
        # Spread violation (0-25 points)
        if spread_arr:
            avg_spread = stats.mean(spread_arr)
            spread_violations = sum(1 for s in spread_arr if s > spread_thr) / len(spread_arr) * 100
            if avg_spread > spread_thr * 3:
                risk_score += 25
            elif avg_spread > spread_thr * 2:
                risk_score += 20
            elif avg_spread > spread_thr:
                risk_score += 10 + (spread_violations / 10)
        
        # Liquidity violation (0-30 points)
        if total_liq_arr:
            avg_liq = stats.mean(total_liq_arr)
            liq_violations = sum(1 for l in total_liq_arr if l < depth_thr) / len(total_liq_arr) * 100
            if avg_liq < depth_thr * 0.3:
                risk_score += 30
            elif avg_liq < depth_thr * 0.5:
                risk_score += 20
            elif avg_liq < depth_thr:
                risk_score += 10 + (liq_violations / 10)
        
        # Volume deficiency (0-20 points)
        if vol_arr:
            avg_vol = stats.mean(vol_arr)
            if avg_vol < vol_thr * 0.2:
                risk_score += 20
            elif avg_vol < vol_thr * 0.5:
                risk_score += 10
        
        # Micro Burst red flags (0-25 points)
        mb_risk = 0
        if qp_arr and stats.mean(qp_arr) < 0.3:  # Brittle quotes
            mb_risk += 8
        if hhi_arr and stats.mean(hhi_arr) > 0.25:  # Concentrated liquidity
            mb_risk += 7
        if iv_arr and stats.mean(iv_arr) > 0.5:  # Unstable
            mb_risk += 5
        if flip_arr and stats.mean(flip_arr) > 15:  # High churn
            mb_risk += 5
        risk_score += mb_risk
        
        analysis['delisting_risk_score'] = min(100, int(risk_score))
        
        # === MANIPULATION DETECTION (0-100) ===
        manip_score = 0
        
        # Layering/spoofing signals
        if gap_arr:
            avg_gap = stats.mean(gap_arr)
            if avg_gap > 0.001:  # Elevated layering
                manip_score += 30
                analysis['risk_factors'].append(f"🚨 SPOOFING ALERT: Layering Gap STD={avg_gap:.4f} (elevated step-like order book)")
            elif avg_gap > 0.0005:
                manip_score += 15
        
        # Quote instability
        if qp_arr:
            avg_qp = stats.mean(qp_arr)
            if avg_qp < 0.3:
                manip_score += 20
                analysis['risk_factors'].append(f"⚠️ QUOTE INSTABILITY: Persistence={avg_qp:.2f} (brittle, frequent quote changes)")
        
        # Extreme imbalances
        if bid_arr and ask_arr:
            bid_ask_ratios = [b/max(1,a) for b,a in zip(bid_arr, ask_arr)]
            extreme_imbalances = sum(1 for r in bid_ask_ratios if r > 3 or r < 0.33) / len(bid_ask_ratios) * 100
            if extreme_imbalances > 30:
                manip_score += 25
                analysis['risk_factors'].append(f"🔴 WASH TRADING RISK: Extreme bid/ask imbalance {extreme_imbalances:.1f}% of time")
        
        # High churn with low volume
        if flip_arr and vol_arr:
            avg_flip = stats.mean(flip_arr)
            avg_vol = stats.mean(vol_arr)
            if avg_flip > 15 and avg_vol < vol_thr * 0.5:
                manip_score += 25
                analysis['risk_factors'].append(f"⚠️ CHURN ANOMALY: {avg_flip:.0f} quote flips/5s but low volume=${avg_vol:,.0f}")
        
        analysis['market_manipulation_score'] = min(100, int(manip_score))
        
        # === LIQUIDITY QUALITY GRADE ===
        grade_score = 100
        if spread_arr:
            if stats.mean(spread_arr) > spread_thr * 2:
                grade_score -= 30
            elif stats.mean(spread_arr) > spread_thr:
                grade_score -= 15
        if total_liq_arr:
            if stats.mean(total_liq_arr) < depth_thr * 0.5:
                grade_score -= 30
            elif stats.mean(total_liq_arr) < depth_thr:
                grade_score -= 15
        if qp_arr and stats.mean(qp_arr) < 0.4:
            grade_score -= 10
        if hhi_arr and stats.mean(hhi_arr) > 0.2:
            grade_score -= 10
        if iv_arr and stats.mean(iv_arr) > 0.4:
            grade_score -= 5
        
        if grade_score >= 90:
            analysis['liquidity_quality_grade'] = 'A+'
        elif grade_score >= 80:
            analysis['liquidity_quality_grade'] = 'A'
        elif grade_score >= 70:
            analysis['liquidity_quality_grade'] = 'B+'
        elif grade_score >= 60:
            analysis['liquidity_quality_grade'] = 'B'
        elif grade_score >= 50:
            analysis['liquidity_quality_grade'] = 'C'
        elif grade_score >= 40:
            analysis['liquidity_quality_grade'] = 'D'
        else:
            analysis['liquidity_quality_grade'] = 'F'
        
        # === POSITIVE SIGNALS ===
        if spread_arr and stats.mean(spread_arr) < spread_thr * 0.5:
            analysis['positive_signals'].append(f"✅ Tight spread: {stats.mean(spread_arr):.2f}% (< {spread_thr*0.5:.1f}%)")
        if total_liq_arr and stats.mean(total_liq_arr) > depth_thr * 1.5:
            analysis['positive_signals'].append(f"✅ Strong depth: ${stats.mean(total_liq_arr):,.0f} (> ${depth_thr*1.5:,.0f})")
        if qp_arr and stats.mean(qp_arr) > 0.7:
            analysis['positive_signals'].append(f"✅ Stable quotes: Persistence={stats.mean(qp_arr):.2f} (high)")
        if hhi_arr and stats.mean(hhi_arr) < 0.1:
            analysis['positive_signals'].append(f"✅ Diffuse liquidity: HHI={stats.mean(hhi_arr):.2f} (well-distributed)")
        
        # === MICRO BURST INSIGHTS ===
        if qp_arr:
            analysis['micro_burst_insights']['Quote Persistence'] = {
                'avg': stats.mean(qp_arr),
                'min': min(qp_arr),
                'max': max(qp_arr),
                'interpretation': 'STABLE' if stats.mean(qp_arr) > 0.6 else ('MIXED' if stats.mean(qp_arr) > 0.3 else 'BRITTLE')
            }
        if hhi_arr:
            analysis['micro_burst_insights']['Concentration HHI'] = {
                'avg': stats.mean(hhi_arr),
                'min': min(hhi_arr),
                'max': max(hhi_arr),
                'interpretation': 'DIFFUSE' if stats.mean(hhi_arr) < 0.1 else ('BALANCED' if stats.mean(hhi_arr) < 0.25 else 'CONCENTRATED')
            }
        if iv_arr:
            analysis['micro_burst_insights']['Imbalance Volatility'] = {
                'avg': stats.mean(iv_arr),
                'min': min(iv_arr),
                'max': max(iv_arr),
                'interpretation': 'STABLE' if stats.mean(iv_arr) < 0.2 else ('CAUTION' if stats.mean(iv_arr) < 0.5 else 'UNSTABLE')
            }
        if gap_arr:
            analysis['micro_burst_insights']['Layering Gap STD'] = {
                'avg': stats.mean(gap_arr),
                'min': min(gap_arr),
                'max': max(gap_arr),
                'interpretation': 'NORMAL' if stats.mean(gap_arr) < 0.0005 else ('CAUTION' if stats.mean(gap_arr) < 0.001 else 'ELEVATED')
            }
        if flip_arr:
            analysis['micro_burst_insights']['Touch Flip Count'] = {
                'avg': stats.mean(flip_arr),
                'min': min(flip_arr),
                'max': max(flip_arr),
                'interpretation': 'CALM' if stats.mean(flip_arr) < 3 else ('MODERATE' if stats.mean(flip_arr) < 8 else 'HIGH CHURN')
            }
        
        # === ST COMPLIANCE ===
        analysis['st_compliance'] = {
            'Spread': {'compliant': (stats.mean(spread_arr) <= spread_thr) if spread_arr else False, 'value': f"{stats.mean(spread_arr):.2f}%" if spread_arr else 'N/A', 'threshold': f"{spread_thr}%"},
            'Depth': {'compliant': (stats.mean(total_liq_arr) >= depth_thr) if total_liq_arr else False, 'value': f"${stats.mean(total_liq_arr):,.0f}" if total_liq_arr else 'N/A', 'threshold': f"${depth_thr:,.0f}"},
            'Volume': {'compliant': (stats.mean(vol_arr) >= vol_thr) if vol_arr else False, 'value': f"${stats.mean(vol_arr):,.0f}" if vol_arr else 'N/A', 'threshold': f"${vol_thr:,.0f}"}
        }
        
    except Exception as e:
        pass
    
    return analysis

def _generate_strategic_actions(summary: dict, exposure: dict, records: list, targets: dict, current_price: float):
    """Generate detailed strategic action plan with execution steps"""
    actions = []
    try:
        # Get comprehensive analysis first
        comp_analysis = _comprehensive_market_analysis(records, targets)
        
        avg_spread = summary.get('avg_spread_pct') or 0
        avg_liq = summary.get('avg_total_liq_2') or 0
        cap_needed = summary.get('cap_needed_usdt') or 0
        spread_thr = targets.get('spread_threshold', 2.0)
        depth_thr = targets.get('depth_threshold', 500)
        
        # Analyze bid/ask imbalance
        b_arr = [r.get('bid_liq_2') for r in records if isinstance(r.get('bid_liq_2'), (int, float))]
        a_arr = [r.get('ask_liq_2') for r in records if isinstance(r.get('ask_liq_2'), (int, float))]
        avg_bid = sum(b_arr) / len(b_arr) if b_arr else 0
        avg_ask = sum(a_arr) / len(a_arr) if a_arr else 0
        
        delisting_risk = comp_analysis['delisting_risk_score']
        manip_score = comp_analysis['market_manipulation_score']
        
        # CRITICAL: High Delisting Risk
        if delisting_risk > 70:
            actions.append({
                'priority': 1,
                'severity': '🔴 CRITICAL',
                'issue': f'DELISTING RISK: {delisting_risk}/100',
                'strategy': 'Emergency Liquidity Injection & Volume Boost',
                'execution': [
                    f'1. IMMEDIATE: Deploy ${cap_needed:,.0f} USDT across 3 layers (±0.5%, ±1%, ±2%)',
                    f'2. Execute market trades: $500-1000 USDT every 3-5 min for 6 hours',
                    f'3. Coordinate with 2-3 market makers for quote stability',
                    f'4. Set automated spread tightening bot: target {spread_thr/2:.1f}%',
                    f'5. Monitor ST compliance hourly; adjust positions dynamically',
                    f'6. Prepare delisting appeal documentation if risk persists >48h'
                ],
                'capital_required': f'${cap_needed * 1.5:,.0f} USDT',
                'risk_level': 'EXTREME',
                'expected_impact': f'Reduce delisting risk to <50 within 24-48 hours',
                'timeline': 'URGENT: Begin within 1 hour'
            })
        
        # HIGH: Manipulation Detection
        if manip_score > 50:
            actions.append({
                'priority': 2,
                'severity': '🟠 HIGH',
                'issue': f'MANIPULATION SIGNALS: {manip_score}/100',
                'strategy': 'Counter-Manipulation & Market Stabilization',
                'execution': [
                    f'1. Cancel all existing orders; rebuild book with natural-looking distribution',
                    f'2. Implement randomized order placement (±5-15% size variance)',
                    f'3. Deploy anti-layering: orders at 0.3%, 0.7%, 1.2%, 1.8% (irregular intervals)',
                    f'4. Monitor for spoofing: cancel if opposite large orders appear <10s',
                    f'5. Report suspicious activity to exchange compliance',
                    f'6. Engage independent MM to provide authentic liquidity'
                ],
                'capital_required': f'${cap_needed:,.0f} USDT',
                'risk_level': 'High',
                'expected_impact': 'Normalize order book; reduce manipulation score to <30',
                'timeline': '2-6 hours'
            })
        
        # MEDIUM: Spread Management
        if avg_spread > spread_thr:
            severity = "🔴 CRITICAL" if avg_spread > spread_thr * 2 else "🟡 MEDIUM"
            actions.append({
                'priority': 3,
                'severity': severity,
                'issue': f'Excessive Spread ({avg_spread:.2f}%)',
                'strategy': 'Aggressive Market Making',
                'execution': [
                    f'1. Place limit orders at ±{spread_thr/2:.2f}% from mid-price',
                    f'2. Order size: ${max(100, depth_thr/5):,.0f} USDT per side (20% of depth target)',
                    f'3. Refresh every 30-60s; use TWAP algo to avoid detection',
                    f'4. Stop-loss: ±{spread_thr*2:.1f}% (maximum exposure control)',
                    f'5. Target spread: {spread_thr*0.7:.1f}% (30% buffer below threshold)'
                ],
                'capital_required': f'${cap_needed*0.4:,.0f} USDT',
                'risk_level': 'Medium-High',
                'expected_impact': f'Reduce spread to {spread_thr:.1f}% within 2 hours',
                'timeline': '2 hours'
            })
        
        # MEDIUM: Liquidity Depth
        if avg_liq < depth_thr:
            severity = "🔴 CRITICAL" if avg_liq < depth_thr * 0.5 else "🟡 MEDIUM"
            actions.append({
                'priority': 4,
                'severity': severity,
                'issue': f'Insufficient Depth (${avg_liq:,.0f} USDT)',
                'strategy': 'Multi-Layer Liquidity Pyramid',
                'execution': [
                    f'1. Layer 1 (±0.3-0.5%): ${depth_thr*0.25:,.0f} USDT/side - tight quotes',
                    f'2. Layer 2 (±0.8-1.2%): ${depth_thr*0.35:,.0f} USDT/side - mid support',
                    f'3. Layer 3 (±1.5-2.0%): ${depth_thr*0.40:,.0f} USDT/side - deep backstop',
                    f'4. Stagger placement over 6 hours (avoid sudden depth spike)',
                    f'5. Use multiple sub-accounts to simulate organic activity',
                    f'6. Rebalance layers every 2 hours based on fill rates'
                ],
                'capital_required': f'${cap_needed:,.0f} USDT',
                'risk_level': 'Medium',
                'expected_impact': f'Reach ${depth_thr:,.0f} USDT depth within 12 hours',
                'timeline': '6-12 hours'
            })
        
        # LOW: Imbalance Correction
        if avg_ask > avg_bid * 1.5 or avg_bid > avg_ask * 1.5:
            side = "SELL" if avg_ask > avg_bid else "BUY"
            imbalance_ratio = max(avg_ask/max(1,avg_bid), avg_bid/max(1,avg_ask))
            actions.append({
                'priority': 5,
                'severity': '🟢 LOW',
                'issue': f'{side} Pressure ({imbalance_ratio:.1f}x imbalance)',
                'strategy': 'Balancing via Counter-Side Liquidity',
                'execution': [
                    f'1. Focus {70}% of capital on {"BID" if side=="SELL" else "ASK"} side',
                    f'2. Absorb {"sell" if side=="SELL" else "buy"} pressure: ${max(avg_ask, avg_bid)*0.8:,.0f} USDT',
                    f'3. Redistribute accumulated inventory via OTC/CEX transfer',
                    f'4. Gradually restore 50/50 balance over 24 hours',
                    f'5. Monitor for large opposite orders (manipulation red flag)'
                ],
                'capital_required': f'${max(avg_ask, avg_bid)*1.2:,.0f} USDT',
                'risk_level': 'Low-Medium',
                'expected_impact': 'Balance bid/ask to 0.8-1.2 ratio within 12 hours',
                'timeline': '12 hours'
            })
        
        # Sort by priority
        actions.sort(key=lambda x: x['priority'])
        return actions
    except Exception as e:
        return []

def _generate_narrative(summary: dict, exposure: dict, records: list, targets: dict):
    # Ask-bias and fixed sell proxy
    try:
        b_arr = [r.get('bid_liq_2') for r in records if isinstance(r.get('bid_liq_2'), (int, float))]
        a_arr = [r.get('ask_liq_2') for r in records if isinstance(r.get('ask_liq_2'), (int, float))]
        n = min(len(b_arr), len(a_arr))
        ask_dominated = 0
        for i in range(n):
            if (a_arr[i] or 0) > (b_arr[i] or 0):
                ask_dominated += 1
        ask_dom_pct = (ask_dominated * 100.0 / n) if n > 0 else 0.0
        # fixed sell amount proxy: median of top 10% ask snapshots
        a_sorted = sorted(a_arr)
        k = max(1, int(round(len(a_sorted) * 0.9))) if a_sorted else 0
        fixed_sell = None
        if a_sorted:
            top_slice = a_sorted[k:]
            if top_slice:
                import statistics as stats
                fixed_sell = round(stats.median(top_slice), 0)
        lines = []
        lines.append(f"- Average spread was {(summary.get('avg_spread_pct') or 0):.2f}%, with exposure above threshold for {(exposure.get('exposure_spread_pct') or 0):.1f}% of the day (longest {(exposure.get('longest_spread_streak_min') or 0)} min streak).")
        lines.append(f"- Average ±2% total liquidity was {(summary.get('avg_total_liq_2') or 0):,.0f} usdt; liquidity exposure {(exposure.get('exposure_liq_pct') or 0):.1f}% (longest {(exposure.get('longest_liq_streak_min') or 0)} min).")
        lines.append(f"- Ask-dominant minutes: {ask_dom_pct:.1f}% (sell pressure bias).")
        if fixed_sell is not None and fixed_sell > 0:
            lines.append(f"- Persistent sell wall proxy within ±2% estimated around {fixed_sell:,.0f} usdt (median of top decile).")
        # action anchor
        cap_needed = summary.get('cap_needed_usdt')
        if isinstance(cap_needed, (int, float)) and cap_needed > 0:
            lines.append(f"- Estimated capital required to meet ±2% depth target on both sides: {cap_needed:,.0f} usdt.")
        return lines
    except Exception:
        return []
    import statistics as stats
    try:
        sp = [r.get('spread_pct') for r in records if isinstance(r.get('spread_pct'), (int, float))]
        liq = [r.get('total_liq_2') for r in records if isinstance(r.get('total_liq_2'), (int, float))]
        hhi = [r.get('mb_hhi') for r in records if isinstance(r.get('mb_hhi'), (int, float))]
        iv = [r.get('mb_imbalance_vol') for r in records if isinstance(r.get('mb_imbalance_vol'), (int, float))]
        gap = [r.get('mb_layering_gap_std') for r in records if isinstance(r.get('mb_layering_gap_std'), (int, float))]
        flips = [r.get('mb_touch_flip') for r in records if isinstance(r.get('mb_touch_flip'), (int, float))]
        avg = lambda arr: (stats.mean(arr) if arr else None)
        summary = {
            'avg_spread_pct': avg(sp),
            'avg_total_liq_2': avg(liq),
            'avg_hhi': avg(hhi),
            'avg_imbalance_vol': avg(iv),
            'avg_gap_std': avg(gap),
            'avg_flips': avg(flips),
            'count': len(records),
        }
        # Recommended action & capital estimate
        depth_target = float(targets.get('depth_target', 1000) or 1000)
        side_target = depth_target / 2.0
        # Estimate average side deficits using avg of side series if present
        b_arr = [r.get('bid_liq_2') for r in records if isinstance(r.get('bid_liq_2'), (int, float))]
        a_arr = [r.get('ask_liq_2') for r in records if isinstance(r.get('ask_liq_2'), (int, float))]
        avg_b = avg(b_arr) or 0.0
        avg_a = avg(a_arr) or 0.0
        cap_needed = max(0.0, side_target - avg_b) + max(0.0, side_target - avg_a)
        summary['cap_needed_usdt'] = round(cap_needed, 2)
        actions = []
        spread_threshold = float(targets.get('spread_threshold', 2.0) or 2.0)
        if summary['avg_spread_pct'] is not None and summary['avg_spread_pct'] > spread_threshold:
            actions.append('Tighten quotes to meet spread target')
        if summary['avg_total_liq_2'] is not None and summary['avg_total_liq_2'] < depth_target:
            actions.append('Provide additional ±2% liquidity to reach depth target')
        if summary['avg_hhi'] is not None and summary['avg_hhi'] > 0.25:
            actions.append('Monitor concentration; diversify quote placement')
        if summary['avg_gap_std'] is not None and summary['avg_gap_std'] > 0.001:
            actions.append('Inspect layering risk; randomize order ladder')
        if summary['avg_imbalance_vol'] is not None and summary['avg_imbalance_vol'] > 0.5:
            actions.append('Stabilize side imbalance; smooth replenishment cadence')
        summary['actions'] = actions
        return summary
    except Exception:
        return {}

# ============================================================================
# Display selected token details at the bottom (moved here after function definitions)
# ============================================================================
if st.session_state.selected_token_id and st.session_state.selected_token_id in configs:
    st.markdown("---")
    st.markdown("---")
    
    selected_config = configs[st.session_state.selected_token_id]
    exchange = selected_config.get('exchange', '').upper()
    symbol = selected_config.get('symbol', '')
    
    st.markdown(f"## 📊 {exchange} - {symbol} | Detailed Analysis Report")

    # ============================================================================
    # Phase 1: Premium Analysis Report
    # ============================================================================

    # Get token data from tokens_unified.json
    token_data = get_token_data(selected_config['exchange'], selected_config['symbol'])

    if token_data is None:
        st.warning("⚠️ Token data not found in database. Please wait for the next scan cycle.")
    else:
        # Get thresholds for this exchange
        thresholds = get_thresholds(selected_config['exchange'])

        # Get grade and aggregate data
        scan_aggregate = token_data.get('scan_aggregate', {})
        current_snapshot = token_data.get('current_snapshot', {})
        grade = scan_aggregate.get('grade', 'N/A')

        # Calculate summary scores
        scores = calculate_summary_scores(token_data, thresholds)

        # ============================================================================
        # 1. Top Summary Box (Always visible, not collapsible)
        # ============================================================================
        summary_html = create_summary_box_html(
            grade=grade,
            scores=scores,
            exchange=exchange,
            symbol=symbol
        )
        import streamlit.components.v1 as components
        components.html(summary_html, height=200, scrolling=False)

        # ============================================================================
        # 2. 14-Day Grade & Risk Metrics (Always visible)
        # ============================================================================
        st.markdown("---")
        st.markdown("### 📊 14-Day Grade & Risk Metrics (14일 평점 및 위험 지표)")
        
        # Get grade info and risk metrics
        grade_info = token_data.get('grade_info', {})
        gpa_14d = grade_info.get('avg_14d_gpa', 0)
        gpa_14d_grade = grade_info.get('avg_14d_grade', grade)
        average_risk = scan_aggregate.get('average_risk', 0)
        violation_rate = scan_aggregate.get('violation_rate', 0)
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius: 10px; padding: 20px; text-align: center; color: white;'>
                <div style='font-size: 14px; font-weight: 600; margin-bottom: 8px; opacity: 0.9;'>Current Grade</div>
                <div style='font-size: 48px; font-weight: 900; line-height: 1;'>{grade}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            gpa_color = "#0dcaf0" if gpa_14d >= 3.5 else "#20c997" if gpa_14d >= 2.5 else "#ffc107" if gpa_14d >= 1.5 else "#fd7e14" if gpa_14d >= 0.5 else "#dc3545"
            st.markdown(f"""
            <div style='background: {gpa_color}; 
                        border-radius: 10px; padding: 20px; text-align: center; color: white;'>
                <div style='font-size: 14px; font-weight: 600; margin-bottom: 8px; opacity: 0.9;'>14-Day GPA</div>
                <div style='font-size: 48px; font-weight: 900; line-height: 1;'>{gpa_14d:.2f}</div>
                <div style='font-size: 12px; margin-top: 8px; opacity: 0.9;'>Grade: {gpa_14d_grade}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            risk_color = "#dc3545" if average_risk >= 0.7 else "#fd7e14" if average_risk >= 0.5 else "#ffc107" if average_risk >= 0.3 else "#20c997"
            risk_emoji = "🔴" if average_risk >= 0.7 else "🟠" if average_risk >= 0.5 else "🟡" if average_risk >= 0.3 else "🟢"
            st.markdown(f"""
            <div style='background: {risk_color}; 
                        border-radius: 10px; padding: 20px; text-align: center; color: white;'>
                <div style='font-size: 14px; font-weight: 600; margin-bottom: 8px; opacity: 0.9;'>Average Risk</div>
                <div style='font-size: 48px; font-weight: 900; line-height: 1;'>{risk_emoji}</div>
                <div style='font-size: 24px; font-weight: 700; margin-top: 8px;'>{int(average_risk*100)}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            viol_color = "#dc3545" if violation_rate >= 0.5 else "#fd7e14" if violation_rate >= 0.3 else "#ffc107" if violation_rate >= 0.15 else "#20c997"
            viol_emoji = "⚠️" if violation_rate >= 0.5 else "⚡" if violation_rate >= 0.3 else "📊" if violation_rate >= 0.15 else "✅"
            st.markdown(f"""
            <div style='background: {viol_color}; 
                        border-radius: 10px; padding: 20px; text-align: center; color: white;'>
                <div style='font-size: 14px; font-weight: 600; margin-bottom: 8px; opacity: 0.9;'>Violation Rate</div>
                <div style='font-size: 48px; font-weight: 900; line-height: 1;'>{viol_emoji}</div>
                <div style='font-size: 24px; font-weight: 700; margin-top: 8px;'>{int(violation_rate*100)}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Explanation
        st.markdown("""
        **💡 Metric Explanations:**
        - **14-Day GPA**: Average grade point (A=4.0, B=3.0, C=2.0, D=1.0, F=0.0) over the last 14 days
        - **Average Risk**: Percentage of scans where the token violated delisting thresholds (higher = more risky)
        - **Violation Rate**: Frequency of threshold violations in recent scans (lower = more stable)
        """)

        # ============================================================================
        # 3. Basic Information Section (Collapsible)
        # ============================================================================
        with st.expander("📋 Basic Token Information", expanded=False):
            basic_info_html = create_basic_info_html(
                token_data=token_data,
                exchange=exchange,
                symbol=symbol
            )
            components.html(basic_info_html, height=250, scrolling=False)

        # ============================================================================
        # 4. 30-Day Rating History Chart (Collapsible)
        # ============================================================================
        with st.expander("📈 30-Day Rating History", expanded=True):
            st.markdown("#### Rating Trend with Moving Averages")

            # Load grade history
            grade_df = load_grade_history(
                exchange=selected_config['exchange'],
                symbol=selected_config['symbol'],
                days=30
            )

            if not grade_df.empty:
                # Create grade chart
                grade_chart = create_grade_chart(grade_df, current_grade=grade)
                st.altair_chart(grade_chart, use_container_width=True)

                # Summary statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Current Rating", grade)
                with col2:
                    avg_grade = grade_df['grade_numeric'].mean()
                    st.metric("30-Day Average", f"{avg_grade:.2f}")
                with col3:
                    if len(grade_df) >= 84:  # 7 days
                        recent_avg = grade_df['grade_numeric'].tail(84).mean()
                        st.metric("7-Day Average", f"{recent_avg:.2f}")
                    else:
                        st.metric("7-Day Average", "N/A")
                with col4:
                    grade_trend = "↗️ Improving" if len(grade_df) > 1 and grade_df['grade_numeric'].iloc[-1] > grade_df['grade_numeric'].iloc[0] else "↘️ Declining"
                    st.metric("Trend", grade_trend)

                # Rating Statistics Table
                st.markdown("#### 📊 Rating Statistics")

                # Calculate rating distribution
                grade_counts = grade_df['grade'].value_counts()
                total_scans = len(grade_df)

                # Calculate time-based averages
                avg_30d = grade_df['grade_numeric'].mean()
                avg_14d = grade_df['grade_numeric'].tail(168).mean() if len(grade_df) >= 168 else avg_30d  # 14 days
                avg_7d = grade_df['grade_numeric'].tail(84).mean() if len(grade_df) >= 84 else avg_30d  # 7 days

                # Calculate rating transitions
                if len(grade_df) > 1:
                    transitions = (grade_df['grade_numeric'].diff() != 0).sum() - 1  # -1 to exclude first NaN
                    upgrades = (grade_df['grade_numeric'].diff() > 0).sum()
                    downgrades = (grade_df['grade_numeric'].diff() < 0).sum()
                else:
                    transitions = 0
                    upgrades = 0
                    downgrades = 0

                # Create rating distribution table
                rating_order = ['S+', 'S', 'A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F']
                rating_data = []
                for rating in rating_order:
                    count = grade_counts.get(rating, 0)
                    if count > 0:
                        percentage = (count / total_scans) * 100
                        rating_data.append({
                            'Rating': rating,
                            'Count': count,
                            'Percentage': f'{percentage:.1f}%',
                            'Time Period': f'~{(count * 2):.0f}h'  # Each scan is ~2 hours
                        })

                if rating_data:
                    rating_dist_df = pd.DataFrame(rating_data)
                    st.dataframe(rating_dist_df, use_container_width=True, hide_index=True)

                # Key insights
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rating Transitions", f"{transitions}",
                             help="Number of rating changes in 30 days")
                with col2:
                    st.metric("Upgrades / Downgrades", f"↗️ {upgrades} / ↘️ {downgrades}",
                             help="Count of rating improvements vs declines")
                with col3:
                    period_trend = "📈" if avg_7d > avg_30d else "📉" if avg_7d < avg_30d else "→"
                    st.metric("7-Day vs 30-Day", f"{period_trend} {avg_7d:.2f} / {avg_30d:.2f}",
                             help="Recent performance vs overall average")
            else:
                st.info("📊 Rating history will be available after more scan cycles complete.")

        # ============================================================================
        # 5. Volume & Spread Analysis
        # ============================================================================
        with st.expander("📊 Volume & Spread Analysis", expanded=True):
            st.markdown("#### 30-Day Volume and Spread Trends")

            # Load spread/volume history
            sv_df = load_spread_volume_history(
                exchange=selected_config['exchange'],
                symbol=selected_config['symbol'],
                days=30
            )

            if not sv_df.empty:
                # Create the chart
                sv_chart = create_spread_volume_chart(
                    sv_df,
                    spread_threshold=thresholds['spread_threshold'],
                    volume_threshold=thresholds['volume_threshold']
                )
                st.plotly_chart(sv_chart, use_container_width=True)

                # Volume & Spread Statistics Table
                st.markdown("---")
                st.markdown("#### 📊 Volume & Spread Statistics")

                # Calculate statistics
                latest_spread = sv_df['spread_pct'].iloc[-1]
                latest_volume = sv_df['volume_24h'].iloc[-1]

                avg_spread = sv_df['spread_pct'].mean()
                avg_volume = sv_df['volume_24h'].mean()

                min_spread = sv_df['spread_pct'].min()
                min_volume = sv_df['volume_24h'].min()

                max_spread = sv_df['spread_pct'].max()
                max_volume = sv_df['volume_24h'].max()

                # Change from average
                spread_change = ((latest_spread - avg_spread) / avg_spread * 100) if avg_spread > 0 else 0
                volume_change = ((latest_volume - avg_volume) / avg_volume * 100) if avg_volume > 0 else 0

                # Create dataframe for table
                stats_table = pd.DataFrame({
                    'Metric': ['Spread', 'Volume 24h'],
                    'Current': [
                        f'{latest_spread:.3f}%',
                        f'${latest_volume:,.0f}'
                    ],
                    '30-Day Average': [
                        f'{avg_spread:.3f}%',
                        f'${avg_volume:,.0f}'
                    ],
                    'Change from Avg': [
                        f'{spread_change:+.1f}%',
                        f'{volume_change:+.1f}%'
                    ],
                    'Min (30d)': [
                        f'{min_spread:.3f}%',
                        f'${min_volume:,.0f}'
                    ],
                    'Max (30d)': [
                        f'{max_spread:.3f}%',
                        f'${max_volume:,.0f}'
                    ],
                    'Target': [
                        f'{thresholds["spread_threshold"]:.1f}%',
                        f'${thresholds["volume_threshold"]:,.0f}'
                    ]
                })

                st.dataframe(stats_table, use_container_width=True, hide_index=True)

                # Key insights
                st.markdown("**💡 Key Insights:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    spread_status = "✅ Tight" if latest_spread <= thresholds['spread_threshold'] else "⚠️ Wide"
                    st.metric("Spread Status", spread_status,
                             delta=f"{latest_spread - thresholds['spread_threshold']:.3f}% vs target")
                with col2:
                    volume_status = "✅ Sufficient" if latest_volume >= thresholds['volume_threshold'] else "⚠️ Low"
                    st.metric("Volume Status", volume_status,
                             delta=f"${latest_volume - thresholds['volume_threshold']:,.0f} vs target")
                with col3:
                    spread_volatility = (max_spread - min_spread) / avg_spread * 100 if avg_spread > 0 else 0
                    st.metric("Spread Volatility", f"{spread_volatility:.1f}%",
                             help="(Max - Min) / Average × 100")
            else:
                st.info("📊 Data will be available after more scan cycles complete.")

        # ============================================================================
        # 6. Depth Analysis
        # ============================================================================
        with st.expander("💧 Depth Analysis", expanded=True):
            st.markdown("#### 30-Day Depth Distribution (2%, 5%, 10%)")

            # Load depth history
            depth_df = load_depth_history(
                exchange=selected_config['exchange'],
                symbol=selected_config['symbol'],
                days=30
            )

            if not depth_df.empty:
                # Create the chart
                depth_chart = create_depth_area_chart(
                    depth_df,
                    depth_threshold=thresholds['depth_threshold']
                )
                st.altair_chart(depth_chart, use_container_width=True)

                # Liquidity Distribution Table
                st.markdown("---")
                st.markdown("#### 📊 Liquidity Distribution Table")

                # Calculate statistics for each depth level
                latest_2pct = depth_df['depth_2pct'].iloc[-1]
                latest_5pct = depth_df['depth_5pct'].iloc[-1]
                latest_10pct = depth_df['depth_10pct'].iloc[-1]

                avg_2pct = depth_df['depth_2pct'].mean()
                avg_5pct = depth_df['depth_5pct'].mean()
                avg_10pct = depth_df['depth_10pct'].mean()

                min_2pct = depth_df['depth_2pct'].min()
                min_5pct = depth_df['depth_5pct'].min()
                min_10pct = depth_df['depth_10pct'].min()

                max_2pct = depth_df['depth_2pct'].max()
                max_5pct = depth_df['depth_5pct'].max()
                max_10pct = depth_df['depth_10pct'].max()

                # Change from average
                change_2pct = ((latest_2pct - avg_2pct) / avg_2pct * 100) if avg_2pct > 0 else 0
                change_5pct = ((latest_5pct - avg_5pct) / avg_5pct * 100) if avg_5pct > 0 else 0
                change_10pct = ((latest_10pct - avg_10pct) / avg_10pct * 100) if avg_10pct > 0 else 0

                # Create dataframe for table
                liquidity_table = pd.DataFrame({
                    'Depth Level': ['±2%', '±5%', '±10%'],
                    'Current (USD)': [
                        f'${latest_2pct:,.0f}',
                        f'${latest_5pct:,.0f}',
                        f'${latest_10pct:,.0f}'
                    ],
                    '30-Day Avg (USD)': [
                        f'${avg_2pct:,.0f}',
                        f'${avg_5pct:,.0f}',
                        f'${avg_10pct:,.0f}'
                    ],
                    'Change from Avg': [
                        f'{change_2pct:+.1f}%',
                        f'{change_5pct:+.1f}%',
                        f'{change_10pct:+.1f}%'
                    ],
                    'Min (USD)': [
                        f'${min_2pct:,.0f}',
                        f'${min_5pct:,.0f}',
                        f'${min_10pct:,.0f}'
                    ],
                    'Max (USD)': [
                        f'${max_2pct:,.0f}',
                        f'${max_5pct:,.0f}',
                        f'${max_10pct:,.0f}'
                    ]
                })

                st.dataframe(liquidity_table, use_container_width=True, hide_index=True)

                # Key insights
                st.markdown("**💡 Key Insights:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    trend_emoji = "📈" if change_2pct > 0 else "📉"
                    st.metric("2% Depth Trend", f"{trend_emoji} {abs(change_2pct):.1f}%",
                             delta=f"${latest_2pct - avg_2pct:,.0f} from avg")
                with col2:
                    liquidity_ratio = (latest_10pct / latest_2pct) if latest_2pct > 0 else 0
                    st.metric("10%/2% Ratio", f"{liquidity_ratio:.2f}x",
                             help="Higher ratio = better liquidity distribution")
                with col3:
                    volatility = (max_2pct - min_2pct) / avg_2pct * 100 if avg_2pct > 0 else 0
                    st.metric("2% Depth Volatility", f"{volatility:.1f}%",
                             help="(Max - Min) / Average × 100")
            else:
                st.info("📊 Data will be available after more scan cycles complete.")

        # ============================================================================
        # 7. High-Frequency Time-Series Analysis (1-Minute Data)
        # ============================================================================
        with st.expander("⏱️ High-Frequency Analysis (1-Min Data)", expanded=True):
            st.markdown("#### Real-Time Liquidity Monitoring from Premium Pool")

            # Auto-refresh controls
            col_refresh1, col_refresh2, col_refresh3 = st.columns([2, 1, 1])
            with col_refresh1:
                st.caption("View 1-minute snapshot data aggregated over different time ranges")
            with col_refresh2:
                auto_refresh = st.checkbox("🔄 Auto-refresh (60s)", value=False,
                                          help="Automatically refresh chart every 60 seconds")
            with col_refresh3:
                if st.button("🔄 Refresh Now"):
                    st.rerun()

            # Add auto-refresh mechanism
            if auto_refresh:
                import time
                refresh_placeholder = st.empty()
                current_time = time.time()

                # Initialize session state for last refresh time
                if 'last_analytics_refresh' not in st.session_state:
                    st.session_state.last_analytics_refresh = current_time

                # Check if 60 seconds have passed
                time_since_refresh = current_time - st.session_state.last_analytics_refresh
                if time_since_refresh >= 60:
                    st.session_state.last_analytics_refresh = current_time
                    st.rerun()
                else:
                    remaining = 60 - int(time_since_refresh)
                    refresh_placeholder.caption(f"⏱️ Next refresh in {remaining} seconds...")
                    time.sleep(1)
                    st.rerun()

            # Time range selector
            time_range = st.radio(
                "Select Time Range:",
                options=["24h", "72h", "7d", "30d"],
                horizontal=True,
                help="24h: 1-min intervals | 72h: 5-min intervals | 7d: 15-min intervals | 30d: 1-hour intervals"
            )

            # Initialize TimeSeriesHelper
            ts_helper = TimeSeriesHelper()

            # Load time-series data for selected range
            ts_data = ts_helper.get_timeseries_data(
                exchange=selected_config['exchange'],
                symbol=selected_config['symbol'],
                range_name=time_range
            )

            # Check if data is available
            if 'error' in ts_data:
                st.warning(f"⚠️ {ts_data.get('error', 'No data available')}")
                st.info("""
                **Note:** This feature requires 1-minute snapshot data from Premium Pool monitoring.

                Data will be available once:
                1. Token is added to Premium Pool (watchlist)
                2. Premium pool collector has been running for sufficient time
                3. At least some snapshots have been recorded
                """)
            elif ts_data['data_points'] == 0:
                st.info("📊 No 1-minute snapshot data available yet. Add this token to your watchlist to start collecting data.")
            else:
                # Display data point count and time range info with last update time
                from datetime import datetime, timezone
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Data Points", f"{ts_data['data_points']}")
                with col2:
                    interval_map = {'24h': '1-min', '72h': '5-min', '7d': '15-min', '30d': '1-hour'}
                    st.metric("Interval", interval_map[time_range])
                with col3:
                    st.metric("Time Range", time_range.upper())
                with col4:
                    # Show last data point time
                    if ts_data['timestamps']:
                        last_ts = ts_data['timestamps'][-1]
                        try:
                            last_dt = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
                            last_time_str = last_dt.strftime('%H:%M:%S')
                            st.metric("Latest Data", last_time_str)
                        except:
                            st.metric("Latest Data", "Now")

                st.markdown("---")

                # Create charts using Plotly for better interactivity
                try:
                    import plotly.graph_objects as go
                    from plotly.subplots import make_subplots

                    # Format timestamps for display
                    formatted_times = [format_timestamp_for_chart(ts, time_range) for ts in ts_data['timestamps']]

                    # Create subplot with 3 rows
                    fig = make_subplots(
                        rows=3, cols=1,
                        subplot_titles=('Spread (%)', 'Depth (USD)', 'Volume 24h (USD)'),
                        vertical_spacing=0.08,
                        row_heights=[0.33, 0.33, 0.33]
                    )

                    # Spread chart with markers on latest point
                    fig.add_trace(
                        go.Scatter(
                            x=formatted_times,
                            y=ts_data['spreads'],
                            name='Spread',
                            line=dict(color='#f59e0b', width=2),
                            mode='lines+markers',
                            marker=dict(
                                size=[4] * (len(formatted_times) - 1) + [12],  # Larger marker for latest
                                color=['#f59e0b'] * (len(formatted_times) - 1) + ['#dc2626'],  # Red for latest
                                symbol='circle'
                            ),
                            hovertemplate='<b>Time:</b> %{x}<br><b>Spread:</b> %{y:.3f}%<extra></extra>'
                        ),
                        row=1, col=1
                    )

                    # Add spread threshold line
                    if thresholds['spread_threshold']:
                        fig.add_hline(
                            y=thresholds['spread_threshold'],
                            line_dash="dash",
                            line_color="red",
                            opacity=0.5,
                            row=1, col=1
                        )

                    # Depth chart
                    fig.add_trace(
                        go.Scatter(
                            x=formatted_times,
                            y=ts_data['depths'],
                            name='Depth 2%',
                            line=dict(color='#3b82f6', width=2),
                            mode='lines',
                            fill='tozeroy',
                            fillcolor='rgba(59, 130, 246, 0.2)'
                        ),
                        row=2, col=1
                    )

                    # Add depth threshold line
                    if thresholds['depth_threshold']:
                        fig.add_hline(
                            y=thresholds['depth_threshold'],
                            line_dash="dash",
                            line_color="red",
                            opacity=0.5,
                            row=2, col=1
                        )

                    # Volume chart
                    fig.add_trace(
                        go.Scatter(
                            x=formatted_times,
                            y=ts_data['volumes'],
                            name='Volume 24h',
                            line=dict(color='#8b5cf6', width=2),
                            mode='lines',
                            fill='tozeroy',
                            fillcolor='rgba(139, 92, 246, 0.2)'
                        ),
                        row=3, col=1
                    )

                    # Add volume threshold line
                    if thresholds.get('volume_threshold'):
                        fig.add_hline(
                            y=thresholds['volume_threshold'],
                            line_dash="dash",
                            line_color="red",
                            opacity=0.5,
                            row=3, col=1
                        )

                    # Update layout
                    fig.update_xaxes(title_text="Time", row=3, col=1)
                    fig.update_yaxes(title_text="Spread (%)", row=1, col=1)
                    fig.update_yaxes(title_text="Depth (USD)", row=2, col=1)
                    fig.update_yaxes(title_text="Volume (USD)", row=3, col=1)

                    fig.update_layout(
                        height=900,
                        showlegend=False,
                        hovermode='x unified',
                        template='plotly_dark'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                except ImportError:
                    st.warning("⚠️ Plotly is not installed. Install it to view charts: `pip install plotly`")

                    # Fallback: Show raw data table
                    st.markdown("**Data Preview (First 10 points):**")
                    preview_df = pd.DataFrame({
                        'Time': [format_timestamp_for_chart(ts, time_range) for ts in ts_data['timestamps'][:10]],
                        'Spread (%)': ts_data['spreads'][:10],
                        'Depth (USD)': ts_data['depths'][:10],
                        'Volume (USD)': ts_data['volumes'][:10]
                    })
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

                # Display statistics
                st.markdown("---")
                st.markdown("#### 📊 Statistics Summary")

                stats = ts_data['stats']

                # Spread stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Spread (%)**")
                    st.markdown(f"- Current: `{stats['spread']['current']:.3f}%`")
                    st.markdown(f"- Average: `{stats['spread']['avg']:.3f}%`")
                    st.markdown(f"- Min: `{stats['spread']['min']:.3f}%`")
                    st.markdown(f"- Max: `{stats['spread']['max']:.3f}%`")

                with col2:
                    st.markdown("**Depth 2% (USD)**")
                    st.markdown(f"- Current: `${stats['depth']['current']:,.0f}`")
                    st.markdown(f"- Average: `${stats['depth']['avg']:,.0f}`")
                    st.markdown(f"- Min: `${stats['depth']['min']:,.0f}`")
                    st.markdown(f"- Max: `${stats['depth']['max']:,.0f}`")

                with col3:
                    st.markdown("**Volume 24h (USD)**")
                    st.markdown(f"- Current: `${stats['volume']['current']:,.0f}`")
                    st.markdown(f"- Average: `${stats['volume']['avg']:,.0f}`")
                    st.markdown(f"- Min: `${stats['volume']['min']:,.0f}`")
                    st.markdown(f"- Max: `${stats['volume']['max']:,.0f}`")

                # Key insights
                st.markdown("---")
                st.markdown("**💡 Key Insights:**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    spread_current = stats['spread']['current']
                    spread_avg = stats['spread']['avg']
                    spread_status = "✅ Below Avg" if spread_current < spread_avg else "⚠️ Above Avg"
                    spread_delta = ((spread_current - spread_avg) / spread_avg * 100) if spread_avg > 0 else 0
                    st.metric("Spread vs Average", spread_status, f"{spread_delta:+.1f}%")

                with col2:
                    depth_current = stats['depth']['current']
                    depth_avg = stats['depth']['avg']
                    depth_status = "✅ Above Avg" if depth_current > depth_avg else "⚠️ Below Avg"
                    depth_delta = ((depth_current - depth_avg) / depth_avg * 100) if depth_avg > 0 else 0
                    st.metric("Depth vs Average", depth_status, f"{depth_delta:+.1f}%")

                with col3:
                    volume_current = stats['volume']['current']
                    volume_avg = stats['volume']['avg']
                    volume_status = "✅ Above Avg" if volume_current > volume_avg else "⚠️ Below Avg"
                    volume_delta = ((volume_current - volume_avg) / volume_avg * 100) if volume_avg > 0 else 0
                    st.metric("Volume vs Average", volume_status, f"{volume_delta:+.1f}%")

                # Volatility metrics
                st.markdown("---")
                st.markdown("**📈 Volatility Metrics:**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    spread_volatility = ((stats['spread']['max'] - stats['spread']['min']) / stats['spread']['avg'] * 100) if stats['spread']['avg'] > 0 else 0
                    st.metric("Spread Volatility", f"{spread_volatility:.1f}%", help="(Max - Min) / Average × 100")

                with col2:
                    depth_volatility = ((stats['depth']['max'] - stats['depth']['min']) / stats['depth']['avg'] * 100) if stats['depth']['avg'] > 0 else 0
                    st.metric("Depth Volatility", f"{depth_volatility:.1f}%", help="(Max - Min) / Average × 100")

                with col3:
                    volume_volatility = ((stats['volume']['max'] - stats['volume']['min']) / stats['volume']['avg'] * 100) if stats['volume']['avg'] > 0 else 0
                    st.metric("Volume Volatility", f"{volume_volatility:.1f}%", help="(Max - Min) / Average × 100")

        with st.expander("🚀 Advanced Indicators (Phase 3)", expanded=False):
            # Load latest microburst data for this token
            try:
                from pathlib import Path
                import json as json_lib
                from datetime import datetime, timedelta

                microburst_dir = Path("microburst_analysis")
                if microburst_dir.exists():
                    # Find latest microburst file
                    microburst_files = sorted(microburst_dir.glob("microburst_*.json"), reverse=True)
                    if microburst_files:
                        latest_file = microburst_files[0]
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            microburst_data = json_lib.load(f)

                        # Find data for current token
                        token_data_mb = None
                        for result in microburst_data.get('results', []):
                            if (result.get('exchange') == token_data.get('exchange') and
                                result.get('symbol') == token_data.get('symbol')):
                                token_data_mb = result
                                break

                        if token_data_mb:
                            st.markdown("#### ⚡ Micro-Burst 5 Indicators")
                            st.caption(f"Last analyzed: {token_data_mb.get('analyzed_at', 'N/A')}")

                            adv = token_data_mb.get('advanced_indicators', {})

                            # Liquidity Score
                            liq_score = adv.get('liquidity_score', {})
                            if liq_score:
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    score = liq_score.get('score', 0)
                                    rating = liq_score.get('rating', 'N/A')
                                    st.metric("💧 Liquidity Score", f"{score}/100", delta=rating.upper())
                                with col2:
                                    st.metric("📊 Spread", f"{liq_score.get('spread_component', 0)}/100")
                                with col3:
                                    st.metric("📏 Depth", f"{liq_score.get('depth_component', 0)}/100")
                                with col4:
                                    st.metric("📈 Volume", f"{liq_score.get('volume_component', 0)}/100")

                            # Volatility & Momentum
                            col1, col2, col3 = st.columns(3)

                            vol_idx = adv.get('volatility_index', {})
                            if vol_idx:
                                with col1:
                                    vol = vol_idx.get('volatility', 0)
                                    level = vol_idx.get('level', 'N/A')
                                    st.metric("📉 Volatility", f"{vol:.4f}", delta=level.upper())

                            momentum = adv.get('price_momentum', {})
                            if momentum:
                                with col2:
                                    mom_val = momentum.get('momentum', 0)
                                    direction = momentum.get('direction', 'N/A')
                                    st.metric("🎯 Momentum", f"{mom_val:.4f}", delta=direction.upper())

                            imbalance = adv.get('bid_ask_imbalance', {})
                            if imbalance:
                                with col3:
                                    avg_imb = imbalance.get('avg', 0)
                                    max_imb = imbalance.get('max', 0)
                                    st.metric("⚖️ Imbalance", f"{avg_imb:.3f}", delta=f"Max: {max_imb:.3f}")

                            # Anomalies
                            if token_data_mb.get('has_anomaly'):
                                st.warning(f"⚠️ Anomalies detected: {', '.join(token_data_mb.get('anomalies', []))}")
                        else:
                            st.info("ℹ️ This token is not in Premium Pool - no micro-burst data available")
                    else:
                        st.info("ℹ️ No micro-burst analysis data available yet")
                else:
                    st.info("ℹ️ Micro-burst analysis directory not found")

            except Exception as e:
                st.error(f"❌ Error loading micro-burst data: {str(e)}")

            st.markdown("---")
            st.markdown("#### 📈 Exchange Deposit Flow & Market Cap")
            st.info("🚧 Coming in future update: On-chain deposit/withdrawal tracking")

            st.markdown("#### 📊 Spread Interval Analysis")
            st.info("🚧 Coming in future update: Spread distribution analysis")

            st.markdown("#### ⚖️ Liquidity Center-of-Gravity (COG)")
            st.info("🚧 Coming in future update: Liquidity center-of-gravity analysis")

        with st.expander("🤖 AI Strategy Recommendations (Phase 4)", expanded=False):
            st.info("🚧 Coming in Phase 4:")
            st.markdown("""
            - 🎯 Liquidity Risk Assessment
            - 💡 Delisting Risk Mitigation Strategy
            - 💰 Token Deposit/Withdrawal Strategy
            - 📊 Order Book Strategy by Price Levels
            - 💵 Cash Budget Recommendations
            """)
