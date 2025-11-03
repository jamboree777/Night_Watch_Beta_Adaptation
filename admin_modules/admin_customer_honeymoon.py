"""
User Management
Complete user management including accounts, subscriptions, and token data
"""
import streamlit as st
import json
import os
import time
from datetime import datetime, timezone
from modules.admin_honeymoon_manager import get_admin_honeymoon_manager


def render_customer_honeymoon_management():
    """Unified User Management UI"""
    st.title("👥 User Management")
    st.caption("Manage users, subscriptions, token data, and evaluation criteria")

    # 탭 생성 - 6개 탭으로 확장
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👤 User Accounts",
        "➕ Add New User",
        "📊 User Token Data",
        "🔗 Wallet Tracking",
        "⚙️ Admin Defaults",
        "📈 Evaluation Criteria"
    ])

    with tab1:
        render_user_list()

    with tab2:
        render_add_new_user()

    with tab3:
        admin_manager = get_admin_honeymoon_manager()
        render_exchange_customer_data(admin_manager)

    with tab4:
        render_wallet_tracking_overview()

    with tab5:
        admin_manager = get_admin_honeymoon_manager()
        render_customer_settings_view(admin_manager)

    with tab6:
        admin_manager = get_admin_honeymoon_manager()
        render_global_settings_management(admin_manager)


def render_user_list():
    """User Accounts List & Management"""
    st.subheader("👤 User Accounts")
    st.caption("Manage users, subscriptions, and permissions")

    # users.json 로드
    users_file = "data/users.json"
    users = {}
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)

    if not users:
        st.info("📭 No users registered yet. Add users in the 'Add New User' tab.")
    else:
        st.markdown(f"### 📊 Total Users: {len(users)}")

        # 사용자 목록 표시
        for user_id, user_info in users.items():
            with st.expander(f"👤 {user_id} ({user_info.get('tier', 'free').upper()})"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown("**User Information:**")
                    st.write(f"- **User ID**: {user_id}")
                    st.write(f"- **Telegram**: @{user_info.get('telegram_username', 'N/A')}")
                    st.write(f"- **Current Tier**: {user_info.get('tier', 'free').upper()}")
                    st.write(f"- **Registered**: {user_info.get('registered_at', 'N/A')[:10]}")
                    st.write(f"- **Last Login**: {user_info.get('last_login', 'N/A')[:10]}")
                    st.write(f"- **Watchlist Items**: {len(user_info.get('watchlist', []))}")

                with col2:
                    st.markdown("**Actions:**")

                    # 구독 등급 변경
                    new_tier = st.selectbox(
                        "Change Tier:",
                        options=["free", "pro", "premium"],
                        index=["free", "pro", "premium"].index(user_info.get('tier', 'free')),
                        key=f"tier_{user_id}"
                    )

                    if st.button("💎 Update Tier", key=f"update_{user_id}"):
                        users[user_id]['tier'] = new_tier
                        with open(users_file, 'w', encoding='utf-8') as f:
                            json.dump(users, f, indent=2, ensure_ascii=False)
                        st.success(f"✅ {user_id} upgraded to {new_tier.upper()}!")
                        st.rerun()

                    if st.button("🗑️ Delete User", key=f"delete_{user_id}"):
                        if st.session_state.get(f'confirm_delete_{user_id}'):
                            del users[user_id]
                            with open(users_file, 'w', encoding='utf-8') as f:
                                json.dump(users, f, indent=2, ensure_ascii=False)
                            st.success(f"✅ User {user_id} deleted")
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_{user_id}'] = True
                            st.warning("⚠️ Click again to confirm deletion")

        # 통계
        st.markdown("---")
        st.markdown("### 📈 Statistics")
        tier_counts = {}
        for user in users.values():
            tier = user.get('tier', 'free')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        cols = st.columns(3)
        cols[0].metric("Free Users", tier_counts.get('free', 0))
        cols[1].metric("Pro Users", tier_counts.get('pro', 0))
        cols[2].metric("Premium Users", tier_counts.get('premium', 0))


def render_add_new_user():
    """Add New User UI"""
    st.subheader("➕ Add New User")
    st.caption("Create a new user account by entering their Telegram username")

    # users.json 로드
    users_file = "data/users.json"
    users = {}
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)

    col1, col2 = st.columns([2, 1])

    with col1:
        telegram_username = st.text_input(
            "Telegram Username",
            placeholder="Enter username (without @)",
            help="Enter the Telegram username without @ symbol",
            key="new_telegram_username"
        )

        user_tier = st.selectbox(
            "Initial Subscription Tier",
            options=["free", "pro", "premium"],
            index=0,
            key="new_user_tier"
        )

        st.markdown("**Initial Settings:**")
        st.write(f"- User ID: `{telegram_username.lower() if telegram_username else 'N/A'}`")
        st.write(f"- Telegram: `@{telegram_username if telegram_username else 'N/A'}`")
        st.write(f"- Tier: `{user_tier.upper()}`")
        st.write(f"- Watchlist: Empty (0 items)")

    with col2:
        st.write("")
        st.write("")
        st.write("")

        if st.button("➕ Create User", type="primary", use_container_width=True):
            if not telegram_username:
                st.error("❌ Please enter a Telegram username")
            elif telegram_username.lower() in users:
                st.error(f"❌ User @{telegram_username} already exists!")
            else:
                # 새 사용자 생성
                new_user = {
                    "user_id": telegram_username.lower(),
                    "telegram_username": telegram_username,
                    "telegram_chat_id": None,
                    "tier": user_tier,
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                    "last_login": datetime.now(timezone.utc).isoformat(),
                    "watchlist": [],
                    "alert_settings": {
                        "enabled": True,
                        "spread_threshold": 2.0,
                        "depth_threshold": 500,
                        "volume_threshold": 10000,
                        "alert_interval_minutes": 60
                    }
                }

                users[telegram_username.lower()] = new_user

                # 저장
                with open(users_file, 'w', encoding='utf-8') as f:
                    json.dump(users, f, indent=2, ensure_ascii=False)

                st.success(f"✅ User @{telegram_username} created successfully with {user_tier.upper()} tier!")
                st.info(f"💡 User can now log in with Telegram username: @{telegram_username}")
                st.balloons()

                time.sleep(2)
                st.rerun()


