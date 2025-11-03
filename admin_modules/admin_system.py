"""
System Settings Module
======================
Unified settings for data collection, updates, and subscription tiers.
"""

import streamlit as st
import json
import os


def render_data_collection_settings():
    """Render Data Collection Settings tab."""
    st.markdown("### 📊 Data Collection Settings")
    st.caption("⚡ Adjust collection frequency based on current load and service requirements")
    
    # Load existing settings
    config_file = "config/subscription_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = _get_default_subscription_config()
    
    system_settings = config.get('system', {})
    
    st.markdown("#### 🔧 Backend System Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        monitoring_interval = st.number_input(
            "Monitoring Refresh Interval (seconds)",
            min_value=60,
            max_value=3600,
            value=system_settings.get('monitoring_refresh_interval_seconds', 300),
            step=60,
            help="How often the backend refreshes monitoring data"
        )
        
        accumulation_interval = st.number_input(
            "Data Accumulation Interval (seconds)",
            min_value=10,
            max_value=600,
            value=system_settings.get('accumulation_interval_seconds', 60),
            step=10,
            help="How often data snapshots are saved"
        )
    
    with col2:
        micro_burst_duration = st.number_input(
            "Micro Burst Duration (seconds)",
            min_value=1,
            max_value=30,
            value=system_settings.get('micro_burst_duration_seconds', 5),
            step=1,
            help="Duration of rapid consecutive snapshots"
        )
        
        micro_burst_interval = st.number_input(
            "Micro Burst Fetch Interval (seconds)",
            min_value=0.01,
            max_value=1.0,
            value=system_settings.get('micro_burst_fetch_interval_seconds', 0.1),
            step=0.01,
            format="%.2f",
            help="Time between snapshots during Micro Burst"
        )
    
    # Save button
    if st.button("💾 Save Data Collection Settings", type="primary"):
        config['system'] = {
            'monitoring_refresh_interval_seconds': monitoring_interval,
            'accumulation_interval_seconds': accumulation_interval,
            'micro_burst_duration_seconds': micro_burst_duration,
            'micro_burst_fetch_interval_seconds': micro_burst_interval
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        st.success("✅ Data collection settings saved!")
        st.rerun()


def render_update_feature_settings():
    """Render Update & Feature Settings tab."""
    st.markdown("### ⏱️ Update & Feature Settings")
    st.caption("Configure update intervals and feature limits for each subscription tier")
    
    # Load existing settings
    config_file = "config/subscription_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = _get_default_subscription_config()
    
    # Watchlist Limits Section
    st.markdown("#### 📊 Watchlist Limits")
    st.caption("Maximum number of tokens each tier can add to their watchlist")
    
    limit_col1, limit_col2, limit_col3 = st.columns(3)
    
    with limit_col1:
        free_watchlist_limit = st.number_input(
            "🆓 Free Tier Limit",
            min_value=1,
            max_value=100,
            value=config.get('free', {}).get('watchlist_limit', 2),
            step=1,
            help="Maximum tokens a free user can add to watchlist"
        )
    
    with limit_col2:
        pro_watchlist_limit = st.number_input(
            "💼 PRO Tier Limit",
            min_value=1,
            max_value=100,
            value=config.get('pro', {}).get('watchlist_limit', 8),
            step=1,
            help="Maximum tokens a PRO user can add to watchlist"
        )
    
    with limit_col3:
        premium_watchlist_limit = st.number_input(
            "👑 Premium Tier Limit",
            min_value=1,
            max_value=1000,
            value=config.get('premium', {}).get('watchlist_limit', 32),
            step=1,
            help="Maximum tokens a Premium user can add to watchlist"
        )
    
    st.markdown("---")
    
    # Free tier settings
    st.markdown("#### 🆓 Free Tier")
    free_settings = config.get('free', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        free_main_board = st.number_input(
            "Main Board Update Interval (minutes)",
            min_value=15,
            max_value=240,
            value=free_settings.get('main_board_interval_minutes', 60),
            step=15,
            key="free_main",
            help="Free users see Main Board updates every X minutes"
        )
        
        free_watchlist = st.number_input(
            "My Watch List Update Interval (minutes)",
            min_value=15,
            max_value=120,
            value=free_settings.get('watchlist_interval_minutes', 30),
            step=5,
            key="free_watch",
            help="Free users get watchlist snapshots every X minutes"
        )
    
    with col2:
        free_dashboard = st.number_input(
            "User Dashboard Update Interval (minutes)",
            min_value=30,
            max_value=240,
            value=free_settings.get('user_dashboard_interval_minutes', 60),
            step=15,
            key="free_dash",
            help="Free users can refresh User Dashboard every X minutes"
        )
        
        free_micro_burst = st.number_input(
            "Micro Burst Limit (per day)",
            min_value=1,
            max_value=10,
            value=free_settings.get('micro_burst_limit_per_day', 3),
            step=1,
            key="free_micro",
            help="Free users can trigger Micro Burst X times per day"
        )
    
    st.markdown("---")
    
    # Pro tier settings
    st.markdown("#### 💎 Pro Tier")
    pro_settings = config.get('pro', config.get('premium', {}))  # Fallback to 'premium' if 'pro' doesn't exist
    
    col1, col2 = st.columns(2)
    
    with col1:
        pro_main_board = st.number_input(
            "Main Board Update Interval (minutes)",
            min_value=1,
            max_value=60,
            value=pro_settings.get('main_board_interval_minutes', 15),
            step=5,
            key="pro_main",
            help="PRO users see Main Board updates every X minutes"
        )
        
        pro_watchlist = st.number_input(
            "My Watch List Update Interval (minutes)",
            min_value=1,
            max_value=30,
            value=pro_settings.get('watchlist_interval_minutes', 5),
            step=1,
            key="pro_watch",
            help="PRO users get watchlist snapshots every X minutes"
        )
    
    with col2:
        pro_dashboard = st.number_input(
            "User Dashboard Update Interval (minutes)",
            min_value=1,
            max_value=15,
            value=pro_settings.get('user_dashboard_interval_minutes', 1),
            step=1,
            key="pro_dash",
            help="PRO users can refresh User Dashboard every X minutes"
        )
        
        pro_micro_burst = st.number_input(
            "Micro Burst Limit (per day)",
            min_value=10,
            max_value=999,
            value=pro_settings.get('micro_burst_limit_per_day', 999),
            step=10,
            key="pro_micro",
            help="PRO users can trigger Micro Burst X times per day (999 = unlimited)"
        )
    
    st.markdown("---")
    
    # Premium tier settings
    st.markdown("#### 🌟 Premium Tier")
    premium_settings = config.get('premium', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        premium_main_board = st.number_input(
            "Main Board Update Interval (minutes)",
            min_value=1,
            max_value=60,
            value=premium_settings.get('main_board_interval_minutes', 5),
            step=1,
            key="premium_main",
            help="Premium users see Main Board updates every X minutes"
        )
        
        premium_watchlist = st.number_input(
            "My Watch List Update Interval (minutes)",
            min_value=1,
            max_value=10,
            value=premium_settings.get('watchlist_interval_minutes', 1),
            step=1,
            key="premium_watch",
            help="Premium users get watchlist snapshots every X minutes"
        )
    
    with col2:
        premium_dashboard = st.number_input(
            "User Dashboard Update Interval (minutes)",
            min_value=1,
            max_value=5,
            value=premium_settings.get('user_dashboard_interval_minutes', 1),
            step=1,
            key="premium_dash",
            help="Premium users get real-time User Dashboard updates"
        )
        
        premium_micro_burst = st.number_input(
            "Micro Burst Limit (per day)",
            min_value=100,
            max_value=9999,
            value=premium_settings.get('micro_burst_limit_per_day', 9999),
            step=100,
            key="premium_micro",
            help="Premium users have virtually unlimited Micro Burst"
        )
    
    # Save button
    if st.button("💾 Save Update & Feature Settings", type="primary"):
        config['free'] = {
            'main_board_interval_minutes': free_main_board,
            'watchlist_interval_minutes': free_watchlist,
            'user_dashboard_interval_minutes': free_dashboard,
            'micro_burst_limit_per_day': free_micro_burst,
            'watchlist_limit': free_watchlist_limit
        }
        
        config['pro'] = {
            'main_board_interval_minutes': pro_main_board,
            'watchlist_interval_minutes': pro_watchlist,
            'user_dashboard_interval_minutes': pro_dashboard,
            'micro_burst_limit_per_day': pro_micro_burst,
            'watchlist_limit': pro_watchlist_limit
        }
        
        config['premium'] = {
            'main_board_interval_minutes': premium_main_board,
            'watchlist_interval_minutes': premium_watchlist,
            'user_dashboard_interval_minutes': premium_dashboard,
            'micro_burst_limit_per_day': premium_micro_burst,
            'watchlist_limit': premium_watchlist_limit
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        st.success("✅ Update & feature settings saved!")
        st.rerun()
    
    st.markdown("---")
    st.info("💡 **Tip**: PRO/Premium users pay more → They deserve better service quality!")


def render_subscription_tiers():
    """Render Subscription Tiers comparison tab."""
    st.markdown("### 💎 Subscription Tiers Comparison")
    st.caption("Overview of features across Free, Pro, and Premium tiers")
    
    # Load existing settings
    config_file = "config/subscription_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = _get_default_subscription_config()
    
    free_settings = config.get('free', {})
    pro_settings = config.get('pro', config.get('premium', {}))
    premium_settings = config.get('premium', {})
    
    # Create comparison table
    comparison_data = {
        "Feature": [
            "Main Board Updates",
            "My Watch List Updates",
            "User Dashboard Updates",
            "Micro Burst Daily Limit",
            "Watchlist Capacity",
            "Custom Monitoring",
            "Periodic Liquidity Reports",
            "MM/Whale/Manipulation Analysis",
            "Telegram Alerts",
            "Arbitrage Service Alerts",
            "Inter-Exchange Arbitrage Execution",
            "Intra-Exchange Arbitrage Execution",
            "Auto LP Machine",
            "AI Liquidity Supply"
        ],
        "🆓 Free": [
            f"{free_settings.get('main_board_interval_minutes', 60)} min",
            f"{free_settings.get('watchlist_interval_minutes', 30)} min",
            f"{free_settings.get('user_dashboard_interval_minutes', 60)} min",
            f"{free_settings.get('micro_burst_limit_per_day', 3)} times",
            f"{free_settings.get('watchlist_limit', 4)} tokens",
            "❌",
            "❌",
            "❌",
            "❌",
            "❌",
            "❌",
            "❌",
            "❌",
            "❌"
        ],
        "💎 Pro": [
            f"{pro_settings.get('main_board_interval_minutes', 15)} min",
            f"{pro_settings.get('watchlist_interval_minutes', 5)} min",
            f"{pro_settings.get('user_dashboard_interval_minutes', 1)} min",
            f"{pro_settings.get('micro_burst_limit_per_day', 999)} times",
            f"{pro_settings.get('watchlist_limit', 20)} tokens",
            "✅",
            "✅ Daily",
            "✅ Real-time",
            "✅ Telegram Bot",
            "✅ Opportunity Alerts",
            "❌",
            "❌",
            "❌",
            "❌"
        ],
        "🌟 Premium": [
            f"{premium_settings.get('main_board_interval_minutes', 5)} min",
            f"{premium_settings.get('watchlist_interval_minutes', 1)} min",
            f"{premium_settings.get('user_dashboard_interval_minutes', 1)} min",
            "Unlimited",
            f"{premium_settings.get('watchlist_limit', 100)} tokens",
            "✅",
            "✅ Real-time",
            "✅ AI-powered",
            "✅ Premium Bot",
            "✅ Auto Execution",
            "✅ Automated",
            "✅ Automated",
            "✅ Fully Automated",
            "✅ AI-powered 24/7"
        ]
    }
    
    import pandas as pd
    df = pd.DataFrame(comparison_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Pricing
    st.markdown("### 💰 Pricing")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🆓 Free**
        - $0/month
        - Basic monitoring
        - Limited updates
        """)
    
    with col2:
        st.markdown("""
        **💎 Pro**
        - $99/month
        - Advanced analytics
        - Custom thresholds
        """)
    
    with col3:
        st.markdown("""
        **🌟 Premium**
        - $2000/month
        - Auto LP Machine
        - AI-powered defense
        """)


def render_main_board_policy():
    """Render Main Board Policy Settings tab."""
    st.markdown("### 📋 Main Board Policy Settings")
    st.caption("Configure entry, exit criteria and minimum stay duration for Main Board tokens")
    
    # Load scanner config
    scanner_config_file = 'config/scanner_config.json'
    if os.path.exists(scanner_config_file):
        with open(scanner_config_file, 'r', encoding='utf-8') as f:
            scanner_config = json.load(f)
    else:
        scanner_config = {"global": {}}
    
    global_config = scanner_config.get('global', {})
    
    st.markdown("#### 📊 Data Processing Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        entry_history_days = st.selectbox(
            "📥 Entry Evaluation Period (days)",
            options=[1, 2, 3, 5, 7],
            index=[1, 2, 3, 5, 7].index(global_config.get('entry_history_days', 2)),
            help="Number of days of scan history required before a token can be posted to Main Board"
        )
        
        exit_history_days = st.selectbox(
            "📤 Exit Evaluation Period (days)",
            options=[3, 5, 7, 10, 14],
            index=[3, 5, 7, 10, 14].index(global_config.get('exit_history_days', 7)),
            help="Number of consecutive days with good grades (B- or higher) required for exit from Main Board"
        )
    
    with col2:
        min_stay_days = st.selectbox(
            "⏱️ Minimum Stay Duration (days)",
            options=[7, 10, 14, 21, 30],
            index=[7, 10, 14, 21, 30].index(global_config.get('min_stay_days', 14)),
            help="Minimum number of days a token must remain on Main Board before exit eligibility"
        )

        default_history_days = st.selectbox(
            "📈 Average Calculation Period (days)",
            options=[1, 2, 3, 5, 7],
            index=[1, 2, 3, 5, 7].index(global_config.get('default_history_days', 2)),
            help="Number of recent days used to calculate average risk and violation rates"
        )

    st.markdown("---")
    st.markdown("#### 📤 Exit Criteria")
    st.caption("Tokens can exit Main Board and move to Archive when violation rate improves")

    grad_col1, grad_col2 = st.columns(2)

    with grad_col1:
        st.info(f"""
        **Exit Evaluation (Current Implementation):**
        - System checks recent **{exit_history_days}-day** violation rate
        - If violation rate < 20%, token moves to ARCHIVED status
        - Tokens in ARCHIVED status are kept for additional 30 days

        **Note:** Entry History Days ({entry_history_days}) is used for MONITORING period
        """)

    with grad_col2:
        st.warning(f"""
        **Requirements:**
        - ✅ Minimum **{min_stay_days} days** on Main Board before exit eligible
        - ✅ Violation rate must drop below 20% in recent {exit_history_days} days
        - ✅ Automatic evaluation on every scan
        - ⚠️ Grade D/F can trigger re-entry to Main Board even from ARCHIVED status
        """)
    
    # Save button
    if st.button("💾 Save Main Board Policy", type="primary"):
        scanner_config['global']['entry_history_days'] = entry_history_days
        scanner_config['global']['exit_history_days'] = exit_history_days
        scanner_config['global']['min_stay_days'] = min_stay_days
        scanner_config['global']['default_history_days'] = default_history_days
        
        with open(scanner_config_file, 'w', encoding='utf-8') as f:
            json.dump(scanner_config, f, indent=2, ensure_ascii=False)
        
        st.success("✅ Main Board policy saved!")
        st.rerun()


def _get_default_subscription_config():
    """Get default subscription configuration."""
    return {
        "subscription_type": "free",
        "subscription_start": None,
        "subscription_end": None,
        "last_free_update": None,
        "free_update_interval_hours": 0.25,
        "users": {},
        "free": {
            "main_board_interval_minutes": 60,
            "watchlist_interval_minutes": 30,
            "user_dashboard_interval_minutes": 60,
            "micro_burst_limit_per_day": 3,
            "watchlist_limit": 2
        },
        "pro": {
            "main_board_interval_minutes": 15,
            "watchlist_interval_minutes": 5,
            "user_dashboard_interval_minutes": 1,
            "micro_burst_limit_per_day": 999,
            "watchlist_limit": 8
        },
        "premium": {
            "main_board_interval_minutes": 5,
            "watchlist_interval_minutes": 1,
            "user_dashboard_interval_minutes": 1,
            "micro_burst_limit_per_day": 9999,
            "watchlist_limit": 32
        },
        "system": {
            "monitoring_refresh_interval_seconds": 300,
            "accumulation_interval_seconds": 60,
            "micro_burst_duration_seconds": 5,
            "micro_burst_fetch_interval_seconds": 0.1
        }
    }
