import streamlit as st
import ccxt
import pandas as pd
import time
import threading
import random
import os
import json
from datetime import datetime

# Global function for price precision conversion
def get_decimal_places(precision):
    """Convert price precision to decimal places - handles all exchange precision formats"""
    if precision is None:
        return 8  # Default fallback
    
    # Handle scientific notation (e.g., 1e-06, 1e-05)
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
            # Scientific notation (e.g., "1e-05", "1e-06")
            try:
                exp = int(precision.lower().split('e-')[1])
                return exp
            except:
                return 8
        elif '.' in precision:
            # Decimal format (e.g., "0.00001", "0.01")
            return len(precision.split('.')[1])
        else:
            # Integer format (e.g., "1", "0")
            return 0
    
    return 8  # Default fallback

st.set_page_config(
    page_title="Crypto Exchange Dashboard",
    page_icon="📊",
    layout="wide"
)

# Sidebar Navigation
st.sidebar.title("⚙️ Admin Settings")
st.sidebar.markdown("---")

# Streamlined menu
admin_section = st.sidebar.radio(
    "Navigate to:",
    ["🎛️ System Control", "👥 User Management", "🎯 Token & Data Management", "🔍 Scan & Monitor", "🔐 API Management", "⚙️ System Settings"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.caption("Night Watch Admin Dashboard v1.0")

# Main content based on selection
if admin_section == "🎛️ System Control":
    from admin_modules.admin_system_control import render_system_control
    render_system_control()

elif admin_section == "👥 User Management":
    from admin_modules.admin_customer_honeymoon import render_customer_honeymoon_management
    render_customer_honeymoon_management()

elif admin_section == "🎯 Token & Data Management":
    st.title("🎯 Token & Data Management")
    st.caption("Comprehensive token and database management")

    # 6개 탭으로 통합
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Main Board",
        "⭐ Premium Pool",
        "⚠️ Delisting Check",
        "🏢 MEXC Assessment",
        "⚪ Whitelist",
        "📦 Archive"
    ])

    with tab1:
        from admin_modules.admin_tokens import render_token_management
        render_token_management()

    with tab2:
        from admin_modules.admin_premium_pool import render_premium_pool
        render_premium_pool()

    with tab3:
        from admin_modules.admin_delisting_check import render_delisting_check
        render_delisting_check()

    with tab4:
        from admin_modules.admin_assessment_zone import render_assessment_zone_management
        render_assessment_zone_management()

    with tab5:
        from admin_modules.admin_whitelist import render_whitelist_management
        render_whitelist_management()

    with tab6:
        st.subheader("📦 Archived Data")
        st.caption("Tokens removed from Main Board but still under observation (30-day retention)")

        from token_lifecycle import TokenLifecycle

        lifecycle = TokenLifecycle()
        archived_tokens = lifecycle.get_archive_tokens()
        main_board_tokens = lifecycle.get_main_board_tokens()

        # 요약 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Archived Tokens", len(archived_tokens))
        with col2:
            st.metric("🚨 Main Board Tokens", len(main_board_tokens))
        with col3:
            chronic_count = sum(1 for t in archived_tokens if t.get('is_chronic'))
            st.metric("⚠️ Chronic Risk", chronic_count)

        st.markdown("---")

        if not archived_tokens:
            st.info("📭 No tokens in archive. Tokens will appear here after being removed from Main Board.")
        else:
            # 만성적 위험 토큰 경고
            chronic_tokens = [t for t in archived_tokens if t.get('is_chronic')]
            if chronic_tokens:
                st.warning(f"⚠️ **{len(chronic_tokens)} chronic high-risk tokens detected** (3+ reentries to Main Board)")

            # 아카이브 토큰 테이블
            st.markdown("### 📋 Archived Tokens")

            import pandas as pd
            df = pd.DataFrame(archived_tokens)
            df['archived_date'] = pd.to_datetime(df['archived_date']).dt.strftime('%Y-%m-%d %H:%M')
            df['archive_until'] = pd.to_datetime(df['archive_until']).dt.strftime('%Y-%m-%d')
            df['status'] = df.apply(lambda x: '⚠️ CHRONIC' if x['is_chronic'] else '📦 Normal', axis=1)

            st.dataframe(
                df[['token_id', 'archived_date', 'archive_until', 'reentry_count', 'status', 'data_size_kb']].rename(columns={
                    'token_id': 'Token',
                    'archived_date': 'Archived At',
                    'archive_until': 'Keep Until',
                    'reentry_count': 'Reentries',
                    'status': 'Status',
                    'data_size_kb': 'Data (KB)'
                }),
                use_container_width=True,
                height=300
            )

elif admin_section == "🔍 Scan & Monitor":
    st.title("🔍 Scan & Monitor")
    st.caption("Configure and monitor all scanning operations")

    # 6가지 스캔 시스템을 2개 탭으로 구성
    tab1, tab2 = st.tabs(["⚙️ Scan Configuration", "📊 Scan Status & Monitor"])

    with tab1:
        st.subheader("⚙️ Scan Configuration")
        st.caption("Configure all scan types and their settings")

        # 스캔 타입별로 expander로 구분
        with st.expander("🔄 **Regular Scan** - Main Board Scan (Every 2 Hours)", expanded=True):
            st.markdown("""
            **Target:** All USDT spot pairs on 4 exchanges (Gate.io, MEXC, KuCoin, Bitget)
            **Frequency:** Fixed 2-hour intervals (00:00, 02:00, 04:00, ..., 22:00 UTC)
            **Purpose:** Monitor all exchange listings for delisting risk detection
            """)
            from admin_modules.admin_scanner import render_scanner
            render_scanner()

        with st.expander("⭐ **Premium Pool Scan** - High-Priority Tokens (Every 1 Minute)"):
            st.markdown("""
            **Target:** Tokens registered in Premium Watch Pool
            **Frequency:** 1-minute intervals
            **Purpose:** Real-time monitoring of user-selected high-priority tokens
            """)
            st.info("Premium Pool scan runs automatically for all tokens in Premium Pool")
            # Premium Pool 스캔 설정 (필요시 추가)

        with st.expander("⚡ **Micro Burst Scan** - Ultra High-Frequency Random Scan"):
            st.markdown("""
            **Target:** Pairs with liquidity monitoring or detailed monitoring enabled
            **Frequency:** Random ultra-high frequency (sub-second intervals)
            **Purpose:** Real-time liquidity tracking and arbitrage opportunity detection
            """)
            st.warning("⚠️ High system resource usage - Use sparingly")
            # Micro Burst 스캔 설정 (필요시 추가)

        st.markdown("---")

        with st.expander("🍯 **Honeymoon Price Scan** - Historical Price Check for Premium Pool"):
            st.markdown("""
            **Target:** Premium Pool tokens
            **Frequency:** Weekly or on-demand
            **Purpose:** Check if listing price exists at 9 months, 7 months, 5 months, 3 months, 1 month ago
            **Use Case:** Identify tokens in "honeymoon period" with stable price history
            """)

        with st.expander("🔗 **Blockchain Explorer & Market Data Scan** - External Data Integration"):
            st.markdown("""
            **Target:** Selected tokens requiring on-chain or external market data
            **Sources:**
            - Blockchain Explorers (Etherscan, BSCScan, etc.)
            - CoinGecko API
            - CoinMarketCap API

            **Purpose:** Cross-reference on-chain activity, market cap, volume data
            """)
            st.caption("⚠️ Not yet implemented - Future feature")

    with tab2:
        st.subheader("📊 Scan Status & Real-Time Monitor")
        st.caption("Monitor all active scans and their current status")

        from admin_modules.admin_scan_monitor import render_scan_monitor
        render_scan_monitor()

elif admin_section == "🔐 API Management":
    st.title("🔐 API Management")
    st.caption("Manage API keys, incentives, and on-chain tracking")

    # 3개 탭으로 확장
    tab1, tab2, tab3 = st.tabs(["🔑 API Keys", "🎁 API Incentives", "🔗 On-Chain Wallets"])

    with tab1:
        from admin_modules.admin_api_management import render_api_management
        render_api_management()

    with tab2:
        from admin_modules.admin_api_provider_incentive import render_api_provider_incentive
        render_api_provider_incentive()

    with tab3:
        from admin_modules.admin_onchain_management import render_onchain_management
        render_onchain_management()

elif admin_section == "⚙️ System Settings":
    st.title("⚙️ System Settings")
    st.caption("Configure data collection intervals and subscription features")
    
    # Tabs for system settings
    settings_tab = st.tabs(["📋 Main Board Policy", "📊 Data Collection", "⏱️ Update & Features", "💎 Subscription Tiers"])
    
    # Tab 1: Main Board Policy Settings
    with settings_tab[0]:
        from admin_modules.admin_system import render_main_board_policy
        render_main_board_policy()
    
    # Tab 2: Data Collection Settings
    with settings_tab[1]:
        from admin_modules.admin_system import render_data_collection_settings
        render_data_collection_settings()
    
    # Tab 3: Update & Feature Settings
    with settings_tab[2]:
        from admin_modules.admin_system import render_update_feature_settings
        render_update_feature_settings()
    
    # Tab 4: Subscription Tiers
    with settings_tab[3]:
        from admin_modules.admin_system import render_subscription_tiers
        render_subscription_tiers()
    
    # Load current settings
    collection_config_file = "data_collection_config.json"
    if os.path.exists(collection_config_file):
        with open(collection_config_file, 'r', encoding='utf-8') as f:
            collection_config = json.load(f)
    else:
        # Default configuration
        collection_config = {
            "main_board": {
                "enabled": False,
                "interval_minutes": 15,
                "description": "Main Board background collection (Crisis Bulletin)"
            },
            "watch_list_free": {
                "enabled": False,
                "interval_minutes": 10,
                "description": "Free user watch list (fetch on page load only)"
            },
            "watch_list_pro": {
                "enabled": True,
                "interval_minutes": 1,
                "description": "PRO user watch list (background collection)"
            },
            "analytics_pro": {
                "enabled": True,
                "interval_seconds": 30,
                "description": "PRO analytics page (active session only)"
            },
            "defender_premium": {
                "enabled": True,
                "interval_seconds": 10,
                "description": "Premium Liquidity Defender (24/7 monitoring)"
            }
        }
    
    # Load monitoring configs to show current token count
    config_file = "monitoring_configs.json"
    monitoring_configs = {}
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            monitoring_configs = json.load(f)

    main_board_count = len(monitoring_configs)
    
    # Summary metrics
    st.markdown("### 📊 Current Status")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Main Board Tokens", main_board_count, help="Tokens currently on Main Board")
    with col2:
        active_layers = sum(1 for layer in collection_config.values() if layer.get('enabled', False))
        st.metric("Active Layers", f"{active_layers}/5", help="Number of collection layers enabled")
    with col3:
        # Calculate estimated API calls per hour for Main Board
        if collection_config['main_board']['enabled']:
            calls_per_hour = (60 / collection_config['main_board']['interval_minutes']) * main_board_count
            st.metric("Main Board API/h", f"{calls_per_hour:.0f}", help="Estimated API calls per hour for Main Board")
        else:
            st.metric("Main Board API/h", "0", help="Background collection disabled")
    with col4:
        # Total estimated API calls per hour (simplified)
        total_calls = 0
        if collection_config['main_board']['enabled']:
            total_calls += (60 / collection_config['main_board']['interval_minutes']) * main_board_count
        if collection_config['watch_list_pro']['enabled']:
            total_calls += (60 / collection_config['watch_list_pro']['interval_minutes']) * 10  # Assume 10 tokens per user
        st.metric("Total Est. API/h", f"{total_calls:.0f}", help="Rough estimate of total API calls per hour")
    
    st.markdown("---")
    
    # Layer 1: Batch Scanner (read-only, configured in High Risk Scanner)
    st.markdown("### 1️⃣ Batch Scanner (거래소 전체 스캔)")
    st.caption("🔒 Configured in 🔍 High Risk Scanner section")
    
    scanner_config_file = "config/scanner_config.json"
    if os.path.exists(scanner_config_file):
        with open(scanner_config_file, 'r', encoding='utf-8') as f:
            scanner_config = json.load(f)
        scheduler_config = scanner_config.get('scheduler', {})
        scan_interval = scheduler_config.get('scan_interval_hours', 2)
        st.info(f"⏰ Current: **{scan_interval} hours** (00:00, {scan_interval:02d}:00, {scan_interval*2:02d}:00, ... UTC)")
    else:
        st.info("⏰ Current: **2 hours** (default)")
    
    st.markdown("---")
    
    # Layer 2: Main Board (Crisis Bulletin)
    st.markdown("### 2️⃣ Main Board (Crisis Bulletin)")
    st.caption(f"📦 Current tokens: **{main_board_count}** | 🎯 Target: 50~100 tokens")
    
    mb_enabled = st.checkbox(
        "✅ Enable background data collection for Main Board",
        value=collection_config['main_board']['enabled'],
        key="mb_enabled",
        help="If disabled, Main Board will only use Batch Scanner data (2-hour intervals)"
    )
    
    if mb_enabled:
        mb_interval = st.slider(
            "⏰ Collection interval (minutes)",
            min_value=1,
            max_value=60,
            value=collection_config['main_board']['interval_minutes'],
            step=1,
            key="mb_interval",
            help=f"Current load: {main_board_count} tokens × (60 ÷ {collection_config['main_board']['interval_minutes']}) = {(60 / collection_config['main_board']['interval_minutes']) * main_board_count:.0f} API calls/hour"
        )
        
        # Load warning
        estimated_calls = (60 / mb_interval) * main_board_count
        if estimated_calls > 10000:
            st.error(f"⚠️ HIGH LOAD: ~{estimated_calls:.0f} API calls/hour. Consider increasing interval or reducing token count.")
        elif estimated_calls > 5000:
            st.warning(f"⚠️ MODERATE LOAD: ~{estimated_calls:.0f} API calls/hour. Monitor API rate limits.")
        else:
            st.success(f"✅ LOW LOAD: ~{estimated_calls:.0f} API calls/hour. Safe for most exchanges.")
        
        collection_config['main_board']['enabled'] = mb_enabled
        collection_config['main_board']['interval_minutes'] = mb_interval
    else:
        st.info("📌 Main Board will display data from Batch Scanner only (2-hour intervals)")
        collection_config['main_board']['enabled'] = False
    
    st.markdown("---")
    
    # Layer 3: My Watch List (Free)
    st.markdown("### 3️⃣ My Watch List (Free Users)")
    st.caption("📦 Target: 10 tokens per user | 🎯 Recommended: Fetch on page load only")
    
    wl_free_enabled = st.checkbox(
        "✅ Enable background data collection for Free users",
        value=collection_config['watch_list_free']['enabled'],
        key="wl_free_enabled",
        help="⚠️ Not recommended. Free users should fetch data only when viewing the page."
    )
    
    if wl_free_enabled:
        st.warning("⚠️ Background collection for Free users is enabled. This may increase server load unnecessarily.")
        wl_free_interval = st.slider(
            "⏰ Collection interval (minutes)",
            min_value=5,
            max_value=60,
            value=collection_config['watch_list_free']['interval_minutes'],
            step=5,
            key="wl_free_interval"
        )
        collection_config['watch_list_free']['enabled'] = wl_free_enabled
        collection_config['watch_list_free']['interval_minutes'] = wl_free_interval
    else:
        st.success("✅ Free users will fetch data only when viewing the page (recommended)")
        collection_config['watch_list_free']['enabled'] = False
    
    st.markdown("---")
    
    # Layer 4: My Watch List (PRO)
    st.markdown("### 4️⃣ My Watch List (PRO Users)")
    st.caption("📦 Target: 10 tokens per user | 🎯 Recommended: 1~5 minutes")
    
    wl_pro_enabled = st.checkbox(
        "✅ Enable background data collection for PRO users",
        value=collection_config['watch_list_pro']['enabled'],
        key="wl_pro_enabled",
        help="PRO users get real-time updates for their watch list"
    )
    
    if wl_pro_enabled:
        wl_pro_interval = st.slider(
            "⏰ Collection interval (minutes)",
            min_value=1,
            max_value=30,
            value=collection_config['watch_list_pro']['interval_minutes'],
            step=1,
            key="wl_pro_interval",
            help="Faster updates = better service, but higher API usage"
        )
        
        # Estimate load (assume 10 PRO users for now)
        estimated_pro_users = 10
        estimated_calls = (60 / wl_pro_interval) * 10 * estimated_pro_users
        st.caption(f"📊 Estimated load (10 PRO users): ~{estimated_calls:.0f} API calls/hour")
        st.info("💡 PRO users = Higher revenue → Maintain or improve service quality, don't downgrade!")
        
        collection_config['watch_list_pro']['enabled'] = wl_pro_enabled
        collection_config['watch_list_pro']['interval_minutes'] = wl_pro_interval
    else:
        st.info("📌 PRO users will fetch data only when viewing the page")
        collection_config['watch_list_pro']['enabled'] = False
    
    st.markdown("---")
    
    # Layer 5: Liquidity Analytics PRO
    st.markdown("### 5️⃣ Liquidity Analytics PRO")
    st.caption("📦 Target: 1 token per active session | 🎯 Recommended: 30~60 seconds")
    
    analytics_enabled = st.checkbox(
        "✅ Enable real-time collection for Analytics page",
        value=collection_config['analytics_pro']['enabled'],
        key="analytics_enabled",
        help="Collection only runs when user has the Analytics page open"
    )
    
    if analytics_enabled:
        analytics_interval = st.slider(
            "⏰ Collection interval (seconds)",
            min_value=10,
            max_value=300,
            value=collection_config['analytics_pro']['interval_seconds'],
            step=10,
            key="analytics_interval",
            help="Active session only - stops when user closes the page"
        )
        
        collection_config['analytics_pro']['enabled'] = analytics_enabled
        collection_config['analytics_pro']['interval_seconds'] = analytics_interval
    else:
        st.info("📌 Analytics page will fetch data only on manual refresh")
        collection_config['analytics_pro']['enabled'] = False
    
    st.markdown("---")
    
    # Layer 6: Liquidity Defender (Premium)
    st.markdown("### 6️⃣ Liquidity Defender (Premium)")
    st.caption("📦 Target: 1~5 tokens per customer | 🎯 Recommended: 10~60 seconds")
    
    defender_enabled = st.checkbox(
        "✅ Enable 24/7 monitoring for Defender",
        value=collection_config['defender_premium']['enabled'],
        key="defender_enabled",
        help="Premium service - 24/7 monitoring with auto-trading"
    )
    
    if defender_enabled:
        defender_interval = st.slider(
            "⏰ Collection interval (seconds)",
            min_value=5,
            max_value=300,
            value=collection_config['defender_premium']['interval_seconds'],
            step=5,
            key="defender_interval",
            help="Faster = more responsive, but higher API usage"
        )
        
        # Estimate load (assume 5 tokens for now)
        estimated_tokens = 5
        estimated_calls = (3600 / defender_interval) * estimated_tokens
        st.caption(f"📊 Estimated load (5 tokens): ~{estimated_calls:.0f} API calls/hour")
        
        collection_config['defender_premium']['enabled'] = defender_enabled
        collection_config['defender_premium']['interval_seconds'] = defender_interval
    else:
        st.info("📌 Liquidity Defender is disabled")
        collection_config['defender_premium']['enabled'] = False
    
    st.markdown("---")
    
    # Save button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            try:
                with open(collection_config_file, 'w', encoding='utf-8') as f:
                    json.dump(collection_config, f, indent=2, ensure_ascii=False)
                st.success("✅ Settings saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving settings: {e}")
    
    with col2:
        if st.button("🔄 Reset to Default", type="secondary", use_container_width=True):
            # Reset to default
            collection_config = {
                "main_board": {"enabled": False, "interval_minutes": 15, "description": "Main Board background collection (Crisis Bulletin)"},
                "watch_list_free": {"enabled": False, "interval_minutes": 10, "description": "Free user watch list (fetch on page load only)"},
                "watch_list_pro": {"enabled": True, "interval_minutes": 1, "description": "PRO user watch list (background collection)"},
                "analytics_pro": {"enabled": True, "interval_seconds": 30, "description": "PRO analytics page (active session only)"},
                "defender_premium": {"enabled": True, "interval_seconds": 10, "description": "Premium Liquidity Defender (24/7 monitoring)"}
            }
            try:
                with open(collection_config_file, 'w', encoding='utf-8') as f:
                    json.dump(collection_config, f, indent=2, ensure_ascii=False)
                st.success("✅ Reset to default settings!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error resetting settings: {e}")
    
    with col3:
        st.caption("💡 Tip: PRO/Premium users pay more → They deserve better service quality!")

