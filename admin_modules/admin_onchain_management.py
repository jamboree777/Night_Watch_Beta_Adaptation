"""
On-Chain Wallet Management for Admin Dashboard
관리자가 토큰별 추적 지갑을 추가/삭제/관리
"""

import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

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

def save_tokens_unified(data: Dict):
    """Save tokens_unified.json"""
    tokens_file = "data/tokens_unified.json"
    with open(tokens_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_premium_pool_tokens(tokens_data: Dict) -> List[Dict]:
    """Get list of premium pool tokens"""
    premium_tokens = []
    for token_id, token_data in tokens_data.items():
        if token_data.get('pool_type') == 'premium':
            premium_tokens.append({
                'token_id': token_id,
                'exchange': token_data.get('exchange', 'unknown'),
                'symbol': token_data.get('symbol', 'unknown'),
                'data': token_data
            })
    return premium_tokens

def render_onchain_management():
    """Render on-chain wallet management UI"""
    st.markdown("## 🔗 On-Chain Wallet Management")
    st.markdown("토큰별 추적 지갑 관리 (입출고 현황 추적)")

    tokens_data = load_tokens_unified()
    premium_tokens = get_premium_pool_tokens(tokens_data)

    if not premium_tokens:
        st.warning("⚠️ 프리미엄 풀에 토큰이 없습니다.")
        return

    # Token selection
    token_options = {
        f"{t['exchange'].upper()} - {t['symbol']}": t['token_id']
        for t in premium_tokens
    }

    selected_label = st.selectbox(
        "토큰 선택",
        options=list(token_options.keys()),
        key="onchain_token_select"
    )

    if not selected_label:
        return

    selected_token_id = token_options[selected_label]
    token_data = tokens_data[selected_token_id]

    st.markdown("---")

    # Section 1: Contract Info
    st.markdown("### 📋 컨트랙트 정보")

    col1, col2 = st.columns(2)

    with col1:
        on_chain_data = token_data.get('on_chain_data', {})

        current_contract = on_chain_data.get('contract_address', '')
        current_chain = on_chain_data.get('chain', 'ETH')

        contract_address = st.text_input(
            "Contract Address",
            value=current_contract,
            placeholder="0x...",
            key="contract_address"
        )

        chain = st.selectbox(
            "Chain",
            options=['ETH', 'BSC', 'POLYGON'],
            index=['ETH', 'BSC', 'POLYGON'].index(current_chain) if current_chain in ['ETH', 'BSC', 'POLYGON'] else 0,
            key="chain_select"
        )

    with col2:
        if st.button("💾 컨트랙트 정보 저장", key="save_contract"):
            if contract_address and contract_address.startswith('0x'):
                if 'on_chain_data' not in token_data:
                    token_data['on_chain_data'] = {}

                token_data['on_chain_data']['contract_address'] = contract_address
                token_data['on_chain_data']['chain'] = chain
                token_data['on_chain_data']['last_updated'] = datetime.now().isoformat()

                save_tokens_unified(tokens_data)
                st.success("✅ 컨트랙트 정보가 저장되었습니다!")
                st.rerun()
            else:
                st.error("❌ 올바른 컨트랙트 주소를 입력하세요.")

    if not contract_address or not contract_address.startswith('0x'):
        st.info("💡 먼저 컨트랙트 주소와 체인을 설정하세요.")
        return

    st.markdown("---")

    # Section 2: Tracked Wallets
    st.markdown("### 👛 추적 지갑 관리")

    tracked_wallets = on_chain_data.get('tracked_wallets', [])

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
                if st.button("🗑️", key=f"delete_wallet_{i}"):
                    tracked_wallets.pop(i)
                    token_data['on_chain_data']['tracked_wallets'] = tracked_wallets
                    save_tokens_unified(tokens_data)
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
            key="new_wallet_address"
        )

        new_wallet_label = st.text_input(
            "Label (예: Gate.io Hot Wallet)",
            placeholder="지갑 설명",
            key="new_wallet_label"
        )

    with col2:
        new_wallet_exchange = st.selectbox(
            "Exchange (선택사항)",
            options=['', 'gateio', 'mexc', 'binance', 'okx', 'other'],
            key="new_wallet_exchange"
        )

        if st.button("➕ 지갑 추가", key="add_wallet"):
            if new_wallet_address and new_wallet_address.startswith('0x') and new_wallet_label:
                if 'tracked_wallets' not in token_data['on_chain_data']:
                    token_data['on_chain_data']['tracked_wallets'] = []

                # Check duplicate
                existing_addresses = [w.get('address', '').lower() for w in tracked_wallets]
                if new_wallet_address.lower() in existing_addresses:
                    st.error("❌ 이미 추가된 지갑 주소입니다.")
                else:
                    token_data['on_chain_data']['tracked_wallets'].append({
                        'address': new_wallet_address,
                        'label': new_wallet_label,
                        'exchange': new_wallet_exchange if new_wallet_exchange else 'unknown',
                        'added_at': datetime.now().isoformat()
                    })

                    save_tokens_unified(tokens_data)
                    st.success(f"✅ 지갑이 추가되었습니다: {new_wallet_label}")
                    st.rerun()
            else:
                st.error("❌ 지갑 주소와 라벨을 모두 입력하세요.")

    st.markdown("---")

    # Section 3: Monitoring Settings
    st.markdown("### ⚙️ 모니터링 설정")

    custom_monitoring = token_data.get('custom_monitoring', {})

    col1, col2 = st.columns(2)

    with col1:
        monitoring_enabled = st.checkbox(
            "입출고 모니터링 활성화",
            value=custom_monitoring.get('enabled', False),
            key="monitoring_enabled"
        )

        target_balance = st.number_input(
            "목표 입고량 (선택사항)",
            min_value=0.0,
            value=float(custom_monitoring.get('target_deposit_balance', 0)),
            step=1.0,
            key="target_balance",
            help="설정 시, 목표 대비 편차로 점수 계산"
        )

    with col2:
        alert_threshold = st.number_input(
            "알림 임계값 (%)",
            min_value=0.1,
            max_value=100.0,
            value=float(custom_monitoring.get('alert_threshold_pct', 0.1)),
            step=0.1,
            key="alert_threshold",
            help="이 비율 이상 변화 시 알림"
        )

        if st.button("💾 모니터링 설정 저장", key="save_monitoring"):
            token_data['custom_monitoring'] = {
                'enabled': monitoring_enabled,
                'target_deposit_balance': target_balance if target_balance > 0 else None,
                'alert_threshold_pct': alert_threshold,
                'updated_at': datetime.now().isoformat()
            }

            save_tokens_unified(tokens_data)
            st.success("✅ 모니터링 설정이 저장되었습니다!")
            st.rerun()

    st.markdown("---")

    # Section 4: Test Collection
    st.markdown("### 🧪 데이터 수집 테스트")

    if tracked_wallets and st.button("🔄 지금 데이터 수집", key="test_collection"):
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
                    else:
                        st.error(f"❌ {wallet_label}: 잔액 조회 실패")

                st.info("💡 자동 수집은 스케줄러에 의해 하루 12회 실행됩니다.")

            except Exception as e:
                st.error(f"❌ 에러: {str(e)}")

if __name__ == "__main__":
    render_onchain_management()
