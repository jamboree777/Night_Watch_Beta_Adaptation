"""
User Wallet Tracking Module
각 유저가 자신만의 온체인 지갑을 추적할 수 있는 기능
"""

import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

def get_user_wallet_file(user_id: str) -> str:
    """Get user-specific wallet tracking file path"""
    user_dir = Path("user_data") / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return str(user_dir / "tracked_wallets.json")

def load_user_wallets(user_id: str) -> Dict:
    """Load user's tracked wallets"""
    wallet_file = get_user_wallet_file(user_id)
    if os.path.exists(wallet_file):
        try:
            with open(wallet_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_wallets(user_id: str, data: Dict):
    """Save user's tracked wallets"""
    wallet_file = get_user_wallet_file(user_id)
    with open(wallet_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_tokens_unified():
    """Load tokens_unified.json"""
    tokens_file = "data/tokens_unified.json"
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_user_premium_tokens(user_id: str) -> List[Dict]:
    """Get premium pool tokens for this user"""
    tokens_data = load_tokens_unified()
    premium_tokens = []

    for token_id, token_data in tokens_data.items():
        # Check if token belongs to this user and is in premium pool
        if token_data.get('pool_type') == 'premium':
            # Check if user owns this token
            api_key = token_data.get('api_key_id', '')
            if api_key and user_id in api_key:  # Simple check, adjust based on your user_id format
                premium_tokens.append({
                    'token_id': token_id,
                    'exchange': token_data.get('exchange', 'unknown'),
                    'symbol': token_data.get('symbol', 'unknown'),
                    'data': token_data
                })

    return premium_tokens

def render_wallet_tracking_ui(user_id: str, selected_token_id: str = None):
    """Render wallet tracking UI for user"""

    st.markdown("### 🔗 Wallet Tracking")
    st.caption("추적하고 싶은 지갑 주소를 추가하여 입출고 현황을 모니터링하세요")

    # Load user's wallet data
    user_wallets = load_user_wallets(user_id)

    # Token selection
    tokens_data = load_tokens_unified()

    if selected_token_id and selected_token_id in tokens_data:
        # Use pre-selected token
        token_data = tokens_data[selected_token_id]
        token_key = selected_token_id

        st.markdown(f"**Selected Token:** {token_data.get('exchange', 'N/A').upper()} - {token_data.get('symbol', 'N/A')}")
    else:
        # Let user select token
        premium_tokens = get_user_premium_tokens(user_id)

        if not premium_tokens:
            st.warning("⚠️ 프리미엄 풀에 토큰이 없습니다. 먼저 토큰을 추가해주세요.")
            return

        token_options = {
            f"{t['exchange'].upper()} - {t['symbol']}": t['token_id']
            for t in premium_tokens
        }

        selected_label = st.selectbox(
            "토큰 선택",
            options=list(token_options.keys()),
            key="user_wallet_token_select"
        )

        if not selected_label:
            return

        token_key = token_options[selected_label]
        token_data = tokens_data[token_key]

    # Get tracking config for this token
    if token_key not in user_wallets:
        user_wallets[token_key] = {
            'contract_address': '',
            'chain': 'ETH',
            'tracked_wallets': [],
            'monitoring_enabled': True
        }

    tracking_config = user_wallets[token_key]

    st.markdown("---")

    # Section 1: Contract Configuration
    st.markdown("#### 📋 컨트랙트 정보")

    col1, col2 = st.columns(2)

    with col1:
        contract_address = st.text_input(
            "Contract Address",
            value=tracking_config.get('contract_address', ''),
            placeholder="0x...",
            key=f"contract_{token_key}"
        )

        chain = st.selectbox(
            "Chain",
            options=['ETH', 'BSC', 'POLYGON'],
            index=['ETH', 'BSC', 'POLYGON'].index(tracking_config.get('chain', 'ETH')),
            key=f"chain_{token_key}"
        )

    with col2:
        if st.button("💾 컨트랙트 저장", key=f"save_contract_{token_key}"):
            if contract_address and contract_address.startswith('0x'):
                tracking_config['contract_address'] = contract_address
                tracking_config['chain'] = chain
                tracking_config['updated_at'] = datetime.now().isoformat()

                user_wallets[token_key] = tracking_config
                save_user_wallets(user_id, user_wallets)

                st.success("✅ 컨트랙트 정보가 저장되었습니다!")
                st.rerun()
            else:
                st.error("❌ 올바른 컨트랙트 주소를 입력하세요.")

    if not contract_address or not contract_address.startswith('0x'):
        st.info("💡 **시작하기:** 먼저 아래 단계를 따라주세요:")
        st.markdown("""
        1. **컨트랙트 주소 입력**: 토큰의 스마트 컨트랙트 주소를 입력하세요 (0x로 시작)
        2. **체인 선택**: ETH, BSC, 또는 POLYGON 선택
        3. **저장 버튼 클릭**: 컨트랙트 정보 저장
        4. 그 다음 추적할 지갑 주소를 추가하세요!
        """)
        return

    st.markdown("---")

    # Section 2: Tracked Wallets Management
    st.markdown("#### 👛 추적 지갑 관리")

    tracked_wallets = tracking_config.get('tracked_wallets', [])

    # Display existing wallets
    if tracked_wallets:
        st.markdown("**현재 추적 중인 지갑:**")

        for i, wallet in enumerate(tracked_wallets):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.text(f"🔑 {wallet.get('address', '')[:10]}...{wallet.get('address', '')[-8:]}")

            with col2:
                st.text(f"📛 {wallet.get('label', 'Unknown')}")

            with col3:
                st.text(f"🏢 {wallet.get('exchange', 'N/A')}")

            with col4:
                if st.button("🗑️", key=f"delete_wallet_{token_key}_{i}"):
                    tracked_wallets.pop(i)
                    tracking_config['tracked_wallets'] = tracked_wallets
                    user_wallets[token_key] = tracking_config
                    save_user_wallets(user_id, user_wallets)
                    st.success("✅ 지갑이 삭제되었습니다!")
                    st.rerun()
    else:
        st.info("추적 중인 지갑이 없습니다. 아래에서 추가하세요.")

    st.markdown("---")
    st.markdown("**새 지갑 추가:**")

    col1, col2 = st.columns(2)

    with col1:
        new_wallet_address = st.text_input(
            "Wallet Address",
            placeholder="0x...",
            key=f"new_wallet_{token_key}"
        )

        new_wallet_label = st.text_input(
            "Label (예: Gate.io Hot Wallet)",
            placeholder="지갑 설명",
            key=f"new_label_{token_key}"
        )

    with col2:
        new_wallet_exchange = st.selectbox(
            "Exchange (선택사항)",
            options=['', 'gateio', 'mexc', 'binance', 'okx', 'other'],
            key=f"new_exchange_{token_key}"
        )

        if st.button("➕ 지갑 추가", key=f"add_wallet_{token_key}"):
            if new_wallet_address and new_wallet_address.startswith('0x') and new_wallet_label:
                # Check duplicate
                existing_addresses = [w.get('address', '').lower() for w in tracked_wallets]
                if new_wallet_address.lower() in existing_addresses:
                    st.error("❌ 이미 추가된 지갑 주소입니다.")
                else:
                    tracked_wallets.append({
                        'address': new_wallet_address,
                        'label': new_wallet_label,
                        'exchange': new_wallet_exchange if new_wallet_exchange else 'unknown',
                        'added_at': datetime.now().isoformat()
                    })

                    tracking_config['tracked_wallets'] = tracked_wallets
                    user_wallets[token_key] = tracking_config
                    save_user_wallets(user_id, user_wallets)

                    st.success(f"✅ 지갑이 추가되었습니다: {new_wallet_label}")
                    st.rerun()
            else:
                st.error("❌ 지갑 주소와 라벨을 모두 입력하세요.")

    st.markdown("---")

    # Section 3: Data Collection & Visualization
    if tracked_wallets:
        st.markdown("#### 📊 입출고 현황")

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("🔄 데이터 수집", key=f"collect_{token_key}"):
                with st.spinner("데이터 수집 중..."):
                    try:
                        from onchain_data_collector import OnChainCollector

                        collector = OnChainCollector()

                        st.markdown("**수집 결과:**")

                        for wallet in tracked_wallets:
                            wallet_address = wallet.get('address')
                            wallet_label = wallet.get('label', 'Unknown')

                            balance = collector.get_token_balance(
                                contract_address,
                                wallet_address,
                                chain
                            )

                            if balance is not None:
                                st.success(f"✅ {wallet_label}: {balance:,.8f} tokens")

                                # Save to history
                                history_file = get_wallet_history_file(user_id, token_key, wallet_address)
                                save_balance_history(history_file, balance)
                            else:
                                st.error(f"❌ {wallet_label}: 잔액 조회 실패")

                        st.info("💡 자동 수집은 하루 12회 실행됩니다.")

                    except Exception as e:
                        st.error(f"❌ 에러: {str(e)}")

        with col2:
            st.info("💡 '데이터 수집' 버튼을 눌러 현재 잔액을 조회하세요.")

        # Show historical data if available
        st.markdown("---")
        render_wallet_charts(user_id, token_key, tracked_wallets, contract_address, chain)

def get_wallet_history_file(user_id: str, token_key: str, wallet_address: str) -> str:
    """Get wallet balance history file path"""
    user_dir = Path("user_data") / user_id / "wallet_history"
    user_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename from wallet address
    safe_address = wallet_address.replace('0x', '').lower()
    return str(user_dir / f"{token_key}_{safe_address}.jsonl")

def save_balance_history(history_file: str, balance: float):
    """Append balance to history file (JSONL format)"""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'balance': balance
    }

    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')

def load_balance_history(history_file: str) -> List[Dict]:
    """Load balance history from JSONL file"""
    if not os.path.exists(history_file):
        return []

    history = []
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    history.append(json.loads(line))
    except:
        return []

    return history

def render_wallet_charts(user_id: str, token_key: str, tracked_wallets: List[Dict],
                         contract_address: str, chain: str):
    """Render wallet balance charts"""

    st.markdown("#### 📈 잔액 추이")

    # Collect all wallet histories
    all_data = []

    for wallet in tracked_wallets:
        wallet_address = wallet.get('address')
        wallet_label = wallet.get('label', 'Unknown')

        history_file = get_wallet_history_file(user_id, token_key, wallet_address)
        history = load_balance_history(history_file)

        if history:
            for entry in history:
                all_data.append({
                    'timestamp': entry['timestamp'],
                    'balance': entry['balance'],
                    'wallet': wallet_label,
                    'wallet_address': wallet_address
                })

    if not all_data:
        st.info("📊 아직 수집된 데이터가 없습니다. '데이터 수집' 버튼을 눌러 데이터를 수집하세요.")
        return

    # Create DataFrame
    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

    # Display chart
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=("Wallet Balance Over Time", "Balance Changes"),
            vertical_spacing=0.12
        )

        # Plot each wallet
        for wallet_label in df['wallet'].unique():
            wallet_df = df[df['wallet'] == wallet_label]

            # Balance line chart
            fig.add_trace(
                go.Scatter(
                    x=wallet_df['timestamp'],
                    y=wallet_df['balance'],
                    mode='lines+markers',
                    name=wallet_label,
                    line=dict(width=2),
                    marker=dict(size=6)
                ),
                row=1, col=1
            )

            # Calculate changes
            wallet_df['balance_change'] = wallet_df['balance'].diff()
            wallet_df['balance_change_pct'] = wallet_df['balance'].pct_change() * 100

            # Balance change bar chart
            colors = ['green' if x >= 0 else 'red' for x in wallet_df['balance_change'].fillna(0)]

            fig.add_trace(
                go.Bar(
                    x=wallet_df['timestamp'],
                    y=wallet_df['balance_change'].fillna(0),
                    name=f"{wallet_label} (Change)",
                    marker_color=colors,
                    showlegend=False
                ),
                row=2, col=1
            )

        # Update layout
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Balance (Tokens)", row=1, col=1)
        fig.update_yaxes(title_text="Change (Tokens)", row=2, col=1)

        fig.update_layout(
            height=800,
            hovermode='x unified',
            template='plotly_dark',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show statistics
        st.markdown("---")
        st.markdown("#### 📊 통계")

        for wallet_label in df['wallet'].unique():
            wallet_df = df[df['wallet'] == wallet_label]

            if len(wallet_df) > 1:
                current_balance = wallet_df.iloc[-1]['balance']
                previous_balance = wallet_df.iloc[0]['balance']
                total_change = current_balance - previous_balance
                total_change_pct = (total_change / previous_balance * 100) if previous_balance > 0 else 0

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Wallet", wallet_label)

                with col2:
                    st.metric("Current Balance", f"{current_balance:,.8f}")

                with col3:
                    st.metric("Total Change", f"{total_change:+,.8f}", f"{total_change_pct:+.2f}%")

                with col4:
                    # Check for large movements (>0.1%)
                    wallet_df['large_move'] = wallet_df['balance_change_pct'].abs() > 0.1
                    large_moves = wallet_df['large_move'].sum()
                    st.metric("대형 이동 (>0.1%)", f"{large_moves}회")

    except ImportError:
        st.warning("⚠️ Plotly가 설치되지 않았습니다. 차트를 보려면 설치하세요: `pip install plotly`")

        # Fallback: Show data table
        st.dataframe(df, use_container_width=True)