elif admin_section == "🔍 High Risk Scanner":
    st.title("🔍 High Risk Token Scanner")
    st.markdown("**Automated scanner for high-risk tokens across 4 major exchanges**")
    
    # 설정 로드
    scanner_config_file = "config/scanner_config.json"
    if os.path.exists(scanner_config_file):
        with open(scanner_config_file, 'r', encoding='utf-8') as f:
            scanner_config = json.load(f)
    else:
        scanner_config = {
            "exchanges": {
                "gateio": {"enabled": True, "spread_threshold": 1.0, "spread_required": True, "depth_threshold": 500.0, "depth_required": True, "volume_threshold": 10000.0, "volume_required": False, "scan_interval_hours": 4, "history_days": 2},
                "mexc": {"enabled": True, "spread_threshold": 1.0, "spread_required": True, "depth_threshold": 500.0, "depth_required": True, "volume_threshold": 10000.0, "volume_required": False, "scan_interval_hours": 4, "history_days": 2},
                "kucoin": {"enabled": True, "spread_threshold": 1.0, "spread_required": True, "depth_threshold": 500.0, "depth_required": True, "volume_threshold": 10000.0, "volume_required": False, "scan_interval_hours": 4, "history_days": 2},
                "bitget": {"enabled": True, "spread_threshold": 1.0, "spread_required": True, "depth_threshold": 500.0, "depth_required": True, "volume_threshold": 10000.0, "volume_required": False, "scan_interval_hours": 4, "history_days": 2}
            },
            "global": {"default_scan_interval_hours": 4, "default_history_days": 2}
        }
    
    # 스캐너 상태
    enabled_exchanges = [ex for ex, cfg in scanner_config['exchanges'].items() if cfg['enabled']]
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Enabled Exchanges", len(enabled_exchanges), help=", ".join([ex.upper() for ex in enabled_exchanges]))
    with col2:
        # 활성화된 거래소들의 평균 스캔 주기 표시
        if enabled_exchanges:
            avg_interval = sum(scanner_config['exchanges'][ex].get('scan_interval_hours', 4) for ex in enabled_exchanges) / len(enabled_exchanges)
            st.metric("Avg Scan Interval", f"{avg_interval:.1f} hours")
    
    st.markdown("---")
    
    # 📅 자동 스케줄러 설정
    st.markdown("### 📅 Automated Scan Scheduler")
    st.caption("Configure automatic scanning with UTC-based scheduling")
    
    scheduler_config = scanner_config.get('scheduler', {
        'enabled': False,
        'scan_interval_hours': 4,
        'next_scan_time': None,
        'last_scan_time': None
    })
    
    sched_col1, sched_col2, sched_col3 = st.columns([2, 2, 1])
    
    with sched_col1:
        scheduler_enabled = st.checkbox(
            "✅ Enable Automated Scheduler",
            value=scheduler_config.get('enabled', False),
            key="scheduler_enabled",
            help="Automatically run scans at scheduled intervals (UTC-based)"
        )
        if scheduler_enabled != scheduler_config.get('enabled', False):
            scanner_config['scheduler']['enabled'] = scheduler_enabled
            config_changed = True
    
    with sched_col2:
        scan_interval = st.selectbox(
            "⏰ Scan Interval (UTC 00:00 base)",
            options=[1, 2, 3, 4, 6, 12],
            index=[1, 2, 3, 4, 6, 12].index(scheduler_config.get('scan_interval_hours', 4)),
            key="scheduler_interval",
            help="Scans will run at UTC hours divisible by this interval (e.g., 4h = 00:00, 04:00, 08:00, ...)"
        )
        if scan_interval != scheduler_config.get('scan_interval_hours', 4):
            scanner_config['scheduler']['scan_interval_hours'] = scan_interval
            config_changed = True
    
    with sched_col3:
        st.info("📊 History: 2 days")
    
    # 스케줄러 상태 표시
    if scheduler_enabled:
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            history_days = scanner_config.get('global', {}).get('default_history_days', 2)
            expected_scans = (history_days * 24) // scan_interval
            st.metric("Expected Scans", f"{expected_scans} scans", 
                     help=f"{history_days} days × (24h ÷ {scan_interval}h)")
        
        with status_col2:
            last_scan = scheduler_config.get('last_scan_time', 'Never')
            if last_scan and last_scan != 'Never':
                try:
                    last_dt = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                    last_scan = last_dt.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    pass
            st.metric("Last Scan", last_scan if last_scan != 'Never' else "N/A")
        
        with status_col3:
            next_scan = scheduler_config.get('next_scan_time', 'Not scheduled')
            if next_scan and next_scan != 'Not scheduled':
                try:
                    next_dt = datetime.fromisoformat(next_scan.replace('Z', '+00:00'))
                    next_scan = next_dt.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    pass
            st.metric("Next Scan", next_scan if next_scan != 'Not scheduled' else "N/A")
        
        # 데이터 병합 정책
        st.caption("**⚙️ Data Merge Policy (when changing settings)**")
        merge_policy = st.radio(
            "Select policy:",
            options=['keep_existing', 'clear_and_restart'],
            index=0 if scheduler_config.get('data_merge_policy', 'keep_existing') == 'keep_existing' else 1,
            key="scheduler_merge_policy",
            help="Keep existing: Merge old data with new settings | Clear and restart: Delete old data and start fresh",
            horizontal=True
        )
        if merge_policy != scheduler_config.get('data_merge_policy', 'keep_existing'):
            scanner_config['scheduler']['data_merge_policy'] = merge_policy
            config_changed = True
        
        if merge_policy == 'keep_existing':
            st.info("📌 Existing scan data will be kept and merged with new scans")
        else:
            st.warning("⚠️ Existing scan data will be cleared when settings are changed")
    
    st.markdown("---")
    
    # 거래소별 임계값 설정
    st.markdown("### ⚙️ Exchange-Specific Thresholds")
    st.caption("Customize spread and depth thresholds for each exchange")
    
    config_changed = False
    
    for exchange_id in ['gateio', 'mexc', 'kucoin', 'bitget']:
        ex_config = scanner_config['exchanges'][exchange_id]
        
        # 마지막 스캔 시간 표시
        last_scan = ex_config.get('last_scan_time', None)
        if last_scan:
            try:
                from datetime import datetime
                last_dt = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                time_ago = datetime.now(timezone.utc) - last_dt
                hours_ago = int(time_ago.total_seconds() / 3600)
                minutes_ago = int((time_ago.total_seconds() % 3600) / 60)
                
                if hours_ago > 0:
                    time_str = f"{hours_ago}h {minutes_ago}m ago"
                else:
                    time_str = f"{minutes_ago}m ago"
                
                expander_title = f"🔧 {exchange_id.upper()} Settings (Last scan: {time_str})"
            except:
                expander_title = f"🔧 {exchange_id.upper()} Settings"
        else:
            expander_title = f"🔧 {exchange_id.upper()} Settings (Never scanned)"
        
        with st.expander(expander_title, expanded=False):
            # Exchange enabled
            enabled = st.checkbox(
                "✅ Enable this exchange",
                value=ex_config.get('enabled', True),
                key=f"scanner_{exchange_id}_enabled"
            )
            if enabled != ex_config.get('enabled', True):
                scanner_config['exchanges'][exchange_id]['enabled'] = enabled
                config_changed = True
            
            st.markdown("---")
            st.caption("**Configure thresholds and select which filters are required (AND logic)**")
            
            # 3개 필터 행
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            # 1. Spread Filter
            with filter_col1:
                st.markdown("**📈 Spread Filter**")
                spread_req = st.checkbox(
                    "Required",
                    value=ex_config.get('spread_required', True),
                    key=f"scanner_{exchange_id}_spread_req",
                    help="If checked, spread > threshold is REQUIRED"
                )
                spread = st.number_input(
                    "Threshold (%)",
                    min_value=0.1,
                    max_value=10.0,
                    value=float(ex_config.get('spread_threshold', 1.0)),
                    step=0.1,
                    key=f"scanner_{exchange_id}_spread",
                    help="Flag if spread > this value"
                )
                if spread_req != ex_config.get('spread_required', True):
                    scanner_config['exchanges'][exchange_id]['spread_required'] = spread_req
                    config_changed = True
                if spread != ex_config.get('spread_threshold', 1.0):
                    scanner_config['exchanges'][exchange_id]['spread_threshold'] = spread
                    config_changed = True
            
            # 2. Depth Filter
            with filter_col2:
                st.markdown("**💧 Depth Filter**")
                depth_req = st.checkbox(
                    "Required",
                    value=ex_config.get('depth_required', True),
                    key=f"scanner_{exchange_id}_depth_req",
                    help="If checked, ±2% depth < threshold is REQUIRED"
                )
                depth = st.number_input(
                    "Threshold ($)",
                    min_value=10.0,
                    max_value=5000.0,
                    value=float(ex_config.get('depth_threshold', 500.0)),
                    step=50.0,
                    key=f"scanner_{exchange_id}_depth",
                    help="Flag if ±2% depth < this value"
                )
                if depth_req != ex_config.get('depth_required', True):
                    scanner_config['exchanges'][exchange_id]['depth_required'] = depth_req
                    config_changed = True
                if depth != ex_config.get('depth_threshold', 500.0):
                    scanner_config['exchanges'][exchange_id]['depth_threshold'] = depth
                    config_changed = True
            
            # 3. Volume Filter
            with filter_col3:
                st.markdown("**📊 Volume Filter**")
                volume_req = st.checkbox(
                    "Required",
                    value=ex_config.get('volume_required', False),
                    key=f"scanner_{exchange_id}_volume_req",
                    help="If checked, 24h volume < threshold is REQUIRED"
                )
                volume = st.number_input(
                    "Threshold ($)",
                    min_value=100.0,
                    max_value=100000.0,
                    value=float(ex_config.get('volume_threshold', 10000.0)),
                    step=1000.0,
                    key=f"scanner_{exchange_id}_volume",
                    help="Flag if 24h volume < this value"
                )
                if volume_req != ex_config.get('volume_required', False):
                    scanner_config['exchanges'][exchange_id]['volume_required'] = volume_req
                    config_changed = True
                if volume != ex_config.get('volume_threshold', 10000.0):
                    scanner_config['exchanges'][exchange_id]['volume_threshold'] = volume
                    config_changed = True
            
            # 스캔 주기 및 평균 기간 설정
            st.markdown("---")
            schedule_col1, schedule_col2 = st.columns(2)
            
            with schedule_col1:
                scan_interval = st.number_input(
                    "⏰ Scan Interval (hours)",
                    min_value=1,
                    max_value=24,
                    value=ex_config.get('scan_interval_hours', 2),
                    step=1,
                    key=f"scanner_{exchange_id}_interval",
                    help="How often to scan this exchange (e.g., 2 = every 2 hours)"
                )
                if scan_interval != ex_config.get('scan_interval_hours', 2):
                    scanner_config['exchanges'][exchange_id]['scan_interval_hours'] = scan_interval
                    config_changed = True
            
            with schedule_col2:
                history_days = st.number_input(
                    "📅 Average Period (days)",
                    min_value=1,
                    max_value=7,
                    value=ex_config.get('history_days', 2),
                    step=1,
                    key=f"scanner_{exchange_id}_history",
                    help="Calculate average over this many days (e.g., 2 = 2-day average)"
                )
                if history_days != ex_config.get('history_days', 2):
                    scanner_config['exchanges'][exchange_id]['history_days'] = history_days
                    config_changed = True
            
            # 현재 필터 요약
            required_filters = []
            if scanner_config['exchanges'][exchange_id].get('spread_required'):
                required_filters.append(f"Spread>{scanner_config['exchanges'][exchange_id]['spread_threshold']}%")
            if scanner_config['exchanges'][exchange_id].get('depth_required'):
                required_filters.append(f"Depth<${scanner_config['exchanges'][exchange_id]['depth_threshold']}")
            if scanner_config['exchanges'][exchange_id].get('volume_required'):
                required_filters.append(f"Vol<${scanner_config['exchanges'][exchange_id]['volume_threshold']}")
            
            if required_filters:
                st.info(f"**Active filters:** {' AND '.join(required_filters)} | Interval: {scan_interval}h | History: {history_days}d")
            else:
                st.warning(f"⚠️ No required filters! All tokens will pass. | Interval: {scan_interval}h | History: {history_days}d")
    
    if config_changed:
        if st.button("💾 Save Scanner Configuration", type="primary"):
            # 파일의 기존 값을 다시 읽어서 enabled 필드 보존
            if os.path.exists(scanner_config_file):
                with open(scanner_config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
                # 기존 enabled 값 보존 (변경되지 않은 거래소의 경우)
                for ex_id in existing_config.get('exchanges', {}).keys():
                    if ex_id in scanner_config.get('exchanges', {}):
                        # enabled 필드가 명시적으로 변경되지 않았다면 기존 값 유지
                        if f"scanner_{ex_id}_enabled" not in st.session_state:
                            scanner_config['exchanges'][ex_id]['enabled'] = existing_config['exchanges'][ex_id].get('enabled', True)
            
            with open(scanner_config_file, 'w', encoding='utf-8') as f:
                json.dump(scanner_config, f, indent=2, ensure_ascii=False)
            st.success("✅ Scanner configuration saved!")
            st.rerun()
    
    st.markdown("---")
    
    # 수동 스캔 실행
    st.markdown("### 🚀 Manual Scan")
    
    # 거래소 선택
    st.caption("**Select exchanges to scan (급변하는 거래소만 선택적으로 스캔 가능)**")
    exchange_cols = st.columns(4)
    
    selected_exchanges = []
    with exchange_cols[0]:
        if st.checkbox("Gate.io", value=True, key="scan_gateio"):
            selected_exchanges.append('gateio')
    with exchange_cols[1]:
        if st.checkbox("MEXC", value=True, key="scan_mexc"):
            selected_exchanges.append('mexc')
    with exchange_cols[2]:
        if st.checkbox("KuCoin", value=True, key="scan_kucoin"):
            selected_exchanges.append('kucoin')
    with exchange_cols[3]:
        if st.checkbox("Bitget", value=True, key="scan_bitget"):
            selected_exchanges.append('bitget')
    
    scan_col1, scan_col2 = st.columns([2, 1])
    
    with scan_col1:
        if selected_exchanges:
            st.info(f"💡 Will scan: {', '.join([ex.upper() for ex in selected_exchanges])}")
        else:
            st.warning("⚠️ Please select at least one exchange")
    
    with scan_col2:
        if st.button("🔍 Run Scan Now", type="primary", use_container_width=True, disabled=not selected_exchanges):
            try:
                # 백그라운드에서 스캔 실행
                import subprocess
                import sys
                
                # Python 실행 파일 경로 가져오기
                python_exe = sys.executable
                
                # 거래소 선택 인자 추가
                scan_args = [python_exe, '-m', 'batch_scanner']
                if selected_exchanges:
                    scan_args.extend(['--exchanges'] + selected_exchanges)
                
                # 백그라운드 프로세스 시작
                subprocess.Popen(
                    scan_args,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                    cwd=os.getcwd()
                )
                
                st.success("✅ 백그라운드 스캔 시작!")
                st.info("🔄 아래 'Scan Status (Live)' 섹션에서 실시간 진행 상황을 확인하세요")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Scan failed: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # 🔄 Scan Status (실시간 스캔 진행 상태 - 항상 표시, 자동 새로고침)
    st.markdown("### 🔄 Scan Status (Live)")
    
    # scan_history.json 로드 (거래소별 진행 상태)
    scan_history_file = "scan_history.json"
    scan_history = {}
    if os.path.exists(scan_history_file):
        try:
            with open(scan_history_file, 'r', encoding='utf-8') as f:
                scan_history = json.load(f)
        except:
            scan_history = {}
    
    if os.path.exists('scan_status.json'):
        try:
            with open('scan_status.json', 'r', encoding='utf-8') as f:
                scan_status = json.load(f)
            
            status = scan_status.get('status', 'idle')
            
            if status == 'running':
                # 스캔 진행 중 - 자동 새로고침
                current_exchange = scan_status.get('current_exchange', 'unknown')
                
                st.info(f"🔄 **Scanning in progress...** Current: **{current_exchange.upper()}**")
                
                # 거래소별 진행 상태 바
                from batch_scanner import EXCHANGES
                
                exchange_cols = st.columns(len(EXCHANGES))
                
                for idx, exchange_id in enumerate(EXCHANGES):
                    with exchange_cols[idx]:
                        ex_data = scan_history.get(exchange_id, {})
                        ex_status = ex_data.get('status', 'pending')
                        ex_progress = ex_data.get('progress', '0/0')
                        ex_pct = float(ex_data.get('progress_pct', 0))
                        ex_found = int(ex_data.get('found', 0))
                        
                        if ex_status == 'completed':
                            st.success(f"**{exchange_id.upper()}**")
                            st.caption(f"✅ {ex_progress} | **{ex_found} tokens**")
                            st.progress(1.0)
                        elif ex_status == 'running':
                            st.info(f"**{exchange_id.upper()}**")
                            st.caption(f"🔄 {ex_progress} ({ex_pct:.1f}%) | **{ex_found} found**")
                            st.progress(ex_pct / 100.0)
                        else:
                            st.caption(f"**{exchange_id.upper()}**")
                            st.caption(f"⏳ Waiting... | **{ex_found} found**")
                            st.progress(0.0)
                
                # 자동 새로고침 (3초마다)
                time.sleep(3)
                st.rerun()
            
            elif status == 'completed':
                # 스캔 완료
                total_found = int(scan_status.get('total_found', 0))
                timestamp = str(scan_status.get('timestamp', 'Unknown'))
                
                st.success(f"✅ **Scan Completed** - Found: **{total_found}** tokens | Last Update: {timestamp[:19]}")
                
                # 거래소별 최종 결과 (진행 중과 동일한 형식 유지)
                from batch_scanner import EXCHANGES
                
                exchange_cols = st.columns(len(EXCHANGES))
                
                for idx, exchange_id in enumerate(EXCHANGES):
                    with exchange_cols[idx]:
                        ex_data = scan_history.get(exchange_id, {})
                        ex_status = ex_data.get('status', 'completed')
                        ex_progress = ex_data.get('progress', 'N/A')
                        ex_found = int(ex_data.get('found', 0))
                        
                        st.success(f"**{exchange_id.upper()}**")
                        st.caption(f"✅ {ex_progress} | **{ex_found} tokens**")
                        st.progress(1.0)
            
            else:
                # idle 상태
                st.warning("⏸️ No scan activity yet. Click 'Run Scan Now' to start!")
        
        except Exception as e:
            st.error(f"⚠️ Error reading scan status: {e}")
            st.caption("scan_status.json 파일을 읽는 중 오류가 발생했습니다.")
    else:
        st.warning("⏸️ No scan activity yet. Click 'Run Scan Now' to start!")
    
    st.markdown("---")
    
    # 스캔 결과 표시 (2개 탭: Latest Manual Scan / Accumulated Average)
    st.markdown("### 📊 Scan Results")
    
    tab1, tab2 = st.tabs(["📋 Latest Manual Scan", "📈 Accumulated Average"])
    
    # ===== TAB 1: Latest Manual Scan =====
    with tab1:
        latest_scan_file = "scan_history/latest.json"
        
        # 스캔 진행 중인지 확인
        is_scanning = False
        if os.path.exists('scan_status.json'):
            try:
                with open('scan_status.json', 'r', encoding='utf-8') as f:
                    scan_status = json.load(f)
                    is_scanning = (scan_status.get('status') == 'running')
            except:
                pass
        
        if is_scanning:
            # 스캔 진행 중
            st.info("🔄 **Scan in progress...** Results will appear here when complete.")
            st.caption("Check the 'Scan Status (Live)' section above for real-time progress.")
        
        elif os.path.exists(latest_scan_file):
            try:
                with open(latest_scan_file, 'r', encoding='utf-8') as f:
                    latest_data = json.load(f)
                
                tokens = latest_data.get('tokens', [])
                scan_time = latest_data.get('scan_time', 'Unknown')
                
                # 정보 표시
                info_col1, info_col2, info_col3 = st.columns(3)
                with info_col1:
                    st.metric("Total Tokens", len(tokens))
                with info_col2:
                    st.metric("Scan Time", scan_time[:19])
                with info_col3:
                    if st.button("🗑️ Delete This Scan", type="secondary"):
                        os.remove(latest_scan_file)
                        st.success("✅ Latest scan deleted!")
                        st.rerun()
                
                st.markdown("---")
                
                if tokens:
                    # 필터링
                    exchange_filter = st.multiselect(
                        "Filter by Exchange",
                        options=['gateio', 'mexc', 'kucoin', 'bitget'],
                        default=['gateio', 'mexc', 'kucoin', 'bitget'],
                        key="latest_exchange_filter"
                    )
                    
                    filtered_tokens = [t for t in tokens if t['exchange'] in exchange_filter]
                    
                    st.markdown(f"**Showing {len(filtered_tokens)} tokens** (sorted by ±2% depth ascending)")
                    
                    # 테이블
                    token_df = pd.DataFrame([
                        {
                            "Exchange": t['exchange'].upper(),
                            "Symbol": t['symbol'],
                            "Spread": f"{t['spread_pct']:.2f}%",
                            "±2% Depth": f"${t['depth_2pct']:.2f}",
                            "24h Volume": f"${t['quote_volume']:.2f}",
                            "Bid": f"${t['bid']:.8f}",
                            "Ask": f"${t['ask']:.8f}"
                        }
                        for t in filtered_tokens
                    ])
                    
                    st.dataframe(token_df, use_container_width=True, height=400)
                else:
                    st.info("📭 No tokens found in latest scan")
            
            except Exception as e:
                st.error(f"❌ Error loading latest scan: {e}")
        else:
            st.info("📭 No manual scan results yet. Click 'Run Scan Now' above to start!")
    
    # ===== TAB 2: Accumulated Average =====
    with tab2:
        # high_risk_tokens.json 로드
        high_risk_file = "high_risk_tokens.json"
        
        if os.path.exists(high_risk_file):
            try:
                with open(high_risk_file, 'r', encoding='utf-8') as f:
                    high_risk_data = json.load(f)
                
                tokens = high_risk_data.get('tokens', [])
                updated_at = high_risk_data.get('updated_at', 'Unknown')
                
                # 정보 표시
                info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                with info_col1:
                    st.metric("Total Tokens", len(tokens))
                with info_col2:
                    approved_count = sum(1 for t in tokens if t.get('approved', False))
                    st.metric("Approved", approved_count)
                with info_col3:
                    st.caption(f"Last Updated: {updated_at[:19]}")
                with info_col4:
                    if st.button("📊 Calculate Average", type="primary"):
                        from batch_scanner import calculate_2day_average
                        calculate_2day_average()
                        st.success("✅ Average calculated!")
                        st.rerun()
                
                st.markdown("---")
                
                if tokens:
                    # 필터링 옵션
                    filter_col1, filter_col2 = st.columns(2)
                    
                    with filter_col1:
                        show_approved_only = st.checkbox("Show Approved Only", value=False, key="avg_show_approved")
                    
                    with filter_col2:
                        exchange_filter = st.multiselect(
                            "Filter by Exchange",
                            options=['gateio', 'mexc', 'kucoin', 'bitget'],
                            default=['gateio', 'mexc', 'kucoin', 'bitget'],
                            key="avg_exchange_filter"
                        )
                    
                    # 필터링 적용
                    filtered_tokens = [
                        t for t in tokens
                        if (not show_approved_only or t.get('approved', False))
                        and t['exchange'] in exchange_filter
                    ]
                    
                    st.markdown(f"**Showing {len(filtered_tokens)} tokens** (sorted by ±2% depth ascending)")
                    
                    # 자동 승인 설정
                    auto_approve_col1, auto_approve_col2 = st.columns(2)
                
                    with auto_approve_col1:
                        st.markdown("**🤖 Auto-Approve Settings (by Exchange)**")
                        auto_approve_config = {}
                        auto_col1, auto_col2, auto_col3, auto_col4 = st.columns(4)
                    
                        with auto_col1:
                            auto_approve_config['gateio'] = st.checkbox("Gate.io Auto", value=False, key="auto_gateio", help="Automatically approve all Gate.io tokens")
                        with auto_col2:
                            auto_approve_config['mexc'] = st.checkbox("MEXC Auto", value=False, key="auto_mexc", help="Automatically approve all MEXC tokens")
                        with auto_col3:
                            auto_approve_config['kucoin'] = st.checkbox("KuCoin Auto", value=False, key="auto_kucoin", help="Automatically approve all KuCoin tokens")
                        with auto_col4:
                            auto_approve_config['bitget'] = st.checkbox("Bitget Auto", value=False, key="auto_bitget", help="Automatically approve all Bitget tokens")
                
                    with auto_approve_col2:
                        if any(auto_approve_config.values()):
                            auto_exchanges = [ex.upper() for ex, enabled in auto_approve_config.items() if enabled]
                            st.info(f"🤖 Auto-approve enabled for: {', '.join(auto_exchanges)}")
                        else:
                            st.caption("⚙️ Enable auto-approve to automatically add tokens to Main Board")
                
                # 테이블로 표시
                    token_df = pd.DataFrame([
                        {
                            "Exchange": t['exchange'].upper(),
                            "Symbol": t['symbol'],
                            "Avg Spread": f"{t['avg_spread_pct']:.2f}%",
                            "Avg ±2% Depth": f"${t['avg_depth_2pct']:.2f}",
                            "Samples": t['sample_count'],
                            "Approved": "✅" if t.get('approved', False) else "⏳",
                            "Auto": "🤖" if auto_approve_config.get(t['exchange'], False) else "",
                            "Token ID": f"{t['exchange']}_{t['symbol'].replace('/', '_').lower()}"
                        }
                        for t in filtered_tokens
                    ])
                
                # 인터랙티브 테이블
                    st.dataframe(
                        token_df[["Exchange", "Symbol", "Avg Spread", "Avg ±2% Depth", "Samples", "Approved", "Auto"]],
                        use_container_width=True,
                        height=400
                    )
                
                    st.markdown("---")
                
                # 승인/거부 섹션
                    st.markdown("### ✅ Manage Tokens")
                
                # 미승인 토큰 선택
                    unapproved_tokens = [t for t in filtered_tokens if not t.get('approved', False)]
                    token_options = [
                        f"{t['exchange'].upper()} - {t['symbol']} (Spread: {t['avg_spread_pct']:.2f}%, Depth: ${t['avg_depth_2pct']:.2f})"
                        for t in unapproved_tokens
                    ]
                
                    manage_col1, manage_col2 = st.columns(2)
                
                    with manage_col1:
                        st.markdown("**📝 Manual Approval**")
                    
                    # 전체 선택 옵션
                        select_all_unapproved = st.checkbox(
                            f"Select All Unapproved ({len(token_options)})",
                            value=False,
                            key="select_all_unapproved"
                        )
                    
                        if select_all_unapproved:
                            selected_for_approval = token_options
                        else:
                            selected_for_approval = st.multiselect(
                                "Select tokens to approve:",
                                options=token_options,
                                help="Approved tokens will be added to Main Board"
                            )
                
                    with manage_col2:
                        st.markdown("**🗑️ Remove from Scan Results**")
                    
                    # 전체 토큰에서 삭제할 토큰 선택
                        all_token_options = [
                            f"{t['exchange'].upper()} - {t['symbol']} (Spread: {t['avg_spread_pct']:.2f}%, Depth: ${t['avg_depth_2pct']:.2f}) {'✅' if t.get('approved', False) else '⏳'}"
                            for t in filtered_tokens
                        ]
                    
                    # 전체 선택 옵션
                        select_all_delete = st.checkbox(
                            f"Select All ({len(all_token_options)})",
                            value=False,
                            key="select_all_delete"
                        )
                    
                        if select_all_delete:
                            selected_for_deletion = all_token_options
                        else:
                            selected_for_deletion = st.multiselect(
                                "Select tokens to delete:",
                                options=all_token_options,
                                help="Permanently remove from scan results"
                            )
                
                    approval_col1, approval_col2, approval_col3 = st.columns(3)
                
                    with approval_col1:
                        if st.button("✅ Approve Selected", type="primary", disabled=len(selected_for_approval)==0):
                        # 자동 승인도 함께 처리
                            tokens_to_approve = list(selected_for_approval)
                        
                        # 자동 승인 설정된 거래소의 토큰도 추가
                            for t in unapproved_tokens:
                                if auto_approve_config.get(t['exchange'], False):
                                    token_str = f"{t['exchange'].upper()} - {t['symbol']} (Spread: {t['avg_spread_pct']:.2f}%, Depth: ${t['avg_depth_2pct']:.2f})"
                                    if token_str not in tokens_to_approve:
                                        tokens_to_approve.append(token_str)
                        
                        # 승인 처리
                            for sel in tokens_to_approve:
                            # 선택된 토큰 파싱
                                parts = sel.split(" - ")
                                exchange = parts[0].lower()
                                symbol = parts[1].split(" (")[0]
                            
                            # 토큰 찾아서 승인 상태 업데이트
                                for t in tokens:
                                    if t['exchange'] == exchange and t['symbol'] == symbol:
                                        t['approved'] = True
                                        break
                        
                        # 파일 저장
                            with open(high_risk_file, 'w', encoding='utf-8') as f:
                                json.dump(high_risk_data, f, indent=2, ensure_ascii=False)
                        
                        # monitoring_configs.json에도 추가
                            monitoring_configs = {}
                            config_file = "monitoring_configs.json"
                            if os.path.exists(config_file):
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    monitoring_configs = json.load(f)
                        
                            for sel in tokens_to_approve:
                                parts = sel.split(" - ")
                                exchange = parts[0].lower()
                                symbol = parts[1].split(" (")[0]
                                token_id = f"{exchange}_{symbol.replace('/', '_').lower()}"
                            
                                if token_id not in monitoring_configs:
                                    monitoring_configs[token_id] = {
                                        "exchange": exchange,
                                        "symbol": symbol,
                                        "started_at": datetime.now(timezone.utc).isoformat(),
                                        "status": "active",
                                        "description": f"{symbol} monitoring on {exchange} (High-Risk Scanner)"
                                    }
                        
                            with open(config_file, 'w', encoding='utf-8') as f:
                                json.dump(monitoring_configs, f, indent=2, ensure_ascii=False)
                        
                            st.success(f"✅ Approved {len(tokens_to_approve)} tokens and added to Main Board!")
                            st.rerun()
                
                    with approval_col2:
                        if st.button("🗑️ Delete Selected", type="secondary", disabled=len(selected_for_deletion)==0):
                        # 선택된 토큰 삭제
                            for sel in selected_for_deletion:
                            # 선택된 토큰 파싱 (✅ 또는 ⏳ 제거)
                                sel_clean = sel.replace(" ✅", "").replace(" ⏳", "")
                                parts = sel_clean.split(" - ")
                                exchange = parts[0].lower()
                                symbol = parts[1].split(" (")[0]
                            
                            # 토큰 리스트에서 제거
                                tokens = [t for t in tokens if not (t['exchange'] == exchange and t['symbol'] == symbol)]
                        
                            high_risk_data['tokens'] = tokens
                        
                            with open(high_risk_file, 'w', encoding='utf-8') as f:
                                json.dump(high_risk_data, f, indent=2, ensure_ascii=False)
                        
                            st.success(f"🗑️ Deleted {len(selected_for_deletion)} tokens from scan results")
                            st.rerun()
                
                    with approval_col3:
                        if st.button("🗑️ Clear All Approved", type="secondary"):
                        # 승인된 토큰만 제거
                            tokens_before = len(tokens)
                            tokens = [t for t in tokens if not t.get('approved', False)]
                            high_risk_data['tokens'] = tokens
                        
                            with open(high_risk_file, 'w', encoding='utf-8') as f:
                                json.dump(high_risk_data, f, indent=2, ensure_ascii=False)
                        
                            st.success(f"🗑️ Cleared {tokens_before - len(tokens)} approved tokens from scan results")
                            st.rerun()
                
                else:
                    st.info("📭 No tokens found in accumulated average")
            
            except Exception as e:
                st.error(f"❌ Error loading accumulated average: {e}")
        else:
            st.info("📭 No accumulated average yet. Click '📊 Calculate Average' to generate!")

elif admin_section == "⏱️ Update & Feature Settings":
    st.title("⏱️ Update & Feature Settings")
    
    # Load current settings
    subscription_config_path = "config/subscription_config.json"
    if os.path.exists(subscription_config_path):
        try:
            with open(subscription_config_path, 'r', encoding='utf-8') as f:
                sub_config = json.load(f)
        except:
            sub_config = {}
    else:
        sub_config = {}
    
    # Set default values
    defaults = {
        "free": {
            "main_board_interval_minutes": 15,
            "watchlist_interval_minutes": 5,
            "user_dashboard_interval_minutes": 60,
            "micro_burst_limit_per_day": 3
        },
        "premium": {
            "main_board_interval_minutes": 5,
            "watchlist_interval_minutes": 1,
            "user_dashboard_interval_minutes": 15,
            "micro_burst_limit_per_day": 999
        },
        "system": {
            "monitoring_refresh_interval_seconds": 300,
            "accumulation_interval_seconds": 60,
            "micro_burst_duration_seconds": 10,
            "micro_burst_fetch_interval_seconds": 1
        }
    }
    
    # Merge defaults with existing config
    for tier in ["free", "premium", "system"]:
        if tier not in sub_config:
            sub_config[tier] = {}
        for key, value in defaults[tier].items():
            if key not in sub_config[tier]:
                sub_config[tier][key] = value
    
    # Display Frontend summary at the top
    st.markdown("### 📊 Current Frontend Settings")
    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        st.markdown("**🆓 Free Users**")
        st.info(f"""
        - Main Board: {sub_config['free']['main_board_interval_minutes']} min
        - Watch List: {sub_config['free']['watchlist_interval_minutes']} min
        - User Dashboard: {sub_config['free']['user_dashboard_interval_minutes']} min
        - Micro Burst: {sub_config['free']['micro_burst_limit_per_day']} times/day
        """)
    with summary_col2:
        st.markdown("**💎 Premium Users**")
        st.success(f"""
        - Main Board: {sub_config['premium']['main_board_interval_minutes']} min
        - Watch List: {sub_config['premium']['watchlist_interval_minutes']} min
        - User Dashboard: {sub_config['premium']['user_dashboard_interval_minutes']} min
        - Micro Burst: {'Unlimited' if sub_config['premium']['micro_burst_limit_per_day'] >= 999 else f"{sub_config['premium']['micro_burst_limit_per_day']} times/day"}
        """)
    
    st.markdown("---")
    st.markdown("### 📱 Frontend User Update Settings")
    
    # Free User Settings
    st.markdown("#### 🆓 Free User Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        free_main = st.number_input(
            "Main Board Update (min)",
            min_value=1,
            max_value=120,
            value=sub_config["free"]["main_board_interval_minutes"],
            step=1,
            key="free_main"
        )
    with col2:
        free_watchlist = st.number_input(
            "My Watch List (min)",
            min_value=1,
            max_value=60,
            value=sub_config["free"]["watchlist_interval_minutes"],
            step=1,
            key="free_watchlist"
        )
    with col3:
        free_dashboard = st.number_input(
            "User Dashboard (min)",
            min_value=5,
            max_value=240,
            value=sub_config["free"]["user_dashboard_interval_minutes"],
            step=5,
            key="free_dashboard"
        )
    
    free_micro_burst = st.number_input(
        "🔥 Micro Burst Daily Limit (times)",
        min_value=0,
        max_value=20,
        value=sub_config["free"]["micro_burst_limit_per_day"],
        step=1,
        key="free_micro_burst",
        help="Number of Micro Burst analyses free users can perform per day"
    )
    
    st.markdown("---")
    
    # Premium User Settings
    st.markdown("#### 💎 Premium User Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        premium_main = st.number_input(
            "Main Board Update (min)",
            min_value=1,
            max_value=120,
            value=sub_config["premium"]["main_board_interval_minutes"],
            step=1,
            key="premium_main"
        )
    with col2:
        premium_watchlist = st.number_input(
            "My Watch List (min)",
            min_value=1,
            max_value=60,
            value=sub_config["premium"]["watchlist_interval_minutes"],
            step=1,
            key="premium_watchlist"
        )
    with col3:
        premium_dashboard = st.number_input(
            "User Dashboard (min)",
            min_value=1,
            max_value=240,
            value=sub_config["premium"]["user_dashboard_interval_minutes"],
            step=1,
            key="premium_dashboard"
        )
    
    premium_micro_burst = st.number_input(
        "🔥 Micro Burst Daily Limit (times)",
        min_value=0,
        max_value=9999,
        value=sub_config["premium"]["micro_burst_limit_per_day"],
        step=10,
        key="premium_micro_burst",
        help="Number of Micro Burst analyses premium users can perform per day (999 = Unlimited)"
    )
    
    st.markdown("---")
    
    # Display Backend summary at the top
    st.markdown("### 📊 Current Backend Settings")
    st.info(f"""
    - Monitoring Refresh: {sub_config['system']['monitoring_refresh_interval_seconds']} sec
    - Data Accumulation: {sub_config['system']['accumulation_interval_seconds']} sec
    - Micro Burst Duration: {sub_config['system']['micro_burst_duration_seconds']} sec
    - Micro Burst Fetch: {sub_config['system']['micro_burst_fetch_interval_seconds']} sec
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Backend System Settings")
    st.markdown("*External Data Collection & Processing Intervals*")
    
    col1, col2 = st.columns(2)
    with col1:
        monitoring_refresh = st.number_input(
            "Monitoring Refresh Interval (sec)",
            min_value=10,
            max_value=3600,
            value=sub_config["system"]["monitoring_refresh_interval_seconds"],
            step=10,
            key="monitoring_refresh",
            help="Interval for fetching data from exchange APIs"
        )
        accumulation_interval = st.number_input(
            "Data Accumulation Save Interval (sec)",
            min_value=10,
            max_value=600,
            value=sub_config["system"]["accumulation_interval_seconds"],
            step=10,
            key="accumulation_interval",
            help="Interval for saving collected data to files"
        )
    
    with col2:
        micro_burst_duration = st.number_input(
            "Micro Burst Operation Duration (sec)",
            min_value=5,
            max_value=60,
            value=sub_config["system"]["micro_burst_duration_seconds"],
            step=1,
            key="micro_burst_duration",
            help="Total time duration for Micro Burst analysis"
        )
        micro_burst_fetch = st.number_input(
            "Micro Burst Data Fetch Interval (sec)",
            min_value=0.1,
            max_value=5.0,
            value=float(sub_config["system"]["micro_burst_fetch_interval_seconds"]),
            step=0.1,
            key="micro_burst_fetch",
            help="Interval for collecting data during Micro Burst (0.1 = 100ms)"
        )
    
    st.markdown("---")
    
    if st.button("💾 Save All Settings", type="primary", key="save_all_settings"):
        # Update config
        sub_config["free"]["main_board_interval_minutes"] = free_main
        sub_config["free"]["watchlist_interval_minutes"] = free_watchlist
        sub_config["free"]["user_dashboard_interval_minutes"] = free_dashboard
        sub_config["free"]["micro_burst_limit_per_day"] = free_micro_burst
        
        sub_config["premium"]["main_board_interval_minutes"] = premium_main
        sub_config["premium"]["watchlist_interval_minutes"] = premium_watchlist
        sub_config["premium"]["user_dashboard_interval_minutes"] = premium_dashboard
        sub_config["premium"]["micro_burst_limit_per_day"] = premium_micro_burst
        
        sub_config["system"]["monitoring_refresh_interval_seconds"] = monitoring_refresh
        sub_config["system"]["accumulation_interval_seconds"] = accumulation_interval
        sub_config["system"]["micro_burst_duration_seconds"] = micro_burst_duration
        sub_config["system"]["micro_burst_fetch_interval_seconds"] = micro_burst_fetch
        
        try:
            with open(subscription_config_path, 'w', encoding='utf-8') as f:
                json.dump(sub_config, f, ensure_ascii=False, indent=2)
            st.success("✅ All settings have been saved successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error during save: {str(e)}")

elif admin_section == "🤖 AI Alert Import":
    st.title("🤖 AI Alert Import Management")
    
    tab1, tab2, tab3 = st.tabs(["📥 File Upload", "🔗 URL Import", "⚙️ Automation Settings"])
    
    with tab1:
        st.markdown("##### 엑셀 파일 직접 업로드")
        uploaded_file = st.file_uploader(
            "엑셀 파일 선택 (AI 경고 종목)", 
            type=['xlsx', 'xls'],
            help="필수 컬럼: exchange, symbol | 선택 컬럼: description, api_key, api_secret"
        )
        
        if st.button("📥 Import from File", type="primary", key="import_from_file"):
            if uploaded_file is not None:
                try:
                    import tempfile
                    from excel_processor import ExcelProcessor
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    processor = ExcelProcessor()
                    result = processor.process_excel_file(tmp_path)
                    
                    os.unlink(tmp_path)
                    
                    if result['success']:
                        st.success(f"✅ {result['added_count']}개 종목이 성공적으로 추가되었습니다!")
                        if result['added_tokens']:
                            with st.expander("추가된 종목 목록", expanded=True):
                                for token in result['added_tokens']:
                                    st.write(f"✓ {token['exchange']} - {token['symbol']}")
                        
                        if result['skipped_count'] > 0:
                            st.warning(f"⚠️ {result['skipped_count']}개 종목이 이미 존재하여 건너뛰었습니다.")
                        
                        if result['errors']:
                            with st.expander("오류 목록", expanded=False):
                                for error in result['errors']:
                                    st.error(f"❌ {error}")
                        
                        st.rerun()
                    else:
                        st.error("❌ 파일 처리 중 오류가 발생했습니다.")
                        for error in result['errors']:
                            st.error(f"- {error}")
                            
                except Exception as e:
                    st.error(f"❌ 파일 처리 중 오류: {str(e)}")
            else:
                st.warning("⚠️ 먼저 엑셀 파일을 업로드해주세요.")
    
    with tab2:
        st.markdown("##### URL에서 엑셀 파일 자동 다운로드")
        
        # 저장된 URL 설정 로드
        ai_config_file = "ai_import_config.json"
        if os.path.exists(ai_config_file):
            with open(ai_config_file, 'r', encoding='utf-8') as f:
                ai_config = json.load(f)
        else:
            ai_config = {"excel_url": "", "n8n_webhook_url": ""}
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            excel_url = st.text_input(
                "엑셀 파일 URL",
                value=ai_config.get("excel_url", ""),
                placeholder="https://example.com/ai_alerts.xlsx 또는 n8n 웹훅 URL",
                help="직접 다운로드 가능한 엑셀 파일 URL 또는 n8n 웹훅 URL을 입력하세요"
            )
        
        with col2:
            save_url = st.button("💾 URL 저장", key="save_excel_url")
            if save_url and excel_url:
                ai_config["excel_url"] = excel_url
                with open(ai_config_file, 'w', encoding='utf-8') as f:
                    json.dump(ai_config, f, ensure_ascii=False, indent=2)
                st.success("✅ URL이 저장되었습니다!")
        
        if st.button("🔗 URL에서 가져오기", type="primary", key="import_from_url"):
            if excel_url:
                try:
                    import requests
                    import tempfile
                    from excel_processor import ExcelProcessor
                    
                    with st.spinner("엑셀 파일 다운로드 중..."):
                        response = requests.get(excel_url, timeout=30)
                        response.raise_for_status()
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                            tmp_file.write(response.content)
                            tmp_path = tmp_file.name
                    
                    with st.spinner("종목 처리 중..."):
                        processor = ExcelProcessor()
                        result = processor.process_excel_file(tmp_path)
                        
                        os.unlink(tmp_path)
                    
                    if result['success']:
                        st.success(f"✅ {result['added_count']}개 종목이 성공적으로 추가되었습니다!")
                        if result['added_tokens']:
                            with st.expander("추가된 종목 목록", expanded=True):
                                for token in result['added_tokens']:
                                    st.write(f"✓ {token['exchange']} - {token['symbol']}")
                        
                        if result['skipped_count'] > 0:
                            st.warning(f"⚠️ {result['skipped_count']}개 종목이 이미 존재하여 건너뛰었습니다.")
                        
                        st.rerun()
                    else:
                        st.error("❌ 파일 처리 중 오류가 발생했습니다.")
                        for error in result['errors']:
                            st.error(f"- {error}")
                            
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ URL에서 파일 다운로드 실패: {str(e)}")
                except Exception as e:
                    st.error(f"❌ 처리 중 오류: {str(e)}")
            else:
                st.warning("⚠️ URL을 입력해주세요.")
    
    with tab3:
        st.markdown("##### 자동화 스케줄 설정")
        
        # 현재 설정 로드
        if os.path.exists(ai_config_file):
            with open(ai_config_file, 'r', encoding='utf-8') as f:
                ai_config = json.load(f)
        else:
            ai_config = {
                "enabled": False,
                "import_time": "09:00",
                "excel_url": "",
                "backup_enabled": True
            }
        
        col1, col2 = st.columns(2)
        
        with col1:
            auto_enabled = st.checkbox(
                "자동 가져오기 활성화",
                value=ai_config.get("enabled", False),
                help="매일 지정된 시간에 자동으로 AI 경고 종목을 가져옵니다"
            )
            
            import_time = st.time_input(
                "실행 시간",
                value=pd.to_datetime(ai_config.get("import_time", "09:00")).time(),
                help="매일 자동으로 실행할 시간"
            )
        
        with col2:
            backup_enabled = st.checkbox(
                "백업 활성화",
                value=ai_config.get("backup_enabled", True),
                help="가져온 엑셀 파일을 백업합니다"
            )
            
            if ai_config.get("last_import"):
                st.info(f"마지막 실행: {ai_config['last_import'][:19]}")
            else:
                st.info("마지막 실행: 없음")
        
        if st.button("💾 자동화 설정 저장", key="save_automation"):
            ai_config["enabled"] = auto_enabled
            ai_config["import_time"] = import_time.strftime("%H:%M")
            ai_config["backup_enabled"] = backup_enabled
            
            with open(ai_config_file, 'w', encoding='utf-8') as f:
                json.dump(ai_config, f, ensure_ascii=False, indent=2)
            
            st.success("✅ 자동화 설정이 저장되었습니다!")
            st.info("💡 스케줄러를 시작하려면: `python daily_ai_import.py` 실행")
        
        # AI Import 요약
        st.markdown("---")
        st.markdown("##### 📊 AI Import 요약")
        
        try:
            from excel_processor import ExcelProcessor
            processor = ExcelProcessor()
            summary = processor.get_import_summary()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("AI 가져온 종목", f"{summary['total_ai_imported']}개")
            with col2:
                if ai_config.get("import_count"):
                    st.metric("총 가져온 횟수", f"{ai_config['import_count']}개")
            
            if summary['tokens']:
                with st.expander("AI 가져온 종목 목록", expanded=False):
                    for token_id, config in summary['tokens'].items():
                        import_date = config.get('import_date', 'N/A')[:10] if config.get('import_date') else 'N/A'
                        st.write(f"• {config['exchange']} - {config['symbol']} ({import_date})")
                        
        except Exception as e:
            st.error(f"Failed to load summary: {str(e)}")

elif admin_section == "📊 Token Management":
    st.title("📊 Token Management")
    
    # Load monitoring configs
    config_file = "monitoring_configs.json"
    monitoring_configs = {}
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            monitoring_configs = json.load(f)
    
    if not monitoring_configs:
        st.info("No tokens are currently being monitored. Please add tokens from below.")

# Lightweight CSS for metric cards with tooltips and pro/disabled styling
st.markdown(
    """
    <style>
    .metric-card{border:1px solid #e0e0e0;border-radius:8px;padding:10px 12px;margin-bottom:8px}
    .metric-label{font-size:12px;color:#666;display:flex;align-items:center;gap:6px}
    .metric-value{font-size:20px;font-weight:700;color:#111;margin-top:4px}
    .micro-burst{border:2px solid #1f77b4;background:#f8f9ff;padding:12px 14px}
    .micro-burst .metric-value{font-size:26px;font-weight:800;color:#1f77b4;margin-top:8px;text-align:center}
    .micro-burst .metric-label{font-size:13px;color:#1f77b4;font-weight:600}
    .qmark{display:inline-block;width:16px;height:16px;border-radius:50%;background:#eef; color:#336; text-align:center; line-height:16px; font-size:11px; cursor:help}
    .pro-badge{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:6px;background:#eee;color:#666;font-size:10px;border:1px solid #ddd}
    .disabled .metric-label{color:#999}
    .disabled .metric-value{color:#aaa}
    </style>
    """,
    unsafe_allow_html=True,
)

def render_metric_card(container, label: str, value: str, tooltip: str, pro: bool=False, disabled: bool=False, details: str="", micro_burst: bool=False):
    cls = "metric-card disabled" if disabled else "metric-card"
    if micro_burst:
        cls += " micro-burst"
    pro_html = '<span class="pro-badge">PRO</span>' if pro else ""
    # Avoid residual ghost text under cards when no details provided
    details_html = f'<div class="metric-details" style="font-size:11px;color:#888;margin-top:3px;">{details}</div>' if (details and details.strip()) else ""
    html = f"""
    <div class='{cls}'>
      <div class='metric-label'>
        <span>{label}</span>
        <span class='qmark' title="{tooltip}">?</span>
        {pro_html}
      </div>
      <div class='metric-value'>{value}</div>
      {details_html}
    </div>
    """
    container.markdown(html, unsafe_allow_html=True)
    # Insert a small, zero-height divider to prevent duplicate rendering artifacts
    container.markdown("<div style='height:0px;margin:0;padding:0;'></div>", unsafe_allow_html=True)

# ---------------------------
# Token Management Section (continued)
# ---------------------------
if admin_section == "📊 Token Management":
    # Continue with token management interface
    # Original dashboard code goes here
    st.header("⚙️ Monitoring Settings")

    # Monitoring refresh interval (seconds)
    monitor_interval_label = st.selectbox(
        "Monitoring refresh interval",
        options=["15 sec", "30 sec", "60 sec"],
        index=1,
    )
    monitor_interval_s = {"15 sec": 15, "30 sec": 30, "60 sec": 60}[monitor_interval_label]
    st.session_state["monitor_interval_s"] = monitor_interval_s

    # Accumulation interval (seconds)
    accum_interval_label = st.selectbox(
        "Accumulation interval",
        options=["60 sec", "120 sec", "300 sec"],
        index=0,
    )
    accum_interval_s = {"60 sec": 60, "120 sec": 120, "300 sec": 300}[accum_interval_label]
    st.session_state["accum_interval_s"] = accum_interval_s

    st.divider()
    st.subheader("🧪 Micro Burst (Pro)")
    enable_micro_burst = st.checkbox("Enable Micro Burst capture", value=False)
    period_min = st.slider("Burst period (minutes)", min_value=1, max_value=30, value=5)
    burst_samples = st.slider("Samples per burst", min_value=5, max_value=20, value=10)
    burst_interval = st.number_input("Per-sample interval (sec)", min_value=0.1, max_value=1.0, value=0.2, step=0.1)

    st.session_state["enable_micro_burst"] = enable_micro_burst
    st.session_state["burst_period_min"] = period_min
    st.session_state["burst_samples"] = int(burst_samples)
    st.session_state["burst_interval_s"] = float(burst_interval)


# ---------------------------
# Micro burst worker helpers
# ---------------------------
def micro_burst_capture(exchange, symbol, depth=150, samples=10, interval=0.2):
    """Enhanced micro burst capture with validation"""
    frames = []
    successful_captures = 0
    
    for i in range(samples):
        t0 = time.time()
        try:
            ob = exchange.fetch_order_book(symbol, limit=depth)
            
            # Validate orderbook data
            if ob and 'bids' in ob and 'asks' in ob:
                # Ensure data is in correct format
                valid_bids = []
                valid_asks = []
                
                for bid in ob.get('bids', []):
                    if isinstance(bid, (list, tuple)) and len(bid) >= 2:
                        try:
                            price = float(bid[0])
                            amount = float(bid[1])
                            valid_bids.append([price, amount])
                        except (ValueError, TypeError):
                            continue
                
                for ask in ob.get('asks', []):
                    if isinstance(ask, (list, tuple)) and len(ask) >= 2:
                        try:
                            price = float(ask[0])
                            amount = float(ask[1])
                            valid_asks.append([price, amount])
                        except (ValueError, TypeError):
                            continue
                
                frame = {
                    "t": datetime.utcnow().isoformat() + "Z",
                    "bids": valid_bids,
                    "asks": valid_asks,
                    "depth": len(valid_bids) + len(valid_asks)
                }
                frames.append(frame)
                successful_captures += 1
            else:
                # Log failed capture
                frames.append({
                    "t": datetime.utcnow().isoformat() + "Z",
                    "error": "Invalid orderbook data",
                    "bids": [],
                    "asks": []
                })
                
        except Exception as e:
            frames.append({
                "t": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "bids": [],
                "asks": []
            })
        
        # Maintain interval timing
        sleep_left = interval - (time.time() - t0)
        if sleep_left > 0:
            time.sleep(sleep_left)
    
    print(f"[DEBUG] Captured {successful_captures}/{samples} frames successfully")
    return frames


def save_micro_burst(exchange_id, symbol, frames):
    date = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.join("accumulation_data", "micro_bursts", date)
    os.makedirs(base, exist_ok=True)
    ts = datetime.utcnow().strftime("%H%M%S")
    path = os.path.join(base, f"{exchange_id}_{symbol.replace('/', '-')}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "burst": True,
            "exchange": exchange_id,
            "symbol": symbol,
            "frames": frames,
        }, f)
    return path


def micro_burst_worker(get_ctx, stop_event, period_min, samples, interval):
    period_sec = max(60, int(period_min * 60))
    while not stop_event.is_set():
        # random offset within the period
        jitter = random.randint(0, period_sec)
        waited = 0
        while waited < jitter and not stop_event.is_set():
            time.sleep(1)
            waited += 1
        if stop_event.is_set():
            break

        ctx = get_ctx()
        if not ctx:
            # nothing to capture this round
            continue
        exchange, exchange_id, symbol = ctx
        try:
            frames = micro_burst_capture(exchange, symbol, depth=150, samples=samples, interval=interval)
            save_micro_burst(exchange_id, symbol, frames)
        except Exception:
            pass


def ensure_micro_burst_thread():
    if not st.session_state.get("enable_micro_burst"):
        # stop if running
        th = st.session_state.get("micro_burst_thread")
        stop_ev = st.session_state.get("micro_burst_stop")
        if th and stop_ev:
            stop_ev.set()
            st.session_state["micro_burst_thread"] = None
            st.session_state["micro_burst_stop"] = None

    # start if not running
    if not st.session_state.get("micro_burst_thread"):
        def get_ctx():
            data = st.session_state.get("exchange_data")
            if not data:
                return None
            return data["exchange"], data["exchange_id"], data["symbol"]

        stop_ev = threading.Event()
        th = threading.Thread(
            target=micro_burst_worker,
            args=(get_ctx, stop_ev, st.session_state["burst_period_min"], st.session_state["burst_samples"], st.session_state["burst_interval_s"]),
            daemon=True,
        )
        th.start()
        st.session_state["micro_burst_thread"] = th
        st.session_state["micro_burst_stop"] = stop_ev


# Initialize session_state for micro burst if not exists
if "burst_period_min" not in st.session_state:
    st.session_state["burst_period_min"] = 5
if "burst_samples" not in st.session_state:
    st.session_state["burst_samples"] = 60
if "burst_interval_s" not in st.session_state:
    st.session_state["burst_interval_s"] = 5

# evaluate micro burst thread state each run
ensure_micro_burst_thread()


# ---------------------------
# Micro burst metrics compute
# ---------------------------
def _latest_micro_burst_path(exchange_id: str, symbol: str):
    date = datetime.utcnow().strftime("%Y-%m-%d")
    base = os.path.join("accumulation_data", "micro_bursts", date)
    if not os.path.isdir(base):
        return None
    prefix = f"{exchange_id}_{symbol.replace('/', '-')}_"
    candidates = [os.path.join(base, f) for f in os.listdir(base) if f.startswith(prefix) and f.endswith('.json')]
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _compute_micro_burst_metrics(frames, mid_price: float | None = None):
    """Compute micro burst metrics with better error handling"""
    if not frames:
        return None
    
    try:
        # 디버깅을 위한 로깅
        print(f"[DEBUG] Processing {len(frames)} frames")
        
        # Helper: collect top levels with validation
        def top_prices(side, n=3):
            if not side or not isinstance(side, list):
                return []
            valid_levels = []
            for lvl in side[:n]:
                if isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
                    try:
                        price = float(lvl[0])
                        valid_levels.append(price)
                    except (ValueError, TypeError):
                        continue
            return valid_levels

        def notional_within(frame, pct=0.02):
            """Calculate notional within percentage range with validation"""
            bids = frame.get('bids', [])
            asks = frame.get('asks', [])
            
            # Validate data structure
            if not isinstance(bids, list) or not isinstance(asks, list):
                return 0.0, 0.0, 0.0
            
            # Calculate frame-specific mid price
            frame_mid = mid_price or 0.0
            if bids and asks:
                try:
                    if isinstance(bids[0], (list, tuple)) and isinstance(asks[0], (list, tuple)):
                        bid_price = float(bids[0][0]) if len(bids[0]) >= 2 else 0
                        ask_price = float(asks[0][0]) if len(asks[0]) >= 2 else 0
                        if bid_price > 0 and ask_price > 0:
                            frame_mid = (bid_price + ask_price) / 2.0
                except (ValueError, TypeError, IndexError):
                    pass
            
            if frame_mid <= 0:
                return 0.0, 0.0, 0.0
            
            low = frame_mid * (1 - pct)
            high = frame_mid * (1 + pct)
            
            # Calculate notional with validation
            nb = 0.0
            na = 0.0
            sizes = []
            
            for lvl in bids:
                if isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
                    try:
                        p = float(lvl[0])
                        a = float(lvl[1])
                        if low <= p <= high:
                            notional = p * a
                            nb += notional
                            sizes.append(notional)
                    except (ValueError, TypeError):
                        continue
            
            for lvl in asks:
                if isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
                    try:
                        p = float(lvl[0])
                        a = float(lvl[1])
                        if low <= p <= high:
                            notional = p * a
                            na += notional
                            sizes.append(notional)
                    except (ValueError, TypeError):
                        continue
            
            # Calculate HHI
            tot = sum(sizes)
            hhi = sum((s / tot) ** 2 for s in sizes) if tot > 0 else 0.0
            
            return nb, na, hhi

        # Initialize metrics collections
        persist_ratios = []
        hhis = []
        imb_series = []
        layering_stds = []
        touch_flips = 0
        prev_best = None
        
        # Process each frame
        for i, fr in enumerate(frames):
            if not isinstance(fr, dict):
                continue
                
            bids = fr.get('bids', [])
            asks = fr.get('asks', [])
            
            # Skip invalid frames
            if not isinstance(bids, list) or not isinstance(asks, list):
                continue
            
            # Track best bid/ask changes
            if bids and asks:
                try:
                    if isinstance(bids[0], (list, tuple)) and isinstance(asks[0], (list, tuple)):
                        best_bid = float(bids[0][0]) if len(bids[0]) >= 2 else 0
                        best_ask = float(asks[0][0]) if len(asks[0]) >= 2 else 0
                        if best_bid > 0 and best_ask > 0:
                            best = (best_bid, best_ask)
                            if prev_best and best != prev_best:
                                touch_flips += 1
                            prev_best = best
                except (ValueError, TypeError, IndexError):
                    pass

            # Calculate HHI and imbalance
            nb, na, hhi = notional_within(fr, 0.02)
            if hhi > 0:  # Only add valid HHI values
                hhis.append(hhi)
            if nb > 0 or na > 0:  # Only add if there's some liquidity
                imb_series.append(nb - na)

            # Layering regularity analysis - within ±2% range only
            import statistics as stats
            
            # Calculate midpoint for ±2% range
            if best_bid > 0 and best_ask > 0:
                midpoint = (best_bid + best_ask) / 2
                price_range_2pct = midpoint * 0.02  # 2% of midpoint
                
                # Filter orders within ±2% range
                for side_name, side in [("asks", asks), ("bids", bids)]:
                    prices_in_range = []
                    amounts_in_range = []
                    
                    for lvl in side:
                        if isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
                            try:
                                price = float(lvl[0])
                                amount = float(lvl[1])
                                
                                # Check if price is within ±2% of midpoint
                                if side_name == "asks":
                                    if price <= midpoint + price_range_2pct:
                                        prices_in_range.append(price)
                                        amounts_in_range.append(amount)
                                else:  # bids
                                    if price >= midpoint - price_range_2pct:
                                        prices_in_range.append(price)
                                        amounts_in_range.append(amount)
                            except (ValueError, TypeError):
                                continue
                    
                    # Calculate layering metrics for this side within ±2% range
                    if len(prices_in_range) >= 3:
                        # Calculate relative price gaps (as percentage of price)
                        relative_gaps = []
                        for j in range(1, len(prices_in_range)):
                            if prices_in_range[j-1] > 0:
                                gap_pct = abs(prices_in_range[j] - prices_in_range[j-1]) / prices_in_range[j-1] * 100
                                relative_gaps.append(gap_pct)
                        
                        # Calculate amount density variation (spoofing detection)
                        if len(amounts_in_range) >= 3:
                            # Check for unusual amount patterns (large jumps in order sizes)
                            amount_ratios = []
                            for j in range(1, len(amounts_in_range)):
                                if amounts_in_range[j-1] > 0:
                                    ratio = amounts_in_range[j] / amounts_in_range[j-1]
                                    amount_ratios.append(ratio)
                            
                            if len(amount_ratios) >= 2:
                                try:
                                    # Use coefficient of variation for better sensitivity
                                    mean_ratio = stats.mean(amount_ratios)
                                    if mean_ratio > 0:
                                        cv = stats.pstdev(amount_ratios) / mean_ratio
                                        layering_stds.append(cv)
                                except:
                                    pass
                        
                        # Also include relative price gap variation
                        if len(relative_gaps) >= 2:
                            try:
                                gap_std = stats.pstdev(relative_gaps)
                                if gap_std > 0:
                                    layering_stds.append(gap_std)
                            except:
                                pass

            # Quote persistence vs previous frame
            if i > 0:
                prev = frames[i - 1]
                if isinstance(prev, dict):
                    a_now = set(round(p, 12) for p in top_prices(asks, 3))
                    b_now = set(round(p, 12) for p in top_prices(bids, 3))
                    a_prev = set(round(p, 12) for p in top_prices(prev.get('asks', []), 3))
                    b_prev = set(round(p, 12) for p in top_prices(prev.get('bids', []), 3))
                    
                    # Jaccard similarity
                    def jac(s1, s2):
                        if not s1 and not s2:
                            return 0.0
                        u = len(s1 | s2)
                        return (len(s1 & s2) / u) if u > 0 else 0.0
                    
                    persist_ratio = (jac(a_now, a_prev) + jac(b_now, b_prev)) / 2.0
                    persist_ratios.append(persist_ratio)

        # Calculate final metrics with validation
        import statistics as stats
        
        # Improved imbalance volatility calculation - use time intervals
        imbalance_volatility = 0.0
        if len(imb_series) >= 4:  # Need at least 4 data points for meaningful analysis
            # Calculate imbalance changes over different time intervals
            interval_changes = []
            
            # Short-term changes (1-2 frame gaps)
            for gap in [1, 2]:
                for i in range(gap, len(imb_series)):
                    if i - gap >= 0:
                        change = abs(imb_series[i] - imb_series[i - gap])
                        interval_changes.append(change)
            
            # Medium-term changes (3-5 frame gaps) if we have enough data
            if len(imb_series) >= 6:
                for gap in [3, 4, 5]:
                    for i in range(gap, len(imb_series)):
                        if i - gap >= 0:
                            change = abs(imb_series[i] - imb_series[i - gap])
                            interval_changes.append(change)
            
            # Long-term changes (6+ frame gaps) if we have enough data
            if len(imb_series) >= 10:
                for gap in [6, 8, 10]:
                    for i in range(gap, len(imb_series)):
                        if i - gap >= 0:
                            change = abs(imb_series[i] - imb_series[i - gap])
                            interval_changes.append(change)
            
            # Calculate volatility from interval changes
            if len(interval_changes) >= 2:
                # Use coefficient of variation for better sensitivity
                mean_change = stats.mean(interval_changes)
                if mean_change > 0:
                    imbalance_volatility = stats.pstdev(interval_changes) / mean_change
                else:
                    imbalance_volatility = stats.pstdev(interval_changes)
        
        # Improved layering gap std calculation
        layering_gap_std = 0.0
        if layering_stds:
            layering_gap_std = stats.mean(layering_stds)
        
        # Normalize touch flip count by number of frames
        normalized_touch_flips = touch_flips / len(frames) if frames else 0
        
        metrics = {
            "quote_persistence_top3": stats.mean(persist_ratios) if persist_ratios else 0.0,
            "concentration_hhi_2pct": stats.mean(hhis) if hhis else 0.0,
            "imbalance_volatility": imbalance_volatility,
            "layering_gap_std": layering_gap_std,
            "touch_flip_count": normalized_touch_flips,
            "frames_processed": len(frames),
            "valid_frames": len([f for f in frames if isinstance(f, dict) and f.get('bids') and f.get('asks')])  # Count frames with any data
        }
        
        print(f"[DEBUG] Metrics computed: {metrics}")
        return metrics
        
    except Exception as e:
        print(f"[ERROR] Failed to compute micro burst metrics: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_micro_burst_now():
    data = st.session_state.get("exchange_data")
    if not data:
        return None, None
    exchange = data["exchange"]
    exchange_id = data["exchange_id"]
    symbol = data["symbol"]
    frames = micro_burst_capture(
        exchange,
        symbol,
        depth=150,
        samples=st.session_state.get("burst_samples", 10),
        interval=st.session_state.get("burst_interval_s", 0.2),
    )
    path = save_micro_burst(exchange_id, symbol, frames)
    # cache latest in session for immediate metrics
    st.session_state["last_burst_frames"] = frames
    st.session_state["last_burst_path"] = path
    return frames, path

# ========================================
# TOKEN VERIFICATION & QUICK ACTIONS
# ========================================
st.markdown("---")
st.markdown("---")

st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 16px; border-radius: 8px; margin: 20px 0;'>
    <h3 style='color: white; margin: 0; text-align: center;'>
        🔍 Token Verification & Quick Actions
    </h3>
    <p style='color: rgba(255,255,255,0.9); margin: 8px 0 0 0; text-align: center; font-size: 14px;'>
        Legacy feature for manual token search and immediate analysis
    </p>
</div>
""", unsafe_allow_html=True)

st.info("💡 **Note**: This section provides quick access to individual token verification and analysis. For comprehensive monitoring, please use the Token Management menu.")

# Exchange selection
col1, col2 = st.columns(2)

with col1:
    exchange_options = {
        "Binance": "binance",
        "MEXC": "mexc", 
        "MEXC ASSESSMENT": "mexc_assessment",
        "Gate.io": "gateio",
        "Bybit": "bybit",
        "Bitget": "bitget",
        "BingX": "bingx",
        "KuCoin": "kucoin",
        "Huobi": "huobi",
        "Upbit": "upbit",
        "Bithumb": "bithumb",
        "Coinone": "coinone"
    }
    
    selected_exchange = st.selectbox(
        "Select Exchange:",
        options=list(exchange_options.keys()),
        index=0
    )

with col2:
    symbol = st.text_input(
        "Symbol (e.g., BTC/USDT):",
        value="BTC/USDT"
    )

# API Key input for MEXC ASSESSMENT
if selected_exchange == "MEXC ASSESSMENT":
    st.info("🔑 MEXC ASSESSMENT requires API credentials")
    api_key = st.text_input("API Key", type="password", help="Enter your MEXC API Key")
    api_secret = st.text_input("API Secret", type="password", help="Enter your MEXC API Secret")
    
    if not api_key or not api_secret:
        st.warning("⚠️ Please enter both API Key and Secret to continue")
        st.stop()
else:
    api_key = None
    api_secret = None

# Initialize session state
if 'search_done' not in st.session_state:
    st.session_state.search_done = False
if 'exchange_data' not in st.session_state:
    st.session_state.exchange_data = None
## removed: show_orderbook state
if 'show_monitoring' not in st.session_state:
    st.session_state.show_monitoring = False
if 'start_accumulation' not in st.session_state:
    st.session_state.start_accumulation = False
if 'show_manual_inputs_quick' not in st.session_state:
    st.session_state.show_manual_inputs_quick = False

# Search button
if st.button("🔍 Search", type="primary", key="search_btn"):
    try:
        exchange_id = exchange_options[selected_exchange]
        
        # Convert symbol to uppercase
        symbol = symbol.upper()
        
        # Initialize exchange
        if exchange_id in ("mexc_evaluation", "mexc_assessment"):
            # MEXC ASSESSMENT uses MEXC V3 API with special authentication
            exchange = ccxt.mexc({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'},
                'urls': {
                    'api': {
                        'public': 'https://api.mexc.com/api/v3',
                        'private': 'https://api.mexc.com/api/v3'
                    }
                },
                'headers': {
                    'x-mexc-apikey': api_key
                }
            })
        else:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        
        # Load markets
        with st.spinner("Loading markets..."):
            markets = exchange.load_markets()
        
        if symbol in markets:
            st.success(f"✅ {symbol} found on {selected_exchange}")
            
            # Get market info
            market_info = markets[symbol]
            
            # Get ticker data
            with st.spinner("Fetching ticker data..."):
                ticker = exchange.fetch_ticker(symbol)
            
            # Store data in session state
            st.session_state.exchange_data = {
                'exchange': exchange,
                'markets': markets,
                'market_info': market_info,
                'ticker': ticker,
                'symbol': symbol,
                'exchange_id': exchange_id,
                'api_key': api_key,
                'api_secret': api_secret,
                'last_price': ticker['last']  # Store current price (will be converted to USDT later)
            }
            st.session_state.search_done = True
            st.session_state.show_orderbook = False
            st.session_state.show_monitoring = False
            # st.session_state.start_accumulation = False  // keep accumulation running across searches
            
            # Preserve existing accumulation context if present
            if isinstance(st.session_state.exchange_data, dict):
                st.session_state.exchange_data['last_searched_at'] = datetime.now().isoformat() + "Z"
            
        else:
            st.error(f"❌ {symbol} not found on {selected_exchange}")
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# Display results if search is done
if st.session_state.search_done and st.session_state.exchange_data:
    data = st.session_state.exchange_data
    exchange = data['exchange']
    markets = data['markets']
    market_info = data['market_info']
    ticker = data['ticker']
    symbol = data['symbol']
    exchange_id = data['exchange_id']
    
    # Display market info (collapsible)
    with st.expander("📋 CEX Token Settings", expanded=True):
        line1, line2, line3 = st.columns(3)
    
    with line1:
        # Additional token information
        info = market_info.get('info', {})
        
        # Spot Symbol with Token Name
        full_name = info.get('fullName', 'N/A')
        if full_name != 'N/A' and full_name:
            st.metric("Spot Symbol", f"{symbol} ({full_name})")
        else:
            st.metric("Spot Symbol", symbol)
        
        # Only show fees if they exist and are not zero
        if market_info['maker'] is not None and market_info['taker'] is not None:
            if market_info['maker'] > 0 or market_info['taker'] > 0:
                maker_fee = f"{market_info['maker']*100:.2f}%"
                taker_fee = f"{market_info['taker']*100:.2f}%"
                st.metric("Spot Maker/Taker", f"{maker_fee} / {taker_fee}")
        
        # Contract Address with Chain
        contract_address = info.get('contractAddress', 'N/A')
        chain = info.get('chain', 'N/A')
        
        if contract_address != 'N/A' and contract_address:
            if chain != 'N/A' and chain:
                # Display with chain prefix
                st.metric("Contract Address", f"{chain.upper()}: {contract_address[:10]}...{contract_address[-6:]}")
            else:
                # Display without chain prefix
                st.metric("Contract Address", f"{contract_address[:10]}...{contract_address[-6:]}")
        
        # Live Feed removed
    
        with line2:
            # Combined Precision Information
            price_precision = market_info['precision']['price']
            amount_precision = market_info['precision']['amount']
            cost_precision = market_info['precision']['cost']
            if cost_precision is None or cost_precision == 'N/A':
                cost_precision = 0.01
            
            st.metric("PRICE / AMOUNT / COST PRECISION", f"{price_precision} / {amount_precision} / {cost_precision}")
            
            # Trading permissions - detailed display
            permissions = info.get('permissions', [])
            if permissions:
                # Convert permissions to readable format
                permission_map = {
                    'SPOT': 'SPOT',
                    'MARGIN': 'MARGIN', 
                    'FUTURES': 'FUTURES',
                    'OPTIONS': 'OPTIONS',
                    'PERPETUAL': 'PERPETUAL'
                }
                
                readable_permissions = []
                for perm in permissions:
                    readable_permissions.append(permission_map.get(perm, perm))
                
                # Determine trading type
                if len(readable_permissions) == 1:
                    if 'SPOT' in readable_permissions:
                        trading_type = "SPOT ONLY"
                    elif 'MARGIN' in readable_permissions:
                        trading_type = "MARGIN ONLY"
                    elif 'FUTURES' in readable_permissions:
                        trading_type = "FUTURES ONLY"
                    else:
                        trading_type = readable_permissions[0]
                elif 'SPOT' in readable_permissions and 'MARGIN' in readable_permissions:
                    if 'FUTURES' in readable_permissions:
                        trading_type = "SPOT + MARGIN + FUTURES"
                    else:
                        trading_type = "SPOT + MARGIN"
                elif 'SPOT' in readable_permissions and 'FUTURES' in readable_permissions:
                    trading_type = "SPOT + FUTURES"
                elif 'MARGIN' in readable_permissions and 'FUTURES' in readable_permissions:
                    trading_type = "MARGIN + FUTURES"
                else:
                    trading_type = " + ".join(readable_permissions)
                
                st.metric("Trading Permissions", trading_type)
            
            # Order types moved to line3 to avoid duplication
        
        with line3:
            # Commission information - only show if values exist and trading permissions allow margin
            permissions = info.get('permissions', [])
            if 'MARGIN' in permissions or 'FUTURES' in permissions:
                maker_commission = info.get('makerCommission', None)
                taker_commission = info.get('takerCommission', None)
                
                if maker_commission is not None and taker_commission is not None:
                    # Convert to float if string
                    try:
                        maker_val = float(maker_commission) if isinstance(maker_commission, str) else maker_commission
                        taker_val = float(taker_commission) if isinstance(taker_commission, str) else taker_commission
                        
                        if maker_val > 0 or taker_val > 0:
                            st.metric("Margin Maker/Taker", f"{maker_val}% / {taker_val}%")
                    except (ValueError, TypeError):
                        pass
            
            # API minimum order values - always in USDT
            min_cost_usdt = None
            
            # Try to get min_cost first (preferred)
            if 'limits' in market_info and 'cost' in market_info['limits']:
                min_cost = market_info['limits']['cost'].get('min')
                if min_cost is not None and min_cost > 0:
                    min_cost_usdt = min_cost
            
            # If no min_cost, try to calculate from min_amount and current price
            if min_cost_usdt is None:
                min_amount = market_info['limits']['amount'].get('min')
                if min_amount is not None and min_amount > 0:
                    # Get current price in USDT
                    current_price_usdt = 0
                    if 'last_price' in st.session_state.exchange_data:
                        current_price_usdt = st.session_state.exchange_data['last_price']
                    elif ticker.get('last'):
                        # Convert to USDT if needed
                        quote_currency = market_info.get('quote', '')
                        if quote_currency.upper() == 'USDT':
                            current_price_usdt = ticker['last']
                        else:
                            # Convert to USDT using usdt_rate
                            current_price_usdt = ticker['last'] * usdt_rate
                    
                    if current_price_usdt > 0:
                        min_cost_usdt = min_amount * current_price_usdt
            
            # Special handling for MEXC
            if exchange_id == 'mexc' and min_cost_usdt is None:
                min_cost_usdt = 3.0  # MEXC default $3 USDT
            
            # Display API Min Order
            if min_cost_usdt is not None:
                st.metric("API Min Order", f"${min_cost_usdt:,.2f} USDT")
            else:
                st.metric("API Min Order", "N/A")
            
            # API Order Types List
            order_types = info.get('orderTypes', [])
            if order_types:
                st.metric("API Order Types", f"{len(order_types)} types")
                # Show order types in expander
                with st.expander("📋 Order Types List"):
                    for i, order_type in enumerate(order_types, 1):
                        st.write(f"{i}. {order_type}")
    
    with st.expander("💰 Current Price Information (All in USDT)", expanded=True):
        # Convert all volumes to USDT
        quote_currency = market_info['quote']
        current_price = ticker['last']
        # If quote is not USDT, we need to convert
        if quote_currency != 'USDT':
            try:
                # Get USDT conversion rate
                usdt_pair = f"{quote_currency}/USDT"
                if usdt_pair in markets:
                    usdt_ticker = exchange.fetch_ticker(usdt_pair)
                    usdt_rate = usdt_ticker['last']
                else:
                    # Try reverse pair
                    usdt_pair = f"USDT/{quote_currency}"
                    if usdt_pair in markets:
                        usdt_ticker = exchange.fetch_ticker(usdt_pair)
                        usdt_rate = 1 / usdt_ticker['last']
                    else:
                        usdt_rate = 1  # Fallback
            except Exception as e:
                usdt_rate = 1  # Fallback
        else:
            usdt_rate = 1

        # Convert prices to USDT
        price_usdt = current_price * usdt_rate if current_price else 0
        bid_usdt = ticker['bid'] * usdt_rate if ticker['bid'] else 0
        ask_usdt = ticker['ask'] * usdt_rate if ticker['ask'] else 0
        high_usdt = ticker['high'] * usdt_rate if ticker['high'] else 0
        low_usdt = ticker['low'] * usdt_rate if ticker['low'] else 0

        # Convert volumes to USDT
        base_volume_usdt = ticker['baseVolume'] * price_usdt if ticker['baseVolume'] else 0
        quote_volume_usdt = ticker['quoteVolume'] * usdt_rate if ticker['quoteVolume'] else 0

        col1, col2, col3, col4 = st.columns(4)

        # Get price precision for accurate display
        price_precision = market_info['precision']['price']
        
        
        decimal_places = get_decimal_places(price_precision)

        with col1:
            if price_usdt > 0:
                st.metric("Last Price", f"${price_usdt:.{decimal_places}f} USDT")
            else:
                st.metric("Last Price", "N/A")

        with col2:
            if bid_usdt > 0:
                st.metric("Best Bid", f"${bid_usdt:.{decimal_places}f} USDT")
            else:
                st.metric("Best Bid", "N/A")

        with col3:
            if ask_usdt > 0:
                st.metric("Best Ask", f"${ask_usdt:.{decimal_places}f} USDT")
            else:
                st.metric("Best Ask", "N/A")

        with col4:
            if ticker['percentage'] is not None:
                st.metric(
                    "24h Change",
                    f"{ticker['percentage']:+.2f}%",
                    delta=f"{ticker['change'] * usdt_rate:+.2f} USDT" if ticker['change'] else "N/A"
                )
            else:
                st.metric("24h Change", "N/A")

        # 24h statistics
        st.subheader("📈 24h Statistics (All in USDT)")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if base_volume_usdt > 0:
                # Round volume to 0.01 (10^-2) precision
                volume_rounded = round(base_volume_usdt, 2)
                st.metric("24h Volume", f"${volume_rounded:,.2f} USDT")
            else:
                st.metric("24h Volume", "N/A")

        with col2:
            if high_usdt > 0:
                st.metric("24h High", f"${high_usdt:.{decimal_places}f} USDT")
            else:
                st.metric("24h High", "N/A")

        with col3:
            if low_usdt > 0:
                st.metric("24h Low", f"${low_usdt:.{decimal_places}f} USDT")
            else:
                st.metric("24h Low", "N/A")

        with col4:
            if quote_volume_usdt > 0:
                # Round quote volume to 0.01 (10^-2) precision
                quote_volume_rounded = round(quote_volume_usdt, 2)
                st.metric("Quote Volume", f"${quote_volume_rounded:,.2f} USDT")
            else:
                st.metric("Quote Volume", "N/A")
    
    # Next step buttons
    st.subheader("🚀 Next Steps")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🛠️ Manual Inputs (Quick)", type="primary", key="manual_inputs_quick_btn"):
            st.session_state.show_manual_inputs_quick = not bool(st.session_state.get('show_manual_inputs_quick'))
    
    with col2:
        if st.button("📈 Start Monitoring", type="secondary", key="monitoring_btn"):
            st.session_state.show_monitoring = True
    
    with col3:
        if st.button("💾 Save and Accumulation", type="secondary", key="save_btn"):
            st.session_state.start_accumulation = True
            st.success("💾 Data accumulation started!")
            st.info("System will continue saving 1-minute snapshots even when stopped.")

    # Inline quick manual inputs panel (reusing core fields and save)
    if bool(st.session_state.get('show_manual_inputs_quick')):
        st.subheader("⚙️ Manual Inputs Management")
        # Load existing manual inputs
        manual_inputs = {}
        if os.path.exists("manual_inputs.json"):
            try:
                with open("manual_inputs.json", "r", encoding="utf-8") as f:
                    manual_inputs = json.load(f)
            except Exception:
                manual_inputs = {}
        token_key = f"{exchange_id}_{symbol.replace('/', '_').lower()}"
        token_inputs = manual_inputs.get(token_key, {})

        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            st.markdown("**Exchange User Holdings**")
            cex_price = st.number_input("CEX Price (USDT)", min_value=0.0, value=float(token_inputs.get('cex_price', 0) or 0), step=0.00000001, format="%.8f")
            cex_market_cap = st.number_input("User Holdings (USDT)", min_value=0.0, value=float(token_inputs.get('cex_market_cap', 0) or 0), step=1000.0)
            token_inputs['cex_price'] = cex_price
            token_inputs['cex_market_cap'] = cex_market_cap
            # Listing price
            st.markdown("**Listing Price**")
            listing_price = st.number_input("Listing Price (USDT)", min_value=0.0, value=float(token_inputs.get('listing_price', 0) or 0), step=0.00000001, format="%.8f")
            token_inputs['listing_price'] = listing_price
        with qc2:
            st.markdown("**Estimated Holders**")
            holders_price = st.number_input("Holders Price (USDT)", min_value=0.0, value=float(token_inputs.get('holders_price', 0) or 0), step=0.00000001, format="%.8f")
            holders_count = st.number_input("Holders Count", min_value=0, value=int(token_inputs.get('holders_count', 0) or 0), step=10)
            token_inputs['holders_price'] = holders_price
            token_inputs['holders_count'] = holders_count
            st.markdown("**Price Ratio Targets**")
            pr_target = st.number_input("Target (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('price_ratio_target', 10.0)), step=0.5)
            pr_thresh = st.number_input("Threshold (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('price_ratio_threshold', 1.0)), step=0.1)
            token_inputs['price_ratio_target'] = pr_target
            token_inputs['price_ratio_threshold'] = pr_thresh
        with qc3:
            st.markdown("**Depth/Spread/Volume**")
            depth_target = st.number_input("±2% Depth Target (USDT)", min_value=0.0, value=float(token_inputs.get('depth_target', 1000) or 0), step=100.0)
            depth_threshold = st.number_input("±2% Depth Threshold (USDT)", min_value=0.0, value=float(token_inputs.get('depth_threshold', 500) or 0), step=100.0)
            spread_target = st.number_input("Spread Target (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('spread_target', 1.0)), step=0.1)
            spread_threshold = st.number_input("Spread Threshold (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('spread_threshold', 2.0)), step=0.1)
            volume_target = st.number_input("Volume Target (USDT)", min_value=0.0, value=float(token_inputs.get('volume_target', 50000) or 0), step=5000.0)
            volume_threshold = st.number_input("Volume Threshold (USDT)", min_value=0.0, value=float(token_inputs.get('volume_threshold', 20000) or 0), step=5000.0)
            token_inputs['depth_target'] = depth_target
            token_inputs['depth_threshold'] = depth_threshold
            token_inputs['spread_target'] = spread_target
            token_inputs['spread_threshold'] = spread_threshold
            token_inputs['volume_target'] = volume_target
            token_inputs['volume_threshold'] = volume_threshold
        st.subheader("🎯 Target & Threshold Settings")
        # Second row: remaining targets
        qt1, qt2, _ = st.columns(3)
        with qt1:
            st.markdown("**User Holdings Targets**")
            uh_target = st.number_input("User Holdings Target (USDT)", min_value=0.0, value=float(token_inputs.get('user_holdings_target', 150000) or 0), step=10000.0)
            uh_threshold = st.number_input("User Holdings Threshold (USDT)", min_value=0.0, value=float(token_inputs.get('user_holdings_threshold', 70000) or 0), step=10000.0)
            token_inputs['user_holdings_target'] = uh_target
            token_inputs['user_holdings_threshold'] = uh_threshold
        with qt2:
            st.markdown("**Holders Targets**")
            h_target = st.number_input("Holders Target (Count)", min_value=0, value=int(token_inputs.get('holders_target', 200) or 0), step=10)
            h_threshold = st.number_input("Holders Threshold (Count)", min_value=0, value=int(token_inputs.get('holders_threshold', 100) or 0), step=10)
            token_inputs['holders_target'] = h_target
            token_inputs['holders_threshold'] = h_threshold
        apply_to_nw = st.checkbox("Apply to Night Watch", value=True)
        save_col1, save_col2 = st.columns([1,1])
        with save_col1:
            if st.button("💾 Save Manual Inputs", key="quick_save_manual"):
                manual_inputs[token_key] = token_inputs
                with open("manual_inputs.json", "w", encoding="utf-8") as f:
                    json.dump(manual_inputs, f, indent=2)
                st.success("✅ Manual inputs saved!")
        with save_col2:
            if st.button("🔄 Update & Close", key="quick_update_close"):
                manual_inputs[token_key] = token_inputs
                with open("manual_inputs.json", "w", encoding="utf-8") as f:
                    json.dump(manual_inputs, f, indent=2)
                st.session_state.show_manual_inputs_quick = False
                st.rerun()
        st.stop()
    
    # Show real-time monitoring if requested
    if st.session_state.show_monitoring:
        st.subheader("📈 Real-time Monitoring Dashboard")
        
        # Get fresh data
        with st.spinner("Fetching real-time data..."):
            try:
                fresh_ticker = exchange.fetch_ticker(symbol)
                fresh_orderbook = exchange.fetch_order_book(symbol, limit=50)
                
                # Calculate spread
                bid_price = fresh_ticker['bid'] * usdt_rate if fresh_ticker['bid'] else 0
                ask_price = fresh_ticker['ask'] * usdt_rate if fresh_ticker['ask'] else 0
                spread_amount = ask_price - bid_price
                spread_percentage = (spread_amount / bid_price * 100) if bid_price > 0 else 0
                
                # Calculate midpoint
                midpoint = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else 0
                
                # Calculate liquidity in different ranges
                def calculate_liquidity_in_range(orderbook_data, price_range_percent):
                    if midpoint == 0:
                        return 0, 0, 0
                    
                    range_amount = midpoint * price_range_percent / 100
                    min_price = midpoint - range_amount
                    max_price = midpoint + range_amount
                    
                    bid_liquidity = 0
                    ask_liquidity = 0
                    
                    for price, amount in orderbook_data['bids']:
                        price_usdt = price * usdt_rate
                        if min_price <= price_usdt <= midpoint:
                            bid_liquidity += amount * price_usdt
                    
                    for price, amount in orderbook_data['asks']:
                        price_usdt = price * usdt_rate
                        if midpoint <= price_usdt <= max_price:
                            ask_liquidity += amount * price_usdt
                    
                    total_liquidity = bid_liquidity + ask_liquidity
                    net_liquidity = bid_liquidity - ask_liquidity
                    
                    return bid_liquidity, ask_liquidity, total_liquidity, net_liquidity
                
                # Calculate liquidity for different ranges
                bid_2, ask_2, total_2, net_2 = calculate_liquidity_in_range(fresh_orderbook, 2)
                bid_5, ask_5, total_5, net_5 = calculate_liquidity_in_range(fresh_orderbook, 5)
                bid_10, ask_10, total_10, net_10 = calculate_liquidity_in_range(fresh_orderbook, 10)
                
                # Display real-time metrics (collapsible)
                with st.expander("📈 Current Price Info", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Current Price", f"${price_usdt:.{decimal_places}f} USDT")
                        st.metric("Midpoint", f"${midpoint:.{decimal_places}f} USDT")

                    with col2:
                        # Calculate spread in ticks
                        price_precision = market_info['precision']['price']
                        if price_precision <= 0.000001:  # 6 decimal places or more
                            # Calculate spread in original currency, then convert to ticks
                            original_bid = fresh_ticker['bid'] if fresh_ticker['bid'] else 0
                            original_ask = fresh_ticker['ask'] if fresh_ticker['ask'] else 0
                            original_spread = original_ask - original_bid
                            tick_size = price_precision
                            spread_ticks = round(original_spread / tick_size) if original_spread > 0 and tick_size > 0 else 0
                            st.metric("SPREAD", f"{spread_ticks} TICKS / {spread_percentage:.2f}%")
                        else:
                            st.metric("SPREAD", f"${spread_amount:.{decimal_places}f} / {spread_percentage:.2f}%")

                    with col3:
                        # Check if price precision exceeds 6 decimal places
                        price_precision = market_info['precision']['price']
                        if price_precision <= 0.000001:  # 6 decimal places or more
                            # Convert to tick values
                            tick_size = price_precision
                            bid_ticks = int(bid_price / tick_size) if bid_price > 0 else 0
                            ask_ticks = int(ask_price / tick_size) if ask_price > 0 else 0
                            st.metric("BID/ASK", f"{bid_ticks}/{ask_ticks}")
                        else:
                            # Use decimal format
                            st.metric("BID/ASK", f"${bid_price:.{decimal_places}f}/${ask_price:.{decimal_places}f} USDT")

                    with col4:
                        # Round volume to 0.01 (10^-2) precision
                        volume_rounded = round(base_volume_usdt, 2)
                        st.metric("24h Volume", f"${volume_rounded:,.2f} USDT")
                        st.metric("24h Change", f"{ticker['percentage']:+.2f}%")
                
                # Liquidity Analysis moved out as its own box
                st.subheader("💧 Liquidity Analysis")
                
                # Calculate weighted average prices for each range
                def calculate_weighted_price(orders, is_ask=False):
                    if not orders:
                        return 0
                    total_value = 0
                    total_amount = 0
                    for price, amount in orders:
                        value = price * amount
                        total_value += value
                        total_amount += amount
                    return total_value / total_amount if total_amount > 0 else 0
                
                # Get orders within each range
                current_price = fresh_ticker['last'] * usdt_rate
                current_orderbook = fresh_orderbook
                
                # ±2% range
                range_2_min = current_price * 0.98
                range_2_max = current_price * 1.02
                asks_2 = [(p, a) for p, a in current_orderbook['asks'] if range_2_min <= p <= range_2_max]
                bids_2 = [(p, a) for p, a in current_orderbook['bids'] if range_2_min <= p <= range_2_max]
                
                # ±5% range
                range_5_min = current_price * 0.95
                range_5_max = current_price * 1.05
                asks_5 = [(p, a) for p, a in current_orderbook['asks'] if range_5_min <= p <= range_5_max]
                bids_5 = [(p, a) for p, a in current_orderbook['bids'] if range_5_min <= p <= range_5_max]
                
                # ±10% range
                range_10_min = current_price * 0.90
                range_10_max = current_price * 1.10
                asks_10 = [(p, a) for p, a in current_orderbook['asks'] if range_10_min <= p <= range_10_max]
                bids_10 = [(p, a) for p, a in current_orderbook['bids'] if range_10_min <= p <= range_10_max]
                
                # Calculate weighted average prices
                ask_weighted_2 = calculate_weighted_price(asks_2)
                bid_weighted_2 = calculate_weighted_price(bids_2)
                ask_weighted_5 = calculate_weighted_price(asks_5)
                bid_weighted_5 = calculate_weighted_price(bids_5)
                ask_weighted_10 = calculate_weighted_price(asks_10)
                bid_weighted_10 = calculate_weighted_price(bids_10)
                
                # Liquidity Analysis (boxed)
                with st.expander("💧 Liquidity Analysis", expanded=True):
                    # Best Bid/Ask SPREAD (same display rule as above)
                    price_precision = market_info['precision']['price']
                    if price_precision <= 0.000001:  # high precision → show ticks
                        original_bid = fresh_ticker['bid'] if fresh_ticker['bid'] else 0
                        original_ask = fresh_ticker['ask'] if fresh_ticker['ask'] else 0
                        original_spread = (original_ask - original_bid) if (original_ask and original_bid) else 0
                        tick_size = price_precision
                        spread_ticks = round(original_spread / tick_size) if original_spread > 0 and tick_size > 0 else 0
                        st.metric("Best Bid/Ask SPREAD", f"{spread_ticks} TICKS / {spread_percentage:.2f}%")
                    else:
                        st.metric("Best Bid/Ask SPREAD", f"${spread_amount:.{decimal_places}f} / {spread_percentage:.2f}%")

                    # WEIGHTED DEPTH CENTER SPREAD (summary)
                    col_spread1, col_spread2, col_spread3 = st.columns(3)
                    with col_spread1:
                        if ask_weighted_2 > 0 and bid_weighted_2 > 0:
                            weighted_spread_2 = ask_weighted_2 - bid_weighted_2
                            weighted_spread_percentage_2 = (weighted_spread_2 / bid_weighted_2 * 100) if bid_weighted_2 > 0 else 0
                            if price_precision <= 0.000001:
                                ticks_2 = round(weighted_spread_2 / price_precision) if weighted_spread_2 > 0 and price_precision > 0 else 0
                                st.metric("2% WEIGHTED DEPTH CENTER SPREAD", f"{ticks_2} TICKS / {weighted_spread_percentage_2:.2f}%")
                            else:
                                st.metric("2% WEIGHTED DEPTH CENTER SPREAD", f"${weighted_spread_2:.{decimal_places}f} / {weighted_spread_percentage_2:.2f}%")
                    with col_spread2:
                        if ask_weighted_5 > 0 and bid_weighted_5 > 0:
                            weighted_spread_5 = ask_weighted_5 - bid_weighted_5
                            weighted_spread_percentage_5 = (weighted_spread_5 / bid_weighted_5 * 100) if bid_weighted_5 > 0 else 0
                            if price_precision <= 0.000001:
                                ticks_5 = round(weighted_spread_5 / price_precision) if weighted_spread_5 > 0 and price_precision > 0 else 0
                                st.metric("5% WEIGHTED DEPTH CENTER SPREAD", f"{ticks_5} TICKS / {weighted_spread_percentage_5:.2f}%")
                            else:
                                st.metric("5% WEIGHTED DEPTH CENTER SPREAD", f"${weighted_spread_5:.{decimal_places}f} / {weighted_spread_percentage_5:.2f}%")
                    with col_spread3:
                        if ask_weighted_10 > 0 and bid_weighted_10 > 0:
                            weighted_spread_10 = ask_weighted_10 - bid_weighted_10
                            weighted_spread_percentage_10 = (weighted_spread_10 / bid_weighted_10 * 100) if bid_weighted_10 > 0 else 0
                            if price_precision <= 0.000001:
                                ticks_10 = round(weighted_spread_10 / price_precision) if weighted_spread_10 > 0 and price_precision > 0 else 0
                                st.metric("10% WEIGHTED DEPTH CENTER SPREAD", f"{ticks_10} TICKS / {weighted_spread_percentage_10:.2f}%")
                            else:
                                st.metric("10% WEIGHTED DEPTH CENTER SPREAD", f"${weighted_spread_10:.{decimal_places}f} / {weighted_spread_percentage_10:.2f}%")

                    # Collapsible section for per-range liquidity tables
                    with st.expander("📦 Per-Range Liquidity Tables", expanded=False):
                        # 구간별 매수지수 (매수/매도)
                        col_bid_ask1, col_bid_ask2, col_bid_ask3 = st.columns(3)
                        with col_bid_ask1:
                            bid_ask_ratio_2 = bid_2 / ask_2 if ask_2 > 0 else 0
                            st.metric("2% Bid/Ask Ratio", f"{bid_ask_ratio_2:.3f}")
                        with col_bid_ask2:
                            bid_ask_ratio_5 = bid_5 / ask_5 if ask_5 > 0 else 0
                            st.metric("5% Bid/Ask Ratio", f"{bid_ask_ratio_5:.3f}")
                        with col_bid_ask3:
                            bid_ask_ratio_10 = bid_10 / ask_10 if ask_10 > 0 else 0
                            st.metric("10% Bid/Ask Ratio", f"{bid_ask_ratio_10:.3f}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write("**±2% Range**")
                            st.metric("ASK", f"${ask_2:,.2f} USDT")
                            if ask_weighted_2 > 0:
                                st.caption(f"WEIGHTED DEPTH CENTER: ${ask_weighted_2:.{decimal_places}f}")
                            st.metric("BID", f"${bid_2:,.2f} USDT")
                            if bid_weighted_2 > 0:
                                st.caption(f"WEIGHTED DEPTH CENTER: ${bid_weighted_2:.{decimal_places}f}")
                            st.metric("Total", f"${total_2:,.2f} USDT")
                            if net_2 >= 0:
                                st.metric("NET LIQ.", f"BID ${abs(net_2):,.2f} USDT")
                            else:
                                st.metric("NET LIQ.", f"ASK ${abs(net_2):,.2f} USDT")
                        with col2:
                            st.write("**±5% Range**")
                            st.metric("ASK", f"${ask_5:,.2f} USDT")
                            if ask_weighted_5 > 0:
                                st.caption(f"WEIGHTED DEPTH CENTER: ${ask_weighted_5:.{decimal_places}f}")
                            st.metric("BID", f"${bid_5:,.2f} USDT")
                            if bid_weighted_5 > 0:
                                st.caption(f"WEIGHTED DEPTH CENTER: ${bid_weighted_5:.{decimal_places}f}")
                            st.metric("Total", f"${total_5:,.2f} USDT")
                            if net_5 >= 0:
                                st.metric("NET LIQ.", f"BID ${abs(net_5):,.2f} USDT")
                            else:
                                st.metric("NET LIQ.", f"ASK ${abs(net_5):,.2f} USDT")
                        with col3:
                            st.write("**±10% Range**")
                            st.metric("ASK", f"${ask_10:,.2f} USDT")
                            if ask_weighted_10 > 0:
                                st.caption(f"WEIGHTED DEPTH CENTER: ${ask_weighted_10:.{decimal_places}f}")
                            st.metric("BID", f"${bid_10:,.2f} USDT")
                            if bid_weighted_10 > 0:
                                st.caption(f"WEIGHTED DEPTH CENTER: ${bid_weighted_10:.{decimal_places}f}")
                            st.metric("Total", f"${total_10:,.2f} USDT")
                            if net_10 >= 0:
                                st.metric("NET LIQ.", f"BID ${abs(net_10):,.2f} USDT")
                            else:
                                st.metric("NET LIQ.", f"ASK ${abs(net_10):,.2f} USDT")
                
                # Liquidity Health Check
                st.subheader("🏥 Liquidity Health Check")
                
                health_score = 0
                health_issues = []
                
                if spread_percentage < 0.1:
                    health_score += 30
                elif spread_percentage < 0.5:
                    health_score += 20
                else:
                    health_issues.append("High spread")
                
                if total_2 > 1000:
                    health_score += 25
                elif total_2 > 500:
                    health_score += 15
                else:
                    health_issues.append("Low liquidity in ±2% range")
                
                if abs(net_2) < total_2 * 0.3:
                    health_score += 25
                else:
                    health_issues.append("Imbalanced liquidity")
                
                if total_5 > total_2 * 2:
                    health_score += 20
                else:
                    health_issues.append("Limited depth beyond ±2%")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if health_score >= 80:
                        st.success(f"🟢 Health Score: {health_score}/100 - Excellent")
                    elif health_score >= 60:
                        st.warning(f"🟡 Health Score: {health_score}/100 - Good")
                    else:
                        st.error(f"🔴 Health Score: {health_score}/100 - Poor")
                
                with col2:
                    if health_issues:
                        st.write("**Issues Found:**")
                        for issue in health_issues:
                            st.write(f"• {issue}")
                    else:
                        st.success("✅ No issues detected")
                
                # Auto refresh
                if st.button("🔄 Refresh Data", key="refresh_monitoring"):
                    st.rerun()
                
                # ST Thresholds and Target Board (6 items)
                st.subheader("📊 ST Thresholds and Target Board")
                
                # Load manual inputs for thresholds
                manual_inputs = {}
                try:
                    if os.path.exists("manual_inputs.json"):
                        with open("manual_inputs.json", "r", encoding="utf-8") as f:
                            manual_inputs = json.load(f)
                except:
                    manual_inputs = {}
                
                # Get token-specific inputs
                token_key = f"{exchange_id}_{symbol.replace('/', '_').lower()}"
                token_inputs = manual_inputs.get(token_key, {})
                
                # Get current values
                current_price_usdt = fresh_ticker['last'] * usdt_rate if fresh_ticker['last'] else 0
                quote_vol = fresh_ticker['quoteVolume'] * usdt_rate if fresh_ticker['quoteVolume'] else 0
                
                monitor_col1, monitor_col2, monitor_col3 = st.columns(3)
                
                with monitor_col1:
                    # a) Total User Holdings
                    cex_cap = token_inputs.get('cex_cap', 0)
                    user_holdings_target = token_inputs.get('user_holdings_target', 150000)
                    user_holdings_threshold = token_inputs.get('user_holdings_threshold', 70000)
                    
                    if cex_cap > 0:
                        if cex_cap <= user_holdings_threshold:
                            st.error(f"❌ CRITICAL WARNING - User Holdings ≤ ${user_holdings_threshold:,.0f}: ${cex_cap:,.0f}")
                        elif cex_cap <= user_holdings_target:
                            st.warning(f"⚠️ IMMEDIATE ACTION - User Holdings ${user_holdings_threshold:,.0f}-${user_holdings_target:,.0f}: ${cex_cap:,.0f}")
                        else:
                            st.success(f"✅ SAFE - User Holdings > ${user_holdings_target:,.0f}: ${cex_cap:,.0f}")
                    else:
                        st.info("ℹ️ User Holdings not set")
                    
                    st.caption(f"Target: >${user_holdings_target:,.0f} | Threshold: ${user_holdings_threshold:,.0f}")
                    
                    # b) Price Ratio (against Listing)
                    listing_price = token_inputs.get('listing_price', 0)
                    price_ratio_target = token_inputs.get('price_ratio_target', 10.0) / 100
                    price_ratio_threshold = token_inputs.get('price_ratio_threshold', 1.0) / 100
                    
                    if listing_price > 0:
                        price_ratio = current_price_usdt / listing_price if listing_price > 0 else 0
                        if price_ratio >= price_ratio_target:
                            st.success(f"✅ SAFE - Price Ratio ≥ {price_ratio_target:.2%}: {price_ratio:.2%}")
                        elif price_ratio >= price_ratio_threshold:
                            st.warning(f"⚠️ IMMEDIATE ACTION - Price Ratio {price_ratio_threshold:.2%}-{price_ratio_target:.2%}: {price_ratio:.2%}")
                        else:
                            st.error(f"❌ CRITICAL WARNING - Price Ratio < {price_ratio_threshold:.2%}: {price_ratio:.2%}")
                    else:
                        st.info("ℹ️ Listing price not set")
                    
                    st.caption(f"Target: ≥{price_ratio_target:.2%} | Threshold: {price_ratio_threshold:.2%}")
                
                with monitor_col2:
                    # c) # of Holders with +$5
                    estimated_holders = token_inputs.get('estimated_holders', 0)
                    holders_target = token_inputs.get('holders_target', 200)
                    holders_threshold = token_inputs.get('holders_threshold', 100)
                    
                    if estimated_holders > 0:
                        if estimated_holders <= holders_threshold:
                            st.error(f"❌ CRITICAL WARNING - Holders ≤ {holders_threshold}: {estimated_holders}")
                        elif estimated_holders <= holders_target:
                            st.warning(f"⚠️ IMMEDIATE ACTION - Holders {holders_threshold}-{holders_target}: {estimated_holders}")
                        else:
                            st.success(f"✅ SAFE - Holders > {holders_target}: {estimated_holders}")
                    else:
                        st.info("ℹ️ Holders not set")
                    
                    st.caption(f"Target: >{holders_target} | Threshold: {holders_threshold}")
                    
                    # d) ±2% Total Depth
                    depth_target = token_inputs.get('depth_target', 1000)
                    depth_threshold = token_inputs.get('depth_threshold', 500)
                    
                    if total_2 < depth_threshold:
                        st.error(f"❌ CRITICAL WARNING - ±2% Depth < ${depth_threshold:,.0f}: ${total_2:,.0f}")
                    elif total_2 < depth_target:
                        st.warning(f"⚠️ IMMEDIATE ACTION - ±2% Depth ${depth_threshold:,.0f}-${depth_target:,.0f}: ${total_2:,.0f}")
                    else:
                        st.success(f"✅ SAFE - ±2% Depth > ${depth_target:,.0f}: ${total_2:,.0f}")
                    
                    st.caption(f"Target: >${depth_target:,.0f} | Threshold: ${depth_threshold:,.0f}")
                
                with monitor_col3:
                    # e) Spread
                    spread_target = token_inputs.get('spread_target', 1.0)
                    spread_threshold = token_inputs.get('spread_threshold', 2.0)
                    
                    if spread_percentage < spread_target:
                        st.success(f"✅ SAFE - Spread < {spread_target:.1f}%: {spread_percentage:.2f}%")
                    elif spread_percentage < spread_threshold:
                        st.warning(f"⚠️ IMMEDIATE ACTION - Spread {spread_target:.1f}-{spread_threshold:.1f}%: {spread_percentage:.2f}%")
                    else:
                        st.error(f"❌ CRITICAL WARNING - Spread > {spread_threshold:.1f}%: {spread_percentage:.2f}%")
                    
                    st.caption(f"Target: <{spread_target:.1f}% | Threshold: {spread_threshold:.1f}%")
                    
                    # f) Volume
                    volume_target = token_inputs.get('volume_target', 50000)
                    volume_threshold = token_inputs.get('volume_threshold', 20000)
                    
                    if quote_vol <= volume_threshold:
                        st.error(f"❌ CRITICAL WARNING - Volume ≤ ${volume_threshold:,.0f}: ${quote_vol:,.0f}")
                    elif quote_vol <= volume_target:
                        st.warning(f"⚠️ IMMEDIATE ACTION - Volume ${volume_threshold:,.0f}-${volume_target:,.0f}: ${quote_vol:,.0f}")
                    else:
                        st.success(f"✅ SAFE - Volume > ${volume_target:,.0f}: ${quote_vol:,.0f}")
                    
                    st.caption(f"Target: >${volume_target:,.0f} | Threshold: ${volume_threshold:,.0f}")
                
                # Enhanced Micro Burst metrics with better debugging
                st.subheader("⚡ Micro Burst Metrics")
                pro_enabled = bool(st.session_state.get("enable_micro_burst"))
                
                # Add debug mode toggle
                debug_mode = st.checkbox("Show Debug Info", key="mb_debug")
                
                if pro_enabled:
                    col_btn, col_status = st.columns([1, 3])
                    with col_btn:
                        if st.button("Run Burst Now", key="run_burst_now"):
                            frames_now, path_now = run_micro_burst_now()
                            if frames_now:
                                st.success(f"✅ Saved burst: {path_now}")
                                st.caption(f"Captured {len(frames_now)} frames")
                    
                    with col_status:
                        # Show capture status
                        if st.session_state.get("last_burst_frames"):
                            st.info(f"📊 Last burst: {len(st.session_state.get('last_burst_frames', []))} frames in memory")
                
                c1, c2, c3, c4, c5 = st.columns(5)
                
                latest = None
                mb_metrics = None
                error_msg = None
                
                if pro_enabled:
                    try:
                        # Try to get frames from memory first
                        frames = st.session_state.get("last_burst_frames")
                        latest = st.session_state.get("last_burst_path")
                        
                        # If not in memory, load from file
                        if not frames:
                            latest = _latest_micro_burst_path(exchange_id, symbol)
                            if latest:
                                with open(latest, "r", encoding="utf-8") as f:
                                    burst = json.load(f)
                                frames = burst.get("frames", [])
                                
                                if debug_mode:
                                    st.caption(f"📂 Loaded from file: {latest}")
                        
                        if frames:
                            # Show data source info
                            source = 'memory' if st.session_state.get('last_burst_frames') else 'file'
                            
                            if debug_mode:
                                st.caption(f"📊 Source: {source} | Frames: {len(frames)}")
                                
                                # Show sample frame structure
                                if frames:
                                    sample = frames[0]
                                    st.code(f"Sample frame keys: {list(sample.keys())}", language="python")
                                    if 'bids' in sample and sample['bids']:
                                        st.code(f"Sample bid: {sample['bids'][0] if sample['bids'] else 'empty'}", language="python")
                            
                            # Calculate mid price
                            mid = 0
                            if fresh_ticker:
                                bid = fresh_ticker.get('bid', 0)
                                ask = fresh_ticker.get('ask', 0)
                                if bid and ask:
                                    mid = (bid + ask) / 2
                            
                            # Compute metrics
                            mb_metrics = _compute_micro_burst_metrics(frames, mid)
                            
                            if debug_mode:
                                if mb_metrics:
                                    st.code(f"Computed metrics: {json.dumps(mb_metrics, indent=2)}", language="json")
                                else:
                                    st.warning("⚠️ No metrics computed - check console for errors")
                                    
                                # Show frame analysis
                                valid_frames = 0
                                total_bids = 0
                                total_asks = 0
                                for frame in frames:
                                    if isinstance(frame, dict) and 'bids' in frame and 'asks' in frame:
                                        if frame['bids'] and frame['asks']:
                                            valid_frames += 1
                                            total_bids += len(frame['bids'])
                                            total_asks += len(frame['asks'])
                                
                                st.caption(f"📊 Frame Analysis: {valid_frames}/{len(frames)} valid frames, {total_bids} total bids, {total_asks} total asks")
                                
                    except Exception as e:
                        error_msg = str(e)
                        if debug_mode:
                            st.error(f"❌ Error: {error_msg}")
                            import traceback
                            st.code(traceback.format_exc(), language="python")

                # Tooltips
                tip_persist = "Top-3 가격대의 지속성(Jaccard). 0~1. 높을수록 호가 유지/재보급 일관성↑"
                tip_hhi = "±2% 범위 내 공급 노이즈 점유율 HHI. 0~1. 높을수록 소수 집중↑"
                tip_imbv = "±2% 내 (Bid-Ask) 노이즈 불균형의 변동성. 높을수록 초단기 흔들림↑"
                tip_layer = "Top-10 틱 간격의 표준편차. 낮으면 규칙적 레이어링(사다리) 의심"
                tip_flip = "연속 프레임에서 최우선 호가쌍 변화 횟수. 많으면 터치 단 변동 치열"

                # Render metric cards with detailed information inside each box
                if mb_metrics:
                    # Calculate additional details for each metric
                    valid_frames = mb_metrics.get('valid_frames', 0)
                    total_frames = mb_metrics.get('frames_processed', 0)
                    
                    # Quote Persistence details
                    persist_value = mb_metrics['quote_persistence_top3']
                    persist_status = "🟢 Stable" if persist_value > 0.7 else "🟡 Variable" if persist_value > 0.3 else "🔴 Unstable"
                    persist_details = f"{persist_status} | {valid_frames}/{total_frames} frames"
                    
                    # HHI details  
                    hhi_value = mb_metrics['concentration_hhi_2pct']
                    hhi_status = "🟢 Distributed" if hhi_value < 0.3 else "🟡 Concentrated" if hhi_value < 0.7 else "🔴 Monopolized"
                    hhi_details = f"{hhi_status} | ±2% range"
                    
                    # Imbalance Volatility details
                    imb_value = mb_metrics['imbalance_volatility']
                    imb_status = "🟢 Balanced" if imb_value < 1000 else "🟡 Volatile" if imb_value < 5000 else "🔴 Chaotic"
                    imb_details = f"{imb_status} | {imb_value:.0f} volatility"
                    
                    # Layering Gap STD details (스푸핑 감지)
                    layer_value = mb_metrics['layering_gap_std']
                    layer_status = "🔴 Spoofing" if layer_value < 0.001 else "🟡 Regular" if layer_value < 0.01 else "🟢 Natural"
                    layer_details = f"{layer_status} | {layer_value:.6f} std"
                    
                    # Touch Flip details
                    flip_value = mb_metrics['touch_flip_count']
                    flip_status = "🔴 Manipulated" if flip_value > 5 else "🟡 Active" if flip_value > 2 else "🟢 Stable"
                    flip_details = f"{flip_status} | {flip_value} changes"
                    
                    # Render cards with details
                    render_metric_card(c1, "Quote Persistence", f"{persist_value:.3f}", tip_persist, pro=True, details=persist_details, micro_burst=True)
                    render_metric_card(c2, "HHI (±2%)", f"{hhi_value:.3f}", tip_hhi, pro=True, details=hhi_details, micro_burst=True)
                    render_metric_card(c3, "Imbalance Vol", f"{imb_value:.2f}", tip_imbv, pro=True, details=imb_details, micro_burst=True)
                    render_metric_card(c4, "Layer STD", f"{layer_value:.6f}", tip_layer, pro=True, details=layer_details, micro_burst=True)
                    render_metric_card(c5, "Touch Flips", f"{flip_value}", tip_flip, pro=True, details=flip_details, micro_burst=True)
                    
                    # Overall spoofing assessment
                    spoofing_score = 0
                    if layer_value < 0.001: spoofing_score += 40  # Strong layering pattern
                    if persist_value < 0.3: spoofing_score += 30  # Low persistence
                    if flip_value > 5: spoofing_score += 30      # High flip count
                    
                    if spoofing_score >= 70:
                        st.error(f"🚨 HIGH SPOOFING RISK: {spoofing_score}% (Layer: {layer_status}, Persist: {persist_status}, Flips: {flip_status})")
                    elif spoofing_score >= 40:
                        st.warning(f"⚠️ MODERATE SPOOFING RISK: {spoofing_score}% (Layer: {layer_status}, Persist: {persist_status}, Flips: {flip_status})")
                    else:
                        st.success(f"✅ LOW SPOOFING RISK: {spoofing_score}% (Layer: {layer_status}, Persist: {persist_status}, Flips: {flip_status})")
                        
                else:
                    # Show disabled/empty state
                    render_metric_card(c1, "Quote Persistence", "N/A", tip_persist, pro=True, disabled=not pro_enabled, details="No data available", micro_burst=True)
                    render_metric_card(c2, "HHI (±2%)", "N/A", tip_hhi, pro=True, disabled=not pro_enabled, details="No data available", micro_burst=True)
                    render_metric_card(c3, "Imbalance Vol", "N/A", tip_imbv, pro=True, disabled=not pro_enabled, details="No data available", micro_burst=True)
                    render_metric_card(c4, "Layer STD", "N/A", tip_layer, pro=True, disabled=not pro_enabled, details="No data available", micro_burst=True)
                    render_metric_card(c5, "Touch Flips", "N/A", tip_flip, pro=True, disabled=not pro_enabled, details="No data available", micro_burst=True)
                    
                    if pro_enabled and not mb_metrics:
                        if error_msg:
                            st.warning(f"⚠️ Failed to compute metrics: {error_msg}")
                        else:
                            st.info("ℹ️ No micro burst data available. Click 'Run Burst Now' to capture.")

                # Auto refresh by configured interval
                import time
                sleep_s = int(st.session_state.get("monitor_interval_s", 30))
                time.sleep(sleep_s)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error in monitoring: {str(e)}")
        
        # Add "Add to Main Board" button at the end of monitoring
        st.markdown("---")
        st.subheader("📋 Next Step")
        
        add_col1, add_col2 = st.columns([1, 2])
        with add_col1:
            if st.button("📌 Add to Main Board", type="primary", use_container_width=True, key="add_to_mainboard_btn"):
                # Save to monitoring configs for Night Watch Dashboard
                ex_id_norm = st.session_state.exchange_data['exchange_id']
                if ex_id_norm == "mexc_evaluation":
                    ex_id_norm = "mexc_assessment"

                # Load existing configs BEFORE creating the new config (to preserve started_at)
                config_file = "monitoring_configs.json"
                configs = {}
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        configs = json.load(f)
                config_id = f"{ex_id_norm}_{st.session_state.exchange_data['symbol'].replace('/', '_').lower()}"
                existing_started_at = (configs.get(config_id) or {}).get("started_at")

                config = {
                    "exchange": ex_id_norm,
                    "symbol": st.session_state.exchange_data['symbol'],
                    # preserve existing started_at if exists
                    "started_at": existing_started_at or (datetime.now().isoformat() + "Z"),
                    "status": "active",
                    "description": f"{st.session_state.exchange_data['symbol']} monitoring on {ex_id_norm}"
                }

                # include credentials for MEXC ASSESSMENT if provided
                if st.session_state.exchange_data['exchange_id'] in ("mexc_evaluation", "mexc_assessment"):
                    if 'api_key' in st.session_state.exchange_data and 'api_secret' in st.session_state.exchange_data:
                        config["apiKey"] = st.session_state.exchange_data.get('api_key')
                        config["apiSecret"] = st.session_state.exchange_data.get('api_secret')
                
                # Add/replace config (preserving started_at already handled)
                configs[config_id] = config
                
                # Save configs
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, indent=2)
                
                st.success(f"✅ Added to Main Board: {st.session_state.exchange_data['symbol']} on {st.session_state.exchange_data['exchange_id']}")
                st.info("🔗 View on Main Board: http://localhost:8501")
        
        with add_col2:
            st.caption("💡 Click this button to make this token visible on the Main Board (Crisis Bulletin)")
    
    # Show accumulation status if started
    if st.session_state.start_accumulation:
        st.subheader("💾 Data Accumulation Status")
        
        # Create data directory if not exists
        import os
        data_dir = "accumulation_data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Get current data
        data = st.session_state.exchange_data
        exchange = data['exchange']
        symbol = data['symbol']
        exchange_id = data['exchange_id']
        
        try:
            # Fetch current data
            current_ticker = exchange.fetch_ticker(symbol)
            
            # Determine USDT conversion rate for snapshot
            try:
                quote_cur = symbol.split('/')[-1].upper() if '/' in symbol else 'USDT'
                usdt_rate_snapshot = 1.0
                if quote_cur != 'USDT':
                    try:
                        conv = exchange.fetch_ticker(f"{quote_cur}/USDT")
                        usdt_rate_snapshot = float(conv.get('last') or 1.0)
                    except Exception:
                        try:
                            conv = exchange.fetch_ticker(f"USDT/{quote_cur}")
                            last_conv = float(conv.get('last') or 0.0)
                            usdt_rate_snapshot = (1.0 / last_conv) if last_conv > 0 else 1.0
                        except Exception:
                            usdt_rate_snapshot = 1.0
                else:
                    usdt_rate_snapshot = 1.0
            except Exception:
                usdt_rate_snapshot = 1.0
            
            # Try to get maximum orderbook depth (100-150 levels)
            try:
                current_orderbook = exchange.fetch_order_book(symbol, limit=150)
            except:
                try:
                    current_orderbook = exchange.fetch_order_book(symbol, limit=100)
                except:
                    current_orderbook = exchange.fetch_order_book(symbol, limit=50)
            
            # Create snapshot data
            from datetime import datetime
            import json
            
            # Derive basic metrics for downstream reporting
            try:
                bid_snap = float(current_ticker.get('bid') or 0.0)
                ask_snap = float(current_ticker.get('ask') or 0.0)
                bid_u = bid_snap * usdt_rate_snapshot if bid_snap > 0 else 0.0
                ask_u = ask_snap * usdt_rate_snapshot if ask_snap > 0 else 0.0
                spread_pct_snap = ((ask_u - bid_u) / bid_u * 100.0) if (bid_u > 0 and ask_u > 0) else None
                # ±2% depth (USDT notional)
                total_2_u = None; bid_2_u = None; ask_2_u = None
                total_5_u = None; bid_5_u = None; ask_5_u = None
                total_10_u = None; bid_10_u = None; ask_10_u = None
                if isinstance(current_orderbook, dict) and bid_u > 0 and ask_u > 0:
                    mid_u = (bid_u + ask_u) / 2.0
                    low_u = mid_u * 0.98
                    high_u = mid_u * 1.02
                    bt = 0.0; at = 0.0
                    bt5 = 0.0; at5 = 0.0
                    bt10 = 0.0; at10 = 0.0
                    low5 = mid_u * 0.95; high5 = mid_u * 1.05
                    low10 = mid_u * 0.90; high10 = mid_u * 1.10
                    for p,a in (current_orderbook.get('bids') or []):
                        try:
                            p_u = float(p) * usdt_rate_snapshot; a = float(a)
                            if low_u <= p_u <= mid_u:
                                bt += p_u * a
                            if low5 <= p_u <= mid_u:
                                bt5 += p_u * a
                            if low10 <= p_u <= mid_u:
                                bt10 += p_u * a
                        except Exception:
                            pass
                    for p,a in (current_orderbook.get('asks') or []):
                        try:
                            p_u = float(p) * usdt_rate_snapshot; a = float(a)
                            if mid_u <= p_u <= high_u:
                                at += p_u * a
                            if mid_u <= p_u <= high5:
                                at5 += p_u * a
                            if mid_u <= p_u <= high10:
                                at10 += p_u * a
                        except Exception:
                            pass
                    bid_2_u = bt; ask_2_u = at; total_2_u = bt + at
                    bid_5_u = bt5; ask_5_u = at5; total_5_u = bt5 + at5
                    bid_10_u = bt10; ask_10_u = at10; total_10_u = bt10 + at10
            except Exception:
                spread_pct_snap = None; bid_2_u = None; ask_2_u = None; total_2_u = None; bid_5_u=None; ask_5_u=None; total_5_u=None; bid_10_u=None; ask_10_u=None; total_10_u=None
            
            snapshot = {
                'timestamp': datetime.utcnow().isoformat(),
                'exchange': exchange_id,
                'symbol': symbol,
                'ticker': current_ticker,
                'orderbook': current_orderbook,
                'utc_date': datetime.utcnow().strftime('%Y-%m-%d'),
                'usdt_rate': usdt_rate_snapshot,
                'metrics': {
                    'spread_pct': spread_pct_snap,
                    'bid_liq_2_usdt': bid_2_u,
                    'ask_liq_2_usdt': ask_2_u,
                    'total_liq_2_usdt': total_2_u,
                    'bid_liq_5_usdt': bid_5_u,
                    'ask_liq_5_usdt': ask_5_u,
                    'total_liq_5_usdt': total_5_u,
                    'bid_liq_10_usdt': bid_10_u,
                    'ask_liq_10_usdt': ask_10_u,
                    'total_liq_10_usdt': total_10_u,
                }
            }
            
            # Save to file
            filename = f"{data_dir}/{exchange_id}_{symbol.replace('/', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(snapshot, f, indent=2)
            
            st.success(f"✅ Snapshot saved: {filename}")
            
            # Show accumulation info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Current Price", f"${current_ticker['last']:.{decimal_places}f} USDT")
            
            with col2:
                st.metric("Bid/Ask Levels", f"{len(current_orderbook['bids'])}/{len(current_orderbook['asks'])}")
                st.caption(f"Max depth: {max(len(current_orderbook['bids']), len(current_orderbook['asks']))} levels")
            
            with col3:
                # Round volume to 0.01 (10^-2) precision
                volume_rounded = round(current_ticker['baseVolume'], 2)
                st.metric("24h Volume", f"${volume_rounded:,.2f} USDT")
            
            # Show saved files count
            files = [f for f in os.listdir(data_dir) if f.startswith(f"{exchange_id}_{symbol.replace('/', '_')}")]
            st.info(f"📁 Total snapshots saved: {len(files)}")
            
            # Auto refresh by configured accumulation interval
            import time
            sleep_s = int(st.session_state.get("accum_interval_s", 60))
            time.sleep(sleep_s)
            st.rerun()
            
        except Exception as e:
            st.error(f"Error in accumulation: {str(e)}")

# Auto refresh option removed in favor of sidebar interval settings


# Hide base Manual Inputs sections from default view – replaced by Quick panel
# (wrapped in expander so not shown unless explicitly opened)
st.markdown("---")
with st.expander("🛠️ Manual Inputs (Full)", expanded=False):
    st.info("Manual Inputs full panel hidden. Use 'Manual Inputs (Quick)' to edit.")

# Load existing manual inputs
manual_inputs = {}
if os.path.exists("manual_inputs.json"):
    with open("manual_inputs.json", "r", encoding="utf-8") as f:
        manual_inputs = json.load(f)

# Get current token info
current_token_key = None
if ('exchange_data' in st.session_state and 
    st.session_state.exchange_data is not None and 
    'symbol' in st.session_state.exchange_data and 
    'exchange_id' in st.session_state.exchange_data):
    current_token_key = f"{st.session_state.exchange_data['exchange_id']}_{st.session_state.exchange_data['symbol'].replace('/', '_').lower()}"

if current_token_key:
    st.info(f"Setting inputs for: {st.session_state.exchange_data['symbol']} on {st.session_state.exchange_data['exchange_id']}")
    st.caption(f"Token Key: {current_token_key}")
    
    # Initialize token inputs if not exists
    if current_token_key not in manual_inputs:
        manual_inputs[current_token_key] = {}
    
    token_inputs = manual_inputs[current_token_key]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Exchange User Holdings - Market Cap at specific price
        st.markdown("**Exchange User Holdings**")
        cex_price = st.number_input(
            "CEX Price (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('cex_price', 0)),
            step=0.00000001,
            format="%.8f",
            help="Price when market cap was calculated"
        )
        token_inputs['cex_price'] = cex_price
        
        cex_market_cap = st.number_input(
            "Exchange User Holdings (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('cex_market_cap', 0)),
            step=1000.0,
            help="Market cap at the specified price"
        )
        token_inputs['cex_market_cap'] = cex_market_cap
        
        # Calculate current CEX CAP based on current price (proportional to price change)
        if cex_price > 0 and cex_market_cap > 0:
            current_price = 0
            if st.session_state.exchange_data and 'last_price' in st.session_state.exchange_data:
                current_price = st.session_state.exchange_data.get('last_price', 0)
            
            if current_price > 0:
                # Market cap changes proportionally with price
                current_cex_cap = cex_market_cap * (current_price / cex_price)
                token_inputs['cex_cap'] = current_cex_cap
                st.info(f"Current Exchange User Holdings: ${current_cex_cap:,.0f}")
                st.caption(f"Price ratio: {current_price/cex_price:.4f}x")
            else:
                token_inputs['cex_cap'] = None
                st.warning("Current price not available - cannot calculate current holdings")
        
        # Listing Price
        st.markdown("**Listing Price**")
        listing_price = st.number_input(
            "Listing Price (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('listing_price', 0)),
            step=0.00000001,
            format="%.8f",
            help="Initial listing price for price drop calculation"
        )
        token_inputs['listing_price'] = listing_price
    
    with col2:
        # Estimated Holders - Price and Count
        st.markdown("**Estimated Holders**")
        holders_price = st.number_input(
            "Holders Price (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('holders_price', 0)),
            step=0.00000001,
            format="%.8f",
            help="Price when counting holders"
        )
        token_inputs['holders_price'] = holders_price
        
        holders_count = st.number_input(
            "Holders Count", 
            min_value=0, 
            value=int(token_inputs.get('holders_count', 0)),
            step=10,
            help="Number of holders at the specified price"
        )
        token_inputs['holders_count'] = holders_count
        
        # Calculate estimated holders for $5+ threshold
        if holders_price > 0 and holders_count > 0:
            # Estimate holders with $5+ at current price
            current_price = 0
            if st.session_state.exchange_data and 'last_price' in st.session_state.exchange_data:
                current_price = st.session_state.exchange_data.get('last_price', 0)
            
            if current_price > 0:
                # Assume holders are distributed, estimate those with $5+ at current price
                # Higher price = more people can afford $5+ worth, so proportional increase
                estimated_holders = int(holders_count * (current_price / holders_price))
                token_inputs['estimated_holders'] = estimated_holders
                st.info(f"Estimated $5+ holders: {estimated_holders}")
    
    with col3:
        # Save button
        if st.button("💾 Save Manual Inputs", type="primary"):
            manual_inputs[current_token_key] = token_inputs
            try:
                with open("manual_inputs.json", "w", encoding="utf-8") as f:
                    json.dump(manual_inputs, f, indent=2)
                st.success("✅ Manual inputs saved!")
                st.caption(f"Saved to: manual_inputs.json with key: {current_token_key}")
            except Exception as e:
                st.error(f"❌ Error saving: {str(e)}")
    
    # Target and Threshold Settings
    st.markdown("### 🎯 Target & Threshold Settings")
    st.caption("Configure risk monitoring criteria for this token")
    auto_apply = st.checkbox("Auto-apply to Night Watch", value=True, help="Save changes immediately to manual_inputs.json so Night Watch reflects them in real-time")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**User Holdings**")
        user_holdings_target = st.number_input(
            "Target (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('user_holdings_target', 150000)),
            step=10000.0,
            help="Target value for user holdings (SAFE threshold)"
        )
        token_inputs['user_holdings_target'] = user_holdings_target
        
        user_holdings_threshold = st.number_input(
            "Threshold (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('user_holdings_threshold', 70000)),
            step=10000.0,
            help="Critical warning threshold for user holdings"
        )
        token_inputs['user_holdings_threshold'] = user_holdings_threshold
        
        st.markdown("**Price Ratio**")
        price_ratio_target = st.number_input(
            "Target (%)", 
            min_value=0.0, 
            max_value=100.0,
            value=float(token_inputs.get('price_ratio_target', 10.0)),
            step=1.0,
            help="Target price ratio vs listing price (SAFE threshold)"
        )
        token_inputs['price_ratio_target'] = price_ratio_target
        
        price_ratio_threshold = st.number_input(
            "Threshold (%)", 
            min_value=0.0, 
            max_value=100.0,
            value=float(token_inputs.get('price_ratio_threshold', 1.0)),
            step=0.1,
            help="Critical warning threshold for price ratio"
        )
        token_inputs['price_ratio_threshold'] = price_ratio_threshold
    
    with col2:
        st.markdown("**Holders**")
        holders_target = st.number_input(
            "Target (Count)", 
            min_value=0, 
            value=int(token_inputs.get('holders_target', 200)),
            step=10,
            help="Target number of holders (SAFE threshold)"
        )
        token_inputs['holders_target'] = holders_target
        
        holders_threshold = st.number_input(
            "Threshold (Count)", 
            min_value=0, 
            value=int(token_inputs.get('holders_threshold', 100)),
            step=10,
            help="Critical warning threshold for holders"
        )
        token_inputs['holders_threshold'] = holders_threshold
        
        st.markdown("**±2% Depth**")
        depth_target = st.number_input(
            "Target (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('depth_target', 1000)),
            step=100.0,
            help="Target liquidity depth (SAFE threshold)"
        )
        token_inputs['depth_target'] = depth_target
        
        depth_threshold = st.number_input(
            "Threshold (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('depth_threshold', 500)),
            step=100.0,
            help="Critical warning threshold for liquidity depth"
        )
        token_inputs['depth_threshold'] = depth_threshold
    
    with col3:
        st.markdown("**Spread**")
        spread_target = st.number_input(
            "Target (%)", 
            min_value=0.0, 
            max_value=100.0,
            value=float(token_inputs.get('spread_target', 1.0)),
            step=0.1,
            help="Target spread (SAFE threshold)"
        )
        token_inputs['spread_target'] = spread_target
        
        spread_threshold = st.number_input(
            "Threshold (%)", 
            min_value=0.0, 
            max_value=100.0,
            value=float(token_inputs.get('spread_threshold', 2.0)),
            step=0.1,
            help="Critical warning threshold for spread"
        )
        token_inputs['spread_threshold'] = spread_threshold
        
        st.markdown("**Volume**")
        volume_target = st.number_input(
            "Target (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('volume_target', 50000)),
            step=5000.0,
            help="Target 24h volume (SAFE threshold)"
        )
        token_inputs['volume_target'] = volume_target
        
        volume_threshold = st.number_input(
            "Threshold (USDT)", 
            min_value=0.0, 
            value=float(token_inputs.get('volume_threshold', 20000)),
            step=5000.0,
            help="Critical warning threshold for 24h volume"
        )
        token_inputs['volume_threshold'] = volume_threshold
    
    # Display current monitoring values (6 items like Night Watch)
    st.markdown("### 🚨 Current Monitoring Values:")
    
    # Compute fresh, exchange-accurate metrics to avoid missing data
    current_price_usdt = 0.0
    current_volume_usdt = 0.0
    current_spread = 0.0
    current_liquidity = 0.0
    try:
        # Quote to USDT conversion
        quote_currency = market_info.get('quote', 'USDT') if isinstance(market_info, dict) else 'USDT'
        usdt_rate = 1.0
        if quote_currency and quote_currency.upper() != 'USDT':
            # Try quote/USDT then USDT/quote
            try:
                conv = exchange.fetch_ticker(f"{quote_currency}/USDT")
                usdt_rate = float(conv.get('last') or 1.0) if conv else 1.0
            except:
                try:
                    conv = exchange.fetch_ticker(f"USDT/{quote_currency}")
                    last_conv = float(conv.get('last') or 0.0) if conv else 0.0
                    usdt_rate = (1.0 / last_conv) if last_conv > 0 else 1.0
                except:
                    usdt_rate = 1.0
        # Ticker
        fresh_ticker = exchange.fetch_ticker(symbol)
        last = float(fresh_ticker.get('last') or 0.0)
        bid = float(fresh_ticker.get('bid') or 0.0)
        ask = float(fresh_ticker.get('ask') or 0.0)
        quote_vol = float(fresh_ticker.get('quoteVolume') or 0.0)
        current_price_usdt = last * usdt_rate if last > 0 else 0.0
        current_volume_usdt = quote_vol * usdt_rate if quote_vol > 0 else 0.0
        # Spread
        bid_usdt = bid * usdt_rate if bid > 0 else 0.0
        ask_usdt = ask * usdt_rate if ask > 0 else 0.0
        if bid_usdt > 0 and ask_usdt > 0:
            current_spread = ((ask_usdt - bid_usdt) / bid_usdt) * 100.0
        # Orderbook and ±2% liquidity
        try:
            ob = exchange.fetch_order_book(symbol, limit=150)
        except:
            try:
                ob = exchange.fetch_order_book(symbol, limit=100)
            except:
                ob = exchange.fetch_order_book(symbol, limit=50)
        if bid_usdt > 0 and ask_usdt > 0 and isinstance(ob, dict):
            midpoint = (bid_usdt + ask_usdt) / 2.0
            rng = midpoint * 0.02
            min_p = midpoint - rng
            max_p = midpoint + rng
            bid_liq = 0.0
            ask_liq = 0.0
            for lvl in ob.get('bids') or []:
                try:
                    p, a = float(lvl[0]), float(lvl[1])
                    p_usdt = p * usdt_rate
                    if min_p <= p_usdt <= midpoint:
                        bid_liq += p_usdt * a
                except:
                    continue
            for lvl in ob.get('asks') or []:
                try:
                    p, a = float(lvl[0]), float(lvl[1])
                    p_usdt = p * usdt_rate
                    if midpoint <= p_usdt <= max_p:
                        ask_liq += p_usdt * a
                except:
                    continue
            current_liquidity = bid_liq + ask_liq
    except Exception:
        pass
    
    monitor_col1, monitor_col2, monitor_col3 = st.columns(3)
    
    with monitor_col1:
        # a) Total User Holdings
        cex_cap_value = token_inputs.get('cex_cap', 0)
        user_holdings_target = token_inputs.get('user_holdings_target', 150000)
        user_holdings_threshold = token_inputs.get('user_holdings_threshold', 70000)
        
        # Recompute cex_cap in real-time if inputs exist
        cex_price = float(token_inputs.get('cex_price', 0) or 0)
        cex_mc = float(token_inputs.get('cex_market_cap', 0) or 0)
        if cex_price > 0 and cex_mc > 0 and current_price_usdt > 0:
            cex_cap_value = cex_mc * (current_price_usdt / cex_price)
            token_inputs['cex_cap'] = cex_cap_value

        if cex_cap_value > 0:
            if cex_cap_value <= user_holdings_threshold:
                st.error(f"❌ CRITICAL WARNING - User Holdings ≤ ${user_holdings_threshold:,.0f}: ${cex_cap_value:,.0f}")
            elif cex_cap_value <= user_holdings_target:
                st.warning(f"⚠️ IMMEDIATE ACTION - User Holdings ${user_holdings_threshold:,.0f}-${user_holdings_target:,.0f}: ${cex_cap_value:,.0f}")
            else:
                st.success(f"✅ SAFE - User Holdings > ${user_holdings_target:,.0f}: ${cex_cap_value:,.0f}")
        else:
            st.info("ℹ️ User Holdings not set")
        
        st.caption(f"Target: >${user_holdings_target:,.0f} | Threshold: ${user_holdings_threshold:,.0f}")
        
        # b) Price Ratio (against Listing)
        price_ratio_target = token_inputs.get('price_ratio_target', 10.0) / 100
        price_ratio_threshold = token_inputs.get('price_ratio_threshold', 1.0) / 100
        
        if listing_price > 0 and current_price_usdt > 0:
            price_ratio = current_price_usdt / listing_price
            if price_ratio >= price_ratio_target:
                st.success(f"✅ SAFE - Price Ratio ≥ {price_ratio_target:.2%}: {price_ratio:.2%}")
            elif price_ratio >= price_ratio_threshold:
                st.warning(f"⚠️ IMMEDIATE ACTION - Price Ratio {price_ratio_threshold:.2%}-{price_ratio_target:.2%}: {price_ratio:.2%}")
            else:
                st.error(f"❌ CRITICAL WARNING - Price Ratio < {price_ratio_threshold:.2%}: {price_ratio:.2%}")
        else:
            st.info("ℹ️ Price ratio not available")
        
        st.caption(f"Target: ≥{price_ratio_target:.2%} | Threshold: {price_ratio_threshold:.2%}")
    
    with monitor_col2:
        # c) # of Holders with +$5
        estimated_holders = token_inputs.get('estimated_holders', 0)
        holders_target = token_inputs.get('holders_target', 200)
        holders_threshold = token_inputs.get('holders_threshold', 100)
        
        if estimated_holders > 0:
            if estimated_holders <= holders_threshold:
                st.error(f"❌ CRITICAL WARNING - Holders ≤ {holders_threshold}: {estimated_holders}")
            elif estimated_holders <= holders_target:
                st.warning(f"⚠️ IMMEDIATE ACTION - Holders {holders_threshold}-{holders_target}: {estimated_holders}")
            else:
                st.success(f"✅ SAFE - Holders > {holders_target}: {estimated_holders}")
        else:
            st.info("ℹ️ Holders not set")
        
        st.caption(f"Target: >{holders_target} | Threshold: {holders_threshold}")
        
        # d) ±2% Total Depth
        depth_target = token_inputs.get('depth_target', 1000)
        depth_threshold = token_inputs.get('depth_threshold', 500)
        
        if current_liquidity > 0:
            if current_liquidity < depth_threshold:
                st.error(f"❌ CRITICAL WARNING - ±2% Depth < ${depth_threshold:,.0f}: ${current_liquidity:,.0f}")
            elif current_liquidity < depth_target:
                st.warning(f"⚠️ IMMEDIATE ACTION - ±2% Depth ${depth_threshold:,.0f}-${depth_target:,.0f}: ${current_liquidity:,.0f}")
            else:
                st.success(f"✅ SAFE - ±2% Depth > ${depth_target:,.0f}: ${current_liquidity:,.0f}")
        else:
            st.info("ℹ️ Liquidity data not available")
        
        st.caption(f"Target: >${depth_target:,.0f} | Threshold: ${depth_threshold:,.0f}")
    
    with monitor_col3:
        # e) Spread
        spread_target = token_inputs.get('spread_target', 1.0)
        spread_threshold = token_inputs.get('spread_threshold', 2.0)
        
        if current_spread > 0:
            if current_spread < spread_target:
                st.success(f"✅ SAFE - Spread < {spread_target:.1f}%: {current_spread:.2f}%")
            elif current_spread < spread_threshold:
                st.warning(f"⚠️ IMMEDIATE ACTION - Spread {spread_target:.1f}-{spread_threshold:.1f}%: {current_spread:.2f}%")
            else:
                st.error(f"❌ CRITICAL WARNING - Spread > {spread_threshold:.1f}%: {current_spread:.2f}%")
        else:
            st.info("ℹ️ Spread data not available")
        
        st.caption(f"Target: <{spread_target:.1f}% | Threshold: {spread_threshold:.1f}%")
        
        # f) Volume
        volume_target = token_inputs.get('volume_target', 50000)
        volume_threshold = token_inputs.get('volume_threshold', 20000)
        
        if current_volume_usdt > 0:
            if current_volume_usdt <= volume_threshold:
                st.error(f"❌ CRITICAL WARNING - Volume ≤ ${volume_threshold:,.0f}: ${current_volume_usdt:,.0f}")
            elif current_volume_usdt <= volume_target:
                st.warning(f"⚠️ IMMEDIATE ACTION - Volume ${volume_threshold:,.0f}-${volume_target:,.0f}: ${current_volume_usdt:,.0f}")
            else:
                st.success(f"✅ SAFE - Volume > ${volume_target:,.0f}: ${current_volume_usdt:,.0f}")
        else:
            st.info("ℹ️ Volume data not available")
        
        st.caption(f"Target: >${volume_target:,.0f} | Threshold: ${volume_threshold:,.0f}")

    # Auto-apply updated manual inputs to Night Watch
    if auto_apply:
        manual_inputs[current_token_key] = token_inputs
        try:
            with open("manual_inputs.json", "w", encoding="utf-8") as f:
                json.dump(manual_inputs, f, indent=2)
            st.caption("Manual inputs auto-saved for Night Watch")
        except Exception as e:
            st.caption(f"Failed to auto-save manual inputs: {e}")

# removed duplicate bottom Data Accumulation section (moved to top expander)