def render_exchange_customer_data(admin_manager):
    """User Input Data View UI"""
    st.subheader("📊 User Input Data (Reference Only)")
    st.caption("View token listing information entered by users - grouped by exchange")
    
    # 모든 고객의 토큰 설정 조회
    all_user_tokens = admin_manager.get_all_user_tokens()
    
    if not all_user_tokens:
        st.info("No honeymoon information set by customers.")
        return
    
    # 거래소별로 데이터 정리
    exchange_data = {}
    for user_id, user_tokens in all_user_tokens.items():
        for token in user_tokens:
            exchange = token['exchange']
            if exchange not in exchange_data:
                exchange_data[exchange] = []
            
            exchange_data[exchange].append({
                'user_id': user_id,
                'symbol': token['symbol'],
                'listing_date': token['listing_date'],
                'listing_price': token['listing_price'],
                'created_at': token['created_at'],
                'updated_at': token['updated_at']
            })
    
    # 거래소 선택
    exchange_list = list(exchange_data.keys())
    selected_exchange = st.selectbox(
        "Select Exchange",
        exchange_list,
        key="exchange_selector"
    )
    
    if selected_exchange:
        tokens = exchange_data[selected_exchange]
        
        st.markdown(f"### 📊 {selected_exchange.upper()} Exchange Customer Data")
        st.caption(f"Total {len(tokens)} customer settings")
        
        # 통계 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            unique_customers = len(set(token['user_id'] for token in tokens))
            st.metric("Unique Customers", unique_customers)
        
        with col2:
            unique_symbols = len(set(token['symbol'] for token in tokens))
            st.metric("Unique Symbols", unique_symbols)
        
        with col3:
            # 최근 7일 내 설정
            recent_count = 0
            for token in tokens:
                created_date = datetime.fromisoformat(token['created_at'].replace('Z', '+00:00'))
                days_ago = (datetime.now(timezone.utc) - created_date).days
                if days_ago <= 7:
                    recent_count += 1
            st.metric("Recent Settings (7 days)", recent_count)
        
        with col4:
            # 평균 상장가격
            if tokens:
                avg_price = sum(token['listing_price'] for token in tokens) / len(tokens)
                st.metric("Avg Listing Price", f"${avg_price:,.2f}")
        
        # 데이터 테이블
        st.markdown("---")
        st.subheader("📋 Detailed Data")
        
        # 데이터프레임으로 표시
        import pandas as pd
        
        df_data = []
        for token in tokens:
            df_data.append({
                'Customer ID': token['user_id'],
                'Symbol': token['symbol'],
                'Listing Date': token['listing_date'][:10],  # YYYY-MM-DD만 표시
                'Listing Price (USDT)': f"${token['listing_price']:,.8f}",
                'Created': token['created_at'][:16].replace('T', ' '),  # YYYY-MM-DD HH:MM만 표시
                'Updated': token['updated_at'][:16].replace('T', ' ')
            })
        
        df = pd.DataFrame(df_data)
        
        # 정렬 옵션
        sort_option = st.selectbox(
            "Sort By",
            ["Updated (Latest)", "Created (Latest)", "Listing Price (High)", "Listing Price (Low)", "Customer ID"],
            key="sort_option"
        )
        
        if sort_option == "Updated (Latest)":
            df = df.sort_values('Updated', ascending=False)
        elif sort_option == "Created (Latest)":
            df = df.sort_values('Created', ascending=False)
        elif sort_option == "Listing Price (High)":
            df = df.sort_values('Listing Price (USDT)', ascending=False)
        elif sort_option == "Listing Price (Low)":
            df = df.sort_values('Listing Price (USDT)', ascending=True)
        elif sort_option == "Customer ID":
            df = df.sort_values('Customer ID')
        
        # 페이지네이션
        page_size = 20
        total_pages = (len(df) + page_size - 1) // page_size
        
        if total_pages > 1:
            page = st.selectbox(
                "Page",
                range(1, total_pages + 1),
                key="page_selector"
            )
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            df_page = df.iloc[start_idx:end_idx]
        else:
            df_page = df
        
        st.dataframe(df_page, use_container_width=True)
        
        if total_pages > 1:
            st.caption(f"Page {page} / {total_pages} (Total {len(df)} items)")
        
        # 심볼별 집계
        st.markdown("---")
        st.subheader("📈 Symbol Summary")
        
        symbol_stats = {}
        for token in tokens:
            symbol = token['symbol']
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'count': 0,
                    'prices': [],
                    'customers': set()
                }
            symbol_stats[symbol]['count'] += 1
            symbol_stats[symbol]['prices'].append(token['listing_price'])
            symbol_stats[symbol]['customers'].add(token['user_id'])
        
        # 심볼별 통계 표시
        symbol_df_data = []
        for symbol, stats in symbol_stats.items():
            symbol_df_data.append({
                'Symbol': symbol,
                'Settings Count': stats['count'],
                'Unique Customers': len(stats['customers']),
                'Max Listing Price': f"${max(stats['prices']):,.8f}",
                'Min Listing Price': f"${min(stats['prices']):,.8f}",
                'Avg Listing Price': f"${sum(stats['prices'])/len(stats['prices']):,.8f}"
            })
        
        symbol_df = pd.DataFrame(symbol_df_data)
        symbol_df = symbol_df.sort_values('Settings Count', ascending=False)
        
        st.dataframe(symbol_df, use_container_width=True)
        
        # CSV 다운로드 버튼
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"{selected_exchange}_customer_data.csv",
            mime="text/csv"
        )


