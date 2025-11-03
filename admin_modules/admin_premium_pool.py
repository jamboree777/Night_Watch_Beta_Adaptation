"""
Premium Pool Management Module for Admin Dashboard
Manages the 200-token premium watch pool with 1-minute snapshots
"""

import streamlit as st
import json
import os
from datetime import datetime, timezone
from modules.token_manager import TokenManager
import pandas as pd


def load_users():
    """Load users.json"""
    if os.path.exists('data/users.json'):
        with open('data/users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def render_premium_pool():
    """Render Premium Pool Management"""
    
    st.markdown("## 💎 Premium Pool (200) Management")
    st.markdown("""
    **유료 고객 VIP 서비스용 토큰 풀 관리**
    
    이 풀에 포함된 토큰은 다음의 고급 모니터링 서비스를 제공받습니다:
    - ⚡ **1분 단위 실시간 스냅샷 수집**
    - 🔬 **Micro Burst 분석** (0.05초 간격, 100프레임)
    - 📊 **고급 유동성 메트릭** (Quote Persistence, HHI, Imbalance, Layering Gap, Touch Flip Count)
    - 📈 **1개월 데이터 보관 및 DB 다운로드**
    - 🚨 **Telegram 실시간 알림**
    
    ---
    """)
    
    # Token Manager 초기화
    tm = TokenManager()
    
    # 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 All Users Watchlist",
        "📊 Premium Pool (200)",
        "➕ Add from Main Board",
        "🔍 Manual Search"
    ])
    
    # ===== Tab 1: All Users Watchlist =====
    with tab1:
        render_add_from_user_watchlists(tm)
    
    # ===== Tab 2: Premium Pool (200) =====
    with tab2:
        render_current_pool(tm)
    
    # ===== Tab 3: Add from Main Board =====
    with tab3:
        render_add_from_main_board(tm)
    
    # ===== Tab 4: Manual Search =====
    with tab4:
        render_manual_search(tm)


