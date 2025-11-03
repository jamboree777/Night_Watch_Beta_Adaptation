"""
Manual Token Setup Module
==========================
Complete token setup workflow: Search → Manual Input → Monitoring → Micro Burst
"""

import streamlit as st
import ccxt
import os
import json
import time
import threading
import random
import statistics
from datetime import datetime, timezone


def render_manual_setup():
    """Render complete manual token setup workflow."""
    st.title("⚙️ Manual Token Setup")
    st.caption("Complete workflow: Search Token → Configure Manual Inputs → Start Monitoring → Micro Burst Analysis")
    
    # Initialize session state
    if 'search_done' not in st.session_state:
        st.session_state.search_done = False
    if 'show_monitoring' not in st.session_state:
        st.session_state.show_monitoring = False
    if 'start_accumulation' not in st.session_state:
        st.session_state.start_accumulation = False
    if 'show_manual_inputs_quick' not in st.session_state:
        st.session_state.show_manual_inputs_quick = False
    
    # Step 1: Token Search
    _render_token_search()
    
    # Step 2: Display results and options (if search done)
    if st.session_state.search_done and st.session_state.exchange_data:
        _render_token_info()
        _render_action_buttons()
        
        # Step 3: Manual Inputs (if requested)
        if st.session_state.show_manual_inputs_quick:
            _render_manual_inputs()
        
        # Step 4: Monitoring Dashboard (if requested)
        if st.session_state.show_monitoring:
            _render_monitoring_dashboard()


