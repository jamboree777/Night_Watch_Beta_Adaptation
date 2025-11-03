import streamlit as st
import json
import os
from datetime import datetime, timezone

WHITELIST_FILE = "data/whitelist.json"

def load_whitelist():
    """화이트리스트 로드"""
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 기본 구조
    return {
        "gateio": [],
        "mexc": [],
        "kucoin": [],
        "bitget": [],
        "last_updated": None
    }

def save_whitelist(whitelist):
    """화이트리스트 저장"""
    os.makedirs("data", exist_ok=True)
    whitelist['last_updated'] = datetime.now(timezone.utc).isoformat()
    
    with open(WHITELIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(whitelist, f, indent=2, ensure_ascii=False)

def render_whitelist_management():
    """화이트리스트 관리 UI"""
    st.markdown("## ⚪ Whitelist Management")
    st.markdown("메이저 코인을 화이트리스트에 추가하면 배치 스캔에서 **영구적으로 제외**됩니다.")
    
    # 화이트리스트 로드
    whitelist = load_whitelist()
    
    # 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Gate.io", len(whitelist.get('gateio', [])))
    with col2:
        st.metric("MEXC", len(whitelist.get('mexc', [])))
    with col3:
        st.metric("KuCoin", len(whitelist.get('kucoin', [])))
    with col4:
        st.metric("Bitget", len(whitelist.get('bitget', [])))
    
    if whitelist.get('last_updated'):
        last_update = datetime.fromisoformat(whitelist['last_updated'].replace('Z', '+00:00'))
        st.caption(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    st.markdown("---")
    
    # 탭으로 거래소별 관리
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏦 Gate.io", "🏦 MEXC", "🏦 KuCoin", "🏦 Bitget", "📥 Bulk Import"])
    
    # Gate.io
    with tab1:
        render_exchange_whitelist("Gate.io", "gateio", whitelist)
    
    # MEXC
    with tab2:
        render_exchange_whitelist("MEXC", "mexc", whitelist)
    
    # KuCoin
    with tab3:
        render_exchange_whitelist("KuCoin", "kucoin", whitelist)
    
    # Bitget
    with tab4:
        render_exchange_whitelist("Bitget", "bitget", whitelist)
    
    # Bulk Import
    with tab5:
        render_bulk_import(whitelist)

def render_exchange_whitelist(exchange_name, exchange_key, whitelist):
    """거래소별 화이트리스트 관리"""
    current_list = whitelist.get(exchange_key, [])
    st.markdown(f"### {exchange_name} Whitelist ({len(current_list)} tokens)")
    
    # 토큰 추가
    st.markdown("#### ➕ Add Token")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_symbol = st.text_input(
            "Token Symbol (e.g., BTC, ETH, DOGE)",
            key=f"add_symbol_{exchange_key}",
            help="대소문자 구분 없이 심볼만 입력하세요. 자동으로 /USDT가 추가됩니다."
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("Add", key=f"add_btn_{exchange_key}", type="primary"):
            if new_symbol:
                # 대소문자 정규화
                symbol_normalized = new_symbol.strip().upper()
                pair = f"{symbol_normalized}/USDT"
                
                # 중복 체크
                if pair in whitelist.get(exchange_key, []):
                    st.warning(f"⚠️ {pair} is already in the whitelist!")
                else:
                    # 추가
                    if exchange_key not in whitelist:
                        whitelist[exchange_key] = []
                    whitelist[exchange_key].append(pair)
                    whitelist[exchange_key].sort()  # 정렬
                    save_whitelist(whitelist)
                    st.success(f"✅ Added {pair} to {exchange_name} whitelist!")
                    st.rerun()
            else:
                st.warning("⚠️ Please enter a symbol!")
    
    # 현재 화이트리스트 테이블로 표시
    st.markdown("#### 📋 Current Whitelist")
    
    if current_list:
        # 알파벳 정렬
        sorted_list = sorted(current_list)
        
        # DataFrame으로 표시
        import pandas as pd
        df = pd.DataFrame([
            {
                '#': idx + 1,
                'Symbol': symbol,
                'Exchange': exchange_name
            }
            for idx, symbol in enumerate(sorted_list)
        ])
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(sorted_list) * 35 + 38)
        )
        
        # 벌크 표시
        st.markdown("##### 📦 Bulk List (Copy & Paste)")
        bulk_text = ', '.join([s.replace('/USDT', '') for s in sorted_list])
        st.text_area(
            "Token symbols (comma separated)",
            value=bulk_text,
            height=100,
            key=f"bulk_display_{exchange_key}"
        )
    else:
        st.info("No tokens in whitelist yet.")
    
    # 일괄 삭제
    if current_list:
        st.markdown("---")
        if st.button(f"🗑️ Clear All ({len(current_list)} tokens)", key=f"clear_all_{exchange_key}"):
            if 'confirm_clear' not in st.session_state:
                st.session_state['confirm_clear'] = exchange_key
            else:
                if st.session_state['confirm_clear'] == exchange_key:
                    whitelist[exchange_key] = []
                    save_whitelist(whitelist)
                    st.success(f"✅ Cleared all tokens from {exchange_name} whitelist!")
                    del st.session_state['confirm_clear']
                    st.rerun()
        
        if st.session_state.get('confirm_clear') == exchange_key:
            st.warning("⚠️ Click again to confirm deletion of all tokens!")

def render_bulk_import(whitelist):
    """일괄 임포트"""
    st.markdown("### 📥 Bulk Import")
    st.markdown("여러 토큰을 한 번에 추가할 수 있습니다.")
    
    # 거래소 선택
    selected_exchange = st.selectbox(
        "Target Exchange",
        ["Gate.io", "MEXC", "KuCoin", "Bitget"],
        key="bulk_exchange"
    )
    
    exchange_map = {
        "Gate.io": "gateio",
        "MEXC": "mexc",
        "KuCoin": "kucoin",
        "Bitget": "bitget"
    }
    exchange_key = exchange_map[selected_exchange]
    
    # 텍스트 입력 (쉼표 또는 줄바꿈으로 구분)
    st.markdown("**Enter token symbols below:**")
    bulk_input = st.text_area(
        "Symbols (comma or space separated)",
        height=200,
        placeholder="Example: BTC, ETH, XRP, DOGE, SOL",
        key="bulk_input",
        help="Enter symbols separated by commas or spaces. Do NOT include /USDT - it will be added automatically."
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("Preview", key="preview_bulk", type="secondary"):
            if bulk_input:
                # 쉼표와 공백으로 구분된 심볼 파싱
                symbols = []
                for line in bulk_input.split('\n'):
                    # 쉼표와 공백 모두 구분자로 처리
                    parts = [s.strip().upper() for s in line.replace(',', ' ').split() if s.strip()]
                    symbols.extend(parts)
                
                # 디버그 정보
                st.info(f"🔍 Debug: Input lines = {len(bulk_input.split(chr(10)))}, Parsed symbols = {symbols}")
                
                pairs = [f"{symbol}/USDT" for symbol in symbols]
                
                # 중복 체크
                existing = set(whitelist.get(exchange_key, []))
                new_pairs = [p for p in pairs if p not in existing]
                duplicate_count = len(pairs) - len(new_pairs)
                
                st.markdown("#### 📊 Preview Summary")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Total Parsed", len(symbols))
                with col_b:
                    st.metric("New Tokens", len(new_pairs))
                with col_c:
                    st.metric("Duplicates", duplicate_count)
                
                if new_pairs:
                    st.markdown("##### ✅ Tokens to Add (alphabetical):")
                    sorted_new = sorted(new_pairs)
                    st.code('\n'.join(sorted_new), language=None)
                else:
                    st.warning("⚠️ All tokens are already in the whitelist!")
                
                if duplicate_count > 0:
                    st.markdown("##### ⚠️ Duplicates (will be skipped):")
                    duplicates = [p for p in pairs if p in existing]
                    st.code('\n'.join(sorted(duplicates)), language=None)
            else:
                st.warning("⚠️ Please enter symbols!")
    
    with col2:
        if st.button("Import All", key="import_bulk", type="primary"):
            if bulk_input:
                # 쉼표와 공백으로 구분된 심볼 파싱
                symbols = []
                for line in bulk_input.split('\n'):
                    # 쉼표와 공백 모두 구분자로 처리
                    parts = [s.strip().upper() for s in line.replace(',', ' ').split() if s.strip()]
                    symbols.extend(parts)
                
                pairs = [f"{symbol}/USDT" for symbol in symbols]
                
                # 기존 리스트에 추가 (중복 제거)
                if exchange_key not in whitelist:
                    whitelist[exchange_key] = []
                
                original_count = len(whitelist[exchange_key])
                whitelist[exchange_key] = list(set(whitelist[exchange_key] + pairs))
                whitelist[exchange_key].sort()
                
                added_count = len(whitelist[exchange_key]) - original_count
                total_count = len(whitelist[exchange_key])
                duplicate_count = len(pairs) - added_count
                
                save_whitelist(whitelist)
                
                # 상세 결과 표시
                st.markdown("#### ✅ Import Complete!")
                
                result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                with result_col1:
                    st.metric("Parsed", len(symbols))
                with result_col2:
                    st.metric("Added", added_count, delta=f"+{added_count}")
                with result_col3:
                    st.metric("Duplicates", duplicate_count)
                with result_col4:
                    st.metric("Total", total_count)
                
                st.success(f"✅ Successfully added {added_count} new tokens to {selected_exchange}!")
                
                # 2초 후 자동 새로고침
                import time
                time.sleep(2)
                st.rerun()
            else:
                st.warning("⚠️ Please enter symbols!")
    
    # 추천 메이저 코인 목록
    st.markdown("---")
    st.markdown("#### 💡 Recommended Major Coins")
    
    recommended = {
        "Layer 1 (20)": "BTC, ETH, BNB, XRP, ADA, SOL, AVAX, DOT, ATOM, NEAR, ALGO, TRX, TON, APT, SUI, SEI, FTM, HBAR, VET, ICP",
        "Layer 2 (10)": "ARB, OP, MATIC, IMX, METIS, MANTA, STRK, ZK, SCROLL, BASE",
        "Meme (10)": "DOGE, SHIB, PEPE, FLOKI, BONK, WIF, MEME, BRETT, POPCAT, MEW",
        "Exchange (15)": "BNB, OKB, GT, MX, KCS, BGB, HT, CRO, FTT, LEO, WOO, BAKE, CAKE, DYDX, GMX",
        "DeFi (15)": "UNI, AAVE, MKR, CRV, COMP, SNX, SUSHI, LDO, LINK, RUNE, LUNA, LUNC, INJ, OSMO, KAVA",
        "Stable (10)": "USDT, USDC, DAI, TUSD, FDUSD, USDD, FRAX, BUSD, USDP, GUSD",
        "Others (20)": "LTC, BCH, ETC, XMR, THETA, SAND, MANA, AXS, GMT, APE, GALA, ENJ, CHZ, FLOW, XTZ, EOS, IOTA, KLAY, QTUM, ZIL"
    }
    
    for category, symbols in recommended.items():
        with st.expander(f"**{category}**"):
            st.code(symbols, language=None)
            if st.button(f"Import {category}", key=f"import_{category}"):
                symbol_list = [s.strip() for s in symbols.split(',')]
                pairs = [f"{symbol}/USDT" for symbol in symbol_list]
                
                if exchange_key not in whitelist:
                    whitelist[exchange_key] = []
                
                original_count = len(whitelist[exchange_key])
                whitelist[exchange_key] = list(set(whitelist[exchange_key] + pairs))
                whitelist[exchange_key].sort()
                
                added_count = len(whitelist[exchange_key]) - original_count
                save_whitelist(whitelist)
                
                st.success(f"✅ Added {added_count} new tokens from {category}!")
                st.rerun()