def render_current_pool(tm: TokenManager):
    """현재 프리미엄 풀 표시 및 관리"""
    st.markdown("### 📊 Premium Pool (200) - Active VIP Tokens")
    st.markdown("""
    **💎 유료 고객 서비스용 집중 모니터링 풀 (관리자 + Pro/Premium 유저 워치리스트)**
    
    이 풀에 포함된 토큰은 다음의 고급 서비스가 자동 활성화됩니다:
    
    - ⚡ **1분 단위 스냅샷 수집** (vs 메인보드 2시간)
    - 🔬 **Micro Burst 분석** (0.05초 간격, 100프레임)
    - 📊 **고급 유동성 메트릭** (Quote Persistence, HHI, Imbalance, Layering Gap, Touch Flip)
    - 📈 **1개월 데이터 보관** 및 DB 다운로드
    - 🚨 **Telegram 실시간 알림**
    - 🔒 **최대 200개 제한** (리소스 집중 관리)
    
    ---
    
    **💡 Tip:** 
    - Tab 1 (All Users Watchlist)에서 인기 토큰을 확인 후 여기에 추가하세요.
    - Tab 3/4에서 메인보드 토큰이나 수동 검색으로도 추가 가능합니다.
    
    ---
    """)
    
    # 프리미엄 풀 토큰 가져오기
    pool_tokens = tm.get_premium_pool_tokens()
    
    if not pool_tokens:
        st.info("⚠️ Premium Pool is empty. Add tokens from other tabs.")
        return
    
    st.success(f"✅ **{len(pool_tokens)} / 200** tokens in pool")
    
    # 데이터프레임 생성
    rows = []
    for token_id, token_data in pool_tokens.items():
        # 현재 스냅샷 데이터
        snap = token_data.get('current_snapshot', {})
        
        # 와처 수
        watcher_count = len(token_data.get('watchers', []))
        
        # 프리미엄 풀 정보
        pool_info = token_data.get('premium_pool', {})
        added_at = pool_info.get('added_at', 'N/A')
        added_by = pool_info.get('added_by', 'unknown')
        
        rows.append({
            'Token ID': token_id,
            'Exchange': token_data.get('exchange', 'N/A'),
            'Symbol': token_data.get('symbol', 'N/A'),
            'Spread %': snap.get('spread_pct'),
            'Depth $': snap.get('depth_2pct_usd'),
            'Volume $': snap.get('volume_24h_usd'),
            'Watchers': watcher_count,
            'Added': added_at[:10] if isinstance(added_at, str) and len(added_at) > 10 else added_at,
            'By': added_by
        })
    
    df = pd.DataFrame(rows)
    
    # 정렬 옵션
    sort_col = st.selectbox(
        "Sort by:",
        ['Watchers', 'Exchange', 'Symbol', 'Spread %', 'Depth $', 'Added'],
        key='pool_sort'
    )
    
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=(sort_col != 'Watchers'))
    
    # 데이터프레임 표시
    st.dataframe(df, use_container_width=True, height=400)
    
    # 선택적 삭제
    st.markdown("---")
    st.markdown("### 🗑️ Remove from Pool")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        tokens_to_remove = st.multiselect(
            "Select tokens to remove:",
            options=list(pool_tokens.keys()),
            format_func=lambda x: f"{pool_tokens[x].get('exchange')}/{pool_tokens[x].get('symbol')}",
            key='remove_pool_tokens'
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Remove Selected", type="primary", disabled=not tokens_to_remove, key="remove_selected_from_pool"):
            for token_id in tokens_to_remove:
                tm.remove_from_premium_pool(token_id)
            st.success(f"✅ Removed {len(tokens_to_remove)} token(s) from pool")
            st.rerun()


def render_add_from_main_board(tm: TokenManager):
    """메인보드 토큰에서 프리미엄 풀에 추가"""
    st.markdown("### ➕ Add from Main Board")
    st.markdown("""
    **메인보드의 고위험 토큰을 Premium Pool (200)에 추가합니다.**
    
    - Grade F/D/C 등 델리스팅 위험이 높은 토큰 선별
    - 선택한 토큰 → Premium Pool (Tab 2)에 추가 → 1분 스냅샷 활성화
    
    ---
    """)
    
    # Grade 필터
    selected_grades = st.multiselect(
        "Filter by Grade:",
        ['F', 'D', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+'],
        default=['F', 'D', 'C-'],
        key='mainboard_grade_filter'
    )
    
    # Main Board 토큰 가져오기
    all_tokens = tm.get_all_tokens()
    main_board_tokens = {
        tid: tdata for tid, tdata in all_tokens.items()
        if tdata.get('lifecycle', {}).get('status') == 'MAIN_BOARD'
    }
    
    # Grade 필터 적용
    filtered_tokens = {}
    for tid, tdata in main_board_tokens.items():
        grade = tdata.get('scan_aggregate', {}).get('grade', 'N/A')
        if grade in selected_grades:
            filtered_tokens[tid] = tdata
    
    if not filtered_tokens:
        st.info(f"No tokens found with grades: {', '.join(selected_grades)}")
        return
    
    st.info(f"📊 Found {len(filtered_tokens)} tokens")
    
    # 이미 프리미엄 풀에 있는 토큰 체크
    pool_tokens = tm.get_premium_pool_tokens()
    already_in_pool = set(pool_tokens.keys())
    
    # 데이터프레임 생성
    rows = []
    for tid, tdata in filtered_tokens.items():
        scan = tdata.get('scan_aggregate', {})
        in_pool = tid in already_in_pool
        
        rows.append({
            'Token ID': tid,
            'Exchange': tdata.get('exchange'),
            'Symbol': tdata.get('symbol'),
            'Grade': scan.get('grade', 'N/A'),
            'Risk %': f"{scan.get('average_risk', 0) * 100:.1f}",
            'Violation %': f"{scan.get('violation_rate', 0) * 100:.1f}",
            'In Pool': '✅' if in_pool else '❌'
        })
    
    df = pd.DataFrame(rows)
    
    # 필터링 옵션 추가
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        exchange_filter = st.multiselect(
            "Filter by Exchange:",
            options=sorted(set(r['Exchange'] for r in rows)),
            default=sorted(set(r['Exchange'] for r in rows)),
            key='mainboard_exchange_filter'
        )
    with col_f2:
        grade_filter = st.multiselect(
            "Filter by Grade:",
            options=sorted(set(r['Grade'] for r in rows)),
            default=sorted(set(r['Grade'] for r in rows)),
            key='mainboard_grade_display_filter'
        )
    with col_f3:
        pool_status_filter = st.selectbox(
            "Pool Status:",
            ['All', 'Not in Pool', 'Already in Pool'],
            key='mainboard_pool_status_filter'
        )
    
    # 필터 적용
    df_filtered = df.copy()
    if exchange_filter:
        df_filtered = df_filtered[df_filtered['Exchange'].isin(exchange_filter)]
    if grade_filter:
        df_filtered = df_filtered[df_filtered['Grade'].isin(grade_filter)]
    if pool_status_filter == 'Not in Pool':
        df_filtered = df_filtered[df_filtered['In Pool'] == '❌']
    elif pool_status_filter == 'Already in Pool':
        df_filtered = df_filtered[df_filtered['In Pool'] == '✅']
    
    st.dataframe(df_filtered, use_container_width=True, height=300)
    
    # 추가 기능
    st.markdown("---")
    
    # 프리미엄 풀에 없는 토큰만 선택 가능
    available_tokens = {tid: tdata for tid, tdata in filtered_tokens.items() if tid not in already_in_pool}
    
    if not available_tokens:
        st.warning("⚠️ All tokens are already in the premium pool.")
        return
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        tokens_to_add = st.multiselect(
            "Select tokens to add:",
            options=list(available_tokens.keys()),
            format_func=lambda x: f"{available_tokens[x].get('exchange')}/{available_tokens[x].get('symbol')} (Grade {available_tokens[x].get('scan_aggregate', {}).get('grade', 'N/A')})",
            key='add_from_mainboard'
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add Selected", type="primary", disabled=not tokens_to_add, key="add_selected_from_mainboard"):
            success_count = 0
            for token_id in tokens_to_add:
                if tm.add_to_premium_pool(token_id, added_by="admin"):
                    success_count += 1
            st.success(f"✅ Added {success_count}/{len(tokens_to_add)} token(s) to premium pool. 1-minute snapshot collection will start automatically.")
            st.rerun()


def render_add_from_user_watchlists(tm: TokenManager):
    """관리자 + 사용자 와치리스트 통합"""
    st.markdown("### 👥 All Users Watchlist (💎 Paid + 🆓 Free)")
    st.markdown("""
    **전체 사용자의 워치리스트를 통합하여 표시합니다.**
    
    - 💎 **Paid Users (Pro + Premium)**: 유료 사용자
    - 🆓 **Free Users**: 무료 사용자
    - 📊 **목적**: 인기 토큰 발견, 트렌드 분석, 마케팅 인사이트
    
    ---
    
    **💡 Workflow:**
    1. 이 탭에서 전체 사용자의 관심 토큰 확인
    2. 💎 Paid 사용자가 많이 보는 토큰 = 유료 고객 우선 관심사
    3. 🆓 Free 사용자가 많이 보는 토큰 = 유료 전환 마케팅 기회
    4. 선택한 토큰을 **Premium Pool (200)** (Tab 2)에 추가
    5. → 1분 스냅샷 + Micro Burst 분석 자동 활성화
    
    ---
    """)
    
    # users.json 로드
    users = load_users()
    
    if not users:
        st.warning("⚠️ No users found in users.json")
        return
    
    # 모든 사용자의 워치리스트 수집 (관리자 포함)
    watchlist_aggregation = {}  # {token_id: {'exchange': str, 'symbol': str, 'watchers': [user_ids]}}
    
    for user_id, user_data in users.items():
        watchlist = user_data.get('watchlist', [])
        for item in watchlist:
            exchange = item.get('exchange', '').lower()
            symbol = item.get('symbol', '')
            
            if exchange and symbol:
                token_id = f"{exchange}_{symbol.replace('/', '_').lower()}"
                
                if token_id not in watchlist_aggregation:
                    watchlist_aggregation[token_id] = {
                        'exchange': exchange,
                        'symbol': symbol,
                        'watchers': []
                    }
                
                # 중복 방지
                if user_id not in watchlist_aggregation[token_id]['watchers']:
                    watchlist_aggregation[token_id]['watchers'].append(user_id)
    
    if not watchlist_aggregation:
        st.info("⚠️ No tokens found in any watchlist.")
        return
    
    # 프리미엄 풀에 이미 있는 토큰
    pool_tokens = tm.get_premium_pool_tokens()
    already_in_pool = set(pool_tokens.keys())
    
    # 통계 표시
    total_unique_tokens = len(watchlist_aggregation)
    total_watchers = len([u for u in users if users[u].get('watchlist')])
    admin_count = sum(1 for u in users if users[u].get('is_admin', False))
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("📊 Unique Tokens", total_unique_tokens)
    with col_stat2:
        st.metric("👥 Active Watchers", total_watchers)
    with col_stat3:
        st.metric("👑 Admins", admin_count)
    
    st.markdown("---")
    
    # 최소 와처 수 필터
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        min_watchers = st.slider(
            "Minimum watchers:",
            min_value=1,
            max_value=20,
            value=1,
            key='min_watchers_filter'
        )
    
    with col_f2:
        exchange_options = sorted(set(data['exchange'].upper() for data in watchlist_aggregation.values()))
        exchange_filter = st.multiselect(
            "Filter by Exchange:",
            options=exchange_options,
            default=exchange_options,
            key='watchlist_exchange_filter'
        )
    
    with col_f3:
        pool_status = st.selectbox(
            "Pool Status:",
            ['All', 'Not in Pool', 'In Pool'],
            key='watchlist_pool_status'
        )
    
    # 데이터프레임 생성
    rows = []
    for token_id, data in watchlist_aggregation.items():
        watcher_count = len(data['watchers'])
        
        # 필터 적용
        if watcher_count < min_watchers:
            continue
        
        if exchange_filter and data['exchange'].upper() not in exchange_filter:
            continue
        
        in_pool = token_id in already_in_pool
        
        if pool_status == 'Not in Pool' and in_pool:
            continue
        elif pool_status == 'In Pool' and not in_pool:
            continue
        
        # 토큰 정보 가져오기
        token = tm.get_token_by_id(token_id)
        grade = 'N/A'
        risk = 0
        
        if token:
            scan = token.get('scan_aggregate', {})
            grade = scan.get('grade', 'N/A')
            risk = scan.get('average_risk', 0) * 100
        
        # 와처를 Free vs Paid로 분류
        free_watchers = []
        paid_watchers = []
        
        for watcher_id in data['watchers']:
            user_info = users.get(watcher_id, {})
            tier = user_info.get('tier', 'free')
            
            if tier in ['pro', 'premium']:
                paid_watchers.append(watcher_id)
            else:
                free_watchers.append(watcher_id)
        
        free_count = len(free_watchers)
        paid_count = len(paid_watchers)
        
        # 와처 리스트 미리보기 (Free와 Paid 구분)
        watcher_details = []
        
        # Paid 사용자 먼저 표시 (최대 3명)
        if paid_watchers:
            paid_preview = ', '.join(paid_watchers[:3])
            if len(paid_watchers) > 3:
                paid_preview += f" (+{len(paid_watchers) - 3})"
            watcher_details.append(f"💎 {paid_preview}")
        
        # Free 사용자 표시 (최대 3명)
        if free_watchers:
            free_preview = ', '.join(free_watchers[:3])
            if len(free_watchers) > 3:
                free_preview += f" (+{len(free_watchers) - 3})"
            watcher_details.append(f"🆓 {free_preview}")
        
        watcher_preview = ' | '.join(watcher_details) if watcher_details else 'N/A'
        
        rows.append({
            'Token ID': token_id,
            'Exchange': data['exchange'].upper(),
            'Symbol': data['symbol'],
            'Total': watcher_count,
            '💎 Paid': paid_count,
            '🆓 Free': free_count,
            'Grade': grade,
            'Risk %': f"{risk:.1f}",
            'In Pool': '✅' if in_pool else '❌',
            'Who': watcher_preview
        })
    
    if not rows:
        st.info(f"No tokens match the current filters.")
        return
    
    # 정렬 (Total 와처 수 내림차순)
    df = pd.DataFrame(rows)
    df = df.sort_values('Total', ascending=False)
    
    # 통계 계산
    total_paid = df['💎 Paid'].sum()
    total_free = df['🆓 Free'].sum()
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.success(f"✅ Displaying {len(df)} / {total_unique_tokens} tokens")
    with col_s2:
        st.info(f"💎 **Paid Users**: {total_paid}")
    with col_s3:
        st.info(f"🆓 **Free Users**: {total_free}")
    
    # 데이터프레임 표시
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        column_config={
            'Total': st.column_config.NumberColumn(
                'Total',
                help='Total watchers (Paid + Free)',
                format='%d 👤'
            ),
            '💎 Paid': st.column_config.NumberColumn(
                '💎 Paid',
                help='Pro + Premium users',
                format='%d'
            ),
            '🆓 Free': st.column_config.NumberColumn(
                '🆓 Free',
                help='Free tier users',
                format='%d'
            ),
            'Risk %': st.column_config.NumberColumn(
                'Risk %',
                help='Average risk percentage'
            )
        }
    )
    
    # 추가 기능
    st.markdown("---")
    st.markdown("### ➕ Add to Premium Pool")
    
    # 프리미엄 풀에 없는 토큰만 선택 가능
    available_token_ids = [row['Token ID'] for row in rows if row['In Pool'] == '❌']
    
    if not available_token_ids:
        st.warning("⚠️ All displayed tokens are already in the premium pool.")
        return
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        tokens_to_add = st.multiselect(
            "Select tokens to add to Premium Pool (200):",
            options=available_token_ids,
            format_func=lambda x: f"{next((r['Exchange'] for r in rows if r['Token ID'] == x), '')}/{next((r['Symbol'] for r in rows if r['Token ID'] == x), '')} ({next((r['Total'] for r in rows if r['Token ID'] == x), 0)} watchers: 💎{next((r['💎 Paid'] for r in rows if r['Token ID'] == x), 0)} / 🆓{next((r['🆓 Free'] for r in rows if r['Token ID'] == x), 0)})",
            key='add_from_watchlists'
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add Selected", type="primary", disabled=not tokens_to_add, key="add_selected_from_watchlists"):
            success_count = 0
            for token_id in tokens_to_add:
                if tm.add_to_premium_pool(token_id, added_by="admin"):
                    success_count += 1
            st.success(f"✅ Added {success_count}/{len(tokens_to_add)} token(s) to premium pool. 1-minute snapshot collection will start automatically.")
            st.rerun()


def render_manual_search(tm: TokenManager):
    """수동 검색으로 프리미엄 풀에 추가"""
    st.markdown("### 🔍 Manual Search & Add")
    st.markdown("""
    **거래소와 심볼로 직접 검색하여 Premium Pool (200)에 추가합니다.**
    
    - 특정 토큰을 직접 검색
    - 토큰 정보 확인 (Grade, Risk, Watchers 등)
    - Premium Pool (Tab 2)에 추가/제거
    
    ---
    """)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        exchange = st.selectbox(
            "Exchange:",
            ['gateio', 'mexc', 'mexc_assessment', 'kucoin', 'bitget'],
            key='manual_exchange'
        )
    
    with col2:
        symbol = st.text_input(
            "Symbol (e.g., BTC/USDT):",
            key='manual_symbol'
        ).upper()
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 Search", type="primary")
    
    if search_clicked and symbol:
        # Generate token_id first
        token_id = f"{exchange}_{symbol.replace('/', '_').lower()}"
        
        # 토큰 검색
        token = tm.get_token_by_id(token_id)
        
        if token:
            st.success(f"✅ Found: {exchange}/{symbol}")
            
            # 토큰 정보 표시
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                status = token.get('lifecycle', {}).get('status', 'N/A')
                st.metric("Status", status)
            
            with col_b:
                watchers = len(token.get('watchers', []))
                st.metric("Watchers", watchers)
            
            with col_c:
                in_pool = token.get('premium_pool', {}).get('in_pool', False)
                st.metric("In Pool", "✅ Yes" if in_pool else "❌ No")
            
            # 스냅샷 데이터
            if token.get('current_snapshot'):
                snap = token['current_snapshot']
                st.markdown("**Current Data:**")
                st.write(f"- Spread: {snap.get('spread_pct', 'N/A')}%")
                st.write(f"- Depth: ${snap.get('depth_2pct', 'N/A')}")
                st.write(f"- Volume: ${snap.get('volume_24h', 'N/A')}")
            
            # Grade 정보
            if token.get('scan_aggregate'):
                scan = token['scan_aggregate']
                st.markdown("**Grade & Risk:**")
                st.write(f"- Grade: {scan.get('grade', 'N/A')}")
                st.write(f"- Risk: {scan.get('average_risk', 0) * 100:.1f}%")
                st.write(f"- Violation: {scan.get('violation_rate', 0) * 100:.1f}%")
            
            # 추가/제거 버튼
            st.markdown("---")
            
            # token_id is already generated above, just use it
            
            if in_pool:
                if st.button("🗑️ Remove from Premium Pool", key='manual_remove'):
                    tm.remove_from_premium_pool(token_id)
                    st.success("✅ Removed from premium pool")
                    st.rerun()
            else:
                if st.button("➕ Add to Premium Pool", type="primary", key='manual_add'):
                    success = tm.add_to_premium_pool(token_id)
                    if success:
                        st.success("✅ Added to premium pool! 1-minute snapshot collection will start automatically.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add token to premium pool")
        else:
            st.error(f"❌ Token not found: {exchange}/{symbol}")
            st.info("💡 Tip: The token must already exist in the unified database.")
