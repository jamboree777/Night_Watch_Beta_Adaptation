"""
API Management Module
통합 API 키 관리 (거래소, 블록체인, 기타 서비스)
"""
import streamlit as st
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# admin_exchange_api_keys 모듈을 최상단에서 import (중복 로드 방지)
if 'admin_modules.admin_exchange_api_keys' not in sys.modules:
    from admin_modules import admin_exchange_api_keys

def load_api_keys():
    """API 키 데이터 로드"""
    api_keys_file = "config/exchange_api_keys.json"
    if os.path.exists(api_keys_file):
        try:
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_api_keys(data):
    """API 키 데이터 저장"""
    api_keys_file = "config/exchange_api_keys.json"
    with open(api_keys_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def render_api_management():
    """API Management 메인 화면"""
    st.title("🔐 API Management")
    st.caption("거래소, 블록체인 익스플로러, 기타 서비스 API 통합 관리")
    
    # 3개 탭 생성
    tab1, tab2, tab3 = st.tabs([
        "🏦 Main Exchange APIs",
        "🔗 Blockchain Explorer APIs", 
        "🔧 Other API Keys"
    ])
    
    # ==================== TAB 1: Main Exchange APIs ====================
    with tab1:
        render_main_exchange_apis()
    
    # ==================== TAB 2: Blockchain Explorer APIs ====================
    with tab2:
        render_blockchain_explorer_apis()
    
    # ==================== TAB 3: Other API Keys ====================
    with tab3:
        render_other_api_keys()


def render_main_exchange_apis():
    """기존 거래소 API 관리 (admin_exchange_api_keys.py에서 이동)"""
    # 최상단에서 이미 import된 모듈 사용
    from admin_modules.admin_exchange_api_keys import render_exchange_api_keys
    render_exchange_api_keys()


def load_blockchain_api_keys():
    """블록체인 API 키 로드"""
    api_config_file = "config/api_config.json"
    if os.path.exists(api_config_file):
        try:
            with open(api_config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_blockchain_api_keys(data):
    """블록체인 API 키 저장"""
    api_config_file = "config/api_config.json"
    with open(api_config_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def render_blockchain_explorer_apis():
    """블록체인 익스플로러 API 및 추적 계정 관리"""
    st.header("🔗 Blockchain Explorer APIs")
    st.caption("온체인 거래 추적 및 계정 모니터링")

    # Load existing API keys
    api_keys = load_blockchain_api_keys()

    # ============ 블록체인 익스플로러 API ============
    st.subheader("1️⃣ Blockchain Explorer APIs")
    st.info("💡 Phase 3 온체인 데이터 수집을 위한 API 키")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Etherscan API**")
        current_etherscan = api_keys.get('etherscan_api_key', '')

        if current_etherscan:
            st.success(f"✅ API Key 저장됨: {current_etherscan[:8]}...{current_etherscan[-4:]}")

        etherscan_key = st.text_input(
            "API Key",
            value=current_etherscan,
            type="password",
            key="etherscan_key",
            help="https://etherscan.io/apis"
        )
        if st.button("💾 Save Etherscan Key", key="save_etherscan"):
            if etherscan_key:
                api_keys['etherscan_api_key'] = etherscan_key
                save_blockchain_api_keys(api_keys)
                st.success("✅ Etherscan API 키가 저장되었습니다!")
                st.rerun()
            else:
                st.error("❌ API 키를 입력하세요")

    with col2:
        st.markdown("**BscScan API**")
        current_bscscan = api_keys.get('bscscan_api_key', '')

        if current_bscscan:
            st.success(f"✅ API Key 저장됨: {current_bscscan[:8]}...{current_bscscan[-4:]}")

        bscscan_key = st.text_input(
            "API Key",
            value=current_bscscan,
            type="password",
            key="bscscan_key",
            help="https://bscscan.com/apis"
        )
        if st.button("💾 Save BscScan Key", key="save_bscscan"):
            if bscscan_key:
                api_keys['bscscan_api_key'] = bscscan_key
                save_blockchain_api_keys(api_keys)
                st.success("✅ BscScan API 키가 저장되었습니다!")
                st.rerun()
            else:
                st.error("❌ API 키를 입력하세요")

    # PolygonScan 추가
    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**PolygonScan API** (선택)")
        current_polygonscan = api_keys.get('polygonscan_api_key', '')

        if current_polygonscan:
            st.success(f"✅ API Key 저장됨: {current_polygonscan[:8]}...{current_polygonscan[-4:]}")

        polygonscan_key = st.text_input(
            "API Key",
            value=current_polygonscan,
            type="password",
            key="polygonscan_key",
            help="https://polygonscan.com/apis"
        )
        if st.button("💾 Save PolygonScan Key", key="save_polygonscan"):
            if polygonscan_key:
                api_keys['polygonscan_api_key'] = polygonscan_key
                save_blockchain_api_keys(api_keys)
                st.success("✅ PolygonScan API 키가 저장되었습니다!")
                st.rerun()
            else:
                st.error("❌ API 키를 입력하세요")

    with col4:
        st.markdown("**API 키 상태**")
        st.caption("저장된 API 키 요약")

        if api_keys.get('etherscan_api_key'):
            st.write("✅ Etherscan")
        else:
            st.write("❌ Etherscan")

        if api_keys.get('bscscan_api_key'):
            st.write("✅ BscScan")
        else:
            st.write("❌ BscScan")

        if api_keys.get('polygonscan_api_key'):
            st.write("✅ PolygonScan")
        else:
            st.write("⚪ PolygonScan (선택)")

    # Test Connection
    st.markdown("---")
    if st.button("🧪 Test API Connection", key="test_blockchain_api"):
        if api_keys.get('etherscan_api_key'):
            with st.spinner("Etherscan API 연결 테스트 중..."):
                try:
                    from onchain_data_collector import OnChainCollector
                    collector = OnChainCollector()

                    # Test with WBTC contract
                    test_address = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
                    token_info = collector.get_token_info(test_address, 'ETH')

                    if token_info:
                        st.success(f"✅ Etherscan API 연결 성공! (테스트: {token_info['symbol']})")
                    else:
                        st.error("❌ Etherscan API 연결 실패")
                except Exception as e:
                    st.error(f"❌ 테스트 실패: {str(e)}")
        else:
            st.warning("⚠️ Etherscan API 키를 먼저 저장하세요")
    
    st.markdown("---")
    
    # ============ 계정 스캔/추적 기능 ============
    st.subheader("2️⃣ Account Scanning & Tracking")
    st.info("💡 특정 지갑 주소 및 거래소 계정 추적 (향후 구현 예정)")
    
    # 추적 계정 등록
    st.markdown("**📍 추적 계정 등록**")
    
    account_type = st.selectbox(
        "계정 유형",
        ["팀 지갑 (Team Wallet)", "거래소 핫월렛 (Exchange Hot Wallet)", "고래 계정 (Whale Account)", "기타 (Other)"],
        key="account_type"
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        account_address = st.text_input(
            "지갑 주소 / 계정 ID",
            placeholder="0x1234... 또는 거래소 계정 ID",
            key="account_address"
        )
    
    with col2:
        blockchain_network = st.selectbox(
            "네트워크",
            ["Ethereum", "BSC", "Polygon", "Arbitrum", "Optimism", "거래소 내부"],
            key="blockchain_network"
        )
    
    account_label = st.text_input(
        "계정 라벨 (선택)",
        placeholder="예: Binance Hot Wallet #1",
        key="account_label"
    )
    
    account_notes = st.text_area(
        "메모 (선택)",
        placeholder="이 계정에 대한 추가 설명...",
        height=80,
        key="account_notes"
    )
    
    if st.button("➕ Add Tracking Account", type="primary"):
        if not account_address:
            st.error("❌ 지갑 주소 또는 계정 ID를 입력하세요")
        else:
            st.warning("⚠️ 기능 구현 예정")
            st.info(f"""
            **등록 예정:**
            - 유형: {account_type}
            - 주소: {account_address}
            - 네트워크: {blockchain_network}
            - 라벨: {account_label or '(없음)'}
            """)
    
    st.markdown("---")
    
    # ============ 등록된 추적 계정 목록 ============
    st.subheader("3️⃣ Registered Tracking Accounts")
    st.info("💡 현재 등록된 추적 계정이 없습니다 (향후 구현 예정)")
    
    # 샘플 데이터 표시 (향후 실제 데이터로 교체)
    st.caption("예시 화면:")
    with st.expander("🐋 Whale Account #1 - 0x742d...4e2f (Ethereum)"):
        st.write("**라벨:** Binance Hot Wallet")
        st.write("**네트워크:** Ethereum")
        st.write("**등록일:** 2025-10-12")
        st.write("**마지막 활동:** 2시간 전")
        col1, col2 = st.columns(2)
        with col1:
            st.button("🔍 View Transactions", key="sample_view")
        with col2:
            st.button("🗑️ Remove", key="sample_remove")


def render_other_api_keys():
    """기타 서비스 API 키 관리 (Slack, Telegram, Google 등)"""
    st.header("🔧 Other API Keys")
    st.caption("알림, 문서 연동 등 기타 서비스 API 관리")
    
    # ============ Messaging & Notifications ============
    st.subheader("1️⃣ Messaging & Notifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📱 Telegram Bot**")
        telegram_token = st.text_input(
            "Bot Token",
            type="password",
            placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            key="telegram_token",
            help="@BotFather에서 발급받은 토큰"
        )
        telegram_chat_id = st.text_input(
            "Chat ID (선택)",
            placeholder="-1001234567890",
            key="telegram_chat_id"
        )
        if st.button("💾 Save Telegram", key="save_telegram"):
            st.warning("⚠️ 기능 구현 예정")
    
    with col2:
        st.markdown("**💬 Slack Bot**")
        slack_token = st.text_input(
            "Bot Token",
            type="password",
            placeholder="xoxb-1234-5678-abcd",
            key="slack_token",
            help="Slack App에서 발급받은 Bot Token"
        )
        slack_channel = st.text_input(
            "Channel ID (선택)",
            placeholder="#alerts",
            key="slack_channel"
        )
        if st.button("💾 Save Slack", key="save_slack"):
            st.warning("⚠️ 기능 구현 예정")
    
    st.markdown("---")
    
    # ============ Google Services ============
    st.subheader("2️⃣ Google Services")
    
    st.markdown("**🔐 Google OAuth 2.0**")
    st.caption("Google Drive, Sheets, Docs 등 Google 서비스 연동")
    
    google_client_id = st.text_input(
        "Client ID",
        placeholder="1234567890-abcdefg.apps.googleusercontent.com",
        key="google_client_id"
    )
    
    google_client_secret = st.text_input(
        "Client Secret",
        type="password",
        placeholder="GOCSPX-abcdefghijklmnop",
        key="google_client_secret"
    )
    
    google_services = st.multiselect(
        "사용할 서비스",
        ["Gmail (이메일 알림)", "Google Sheets (데이터 내보내기)", "Google Drive (백업)", "Google Docs (리포트)"],
        key="google_services"
    )
    
    if st.button("💾 Save Google OAuth", key="save_google"):
        st.warning("⚠️ 기능 구현 예정")
    
    st.markdown("---")
    
    # ============ Custom Webhooks & URLs ============
    st.subheader("3️⃣ Custom Webhooks & URLs")
    
    st.markdown("**🔗 Webhook URLs**")
    st.caption("커스텀 알림 및 데이터 전송")
    
    webhook_name = st.text_input(
        "Webhook 이름",
        placeholder="예: Discord Alert Webhook",
        key="webhook_name"
    )
    
    webhook_url = st.text_input(
        "Webhook URL",
        placeholder="https://discord.com/api/webhooks/...",
        key="webhook_url"
    )
    
    webhook_method = st.selectbox(
        "HTTP Method",
        ["POST", "GET", "PUT"],
        key="webhook_method"
    )
    
    webhook_headers = st.text_area(
        "Custom Headers (JSON)",
        placeholder='{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer token"\n}',
        height=100,
        key="webhook_headers"
    )
    
    if st.button("➕ Add Webhook", type="primary"):
        if not webhook_name or not webhook_url:
            st.error("❌ Webhook 이름과 URL을 입력하세요")
        else:
            st.warning("⚠️ 기능 구현 예정")
            st.info(f"""
            **등록 예정:**
            - 이름: {webhook_name}
            - URL: {webhook_url}
            - Method: {webhook_method}
            """)
    
    st.markdown("---")
    
    # ============ Email SMTP Settings ============
    st.subheader("4️⃣ Email SMTP Settings")
    
    st.markdown("**📧 SMTP 서버 설정**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        smtp_server = st.text_input(
            "SMTP Server",
            placeholder="smtp.gmail.com",
            key="smtp_server"
        )
        smtp_port = st.number_input(
            "Port",
            value=587,
            key="smtp_port"
        )
    
    with col2:
        smtp_email = st.text_input(
            "Email Address",
            placeholder="your-email@gmail.com",
            key="smtp_email"
        )
        smtp_password = st.text_input(
            "Password / App Password",
            type="password",
            key="smtp_password"
        )
    
    smtp_use_tls = st.checkbox("Use TLS", value=True, key="smtp_use_tls")
    
    if st.button("💾 Save SMTP Settings", key="save_smtp"):
        st.warning("⚠️ 기능 구현 예정")
    
    st.markdown("---")
    
    # ============ 등록된 API 키 목록 ============
    st.subheader("5️⃣ Registered API Keys")
    st.info("💡 현재 등록된 기타 API 키가 없습니다 (향후 구현 예정)")