def render_customer_settings_view(admin_manager):
    """Admin Defaults Management UI"""
    st.subheader("⚙️ Admin Defaults Management")
    st.caption("Set default listing values for exchanges - used when user data not available")
    
    # 모든 고객의 토큰 설정 조회
    all_user_tokens = admin_manager.get_all_user_tokens()
    
    if not all_user_tokens:
        st.info("No honeymoon information set by customers.")
        return
    
    # 고객 선택
    customer_list = list(all_user_tokens.keys())
    selected_customer = st.selectbox(
        "Select Customer",
        customer_list,
        key="customer_selector"
    )
    
    if selected_customer:
        user_tokens = all_user_tokens[selected_customer]
        
        st.markdown(f"### 📋 {selected_customer}'s Honeymoon Settings")
        st.caption(f"Total {len(user_tokens)} token settings")
        
        # 토큰 목록 표시
        for token in user_tokens:
            with st.expander(f"**{token['exchange'].upper()}** - {token['symbol']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### Basic Information")
                    st.text(f"Exchange: {token['exchange'].upper()}")
                    st.text(f"Symbol: {token['symbol']}")
                    st.text(f"Listing Price: ${token['listing_price']:,.8f} USDT")
                    st.text(f"Listing Date: {token['listing_date']}")
                
                with col2:
                    st.markdown("##### Settings Information")
                    st.text(f"Created: {token['created_at']}")
                    st.text(f"Updated: {token['updated_at']}")
                    
                    # 전역 설정과 비교
                    global_status = admin_manager.get_global_token_honeymoon_status(
                        token['exchange'], token['symbol']
                    )
                    
                    if global_status['status'] == 'not_configured':
                        st.warning("⚠️ Not in Global Settings")
                    else:
                        st.success("✅ In Global Settings")
                        st.text(f"Global Listing Date: {global_status.get('listing_date', 'N/A')}")
                        st.text(f"Global Listing Price: ${global_status.get('listing_price', 0):,.8f} USDT")
        
        # 고객 설정 요약
        st.markdown("---")
        st.markdown("##### 📊 Settings Summary")
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            st.metric("Total Tokens", len(user_tokens))
        
        with summary_col2:
            # 전역 설정과 일치하는 토큰 수
            matching_count = 0
            for token in user_tokens:
                global_status = admin_manager.get_global_token_honeymoon_status(
                    token['exchange'], token['symbol']
                )
                if global_status['status'] != 'not_configured':
                    matching_count += 1
            st.metric("Global Settings Match", f"{matching_count}/{len(user_tokens)}")
        
        with summary_col3:
            # 최근 설정된 토큰 수 (7일 이내)
            recent_count = 0
            for token in user_tokens:
                created_date = datetime.fromisoformat(token['created_at'].replace('Z', '+00:00'))
                days_ago = (datetime.now(timezone.utc) - created_date).days
                if days_ago <= 7:
                    recent_count += 1
            st.metric("Recent Settings (7 days)", recent_count)


