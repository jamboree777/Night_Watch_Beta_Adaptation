#!/usr/bin/env python3
"""
Exchange API Keys Management
거래소별 특수 API 키 관리 (Assessment Zone, Innovation Zone 등)
"""
import streamlit as st
import json
import os
from datetime import datetime, timezone

def load_api_keys():
    """API 키 데이터 로드"""
    keys_file = "config/exchange_api_keys.json"
    if os.path.exists(keys_file):
        with open(keys_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {
        "mexc_assessment": {},
        "binance_innovation": {},
        "okx_assessment": {},
        "custom": {}
    }

def save_api_keys(data):
    """API 키 데이터 저장"""
    with open("config/exchange_api_keys.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def render_exchange_api_keys():
    """거래소 API 키 관리 UI"""
    st.title("🔑 Exchange API Keys")
    st.caption("Manage exchange API keys for enhanced rate limits and special zones")
    
    data = load_api_keys()
    
    # 탭 구성: 일반 거래소 API와 특수 Zone API를 분리
    tab1, tab2, tab3 = st.tabs(["🏦 Main Exchange APIs", "🔐 Special Zone APIs", "➕ Add API Key"])
    
    # Tab 1: 일반 거래소 API 키 (Gate.io, MEXC, KuCoin, Bitget) - 복수 API 지원
    with tab1:
        st.subheader("🏦 Main Exchange API Keys")
        st.info("""
        **💡 Multiple API Keys per Exchange:**
        - ✅ **10x Higher Rate Limits**: Scan 2,800+ tokens faster
        - ✅ **Auto Rotation**: Distribute load across multiple API keys
        - ✅ **Expiration Tracking**: Get notified before keys expire
        - ✅ **Read-Only Safe**: No trading permissions required
        """)
        
        # Main exchanges
        main_exchanges = ["gateio", "mexc", "kucoin", "bitget"]
        
        for exchange_id in main_exchanges:
            with st.expander(f"🏦 {exchange_id.upper()}", expanded=True):
                # 거래소별 API 키 리스트 가져오기 (복수 API 지원)
                if exchange_id not in data:
                    data[exchange_id] = {"keys": []}
                elif not isinstance(data[exchange_id], dict) or "keys" not in data[exchange_id]:
                    # 기존 단일 API 구조를 복수 API 구조로 마이그레이션
                    old_key = data[exchange_id] if isinstance(data[exchange_id], dict) else {}
                    if old_key.get("apiKey"):
                        data[exchange_id] = {
                            "keys": [{
                                "id": f"{exchange_id}_legacy",
                                "name": f"{exchange_id.upper()} API #1",
                                "apiKey": old_key.get("apiKey"),
                                "secret": old_key.get("secret"),
                                "password": old_key.get("password"),
                                "expires_at": None,
                                "active": True,
                                "added_at": old_key.get("last_updated", datetime.now(timezone.utc).isoformat())
                            }]
                        }
                    else:
                        data[exchange_id] = {"keys": []}
                
                api_keys_list = data[exchange_id].get("keys", [])
                
                # 현재 등록된 API 키 표시
                if len(api_keys_list) == 0:
                    st.info(f"📭 No API keys for {exchange_id.upper()}. Add one below.")
                else:
                    st.markdown(f"**Registered Keys: {len(api_keys_list)}**")
                    
                    for idx, key_data in enumerate(api_keys_list):
                        key_id = key_data.get("id", f"{exchange_id}_{idx}")
                        key_name = key_data.get("name", f"API Key #{idx+1}")
                        expires_at = key_data.get("expires_at")
                        is_active = key_data.get("active", True)
                        
                        # 만료 여부 확인
                        is_expired = False
                        days_until_expiry = None
                        if expires_at:
                            from datetime import datetime as dt
                            expiry_date = dt.fromisoformat(expires_at.replace('Z', '+00:00'))
                            now = dt.now(timezone.utc)
                            days_until_expiry = (expiry_date - now).days
                            is_expired = days_until_expiry < 0
                        
                        # 상태 표시
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                        
                        with col1:
                            status_icon = "🔴" if is_expired else ("🟡" if days_until_expiry and days_until_expiry < 7 else "🟢")
                            st.write(f"{status_icon} **{key_name}**")
                            masked_key = key_data.get("apiKey", "")[:8] + "..." if key_data.get("apiKey") else "N/A"
                            st.caption(f"Key: `{masked_key}`")
                            
                            # API 등급 표시
                            api_level_info = key_data.get("api_level", {})
                            tier = api_level_info.get("tier", "basic")
                            tier_icon = {
                                "basic": "🔵",
                                "project_team": "🟡",
                                "vip": "🟢"
                            }.get(tier, "🔵")
                            tier_name = api_level_info.get("tier_name", "Basic API")
                            
                            st.caption(f"{tier_icon} **{tier_name}**")
                            st.caption(f"   {api_level_info.get('description', 'Standard access')}")
                            
                            # Project Team API인 경우 화이트리스트 표시
                            if tier == "project_team":
                                whitelist = api_level_info.get("restricted_tokens_whitelist", [])
                                if whitelist:
                                    with st.expander(f"📝 제한 토큰 {len(whitelist)}개 보기"):
                                        st.write(", ".join(whitelist))
                        
                        with col2:
                            if expires_at:
                                if is_expired:
                                    st.error(f"❌ Expired")
                                elif days_until_expiry < 7:
                                    st.warning(f"⚠️ {days_until_expiry}d left")
                                else:
                                    st.success(f"✅ {days_until_expiry}d left")
                                st.caption(expires_at[:10])
                            else:
                                st.info("No expiry")
                        
                        with col3:
                            # Toggle active status
                            new_active = st.checkbox("Active", value=is_active, key=f"{key_id}_active_{idx}")
                            if new_active != is_active:
                                data[exchange_id]["keys"][idx]["active"] = new_active
                                save_api_keys(data)
                                st.rerun()
                        
                        with col4:
                            # Delete button
                            if st.button("🗑️", key=f"{key_id}_delete_{idx}"):
                                if st.session_state.get(f'confirm_delete_{key_id}_{idx}'):
                                    data[exchange_id]["keys"].pop(idx)
                                    save_api_keys(data)
                                    st.success(f"✅ Deleted")
                                    st.rerun()
                                else:
                                    st.session_state[f'confirm_delete_{key_id}_{idx}'] = True
                                    st.warning("Click again")
                
                st.markdown("---")
                
                # 새 API 키 추가
                st.markdown(f"**➕ Add New API Key for {exchange_id.upper()}**")
                
                col_a, col_b = st.columns([2, 2])
                
                with col_a:
                    new_key_name = st.text_input(
                        "Key Name",
                        placeholder=f"{exchange_id.upper()} API #1",
                        key=f"{exchange_id}_new_name",
                        help="Give this API key a descriptive name"
                    )
                    
                    new_api_key = st.text_input(
                        "API Key",
                        type="password",
                        key=f"{exchange_id}_new_api_key",
                        help=f"Enter your {exchange_id.upper()} API Key"
                    )
                    
                    new_api_secret = st.text_input(
                        "API Secret",
                        type="password",
                        key=f"{exchange_id}_new_secret",
                        help=f"Enter your {exchange_id.upper()} API Secret"
                    )
                    
                    new_passphrase = None
                    if exchange_id == "kucoin":
                        new_passphrase = st.text_input(
                            "API Passphrase",
                            type="password",
                            key=f"{exchange_id}_new_passphrase",
                            help="KuCoin requires an API passphrase"
                        )
                
                with col_b:
                    new_expires_at = st.date_input(
                        "Expiration Date (Optional)",
                        value=None,
                        key=f"{exchange_id}_new_expires",
                        help="Set expiration date to get notified before key expires"
                    )
                    
                    # API 등급 설정
                    st.markdown("**API Access Level:**")
                    api_level = st.radio(
                        "API 등급 선택",
                        options=["basic", "project_team", "vip"],
                        format_func=lambda x: {
                            "basic": "🔵 Basic API (일반 토큰만 접근)",
                            "project_team": "🟡 Project Team API (일반 + 특정 제한 토큰)",
                            "vip": "🟢 VIP API (모든 토큰 접근 가능)"
                        }[x],
                        key=f"{exchange_id}_api_level",
                        help="거래소에서 제공받은 API 등급을 선택하세요"
                    )
                    
                    # 등급 설명
                    if api_level == "basic":
                        st.info("💡 거래소 계좌 홀더에게 제공되는 기본 Private API")
                    elif api_level == "project_team":
                        st.info("💡 프로젝트팀에게 제공되는 API (특정 제한 토큰 접근 가능)")
                    elif api_level == "vip":
                        st.success("💡 최우수 고객에게 제공되는 VIP API (모든 제한 토큰 접근)")
                    
                    # Project Team API일 경우에만 화이트리스트 입력
                    whitelist_tokens = []
                    if api_level == "project_team":
                        st.markdown("**제한 토큰 화이트리스트:**")
                        st.caption("이 API로 접근 가능한 제한 토큰 목록을 입력하세요")
                        tokens_input = st.text_area(
                            "화이트리스트 심볼 (대소문자 구분 없음)",
                            placeholder="예시 1 (줄바꿈):\nCREPE\nABCD\nXYZ\n\n예시 2 (쉼표):\nCREPE, ABCD, XYZ",
                            height=100,
                            key=f"{exchange_id}_whitelist_tokens",
                            help="일반 토큰은 입력 불필요. 제한된 특수 토큰만 입력하세요."
                        )
                        
                        if tokens_input:
                            # 파싱: 줄바꿈 또는 쉼표로 분리
                            for line in tokens_input.split('\n'):
                                for token in line.split(','):
                                    token_clean = token.strip().upper()
                                    if token_clean:
                                        whitelist_tokens.append(token_clean)
                            
                            whitelist_tokens = list(set(whitelist_tokens))  # 중복 제거
                            
                            if whitelist_tokens:
                                st.success(f"✅ 제한 토큰 {len(whitelist_tokens)}개: {', '.join(whitelist_tokens[:5])}{' ...' if len(whitelist_tokens) > 5 else ''}")
                        else:
                            st.warning("⚠️ Project Team API는 화이트리스트가 필수입니다")
                    
                    # Provider 정보 (Project Team & VIP API만)
                    provider_id = ""
                    telegram_id = ""
                    if api_level in ["project_team", "vip"]:
                        st.markdown("---")
                        st.markdown("**🎁 Provider Information (인센티브 제공용):**")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            provider_id = st.text_input(
                                "Provider ID",
                                placeholder="user_id or project_name",
                                key=f"{exchange_id}_provider_id",
                                help="API 제공자 식별용 (사용자 ID 또는 프로젝트명)"
                            )
                        with col2:
                            telegram_id = st.text_input(
                                "Telegram ID",
                                placeholder="@username",
                                key=f"{exchange_id}_telegram_id",
                                help="인센티브 및 지원용 텔레그램 ID"
                            )
                        
                        # Benefits info
                        if api_level == "project_team":
                            st.info("✅ 혜택: 무료 모니터링 + 프리미엄 30% 할인")
                        elif api_level == "vip":
                            st.success("✅ 혜택: 무료 모니터링 + 프리미엄 30% 할인 + VIP 수수료 지급")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Validate API Key 버튼
                    if st.button(f"🔍 Test API Key", key=f"{exchange_id}_test", help="Test with ETH/USDT"):
                        if not new_api_key or not new_api_secret:
                            st.error("❌ Enter API Key and Secret first")
                        else:
                            with st.spinner(f"Testing {exchange_id.upper()} API..."):
                                # test_api_keys 모듈 import
                                import sys
                                sys.path.insert(0, ".")
                                from test_api_keys import test_api_key
                                
                                result = test_api_key(
                                    exchange_id,
                                    new_api_key,
                                    new_api_secret,
                                    new_passphrase if exchange_id == "kucoin" else None
                                )
                                
                                if result['valid']:
                                    st.success(f"✅ {result['message']}")
                                    if result['test_data']:
                                        st.info(f"Spread: {result['test_data']['spread_pct']:.3f}%")
                                else:
                                    st.error(f"❌ {result['message']}")
                    
                    if st.button(f"➕ Add API Key to {exchange_id.upper()}", key=f"{exchange_id}_add_new", type="primary"):
                        if not new_key_name:
                            st.error("❌ Key name is required")
                        elif not new_api_key or not new_api_secret:
                            st.error("❌ Both API Key and Secret are required")
                        elif api_level == "project_team" and not whitelist_tokens:
                            st.error("❌ Project Team API는 화이트리스트가 필수입니다")
                        else:
                            # Generate unique ID
                            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
                            new_key_id = f"{exchange_id}_{timestamp}"
                            
                            # Create new key entry
                            new_key_entry = {
                                "id": new_key_id,
                                "name": new_key_name,
                                "apiKey": new_api_key,
                                "secret": new_api_secret,
                                "expires_at": new_expires_at.isoformat() + "T23:59:59+00:00" if new_expires_at else None,
                                "active": True,
                                "added_at": datetime.now(timezone.utc).isoformat(),
                                "last_used": None,
                                "usage_count": 0,
                                
                                # API 등급 정보
                                "api_level": {
                                    "tier": api_level,  # basic, project_team, vip
                                    "tier_name": {
                                        "basic": "Basic API",
                                        "project_team": "Project Team API",
                                        "vip": "VIP API"
                                    }[api_level],
                                    "description": {
                                        "basic": "일반 토큰만 접근 가능",
                                        "project_team": f"일반 토큰 + 제한 토큰 {len(whitelist_tokens)}개 접근",
                                        "vip": "모든 토큰 접근 가능 (제한 토큰 포함)"
                                    }[api_level],
                                    "restricted_tokens_whitelist": whitelist_tokens if api_level == "project_team" else []
                                },
                                
                                # Provider 정보 (인센티브용)
                                "provider_id": provider_id if api_level in ["project_team", "vip"] else "",
                                "telegram_id": telegram_id if api_level in ["project_team", "vip"] else ""
                            }
                            
                            if exchange_id == "kucoin" and new_passphrase:
                                new_key_entry["password"] = new_passphrase
                            
                            # Add to list
                            data[exchange_id]["keys"].append(new_key_entry)
                            save_api_keys(data)
                            
                            st.success(f"✅ API Key '{new_key_name}' added successfully!")
                            st.balloons()
                            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📚 How to Get API Keys:")
        
        with st.expander("🔗 API Key Links"):
            st.markdown("""
            | Exchange | API Management Page | Required Permissions |
            |----------|---------------------|---------------------|
            | **Gate.io** | [Create API Key](https://www.gate.io/myaccount/apikeys) | ✅ Read Only |
            | **MEXC** | [Create API Key](https://www.mexc.com/user/openapi) | ✅ Read |
            | **KuCoin** | [Create API Key](https://www.kucoin.com/account/api) | ✅ General (Read) |
            | **Bitget** | [Create API Key](https://www.bitget.com/api-doc) | ✅ Read Only |
            
            **⚠️ Important:**
            - Only enable **Read** permissions
            - Never enable **Trade**, **Withdraw**, or **Transfer** permissions
            - API keys are stored locally and never shared
            """)
    
    # Tab 2: 특수 Zone API 키 (기존 코드)
    with tab2:
        st.subheader("📋 Special Zone API Keys")
        st.caption("APIs for Assessment/Innovation zones with token-specific whitelist support")
        
        # 특수 Zone API만 필터링 (일반 거래소 API 제외)
        special_zone_keys = {k: v for k, v in data.items() if k not in ["gateio", "mexc", "kucoin", "bitget"]}
        total_keys = sum(len(keys) for keys in special_zone_keys.values() if isinstance(keys, dict))
        
        if total_keys == 0:
            st.info("📭 No special zone API keys registered yet. Add keys in the 'Add API Key' tab.")
        else:
            # 거래소별로 표시
            for exchange_type, keys in special_zone_keys.items():
                if not keys or not isinstance(keys, dict):
                    continue
                
                st.markdown(f"### 🏦 {exchange_type.upper().replace('_', ' ')}")
                
                for key_id, key_info in keys.items():
                    with st.expander(f"🔑 {key_info['name']}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown("**Key Information:**")
                            st.write(f"- **Name**: {key_info['name']}")
                            st.write(f"- **Exchange**: {key_info['exchange']}")
                            st.write(f"- **Zone**: {key_info.get('zone', 'N/A')}")
                            st.write(f"- **Status**: {'🟢 Active' if key_info.get('active', True) else '🔴 Inactive'}")
                            st.write(f"- **Added**: {key_info.get('added_at', 'N/A')[:10]}")
                            
                            # API Key (masked)
                            api_key_masked = key_info.get('api_key', '')[:8] + "..." if key_info.get('api_key') else 'N/A'
                            st.write(f"- **API Key**: `{api_key_masked}`")
                            
                            # Covered tokens
                            covered_tokens = key_info.get('covered_tokens', [])
                            if covered_tokens:
                                if len(covered_tokens) == 1 and covered_tokens[0] == "ALL":
                                    st.write(f"- **Coverage**: ✅ All tokens in {key_info['zone']}")
                                else:
                                    st.write(f"- **Coverage**: {len(covered_tokens)} tokens")
                                    with st.expander("View covered tokens"):
                                        st.write(", ".join(covered_tokens))
                        
                        with col2:
                            st.markdown("**Actions:**")
                            
                            # Toggle active status
                            new_status = st.checkbox(
                                "Active",
                                value=key_info.get('active', True),
                                key=f"active_{key_id}"
                            )
                            
                            if new_status != key_info.get('active', True):
                                data[exchange_type][key_id]['active'] = new_status
                                save_api_keys(data)
                                st.success(f"✅ Status updated")
                                st.rerun()
                            
                            # Delete key
                            if st.button("🗑️ Delete", key=f"delete_{key_id}"):
                                if st.session_state.get(f'confirm_delete_{key_id}'):
                                    del data[exchange_type][key_id]
                                    save_api_keys(data)
                                    st.success("✅ API Key deleted")
                                    st.rerun()
                                else:
                                    st.session_state[f'confirm_delete_{key_id}'] = True
                                    st.warning("⚠️ Click again to confirm")
    
    # Tab 3: Add Special Zone API Key
    with tab3:
        st.subheader("➕ Add New API Key")
        
        # Exchange 선택
        exchange_info = st.selectbox(
            "Exchange & Zone",
            options=[
                "mexc_assessment",
                "mexc_innovation",
                "binance_innovation",
                "okx_assessment",
                "bybit_innovation",
                "custom"
            ],
            format_func=lambda x: {
                "mexc_assessment": "MEXC - Assessment Zone",
                "mexc_innovation": "MEXC - Innovation Zone",
                "binance_innovation": "Binance - Innovation Zone",
                "okx_assessment": "OKX - Assessment Zone",
                "bybit_innovation": "Bybit - Innovation Zone",
                "custom": "Custom (Other)"
            }[x]
        )
        
        # API Key 이름
        key_name = st.text_input(
            "API Key Name",
            placeholder="e.g., MEXC Assessment Whitelist API",
            help="Give this API key a descriptive name"
        )
        
        # API Key
        api_key = st.text_input(
            "API Key",
            type="password",
            help="The API key provided by the exchange or token project"
        )
        
        # API Secret (optional)
        api_secret = st.text_input(
            "API Secret (Optional)",
            type="password",
            help="Some APIs may require a secret"
        )
        
        st.markdown("---")
        
        # Coverage 선택
        st.markdown("### 📊 Token Coverage")
        
        coverage_type = st.radio(
            "This API key covers:",
            options=["all", "specific"],
            format_func=lambda x: {
                "all": "✅ All tokens in this zone",
                "specific": "📝 Specific token(s) only"
            }[x],
            horizontal=True
        )
        
        covered_tokens = []
        
        if coverage_type == "specific":
            st.markdown("**Enter token symbols (UPPERCASE only, without /USDT)**")
            st.caption("💡 Tip: Enter one symbol per line, or comma-separated")
            
            tokens_input = st.text_area(
                "Token Symbols",
                placeholder="CREPE\nTEST\nANOTHER\n\nor: CREPE, TEST, ANOTHER",
                height=150,
                help="Input will be automatically converted to uppercase"
            )
            
            # Parse input
            if tokens_input:
                # Split by newline and comma
                tokens = []
                for line in tokens_input.split('\n'):
                    for token in line.split(','):
                        token = token.strip().upper()
                        if token:
                            tokens.append(token)
                
                covered_tokens = list(set(tokens))  # Remove duplicates
                
                if covered_tokens:
                    st.success(f"✅ Parsed {len(covered_tokens)} token(s): {', '.join(covered_tokens)}")
        else:
            covered_tokens = ["ALL"]
            st.info("✅ This API key will be used for all tokens in this zone")
        
        st.markdown("---")
        
        # 연락처 정보
        st.markdown("### 👤 Contact Information (Optional)")
        contact_email = st.text_input("Contact Email", placeholder="api@example.com")
        contact_telegram = st.text_input("Contact Telegram", placeholder="@username")
        
        st.markdown("---")
        
        # Revenue share 동의
        st.markdown("### 💰 Revenue Share Agreement")
        st.info("""
        **50:50 Revenue Share Model**
        
        If this API key is provided by a token project or third-party:
        - They will receive **50%** of subscription revenue
        - Revenue is calculated based on weighted token usage
        - Payment is processed monthly
        
        If you are the admin providing your own API keys, this does not apply.
        """)
        
        is_third_party = st.checkbox("This API key is provided by a third-party (enable revenue share)")
        
        # Submit
        if st.button("➕ Add API Key", type="primary"):
            if not key_name:
                st.error("❌ API Key name is required")
            elif not api_key:
                st.error("❌ API Key is required")
            elif coverage_type == "specific" and not covered_tokens:
                st.error("❌ Please specify at least one token symbol")
            else:
                # Generate key ID
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
                key_id = f"{exchange_info}_{timestamp}"
                
                # Extract exchange and zone
                if "_" in exchange_info:
                    exchange, zone = exchange_info.split("_", 1)
                else:
                    exchange = exchange_info
                    zone = "custom"
                
                # Create key entry
                new_key = {
                    "name": key_name,
                    "exchange": exchange,
                    "zone": zone,
                    "api_key": api_key,
                    "api_secret": api_secret if api_secret else None,
                    "covered_tokens": covered_tokens,
                    "active": True,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "is_third_party": is_third_party,
                    "contact_email": contact_email if contact_email else None,
                    "contact_telegram": contact_telegram if contact_telegram else None
                }
                
                # Save
                if exchange_info not in data:
                    data[exchange_info] = {}
                
                data[exchange_info][key_id] = new_key
                save_api_keys(data)
                
                st.success(f"✅ API Key '{key_name}' added successfully!")
                
                if coverage_type == "specific":
                    st.info(f"📊 Coverage: {len(covered_tokens)} token(s) - {', '.join(covered_tokens)}")
                else:
                    st.info(f"📊 Coverage: All tokens in {zone}")
                
                st.balloons()
                st.rerun()