def _render_token_search():
    """Render token search interface."""
    st.markdown("### 🔍 Step 1: Search Token")
    
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        exchange_options = {
            "Gate.io": "gateio",
            "MEXC": "mexc",
            "KuCoin": "kucoin",
            "Bitget": "bitget",
            "MEXC Assessment Zone": "mexc_assessment"
        }
        selected_exchange = st.selectbox("Exchange", list(exchange_options.keys()))
    
    with col2:
        symbol = st.text_input("Symbol (e.g., BTC/USDT)", placeholder="BTC/USDT")
    
    with col3:
        st.write("")
        st.write("")
        api_key = st.text_input("API Key (optional)", type="password", help="Required for MEXC Assessment Zone")
    
    with col4:
        st.write("")
        st.write("")
        api_secret = st.text_input("API Secret (optional)", type="password")
    
    if st.button("🔍 Search", type="primary", key="search_btn"):
        try:
            exchange_id = exchange_options[selected_exchange]
            symbol = symbol.upper()
            
            # Initialize exchange
            if exchange_id == "mexc_assessment":
                if not api_key or not api_secret:
                    st.error("❌ API Key and Secret required for MEXC Assessment Zone")
                    return
                    
                exchange = ccxt.mexc({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
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
                
                # Get market info and ticker
                market_info = markets[symbol]
                with st.spinner("Fetching ticker data..."):
                    ticker = exchange.fetch_ticker(symbol)
                
                # Store in session state
                st.session_state.exchange_data = {
                    'exchange': exchange,
                    'markets': markets,
                    'market_info': market_info,
                    'ticker': ticker,
                    'symbol': symbol,
                    'exchange_id': exchange_id,
                    'api_key': api_key,
                    'api_secret': api_secret,
                    'last_price': ticker['last']
                }
                st.session_state.search_done = True
                st.session_state.show_orderbook = False
                st.session_state.show_monitoring = False
                st.rerun()
            else:
                st.error(f"❌ {symbol} not found on {selected_exchange}")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


def _render_token_info():
    """Render token information after successful search."""
    data = st.session_state.exchange_data
    market_info = data['market_info']
    ticker = data['ticker']
    symbol = data['symbol']
    
    st.markdown("---")
    st.markdown("### 📋 Token Information")
    
    with st.expander("💰 Price & Volume", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Last Price", f"${ticker.get('last', 0):.8f}")
        with col2:
            st.metric("Best Bid/Ask", f"${ticker.get('bid', 0):.8f} / ${ticker.get('ask', 0):.8f}")
        with col3:
            st.metric("24h Volume", f"${ticker.get('quoteVolume', 0):,.2f}")
        with col4:
            change = ticker.get('percentage', 0)
            st.metric("24h Change", f"{change:+.2f}%")
    
    with st.expander("⚙️ Market Settings"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Price Precision", str(market_info['precision']['price']))
            st.metric("Amount Precision", str(market_info['precision']['amount']))
        
        with col2:
            min_cost = market_info.get('limits', {}).get('cost', {}).get('min', 'N/A')
            st.metric("Min Order Cost", f"${min_cost}" if min_cost != 'N/A' else 'N/A')
        
        with col3:
            maker_fee = market_info.get('maker', 0) * 100
            taker_fee = market_info.get('taker', 0) * 100
            st.metric("Maker/Taker Fee", f"{maker_fee:.2f}% / {taker_fee:.2f}%")


def _render_action_buttons():
    """Render action buttons for next steps."""
    st.markdown("---")
    st.markdown("### 🚀 Step 2: Next Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🛠️ Manual Inputs", type="primary", use_container_width=True):
            st.session_state.show_manual_inputs_quick = not st.session_state.get('show_manual_inputs_quick', False)
            st.rerun()
    
    with col2:
        if st.button("📈 Start Monitoring", type="secondary", use_container_width=True):
            st.session_state.show_monitoring = True
            st.rerun()
    
    with col3:
        if st.button("💾 Save & Accumulate", type="secondary", use_container_width=True):
            st.session_state.start_accumulation = True
            st.success("💾 Data accumulation started!")


def _render_manual_inputs():
    """Render manual inputs configuration."""
    st.markdown("---")
    st.markdown("### ⚙️ Step 3: Manual Inputs Configuration")
    
    data = st.session_state.exchange_data
    exchange_id = data['exchange_id']
    symbol = data['symbol']
    
    # Load existing manual inputs
    manual_inputs_file = "manual_inputs.json"
    manual_inputs = {}
    if os.path.exists(manual_inputs_file):
        try:
            with open(manual_inputs_file, 'r', encoding='utf-8') as f:
                manual_inputs = json.load(f)
        except:
            manual_inputs = {}
    
    token_key = f"{exchange_id}_{symbol.replace('/', '_').lower()}"
    token_inputs = manual_inputs.get(token_key, {})
    
    # Three columns for inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🏦 Exchange User Holdings**")
        cex_price = st.number_input("CEX Price (USDT)", min_value=0.0, value=float(token_inputs.get('cex_price', 0) or 0), step=0.00000001, format="%.8f", key="cex_price")
        cex_market_cap = st.number_input("User Holdings (USDT)", min_value=0.0, value=float(token_inputs.get('cex_market_cap', 0) or 0), step=1000.0, key="cex_cap")
        
        st.markdown("**💰 Listing Price**")
        listing_price = st.number_input("Listing Price (USDT)", min_value=0.0, value=float(token_inputs.get('listing_price', 0) or 0), step=0.00000001, format="%.8f", key="listing_price")
    
    with col2:
        st.markdown("**👥 Estimated Holders**")
        holders_price = st.number_input("Holders Price (USDT)", min_value=0.0, value=float(token_inputs.get('holders_price', 0) or 0), step=0.00000001, format="%.8f", key="holders_price")
        holders_count = st.number_input("Holders Count", min_value=0, value=int(token_inputs.get('holders_count', 0) or 0), step=10, key="holders_count")
        
        st.markdown("**📈 Price Ratio Targets**")
        pr_target = st.number_input("Target (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('price_ratio_target', 10.0)), step=0.5, key="pr_target")
        pr_thresh = st.number_input("Threshold (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('price_ratio_threshold', 1.0)), step=0.1, key="pr_thresh")
    
    with col3:
        st.markdown("**💧 Depth/Spread/Volume**")
        depth_target = st.number_input("±2% Depth Target (USDT)", min_value=0.0, value=float(token_inputs.get('depth_target', 1000) or 0), step=100.0, key="depth_target")
        depth_threshold = st.number_input("±2% Depth Threshold (USDT)", min_value=0.0, value=float(token_inputs.get('depth_threshold', 500) or 0), step=100.0, key="depth_thresh")
        spread_target = st.number_input("Spread Target (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('spread_target', 1.0)), step=0.1, key="spread_target")
        spread_threshold = st.number_input("Spread Threshold (%)", min_value=0.0, max_value=100.0, value=float(token_inputs.get('spread_threshold', 2.0)), step=0.1, key="spread_thresh")
        volume_target = st.number_input("Volume Target (USDT)", min_value=0.0, value=float(token_inputs.get('volume_target', 50000) or 0), step=5000.0, key="volume_target")
        volume_threshold = st.number_input("Volume Threshold (USDT)", min_value=0.0, value=float(token_inputs.get('volume_threshold', 20000) or 0), step=5000.0, key="volume_thresh")
    
    # Additional targets
    st.markdown("#### 🎯 Additional Targets")
    target_col1, target_col2, _ = st.columns(3)
    
    with target_col1:
        st.markdown("**💼 User Holdings Targets**")
        uh_target = st.number_input("User Holdings Target (USDT)", min_value=0.0, value=float(token_inputs.get('user_holdings_target', 150000) or 0), step=10000.0, key="uh_target")
        uh_threshold = st.number_input("User Holdings Threshold (USDT)", min_value=0.0, value=float(token_inputs.get('user_holdings_threshold', 70000) or 0), step=10000.0, key="uh_thresh")
    
    with target_col2:
        st.markdown("**👤 Holders Targets**")
        h_target = st.number_input("Holders Target (Count)", min_value=0, value=int(token_inputs.get('holders_target', 200) or 0), step=10, key="h_target")
        h_threshold = st.number_input("Holders Threshold (Count)", min_value=0, value=int(token_inputs.get('holders_threshold', 100) or 0), step=10, key="h_thresh")
    
    # Save buttons
    save_col1, save_col2 = st.columns(2)
    
    with save_col1:
        if st.button("💾 Save Manual Inputs", type="primary", use_container_width=True):
            manual_inputs[token_key] = {
                'cex_price': cex_price,
                'cex_market_cap': cex_market_cap,
                'listing_price': listing_price,
                'holders_price': holders_price,
                'holders_count': holders_count,
                'price_ratio_target': pr_target,
                'price_ratio_threshold': pr_thresh,
                'depth_target': depth_target,
                'depth_threshold': depth_threshold,
                'spread_target': spread_target,
                'spread_threshold': spread_threshold,
                'volume_target': volume_target,
                'volume_threshold': volume_threshold,
                'user_holdings_target': uh_target,
                'user_holdings_threshold': uh_threshold,
                'holders_target': h_target,
                'holders_threshold': h_threshold
            }
            
            with open(manual_inputs_file, 'w', encoding='utf-8') as f:
                json.dump(manual_inputs, f, indent=2)
            
            st.success("✅ Manual inputs saved!")
    
    with save_col2:
        if st.button("🔄 Update & Close", use_container_width=True):
            manual_inputs[token_key] = {
                'cex_price': cex_price,
                'cex_market_cap': cex_market_cap,
                'listing_price': listing_price,
                'holders_price': holders_price,
                'holders_count': holders_count,
                'price_ratio_target': pr_target,
                'price_ratio_threshold': pr_thresh,
                'depth_target': depth_target,
                'depth_threshold': depth_threshold,
                'spread_target': spread_target,
                'spread_threshold': spread_threshold,
                'volume_target': volume_target,
                'volume_threshold': volume_threshold,
                'user_holdings_target': uh_target,
                'user_holdings_threshold': uh_threshold,
                'holders_target': h_target,
                'holders_threshold': h_threshold
            }
            
            with open(manual_inputs_file, 'w', encoding='utf-8') as f:
                json.dump(manual_inputs, f, indent=2)
            
            st.session_state.show_manual_inputs_quick = False
            st.rerun()


def _render_monitoring_dashboard():
    """Render full monitoring dashboard (from backup version)."""
    st.markdown("---")
    st.markdown("### 📈 Step 4: Real-time Monitoring Dashboard")
    
    data = st.session_state.exchange_data
    exchange = data['exchange']
    symbol = data['symbol']
    exchange_id = data['exchange_id']
    market_info = data['market_info']
    
    try:
        # Fetch fresh data
        with st.spinner("Fetching real-time data..."):
            fresh_ticker = exchange.fetch_ticker(symbol)
            fresh_orderbook = exchange.fetch_order_book(symbol, limit=50)
        
        # Get price precision
        price_precision = market_info['precision']['price']
        if isinstance(price_precision, float) and price_precision < 1:
            decimal_places = len(str(price_precision).split('.')[-1].rstrip('0'))
        else:
            decimal_places = 8
        
        # Calculate spread
        bid_price = fresh_ticker.get('bid', 0)
        ask_price = fresh_ticker.get('ask', 0)
        spread_amount = ask_price - bid_price
        spread_percentage = (spread_amount / bid_price * 100) if bid_price > 0 else 0
        midpoint = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else 0
        
        # Display current price info
        with st.expander("📈 Current Price Info", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Current Price", f"${fresh_ticker.get('last', 0):.{decimal_places}f}")
                st.metric("Midpoint", f"${midpoint:.{decimal_places}f}")
            
            with col2:
                st.metric("SPREAD", f"${spread_amount:.{decimal_places}f} / {spread_percentage:.2f}%")
            
            with col3:
                st.metric("BID/ASK", f"${bid_price:.{decimal_places}f} / ${ask_price:.{decimal_places}f}")
            
            with col4:
                st.metric("24h Volume", f"${fresh_ticker.get('quoteVolume', 0):,.2f}")
                change = fresh_ticker.get('percentage', 0)
                st.metric("24h Change", f"{change:+.2f}%")
        
        # Calculate liquidity in different ranges
        def calculate_liquidity_in_range(orderbook, price_range_percent):
            if midpoint == 0:
                return 0, 0, 0, 0
            
            range_amount = midpoint * price_range_percent / 100
            min_price = midpoint - range_amount
            max_price = midpoint + range_amount
            
            bid_liquidity = 0
            ask_liquidity = 0
            
            for price, amount in orderbook['bids']:
                if min_price <= price <= midpoint:
                    bid_liquidity += amount * price
            
            for price, amount in orderbook['asks']:
                if midpoint <= price <= max_price:
                    ask_liquidity += amount * price
            
            total_liquidity = bid_liquidity + ask_liquidity
            net_liquidity = bid_liquidity - ask_liquidity
            
            return bid_liquidity, ask_liquidity, total_liquidity, net_liquidity
        
        # Calculate for different ranges
        bid_2, ask_2, total_2, net_2 = calculate_liquidity_in_range(fresh_orderbook, 2)
        bid_5, ask_5, total_5, net_5 = calculate_liquidity_in_range(fresh_orderbook, 5)
        bid_10, ask_10, total_10, net_10 = calculate_liquidity_in_range(fresh_orderbook, 10)
        
        # Liquidity Analysis
        st.markdown("### 💧 Liquidity Analysis")
        
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
        current_price = fresh_ticker.get('last', 0)
        
        # ±2% range
        range_2_min = current_price * 0.98
        range_2_max = current_price * 1.02
        asks_2 = [(p, a) for p, a in fresh_orderbook['asks'] if range_2_min <= p <= range_2_max]
        bids_2 = [(p, a) for p, a in fresh_orderbook['bids'] if range_2_min <= p <= range_2_max]
        
        # ±5% range
        range_5_min = current_price * 0.95
        range_5_max = current_price * 1.05
        asks_5 = [(p, a) for p, a in fresh_orderbook['asks'] if range_5_min <= p <= range_5_max]
        bids_5 = [(p, a) for p, a in fresh_orderbook['bids'] if range_5_min <= p <= range_5_max]
        
        # ±10% range
        range_10_min = current_price * 0.90
        range_10_max = current_price * 1.10
        asks_10 = [(p, a) for p, a in fresh_orderbook['asks'] if range_10_min <= p <= range_10_max]
        bids_10 = [(p, a) for p, a in fresh_orderbook['bids'] if range_10_min <= p <= range_10_max]
        
        # Calculate weighted average prices
        ask_weighted_2 = calculate_weighted_price(asks_2, is_ask=True)
        bid_weighted_2 = calculate_weighted_price(bids_2, is_ask=False)
        ask_weighted_5 = calculate_weighted_price(asks_5, is_ask=True)
        bid_weighted_5 = calculate_weighted_price(bids_5, is_ask=False)
        ask_weighted_10 = calculate_weighted_price(asks_10, is_ask=True)
        bid_weighted_10 = calculate_weighted_price(bids_10, is_ask=False)
        
        with st.expander("💧 Liquidity Analysis", expanded=True):
            # Best Bid/Ask SPREAD
            st.metric("Best Bid/Ask SPREAD", f"${spread_amount:.{decimal_places}f} / {spread_percentage:.2f}%")
            
            # WEIGHTED DEPTH CENTER SPREAD (summary)
            st.markdown("#### WEIGHTED DEPTH CENTER SPREAD")
            col_spread1, col_spread2, col_spread3 = st.columns(3)
            
            with col_spread1:
                if ask_weighted_2 > 0 and bid_weighted_2 > 0:
                    weighted_spread_2 = ask_weighted_2 - bid_weighted_2
                    weighted_spread_percentage_2 = (weighted_spread_2 / bid_weighted_2 * 100) if bid_weighted_2 > 0 else 0
                    st.metric("±2% WEIGHTED SPREAD", f"${weighted_spread_2:.{decimal_places}f} / {weighted_spread_percentage_2:.2f}%")
                else:
                    st.metric("±2% WEIGHTED SPREAD", "N/A")
            
            with col_spread2:
                if ask_weighted_5 > 0 and bid_weighted_5 > 0:
                    weighted_spread_5 = ask_weighted_5 - bid_weighted_5
                    weighted_spread_percentage_5 = (weighted_spread_5 / bid_weighted_5 * 100) if bid_weighted_5 > 0 else 0
                    st.metric("±5% WEIGHTED SPREAD", f"${weighted_spread_5:.{decimal_places}f} / {weighted_spread_percentage_5:.2f}%")
                else:
                    st.metric("±5% WEIGHTED SPREAD", "N/A")
            
            with col_spread3:
                if ask_weighted_10 > 0 and bid_weighted_10 > 0:
                    weighted_spread_10 = ask_weighted_10 - bid_weighted_10
                    weighted_spread_percentage_10 = (weighted_spread_10 / bid_weighted_10 * 100) if bid_weighted_10 > 0 else 0
                    st.metric("±10% WEIGHTED SPREAD", f"${weighted_spread_10:.{decimal_places}f} / {weighted_spread_percentage_10:.2f}%")
                else:
                    st.metric("±10% WEIGHTED SPREAD", "N/A")
            
            # Collapsible section for per-range liquidity tables
            with st.expander("📦 Per-Range Liquidity Tables", expanded=False):
                # 구간별 매수지수 (매수/매도)
                st.markdown("#### BID/ASK Ratios")
                col_bid_ask1, col_bid_ask2, col_bid_ask3 = st.columns(3)
                with col_bid_ask1:
                    bid_ask_ratio_2 = bid_2 / ask_2 if ask_2 > 0 else 0
                    st.metric("±2% Bid/Ask Ratio", f"{bid_ask_ratio_2:.3f}")
                with col_bid_ask2:
                    bid_ask_ratio_5 = bid_5 / ask_5 if ask_5 > 0 else 0
                    st.metric("±5% Bid/Ask Ratio", f"{bid_ask_ratio_5:.3f}")
                with col_bid_ask3:
                    bid_ask_ratio_10 = bid_10 / ask_10 if ask_10 > 0 else 0
                    st.metric("±10% Bid/Ask Ratio", f"{bid_ask_ratio_10:.3f}")
                
                st.markdown("---")
                st.markdown("#### Detailed Liquidity by Range")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("**±2% Range**")
                    st.metric("ASK", f"${ask_2:,.2f}")
                    if ask_weighted_2 > 0:
                        st.caption(f"WEIGHTED CENTER: ${ask_weighted_2:.{decimal_places}f}")
                    st.metric("BID", f"${bid_2:,.2f}")
                    if bid_weighted_2 > 0:
                        st.caption(f"WEIGHTED CENTER: ${bid_weighted_2:.{decimal_places}f}")
                    st.metric("Total", f"${total_2:,.2f}")
                    if net_2 >= 0:
                        st.metric("NET LIQ.", f"BID ${abs(net_2):,.2f}")
                    else:
                        st.metric("NET LIQ.", f"ASK ${abs(net_2):,.2f}")
                
                with col2:
                    st.write("**±5% Range**")
                    st.metric("ASK", f"${ask_5:,.2f}")
                    if ask_weighted_5 > 0:
                        st.caption(f"WEIGHTED CENTER: ${ask_weighted_5:.{decimal_places}f}")
                    st.metric("BID", f"${bid_5:,.2f}")
                    if bid_weighted_5 > 0:
                        st.caption(f"WEIGHTED CENTER: ${bid_weighted_5:.{decimal_places}f}")
                    st.metric("Total", f"${total_5:,.2f}")
                    if net_5 >= 0:
                        st.metric("NET LIQ.", f"BID ${abs(net_5):,.2f}")
                    else:
                        st.metric("NET LIQ.", f"ASK ${abs(net_5):,.2f}")
                
                with col3:
                    st.write("**±10% Range**")
                    st.metric("ASK", f"${ask_10:,.2f}")
                    if ask_weighted_10 > 0:
                        st.caption(f"WEIGHTED CENTER: ${ask_weighted_10:.{decimal_places}f}")
                    st.metric("BID", f"${bid_10:,.2f}")
                    if bid_weighted_10 > 0:
                        st.caption(f"WEIGHTED CENTER: ${bid_weighted_10:.{decimal_places}f}")
                    st.metric("Total", f"${total_10:,.2f}")
                    if net_10 >= 0:
                        st.metric("NET LIQ.", f"BID ${abs(net_10):,.2f}")
                    else:
                        st.metric("NET LIQ.", f"ASK ${abs(net_10):,.2f}")
        
        # Load manual inputs for thresholds
        manual_inputs_file = "manual_inputs.json"
        manual_inputs = {}
        if os.path.exists(manual_inputs_file):
            try:
                with open(manual_inputs_file, 'r', encoding='utf-8') as f:
                    manual_inputs = json.load(f)
            except:
                manual_inputs = {}
        
        token_key = f"{exchange_id}_{symbol.replace('/', '_').lower()}"
        token_inputs = manual_inputs.get(token_key, {})
        
        # ST Thresholds and Target Board
        st.markdown("### 📊 ST Thresholds and Target Board")
        
        monitor_col1, monitor_col2, monitor_col3 = st.columns(3)
        
        with monitor_col1:
            # User Holdings
            cex_cap = token_inputs.get('cex_market_cap', 0)
            user_holdings_target = token_inputs.get('user_holdings_target', 150000)
            user_holdings_threshold = token_inputs.get('user_holdings_threshold', 70000)
            
            if cex_cap > 0:
                if cex_cap <= user_holdings_threshold:
                    st.error(f"❌ CRITICAL - User Holdings ≤ ${user_holdings_threshold:,.0f}: ${cex_cap:,.0f}")
                elif cex_cap <= user_holdings_target:
                    st.warning(f"⚠️ ACTION - User Holdings ${user_holdings_threshold:,.0f}-${user_holdings_target:,.0f}: ${cex_cap:,.0f}")
                else:
                    st.success(f"✅ SAFE - User Holdings > ${user_holdings_target:,.0f}: ${cex_cap:,.0f}")
            else:
                st.info("ℹ️ User Holdings not set")
            
            st.caption(f"Target: >${user_holdings_target:,.0f} | Threshold: ${user_holdings_threshold:,.0f}")
            
            # Price Ratio
            listing_price = token_inputs.get('listing_price', 0)
            price_ratio_target = token_inputs.get('price_ratio_target', 10.0) / 100
            price_ratio_threshold = token_inputs.get('price_ratio_threshold', 1.0) / 100
            
            if listing_price > 0:
                current_price = fresh_ticker.get('last', 0)
                price_ratio = current_price / listing_price if listing_price > 0 else 0
                if price_ratio >= price_ratio_target:
                    st.success(f"✅ SAFE - Price Ratio ≥ {price_ratio_target:.2%}: {price_ratio:.2%}")
                elif price_ratio >= price_ratio_threshold:
                    st.warning(f"⚠️ ACTION - Price Ratio {price_ratio_threshold:.2%}-{price_ratio_target:.2%}: {price_ratio:.2%}")
                else:
                    st.error(f"❌ CRITICAL - Price Ratio < {price_ratio_threshold:.2%}: {price_ratio:.2%}")
            else:
                st.info("ℹ️ Listing price not set")
        
        with monitor_col2:
            # Holders
            holders_target = token_inputs.get('holders_target', 200)
            holders_threshold = token_inputs.get('holders_threshold', 100)
            estimated_holders = token_inputs.get('estimated_holders', 0)
            
            if estimated_holders > 0:
                if estimated_holders <= holders_threshold:
                    st.error(f"❌ CRITICAL - Holders ≤ {holders_threshold}: {estimated_holders}")
                elif estimated_holders <= holders_target:
                    st.warning(f"⚠️ ACTION - Holders {holders_threshold}-{holders_target}: {estimated_holders}")
                else:
                    st.success(f"✅ SAFE - Holders > {holders_target}: {estimated_holders}")
            else:
                st.info("ℹ️ Holders not set")
            
            st.caption(f"Target: >{holders_target} | Threshold: {holders_threshold}")
            
            # Depth
            depth_target = token_inputs.get('depth_target', 1000)
            depth_threshold = token_inputs.get('depth_threshold', 500)
            
            if total_2 < depth_threshold:
                st.error(f"❌ CRITICAL - ±2% Depth < ${depth_threshold:,.0f}: ${total_2:,.0f}")
            elif total_2 < depth_target:
                st.warning(f"⚠️ ACTION - ±2% Depth ${depth_threshold:,.0f}-${depth_target:,.0f}: ${total_2:,.0f}")
            else:
                st.success(f"✅ SAFE - ±2% Depth > ${depth_target:,.0f}: ${total_2:,.0f}")
            
            st.caption(f"Target: >${depth_target:,.0f} | Threshold: ${depth_threshold:,.0f}")
        
        with monitor_col3:
            # Spread
            spread_target = token_inputs.get('spread_target', 1.0)
            spread_threshold = token_inputs.get('spread_threshold', 2.0)
            
            if spread_percentage < spread_target:
                st.success(f"✅ SAFE - Spread < {spread_target:.1f}%: {spread_percentage:.2f}%")
            elif spread_percentage < spread_threshold:
                st.warning(f"⚠️ ACTION - Spread {spread_target:.1f}-{spread_threshold:.1f}%: {spread_percentage:.2f}%")
            else:
                st.error(f"❌ CRITICAL - Spread > {spread_threshold:.1f}%: {spread_percentage:.2f}%")
            
            st.caption(f"Target: <{spread_target:.1f}% | Threshold: {spread_threshold:.1f}%")
            
            # Volume
            volume_target = token_inputs.get('volume_target', 50000)
            volume_threshold = token_inputs.get('volume_threshold', 20000)
            quote_vol = fresh_ticker.get('quoteVolume', 0)
            
            if quote_vol <= volume_threshold:
                st.error(f"❌ CRITICAL - Volume ≤ ${volume_threshold:,.0f}: ${quote_vol:,.0f}")
            elif quote_vol <= volume_target:
                st.warning(f"⚠️ ACTION - Volume ${volume_threshold:,.0f}-${volume_target:,.0f}: ${quote_vol:,.0f}")
            else:
                st.success(f"✅ SAFE - Volume > ${volume_target:,.0f}: ${quote_vol:,.0f}")
            
            st.caption(f"Target: >${volume_target:,.0f} | Threshold: ${volume_threshold:,.0f}")
        
        # Add to Main Board button
        st.markdown("---")
        st.markdown("### 📋 Add to Main Board")
        
        add_col1, add_col2 = st.columns([1, 2])
        
        with add_col1:
            if st.button("📌 Add to Main Board", type="primary", use_container_width=True, key="add_mainboard"):
                ex_id_norm = exchange_id
                if ex_id_norm == "mexc_evaluation":
                    ex_id_norm = "mexc_assessment"
                
                config_file = "monitoring_configs.json"
                configs = {}
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        configs = json.load(f)
                
                config_id = f"{ex_id_norm}_{symbol.replace('/', '_').lower()}"
                existing_started_at = (configs.get(config_id) or {}).get("started_at")
                
                config = {
                    "exchange": ex_id_norm,
                    "symbol": symbol,
                    "started_at": existing_started_at or datetime.now(timezone.utc).isoformat(),
                    "status": "active",
                    "description": f"{symbol} monitoring on {ex_id_norm}"
                }
                
                if exchange_id in ("mexc_evaluation", "mexc_assessment"):
                    if data.get('api_key') and data.get('api_secret'):
                        config["apiKey"] = data['api_key']
                        config["apiSecret"] = data['api_secret']
                
                configs[config_id] = config
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, indent=2)
                
                st.success(f"✅ Added to Main Board: {symbol}")
                st.info("🔗 View on Main Board: http://localhost:8501")
        
        with add_col2:
            st.caption("💡 Click to make this token visible on the Main Board (Crisis Bulletin)")
        
        
        # Micro Burst Section
        st.markdown("---")
        st.markdown("### ⚡ Micro Burst Metrics")
        
        # Micro Burst Settings
        mb_col1, mb_col2, mb_col3 = st.columns(3)
        with mb_col1:
            enable_micro_burst = st.checkbox("Enable Micro Burst", value=st.session_state.get("enable_micro_burst", False))
            st.session_state["enable_micro_burst"] = enable_micro_burst
        
        with mb_col2:
            burst_samples = st.number_input("Samples per burst", min_value=5, max_value=20, value=10, step=1)
            st.session_state["burst_samples"] = int(burst_samples)
        
        with mb_col3:
            burst_interval = st.number_input("Per-sample interval (sec)", min_value=0.1, max_value=1.0, value=0.2, step=0.1)
            st.session_state["burst_interval_s"] = float(burst_interval)
        
        if enable_micro_burst:
            col_btn, col_status = st.columns([1, 3])
            with col_btn:
                if st.button("🚀 Run Burst Now", key="run_burst_now"):
                    with st.spinner("Capturing micro burst..."):
                        frames_now, path_now = _run_micro_burst_now(exchange, exchange_id, symbol)
                        if frames_now:
                            st.success(f"✅ Saved burst: {os.path.basename(path_now)}")
                            st.caption(f"Captured {len(frames_now)} frames")
            
            with col_status:
                if st.session_state.get("last_burst_frames"):
                    st.info(f"📊 Last burst: {len(st.session_state.get('last_burst_frames', []))} frames in memory")
            
            # Display Micro Burst Metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            
            mb_metrics = None
            try:
                # Try to get frames from memory first
                frames = st.session_state.get("last_burst_frames")
                
                # If not in memory, load from file
                if not frames:
                    latest = _latest_micro_burst_path(exchange_id, symbol)
                    if latest:
                        with open(latest, "r", encoding="utf-8") as f:
                            burst = json.load(f)
                        frames = burst.get("frames", [])
                
                if frames:
                    # Calculate mid price
                    mid = 0
                    if fresh_ticker:
                        bid = fresh_ticker.get('bid', 0)
                        ask = fresh_ticker.get('ask', 0)
                        if bid and ask:
                            mid = (bid + ask) / 2
                    
                    # Compute metrics
                    mb_metrics = _compute_micro_burst_metrics(frames, mid)
            
            except Exception as e:
                st.warning(f"⚠️ Failed to load micro burst data: {str(e)}")
            
            # Tooltips
            tip_persist = "Top-3 가격대의 지속성(Jaccard). 0~1. 높을수록 호가 유지/재보급 일관성↑"
            tip_hhi = "±2% 범위 내 공급 노이즈 점유율 HHI. 0~1. 높을수록 소수 집중↑"
            tip_imbv = "±2% 내 (Bid-Ask) 노이즈 불균형의 변동성. 높을수록 초단기 흔들림↑"
            tip_layer = "Top-10 틱 간격의 표준편차. 낮으면 규칙적 레이어링(사다리) 의심"
            tip_flip = "연속 프레임에서 최우선 호가쌍 변화 횟수. 많으면 터치 단 변동 치열"
            
            if mb_metrics:
                # Quote Persistence
                persist_value = mb_metrics['quote_persistence_top3']
                persist_status = "🟢 Stable" if persist_value > 0.7 else "🟡 Variable" if persist_value > 0.3 else "🔴 Unstable"
                with c1:
                    st.metric("Quote Persistence", f"{persist_value:.3f}", help=tip_persist)
                    st.caption(persist_status)
                
                # HHI
                hhi_value = mb_metrics['concentration_hhi_2pct']
                hhi_status = "🟢 Distributed" if hhi_value < 0.3 else "🟡 Concentrated" if hhi_value < 0.7 else "🔴 Monopolized"
                with c2:
                    st.metric("HHI (±2%)", f"{hhi_value:.3f}", help=tip_hhi)
                    st.caption(hhi_status)
                
                # Imbalance Volatility
                imb_value = mb_metrics['imbalance_volatility']
                imb_status = "🟢 Balanced" if imb_value < 1000 else "🟡 Volatile" if imb_value < 5000 else "🔴 Chaotic"
                with c3:
                    st.metric("Imbalance Vol", f"{imb_value:.2f}", help=tip_imbv)
                    st.caption(imb_status)
                
                # Layering Gap STD
                layer_value = mb_metrics['layering_gap_std']
                layer_status = "🔴 Spoofing" if layer_value < 0.001 else "🟡 Regular" if layer_value < 0.01 else "🟢 Natural"
                with c4:
                    st.metric("Layer STD", f"{layer_value:.6f}", help=tip_layer)
                    st.caption(layer_status)
                
                # Touch Flips
                flip_value = mb_metrics['touch_flip_count']
                flip_status = "🔴 Manipulated" if flip_value > 5 else "🟡 Active" if flip_value > 2 else "🟢 Stable"
                with c5:
                    st.metric("Touch Flips", f"{flip_value:.0f}", help=tip_flip)
                    st.caption(flip_status)
                
                # Overall spoofing assessment
                spoofing_score = 0
                if layer_value < 0.001: spoofing_score += 40
                if persist_value < 0.3: spoofing_score += 30
                if flip_value > 5: spoofing_score += 30
                
                if spoofing_score >= 70:
                    st.error(f"🚨 HIGH SPOOFING RISK: {spoofing_score}%")
                elif spoofing_score >= 40:
                    st.warning(f"⚠️ MODERATE SPOOFING RISK: {spoofing_score}%")
                else:
                    st.success(f"✅ LOW SPOOFING RISK: {spoofing_score}%")
            else:
                with c1:
                    st.metric("Quote Persistence", "N/A", help=tip_persist)
                with c2:
                    st.metric("HHI (±2%)", "N/A", help=tip_hhi)
                with c3:
                    st.metric("Imbalance Vol", "N/A", help=tip_imbv)
                with c4:
                    st.metric("Layer STD", "N/A", help=tip_layer)
                with c5:
                    st.metric("Touch Flips", "N/A", help=tip_flip)
                
                st.info("ℹ️ No micro burst data available. Click 'Run Burst Now' to capture.")
        
    except Exception as e:
        st.error(f"❌ Error in monitoring: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


# ===========================
# Micro Burst Helper Functions
# ===========================

def _micro_burst_capture(exchange, symbol, depth=150, samples=10, interval=0.2):
    """Capture micro burst snapshots."""
    frames = []
    successful_captures = 0
    
    for i in range(samples):
        t0 = time.time()
        try:
            ob = exchange.fetch_order_book(symbol, limit=depth)
            
            if ob and 'bids' in ob and 'asks' in ob:
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
        
        sleep_left = interval - (time.time() - t0)
        if sleep_left > 0:
            time.sleep(sleep_left)
    
    return frames


def _save_micro_burst(exchange_id, symbol, frames):
    """Save micro burst data to file."""
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


def _latest_micro_burst_path(exchange_id: str, symbol: str):
    """Get latest micro burst file path."""
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


def _run_micro_burst_now(exchange, exchange_id, symbol):
    """Run micro burst capture now."""
    frames = _micro_burst_capture(
        exchange,
        symbol,
        depth=150,
        samples=st.session_state.get("burst_samples", 10),
        interval=st.session_state.get("burst_interval_s", 0.2),
    )
    path = _save_micro_burst(exchange_id, symbol, frames)
    st.session_state["last_burst_frames"] = frames
    st.session_state["last_burst_path"] = path
    return frames, path


def _compute_micro_burst_metrics(frames, mid_price: float | None = None):
    """Compute micro burst metrics."""
    if not frames:
        return None
    
    try:
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
            bids = frame.get('bids', [])
            asks = frame.get('asks', [])
            
            if not isinstance(bids, list) or not isinstance(asks, list):
                return 0.0, 0.0, 0.0
            
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
            
            tot = sum(sizes)
            hhi = sum((s / tot) ** 2 for s in sizes) if tot > 0 else 0.0
            
            return nb, na, hhi

        persist_ratios = []
        hhis = []
        imb_series = []
        layering_stds = []
        touch_flips = 0
        prev_best = None
        
        for i, fr in enumerate(frames):
            if not isinstance(fr, dict):
                continue
                
            bids = fr.get('bids', [])
            asks = fr.get('asks', [])
            
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

            nb, na, hhi = notional_within(fr, 0.02)
            if hhi > 0:
                hhis.append(hhi)
            if nb > 0 or na > 0:
                imb_series.append(nb - na)

            # Layering analysis
            if bids and asks and len(bids) >= 3:
                try:
                    prices = [float(b[0]) for b in bids[:10] if isinstance(b, (list, tuple)) and len(b) >= 2]
                    if len(prices) >= 3:
                        gaps = [abs(prices[j] - prices[j-1]) for j in range(1, len(prices))]
                        if gaps:
                            layering_stds.append(statistics.pstdev(gaps))
                except:
                    pass

            # Quote persistence
            if i > 0:
                prev = frames[i - 1]
                if isinstance(prev, dict):
                    a_now = set(round(p, 12) for p in top_prices(asks, 3))
                    b_now = set(round(p, 12) for p in top_prices(bids, 3))
                    a_prev = set(round(p, 12) for p in top_prices(prev.get('asks', []), 3))
                    b_prev = set(round(p, 12) for p in top_prices(prev.get('bids', []), 3))
                    
                    def jac(s1, s2):
                        if not s1 and not s2:
                            return 0.0
                        u = len(s1 | s2)
                        return (len(s1 & s2) / u) if u > 0 else 0.0
                    
                    persist_ratio = (jac(a_now, a_prev) + jac(b_now, b_prev)) / 2.0
                    persist_ratios.append(persist_ratio)

        imbalance_volatility = 0.0
        if len(imb_series) >= 2:
            imbalance_volatility = statistics.pstdev(imb_series)
        
        layering_gap_std = 0.0
        if layering_stds:
            layering_gap_std = statistics.mean(layering_stds)
        
        metrics = {
            "quote_persistence_top3": statistics.mean(persist_ratios) if persist_ratios else 0.0,
            "concentration_hhi_2pct": statistics.mean(hhis) if hhis else 0.0,
            "imbalance_volatility": imbalance_volatility,
            "layering_gap_std": layering_gap_std,
            "touch_flip_count": touch_flips,
            "frames_processed": len(frames),
            "valid_frames": len([f for f in frames if isinstance(f, dict) and f.get('bids') and f.get('asks')])
        }
        
        return metrics
        
    except Exception as e:
        return None