def render_global_settings_management(admin_manager):
    """Evaluation Criteria Management UI"""
    st.subheader("📈 Evaluation Criteria Management")
    st.caption("Set token evaluation criteria and thresholds")
    
    # 전역 토큰 목록
    global_tokens = admin_manager.get_all_global_tokens_status()
    
    # 새 전역 토큰 추가
    with st.expander("➕ Add New Global Token", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            exchange = st.selectbox(
                "Exchange",
                ["gateio", "mexc", "kucoin", "bitget"],
                key="global_exchange"
            )
            symbol = st.text_input(
                "Symbol",
                placeholder="e.g. BTC/USDT",
                key="global_symbol"
            )
        
        with col2:
            listing_date = st.date_input(
                "Listing Date",
                value=datetime.now().date(),
                key="global_listing_date"
            )
            listing_price = st.number_input(
                "Listing Price (USDT)",
                min_value=0.0,
                value=1.0,
                step=0.000001,
                format="%.8f",
                key="global_listing_price"
            )
        
        if st.button("💾 Save Global Settings", type="primary"):
            if symbol and listing_price > 0:
                success = admin_manager.set_global_token_listing(
                    exchange=exchange,
                    symbol=symbol,
                    listing_date=listing_date.isoformat(),
                    listing_price=listing_price
                )
                
                if success:
                    st.success(f"✅ {exchange.upper()} {symbol} global settings saved!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save.")
            else:
                st.error("❌ Please fill in all fields.")
    
    # 전역 토큰 목록
    st.markdown("---")
    st.subheader("📋 Global Token List")
    
    if not global_tokens:
        st.info("No global tokens configured.")
    else:
        for token in global_tokens:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    st.text(f"**{token['exchange'].upper()}** - {token['symbol']}")
                
                with col2:
                    if token['status'] == 'not_configured':
                        st.text("❌ Not Configured")
                    elif token['status'] == 'error':
                        st.text(f"❌ Error: {token.get('error', 'Unknown')}")
                    else:
                        days_since = token['days_since_listing']
                        days_remaining = token['days_remaining']
                        st.text(f"Days since listing: {days_since}")
                        if days_remaining > 0:
                            st.text(f"Honeymoon {days_remaining} days left")
                        else:
                            st.text("Honeymoon ended")
                
                with col3:
                    if token['status'] not in ['not_configured', 'error']:
                        price_drop = token['price_drop_pct']
                        if price_drop >= token['threshold_price_pct']:
                            st.text(f"⚠️ {price_drop:.1f}% drop")
                        else:
                            st.text(f"✅ {price_drop:.1f}% drop")
                
                with col4:
                    if st.button("🗑️", key=f"delete_global_{token['token_key']}", help="Delete"):
                        admin_manager.delete_global_token(token['exchange'], token['symbol'])
                        st.rerun()
                
                st.markdown("---")
    
    # 전역 임계값 설정
    st.markdown("---")
    st.subheader("⚙️ Global Threshold Settings")
    
    config = admin_manager.get_config_summary()
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_days = config['global_threshold_days']
        new_days = st.number_input(
            "Honeymoon Threshold (days)",
            min_value=30,
            max_value=730,
            value=current_days,
            step=30,
            help="Period after listing to be considered honeymoon"
        )
        
        if st.button("💾 Save Honeymoon Period"):
            admin_manager.update_global_thresholds(threshold_days=new_days)
            st.success(f"✅ Honeymoon period set to {new_days} days!")
            st.rerun()
    
    with col2:
        current_pct = config['global_price_drop_threshold_pct']
        new_pct = st.number_input(
            "Price Drop Threshold (%)",
            min_value=0.1,
            max_value=50.0,
            value=current_pct,
            step=0.1,
            help="Percentage drop from listing price to classify as high risk"
        )
        
        if st.button("💾 Save Price Threshold"):
            admin_manager.update_global_thresholds(price_drop_threshold_pct=new_pct)
            st.success(f"✅ Price drop threshold set to {new_pct}%!")
            st.rerun()


def render_statistics_analysis(admin_manager):
    """Statistics and Analysis UI"""
    st.subheader("📊 Statistics and Analysis")
    
    # 모든 고객의 토큰 설정 조회
    all_user_tokens = admin_manager.get_all_user_tokens()
    global_tokens = admin_manager.get_all_global_tokens_status()
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Customers", len(all_user_tokens))
    
    with col2:
        total_user_tokens = sum(len(tokens) for tokens in all_user_tokens.values())
        st.metric("Total Customer Settings", total_user_tokens)
    
    with col3:
        st.metric("Global Settings", len(global_tokens))
    
    with col4:
        # 전역 설정과 일치하는 고객 설정 비율
        matching_count = 0
        for user_tokens in all_user_tokens.values():
            for token in user_tokens:
                global_status = admin_manager.get_global_token_honeymoon_status(
                    token['exchange'], token['symbol']
                )
                if global_status['status'] != 'not_configured':
                    matching_count += 1
        
        if total_user_tokens > 0:
            match_rate = (matching_count / total_user_tokens) * 100
            st.metric("Global Settings Match Rate", f"{match_rate:.1f}%")
        else:
            st.metric("Global Settings Match Rate", "0%")
    
    # 거래소별 통계
    st.markdown("---")
    st.subheader("🏢 Exchange Statistics")
    
    exchange_stats = {}
    for user_tokens in all_user_tokens.values():
        for token in user_tokens:
            exchange = token['exchange']
            if exchange not in exchange_stats:
                exchange_stats[exchange] = 0
            exchange_stats[exchange] += 1
    
    if exchange_stats:
        for exchange, count in exchange_stats.items():
            st.text(f"{exchange.upper()}: {count} settings")
    
    # 최근 활동
    st.markdown("---")
    st.subheader("📈 Recent Activity")
    
    recent_activities = []
    for user_id, user_tokens in all_user_tokens.items():
        for token in user_tokens:
            recent_activities.append({
                'user_id': user_id,
                'exchange': token['exchange'],
                'symbol': token['symbol'],
                'created_at': token['created_at'],
                'updated_at': token['updated_at']
            })
    
    # 최근 10개 활동 표시
    recent_activities.sort(key=lambda x: x['updated_at'], reverse=True)

    for activity in recent_activities[:10]:
        st.text(f"{activity['user_id']}: {activity['exchange'].upper()} {activity['symbol']} ({activity['updated_at']})")


def render_wallet_tracking_overview():
    """Customer Wallet Tracking Overview UI"""
    st.subheader("🔗 Customer Wallet Tracking Overview")
    st.caption("View all customer wallet tracking information and exchange deposit totals")

    import pandas as pd
    from pathlib import Path

    # Load all users' tracked wallets
    user_data_dir = Path("user_data")
    if not user_data_dir.exists():
        st.info("📭 No user data found.")
        return

    all_wallet_data = {}

    for user_dir in user_data_dir.iterdir():
        if user_dir.is_dir():
            user_id = user_dir.name
            wallet_file = user_dir / "tracked_wallets.json"

            if wallet_file.exists():
                try:
                    with open(wallet_file, 'r', encoding='utf-8') as f:
                        all_wallet_data[user_id] = json.load(f)
                except:
                    continue

    if not all_wallet_data:
        st.info("📭 No customers are tracking wallets yet.")
        return

    # Aggregate data
    total_customers = len(all_wallet_data)
    total_tokens = sum(len(wallets) for wallets in all_wallet_data.values())
    total_wallets = 0
    exchange_aggregation = {}

    for user_id, user_wallets in all_wallet_data.items():
        for token_key, tracking_config in user_wallets.items():
            tracked_wallets = tracking_config.get('tracked_wallets', [])
            total_wallets += len(tracked_wallets)

            for wallet in tracked_wallets:
                exchange = wallet.get('exchange', 'unknown')

                if exchange not in exchange_aggregation:
                    exchange_aggregation[exchange] = {
                        'wallet_count': 0,
                        'wallets': [],
                        'total_balance': 0.0,
                        'tokens': set()
                    }

                exchange_aggregation[exchange]['wallet_count'] += 1
                exchange_aggregation[exchange]['wallets'].append({
                    'user_id': user_id,
                    'token': token_key,
                    'address': wallet.get('address'),
                    'label': wallet.get('label'),
                    'added_at': wallet.get('added_at')
                })
                exchange_aggregation[exchange]['tokens'].add(token_key)

    # Overall statistics
    st.markdown("### 📊 Overall Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Customers Tracking", total_customers)

    with col2:
        st.metric("🪙 Tokens Being Tracked", total_tokens)

    with col3:
        st.metric("👛 Total Wallets", total_wallets)

    with col4:
        st.metric("🏢 Exchanges", len(exchange_aggregation))

    # Exchange Aggregation View
    st.markdown("---")
    st.markdown("### 🏢 Exchange Deposit Totals")
    st.caption("Aggregated deposit amounts by exchange (latest balances)")

    if not exchange_aggregation:
        st.info("No exchange data available.")
    else:
        # Calculate latest balances for each exchange
        for exchange, data in exchange_aggregation.items():
            total_balance = 0.0
            wallet_details = []

            for wallet_info in data['wallets']:
                user_id = wallet_info['user_id']
                token_key = wallet_info['token']
                address = wallet_info['address']

                # Get latest balance from history file
                safe_address = address.replace('0x', '').lower()
                history_file = Path("user_data") / user_id / "wallet_history" / f"{token_key}_{safe_address}.jsonl"

                latest_balance = 0.0
                if history_file.exists():
                    try:
                        with open(history_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            if lines:
                                last_entry = json.loads(lines[-1])
                                latest_balance = last_entry.get('balance', 0.0)
                    except:
                        pass

                total_balance += latest_balance
                wallet_details.append({
                    **wallet_info,
                    'balance': latest_balance
                })

            exchange_aggregation[exchange]['total_balance'] = total_balance
            exchange_aggregation[exchange]['wallet_details'] = wallet_details

        # Sort by total balance (descending)
        sorted_exchanges = sorted(exchange_aggregation.items(), key=lambda x: x[1]['total_balance'], reverse=True)

        for exchange, data in sorted_exchanges:
            with st.expander(f"🏢 **{exchange.upper()}** - {data['wallet_count']} wallets | Total: {data['total_balance']:,.2f} tokens", expanded=False):
                st.markdown(f"**Tracked Tokens:** {', '.join(sorted(data['tokens']))}")
                st.markdown(f"**Total Deposit Amount:** {data['total_balance']:,.8f} tokens")
                st.markdown(f"**Wallet Count:** {data['wallet_count']}")

                st.markdown("---")
                st.markdown("#### 📋 Wallet Details")

                # Display wallet details table
                wallet_df_data = []
                for wallet in data['wallet_details']:
                    wallet_df_data.append({
                        'Customer': wallet['user_id'],
                        'Token': wallet['token'],
                        'Label': wallet['label'],
                        'Address': wallet['address'][:10] + '...' + wallet['address'][-8:],
                        'Balance': f"{wallet['balance']:,.2f}",
                        'Added': wallet['added_at'][:10] if wallet['added_at'] else 'N/A'
                    })

                if wallet_df_data:
                    wallet_df = pd.DataFrame(wallet_df_data)
                    st.dataframe(wallet_df, use_container_width=True)
                else:
                    st.info("No wallet details available.")

    # Customer-by-Customer View
    st.markdown("---")
    st.markdown("### 👤 Customer-by-Customer Breakdown")

    customer_selector = st.selectbox(
        "Select Customer",
        options=list(all_wallet_data.keys()),
        key="wallet_customer_selector"
    )

    if customer_selector:
        user_wallets = all_wallet_data[customer_selector]

        st.markdown(f"#### 📊 {customer_selector}'s Wallet Tracking")

        if not user_wallets:
            st.info("This customer hasn't configured any wallet tracking yet.")
        else:
            for token_key, tracking_config in user_wallets.items():
                contract_address = tracking_config.get('contract_address', 'N/A')
                chain = tracking_config.get('chain', 'N/A')
                tracked_wallets = tracking_config.get('tracked_wallets', [])
                monitoring_enabled = tracking_config.get('monitoring_enabled', True)

                status_badge = "✅ Active" if monitoring_enabled else "⏸️ Paused"

                with st.expander(f"🪙 **{token_key}** ({chain}) - {len(tracked_wallets)} wallets | {status_badge}", expanded=False):
                    st.markdown(f"**Contract Address:** `{contract_address}`")
                    st.markdown(f"**Chain:** {chain}")
                    st.markdown(f"**Monitoring:** {status_badge}")
                    st.markdown(f"**Wallets Tracked:** {len(tracked_wallets)}")

                    if tracked_wallets:
                        st.markdown("---")
                        st.markdown("**Tracked Wallets:**")

                        wallet_detail_df = []
                        for wallet in tracked_wallets:
                            address = wallet.get('address')
                            label = wallet.get('label')
                            exchange = wallet.get('exchange')
                            added_at = wallet.get('added_at', 'N/A')

                            # Get latest balance
                            safe_address = address.replace('0x', '').lower()
                            history_file = Path("user_data") / customer_selector / "wallet_history" / f"{token_key}_{safe_address}.jsonl"

                            latest_balance = 0.0
                            last_updated = 'Never'
                            if history_file.exists():
                                try:
                                    with open(history_file, 'r', encoding='utf-8') as f:
                                        lines = f.readlines()
                                        if lines:
                                            last_entry = json.loads(lines[-1])
                                            latest_balance = last_entry.get('balance', 0.0)
                                            last_updated = last_entry.get('timestamp', 'N/A')[:16]
                                except:
                                    pass

                            wallet_detail_df.append({
                                'Label': label,
                                'Exchange': exchange.upper(),
                                'Address': address[:10] + '...' + address[-8:],
                                'Balance': f"{latest_balance:,.2f}",
                                'Last Updated': last_updated,
                                'Added': added_at[:10] if added_at else 'N/A'
                            })

                        if wallet_detail_df:
                            df = pd.DataFrame(wallet_detail_df)
                            st.dataframe(df, use_container_width=True)

    # Export functionality
    st.markdown("---")
    st.markdown("### 📥 Export Data")

    if st.button("📊 Generate CSV Export"):
        # Generate comprehensive CSV with all wallet data
        export_data = []

        for user_id, user_wallets in all_wallet_data.items():
            for token_key, tracking_config in user_wallets.items():
                for wallet in tracking_config.get('tracked_wallets', []):
                    address = wallet.get('address')
                    safe_address = address.replace('0x', '').lower()
                    history_file = Path("user_data") / user_id / "wallet_history" / f"{token_key}_{safe_address}.jsonl"

                    latest_balance = 0.0
                    last_updated = 'Never'
                    if history_file.exists():
                        try:
                            with open(history_file, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                if lines:
                                    last_entry = json.loads(lines[-1])
                                    latest_balance = last_entry.get('balance', 0.0)
                                    last_updated = last_entry.get('timestamp', 'N/A')
                        except:
                            pass

                    export_data.append({
                        'Customer': user_id,
                        'Token': token_key,
                        'Chain': tracking_config.get('chain', 'N/A'),
                        'Contract': tracking_config.get('contract_address', 'N/A'),
                        'Exchange': wallet.get('exchange', 'N/A'),
                        'Wallet_Label': wallet.get('label', 'N/A'),
                        'Wallet_Address': address,
                        'Latest_Balance': latest_balance,
                        'Last_Updated': last_updated,
                        'Added_At': wallet.get('added_at', 'N/A')
                    })

        if export_data:
            export_df = pd.DataFrame(export_data)
            csv = export_df.to_csv(index=False, encoding='utf-8-sig')

            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"wallet_tracking_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            st.success(f"✅ Export ready! {len(export_data)} wallet entries.")
        else:
            st.warning("No data to export.")
