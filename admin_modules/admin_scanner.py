"""
High Risk Scanner Module
=========================
Automated scanner and manual token addition for Main Board.
"""

import streamlit as st
import pandas as pd
import os
import json
import time
import subprocess
from datetime import datetime, timezone


def render_scanner():
    """Render High Risk Scanner section with Automated and Manual tabs."""
    st.title("🔍 High Risk Scanner")
    st.caption("Discover and add high-risk tokens to Main Board")
    
    # Sub-tabs for Scanner
    scanner_tab = st.radio(
        "Select:",
        ["🤖 All Scan (정규스캔)", "📬 Token Requests", "➕ Manual Addition", "⚪ Whitelist"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("---")

    if scanner_tab == "🤖 All Scan (정규스캔)":
        _render_automated_scanner()
    elif scanner_tab == "📬 Token Requests":
        _render_token_requests()
    elif scanner_tab == "➕ Manual Addition":
        _render_manual_addition()
    elif scanner_tab == "⚪ Whitelist":
        from admin_modules.admin_whitelist import render_whitelist_management
        render_whitelist_management()


def _render_automated_scanner():
    """Render Automated Scanner section (All Scan)."""
    # Load scanner config
    scanner_config_file = "config/scanner_config.json"
    if os.path.exists(scanner_config_file):
        with open(scanner_config_file, 'r', encoding='utf-8') as f:
            scanner_config = json.load(f)
    else:
        scanner_config = _get_default_scanner_config()
    
    # Render sub-sections
    _render_scheduler_settings(scanner_config, scanner_config_file)
    st.markdown("---")
    _render_exchange_thresholds(scanner_config, scanner_config_file)
    st.markdown("---")
    _render_manual_scan(scanner_config)
    st.markdown("---")
    _render_scan_results()


def _render_token_requests():
    """Render Token Requests from PRO users."""
    st.markdown("### 📬 Token Monitoring Requests")
    st.caption("Review and approve/reject token monitoring requests from PRO users")
    
    # Load pending requests
    requests_file = "token_requests.json"
    if not os.path.exists(requests_file):
        st.info("📭 No pending requests")
        st.caption("PRO users can submit token monitoring requests from User Dashboard")
        return
    
    try:
        with open(requests_file, 'r', encoding='utf-8') as f:
            all_requests = json.load(f)
    except Exception as e:
        st.error(f"❌ Error loading requests: {e}")
        return
    
    # Filter requests by status
    status_filter = st.radio(
        "Status:",
        ["⏳ Pending", "✅ Approved", "❌ Rejected", "📋 All"],
        horizontal=True,
        key="request_status_filter"
    )
    
    # Map status filter to internal status
    status_map = {
        "⏳ Pending": "pending",
        "✅ Approved": "approved",
        "❌ Rejected": "rejected",
        "📋 All": "all"
    }
    selected_status = status_map[status_filter]
    
    # Filter requests
    if selected_status == "all":
        filtered_requests = all_requests
    else:
        filtered_requests = {k: v for k, v in all_requests.items() if v.get('status') == selected_status}
    
    if not filtered_requests:
        st.info(f"📭 No {selected_status} requests")
        return
    
    st.markdown(f"**{len(filtered_requests)} request(s)**")
    st.markdown("---")
    
    # Display each request
    for request_id, request in filtered_requests.items():
        user_id = request.get('user_id', 'Unknown')
        exchange = request.get('exchange', 'Unknown')
        symbol = request.get('symbol', 'Unknown')
        status = request.get('status', 'pending')
        submitted_at = request.get('submitted_at', 'Unknown')
        note = request.get('note', '')
        
        # Status icon
        status_icon = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }.get(status, '❓')
        
        with st.expander(f"{status_icon} {exchange.upper()} {symbol} - User: {user_id}", expanded=(status == 'pending')):
            req_col1, req_col2 = st.columns([2, 1])
            
            with req_col1:
                st.markdown(f"**Exchange:** {exchange.upper()}")
                st.markdown(f"**Symbol:** {symbol}")
                st.markdown(f"**User ID:** {user_id}")
                st.markdown(f"**Submitted:** {submitted_at[:19]}")
                if note:
                    st.markdown(f"**Note:** {note}")
            
            with req_col2:
                st.markdown(f"**Status:** {status.upper()}")
            
            # Show approval/rejection UI only for pending requests
            if status == 'pending':
                st.markdown("---")
                st.markdown("#### ⚙️ Review & Configure")
                
                # Fetch real-time data
                try:
                    import ccxt
                    
                    # Handle MEXC Assessment Zone
                    api_key = None
                    api_secret = None
                    original_exchange = exchange
                    
                    if exchange == "mexc_assessment":
                        # Load API credentials
                        config_file = "monitoring_configs.json"
                        if os.path.exists(config_file):
                            with open(config_file, 'r', encoding='utf-8') as f:
                                configs = json.load(f)
                                for token_id, config in configs.items():
                                    if 'apiKey' in config and 'mexc' in token_id.lower():
                                        api_key = config.get('apiKey')
                                        api_secret = config.get('apiSecret')
                                        break
                        exchange = "mexc"
                    
                    # Initialize exchange
                    exchange_class = getattr(ccxt, exchange)
                    if exchange == "mexc" and api_key:
                        ex = exchange_class({
                            'apiKey': api_key,
                            'secret': api_secret,
                            'options': {'defaultType': 'spot'}
                        })
                    else:
                        ex = exchange_class()
                    
                    ex.load_markets()
                    
                    if symbol not in ex.markets:
                        st.error(f"❌ {symbol} not found on {exchange.upper()}")
                    else:
                        # Fetch data
                        ticker = ex.fetch_ticker(symbol)
                        orderbook = ex.fetch_order_book(symbol, limit=50)
                        
                        bid = ticker.get('bid', 0)
                        ask = ticker.get('ask', 0)
                        mid = (bid + ask) / 2 if bid and ask else 0
                        spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 0
                        volume_24h = ticker.get('quoteVolume', 0)
                        
                        # Calculate ±2% depth
                        if mid > 0:
                            upper_2pct = mid * 1.02
                            lower_2pct = mid * 0.98
                            bid_liq = sum(price * amount for price, amount in orderbook['bids'] if price >= lower_2pct)
                            ask_liq = sum(price * amount for price, amount in orderbook['asks'] if price <= upper_2pct)
                            total_liq = bid_liq + ask_liq
                        else:
                            total_liq = 0
                        
                        # Display metrics
                        metric_col1, metric_col2, metric_col3 = st.columns(3)
                        with metric_col1:
                            st.metric("Current Price", f"${mid:.8f}")
                        with metric_col2:
                            st.metric("Spread", f"{spread_pct:.2f}%")
                        with metric_col3:
                            st.metric("±2% Depth", f"${total_liq:,.2f}")
                        
                        # Configuration inputs (same as Manual Addition)
                        with st.form(key=f"approve_form_{request_id}"):
                            st.markdown("##### 🎯 Set Thresholds & Targets")
                            
                            config_col1, config_col2 = st.columns(2)
                            
                            with config_col1:
                                st.markdown("**Thresholds**")
                                spread_threshold = st.number_input("Spread (%)", min_value=0.0, value=2.0, step=0.1, key=f"st_{request_id}")
                                depth_threshold = st.number_input("Depth ($)", min_value=0.0, value=500.0, step=50.0, key=f"dt_{request_id}")
                                volume_threshold = st.number_input("Volume ($)", min_value=0.0, value=20000.0, step=1000.0, key=f"vt_{request_id}")
                            
                            with config_col2:
                                st.markdown("**Targets**")
                                spread_target = st.number_input("Spread (%)", min_value=0.0, value=1.0, step=0.1, key=f"sta_{request_id}")
                                depth_target = st.number_input("Depth ($)", min_value=0.0, value=1000.0, step=100.0, key=f"dta_{request_id}")
                                volume_target = st.number_input("Volume ($)", min_value=0.0, value=50000.0, step=5000.0, key=f"vta_{request_id}")
                            
                            action_col1, action_col2 = st.columns(2)
                            with action_col1:
                                approve_btn = st.form_submit_button("✅ Approve & Add", type="primary", use_container_width=True)
                            with action_col2:
                                reject_btn = st.form_submit_button("❌ Reject", use_container_width=True)
                            
                            if approve_btn:
                                # Add to monitoring
                                token_id = f"{original_exchange}_{symbol.replace('/', '_').lower()}"
                                
                                # Update monitoring_configs.json
                                config_file = "monitoring_configs.json"
                                monitoring_configs = {}
                                if os.path.exists(config_file):
                                    with open(config_file, 'r', encoding='utf-8') as f:
                                        monitoring_configs = json.load(f)
                                
                                new_config = {
                                    "exchange": original_exchange,
                                    "symbol": symbol,
                                    "started_at": datetime.now(timezone.utc).isoformat(),
                                    "status": "active",
                                    "description": f"{symbol} monitoring on {original_exchange}",
                                    "requested_by": user_id
                                }
                                
                                if original_exchange == "mexc_assessment" and api_key:
                                    new_config["apiKey"] = api_key
                                    new_config["apiSecret"] = api_secret
                                
                                monitoring_configs[token_id] = new_config
                                
                                # Update manual_inputs.json
                                manual_inputs_file = "manual_inputs.json"
                                manual_inputs = {}
                                if os.path.exists(manual_inputs_file):
                                    with open(manual_inputs_file, 'r', encoding='utf-8') as f:
                                        manual_inputs = json.load(f)
                                
                                manual_inputs[token_id] = {
                                    "spread_threshold": spread_threshold,
                                    "spread_target": spread_target,
                                    "depth_threshold": depth_threshold,
                                    "depth_target": depth_target,
                                    "volume_threshold": volume_threshold,
                                    "volume_target": volume_target
                                }
                                
                                # Save files
                                with open(config_file, 'w', encoding='utf-8') as f:
                                    json.dump(monitoring_configs, f, indent=2, ensure_ascii=False)
                                with open(manual_inputs_file, 'w', encoding='utf-8') as f:
                                    json.dump(manual_inputs, f, indent=2, ensure_ascii=False)
                                
                                # Update request status
                                all_requests[request_id]['status'] = 'approved'
                                all_requests[request_id]['approved_at'] = datetime.now(timezone.utc).isoformat()
                                with open(requests_file, 'w', encoding='utf-8') as f:
                                    json.dump(all_requests, f, indent=2, ensure_ascii=False)
                                
                                st.success(f"✅ Request approved! {symbol} added to monitoring")
                                time.sleep(2)
                                st.rerun()
                            
                            elif reject_btn:
                                # Update request status
                                all_requests[request_id]['status'] = 'rejected'
                                all_requests[request_id]['rejected_at'] = datetime.now(timezone.utc).isoformat()
                                with open(requests_file, 'w', encoding='utf-8') as f:
                                    json.dump(all_requests, f, indent=2, ensure_ascii=False)
                                
                                st.warning(f"❌ Request rejected")
                                time.sleep(2)
                                st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            
            elif status == 'approved':
                st.success(f"✅ Approved on {request.get('approved_at', 'Unknown')[:19]}")
            elif status == 'rejected':
                st.warning(f"❌ Rejected on {request.get('rejected_at', 'Unknown')[:19]}")


def _render_manual_addition():
    """Render Manual Token Addition section."""
    st.markdown("### ➕ Manual Token Addition")
    st.caption("Search and add individual tokens to Main Board with custom thresholds")
    
    # Search form
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        exchange = st.selectbox(
            "Exchange",
            ["gateio", "mexc", "kucoin", "bitget", "mexc_assessment"],
            format_func=lambda x: "MEXC Assessment Zone" if x == "mexc_assessment" else x.upper(),
            key="manual_exchange"
        )
    
    with col2:
        symbol = st.text_input("Symbol (e.g., BTC/USDT)", placeholder="BTC/USDT", key="manual_symbol")
    
    with col3:
        st.write("")
        st.write("")
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
    
    if search_btn and symbol:
        # Validate symbol format
        if "/" not in symbol:
            st.error("❌ Invalid format. Use: BASE/QUOTE (e.g., BTC/USDT)")
            return
        
        with st.spinner(f"🔍 Searching {symbol} on {exchange.upper()}..."):
            try:
                import ccxt
                
                # Initialize variables for API credentials
                api_key = None
                api_secret = None
                
                # Store original exchange selection
                original_exchange = exchange
                
                # Handle MEXC Assessment Zone (use existing API key)
                if exchange == "mexc_assessment":
                    # Load existing API credentials from monitoring_configs.json
                    config_file = "monitoring_configs.json"
                    
                    if os.path.exists(config_file):
                        with open(config_file, 'r', encoding='utf-8') as f:
                            configs = json.load(f)
                            # Find MEXC API credentials
                            for token_id, config in configs.items():
                                if 'apiKey' in config and 'mexc' in token_id.lower():
                                    api_key = config.get('apiKey')
                                    api_secret = config.get('apiSecret')
                                    break
                    
                    if not api_key:
                        st.error("❌ MEXC API credentials not found in monitoring_configs.json")
                        st.info("💡 Please add API key to an existing MEXC token first")
                        return
                    
                    # Use MEXC with API credentials
                    exchange = "mexc"
                    st.info("🔐 Using whitelisted MEXC API key for Assessment Zone")
                
                # Initialize exchange
                exchange_class = getattr(ccxt, exchange)
                
                # Use API credentials if available (for MEXC Assessment Zone)
                if exchange == "mexc" and api_key:
                    ex = exchange_class({
                        'apiKey': api_key,
                        'secret': api_secret,
                        'options': {'defaultType': 'spot'}
                    })
                else:
                    ex = exchange_class()
                
                ex.load_markets()
                
                # Check if market exists
                if symbol not in ex.markets:
                    st.error(f"❌ {symbol} not found on {exchange.upper()}")
                    st.info(f"💡 Available markets: {', '.join(list(ex.markets.keys())[:10])}...")
                    return
                
                # Fetch real-time data
                ticker = ex.fetch_ticker(symbol)
                orderbook = ex.fetch_order_book(symbol, limit=50)
                
                bid = ticker.get('bid', 0)
                ask = ticker.get('ask', 0)
                mid = (bid + ask) / 2 if bid and ask else 0
                spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 0
                volume_24h = ticker.get('quoteVolume', 0)
                
                # Calculate ±2% depth
                if mid > 0:
                    upper_2pct = mid * 1.02
                    lower_2pct = mid * 0.98
                    
                    bid_liq = sum(price * amount for price, amount in orderbook['bids'] if price >= lower_2pct)
                    ask_liq = sum(price * amount for price, amount in orderbook['asks'] if price <= upper_2pct)
                    total_liq = bid_liq + ask_liq
                else:
                    total_liq = 0
                
                # Display results
                st.success(f"✅ Found: {symbol} on {exchange.upper()}")
                
                st.markdown("---")
                st.markdown("#### 📊 Real-Time Data")
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric("Spread", f"{spread_pct:.2f}%")
                with metric_col2:
                    st.metric("±2% Depth", f"${total_liq:,.2f}")
                with metric_col3:
                    st.metric("24h Volume", f"${volume_24h:,.0f}")
                
                st.markdown("---")
                st.markdown("#### 📋 Token Information")
                
                info_col1, info_col2, info_col3 = st.columns(3)
                with info_col1:
                    st.metric("Current Price", f"${mid:.8f}")
                    st.metric("Spread", f"{spread_pct:.2f}%")
                with info_col2:
                    st.metric("±2% Depth", f"${total_liq:,.2f}")
                    st.metric("Best Bid/Ask", f"${bid:.8f} / ${ask:.8f}")
                with info_col3:
                    st.metric("24h Volume", f"${volume_24h:,.0f}")
                    # Get price precision
                    price_precision = ex.markets[symbol].get('precision', {}).get('price', 1e-8)
                    st.metric("Price Precision", f"{price_precision:.8f}")
                
                st.markdown("---")
                
                # Wrap everything in a form to prevent auto-refresh
                with st.form(key="manual_addition_form"):
                    st.markdown("#### ⚙️ Liquidity Thresholds & Targets")
                    st.caption("Set minimum acceptable levels (Threshold) and ideal goals (Target)")
                    
                    thresh_col1, thresh_col2 = st.columns(2)
                    
                    with thresh_col1:
                        st.markdown("**🚨 Thresholds (Alert Level)**")
                        spread_threshold = st.number_input("Spread Threshold (%)", min_value=0.0, value=2.0, step=0.1, key="manual_spread_thresh", help="Alert if spread exceeds this")
                        depth_threshold = st.number_input("±2% Depth Threshold ($)", min_value=0.0, value=500.0, step=50.0, key="manual_depth_thresh", help="Alert if depth falls below this")
                        volume_threshold = st.number_input("24h Volume Threshold ($)", min_value=0.0, value=20000.0, step=1000.0, key="manual_volume_thresh", help="Alert if volume falls below this")
                    
                    with thresh_col2:
                        st.markdown("**🎯 Targets (Ideal Level)**")
                        spread_target = st.number_input("Spread Target (%)", min_value=0.0, value=1.0, step=0.1, key="manual_spread_target", help="Ideal spread to maintain")
                        depth_target = st.number_input("±2% Depth Target ($)", min_value=0.0, value=1000.0, step=100.0, key="manual_depth_target", help="Ideal depth to maintain")
                        volume_target = st.number_input("24h Volume Target ($)", min_value=0.0, value=50000.0, step=5000.0, key="manual_volume_target", help="Ideal daily volume")
                
                    st.markdown("---")
                    
                    # Submit button inside form
                    submit_btn = st.form_submit_button("➕ Add to Main Board", type="primary", use_container_width=True)
                
                # Advanced settings outside form (optional, can be added later)
                st.markdown("#### 📊 Advanced Monitoring Settings (Optional)")
                st.caption("These settings are optional and can be configured later")
                
                with st.expander("💰 Price & Listing Settings", expanded=False):
                    listing_col1, listing_col2 = st.columns(2)
                    with listing_col1:
                        listing_price = st.number_input("Listing Price ($)", min_value=0.0, value=0.0, step=0.00000001, format="%.8f", key="manual_listing_price", help="Initial listing price for ratio tracking")
                        price_ratio_target = st.number_input("Price Ratio Target (%)", min_value=0.0, value=10.0, step=1.0, key="manual_price_ratio_target", help="Target % of listing price")
                    with listing_col2:
                        price_ratio_threshold = st.number_input("Price Ratio Threshold (%)", min_value=0.0, value=1.0, step=0.5, key="manual_price_ratio_thresh", help="Alert if below this % of listing")
                
                with st.expander("🏦 CEX Holdings & Market Cap", expanded=False):
                    cex_col1, cex_col2 = st.columns(2)
                    with cex_col1:
                        st.markdown("**Current Holdings Data**")
                        cex_cap = st.number_input("CEX Holdings ($)", min_value=0.0, value=0.0, step=1000.0, key="manual_cex_cap", help="Current total CEX holdings value")
                        cex_price = st.number_input("Measurement Price ($)", min_value=0.0, value=0.0, step=0.00000001, format="%.8f", key="manual_cex_price", help="Price when holdings were measured")
                        cex_market_cap = st.number_input("Market Cap at Measurement ($)", min_value=0.0, value=0.0, step=1000.0, key="manual_cex_mcap", help="Market cap when holdings were measured")
                    with cex_col2:
                        st.markdown("**Target Levels**")
                        user_holdings_target = st.number_input("Holdings Target ($)", min_value=0.0, value=150000.0, step=10000.0, key="manual_holdings_target", help="Target total user holdings value")
                        user_holdings_threshold = st.number_input("Holdings Threshold ($)", min_value=0.0, value=70000.0, step=5000.0, key="manual_holdings_thresh", help="Alert if holdings fall below")
                
                with st.expander("👥 Holder Count & Community", expanded=False):
                    holder_col1, holder_col2 = st.columns(2)
                    with holder_col1:
                        st.markdown("**Current Holder Data**")
                        estimated_holders = st.number_input("Current Estimated Holders", min_value=0, value=0, step=1, key="manual_est_holders", help="Current estimated number of holders")
                        holders_price = st.number_input("Holder Measurement Price ($)", min_value=0.0, value=0.0, step=0.00000001, format="%.8f", key="manual_holders_price", help="Price when holders were counted")
                        holders_count = st.number_input("Actual Holder Count", min_value=0, value=0, step=1, key="manual_holders_count", help="Actual holder count at measurement")
                    with holder_col2:
                        st.markdown("**Target Levels**")
                        holders_target = st.number_input("Holders Target", min_value=0, value=200, step=10, key="manual_holders_target", help="Target number of holders with $5+")
                        holders_threshold = st.number_input("Holders Threshold", min_value=0, value=100, step=10, key="manual_holders_thresh", help="Alert if holders fall below")
                
                if submit_btn:
                    # Import TokenManager
                    from modules.token_manager import TokenManager
                    tm = TokenManager()
                    
                    # Add to monitoring_configs.json
                    config_file = "monitoring_configs.json"
                    monitoring_configs = {}
                    if os.path.exists(config_file):
                        with open(config_file, 'r', encoding='utf-8') as f:
                            monitoring_configs = json.load(f)
                    
                    token_id = f"{original_exchange}_{symbol.replace('/', '_').lower()}"
                    new_config = {
                        "exchange": original_exchange,
                        "symbol": symbol,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "status": "active",
                        "description": f"{symbol} monitoring on {original_exchange}"
                    }
                    
                    # Add API credentials for MEXC Assessment Zone
                    if original_exchange == "mexc_assessment" and api_key:
                        new_config["apiKey"] = api_key
                        new_config["apiSecret"] = api_secret
                    
                    monitoring_configs[token_id] = new_config
                    
                    # Add to tokens_unified.json via TokenManager
                    token_data = {
                        "id": token_id,
                        "exchange": original_exchange,
                        "symbol": symbol,
                        "lifecycle": {
                            "status": "MAIN_BOARD",
                            "main_board_entry": datetime.now(timezone.utc).isoformat(),
                            "manual_addition": True,  # 수동 추가 플래그
                            "added_by": "admin"
                        },
                        "monitoring": {
                            "spread_threshold": spread_threshold,
                            "depth_threshold": depth_threshold,
                            "volume_threshold": volume_threshold
                        }
                    }
                    tm.update_token(token_data)
                    
                    # Save all custom monitoring settings to manual_inputs.json
                    manual_inputs_file = "manual_inputs.json"
                    manual_inputs = {}
                    if os.path.exists(manual_inputs_file):
                        with open(manual_inputs_file, 'r', encoding='utf-8') as f:
                            manual_inputs = json.load(f)
                    
                    manual_inputs[token_id] = {
                        # Liquidity thresholds & targets
                        "spread_threshold": spread_threshold,
                        "spread_target": spread_target,
                        "depth_threshold": depth_threshold,
                        "depth_target": depth_target,
                        "volume_threshold": volume_threshold,
                        "volume_target": volume_target,
                        
                        # Price & listing
                        "listing_price": listing_price,
                        "price_ratio_target": price_ratio_target,
                        "price_ratio_threshold": price_ratio_threshold,
                        
                        # CEX Holdings & Market Cap
                        "cex_cap": cex_cap,
                        "cex_price": cex_price,
                        "cex_market_cap": cex_market_cap,
                        "user_holdings_target": user_holdings_target,
                        "user_holdings_threshold": user_holdings_threshold,
                        
                        # Holder Count & Community
                        "estimated_holders": estimated_holders,
                        "holders_price": holders_price,
                        "holders_count": holders_count,
                        "holders_target": holders_target,
                        "holders_threshold": holders_threshold
                    }
                    
                    # Save files
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(monitoring_configs, f, indent=2, ensure_ascii=False)
                    
                    with open(manual_inputs_file, 'w', encoding='utf-8') as f:
                        json.dump(manual_inputs, f, indent=2, ensure_ascii=False)
                    
                    st.success(f"✅ {symbol} added to monitoring system!")
                    st.info(f"📊 View real-time analytics: http://localhost:8502 (User Dashboard)")
                    st.info(f"🚨 View on Main Board: http://localhost:8501")
                    st.caption(f"💾 Saved to monitoring_configs.json and manual_inputs.json")
                    time.sleep(3)
                    st.rerun()
                
            except ccxt.NetworkError as e:
                st.error(f"❌ Network Error: {e}")
            except ccxt.ExchangeError as e:
                st.error(f"❌ Exchange Error: {e}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    elif search_btn and not symbol:
        st.warning("⚠️ Please enter a symbol")


def _render_scheduler_settings(scanner_config, config_file):
    """Render Automated Scan Scheduler settings."""
    st.markdown("#### 📅 Automated Scan Scheduler")
    st.caption("Configure automatic scanning for all active exchanges")
    
    scheduler_config = scanner_config.get('scheduler', {
        'enabled': False,
        'scan_interval_hours': 4,
        'next_scan_time': None,
        'last_scan_time': None,
        'run_on_start': False
    })
    
    # Global Settings
    st.markdown("##### ⚙️ Global Settings")
    
    sched_col1, sched_col2, sched_col3, sched_col4, sched_col5 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5])
    
    config_changed = False
    
    with sched_col1:
        scheduler_enabled = st.checkbox(
            "✅ Enable Scheduler",
            value=scheduler_config.get('enabled', False),
            key="scheduler_enabled",
            help="Automatically scan all active exchanges at scheduled intervals"
        )
        if scheduler_enabled != scheduler_config.get('enabled', False):
            scanner_config['scheduler']['enabled'] = scheduler_enabled
            config_changed = True
    
    with sched_col2:
        scan_interval = st.selectbox(
            "⏰ Scan Interval (hours)",
            options=[1, 2, 3, 4, 6, 12],
            index=[1, 2, 3, 4, 6, 12].index(scheduler_config.get('scan_interval_hours', 4)),
            key="scheduler_interval",
            help="All active exchanges will be scanned every X hours",
            format_func=lambda x: f"{x}h"
        )
        if scan_interval != scheduler_config.get('scan_interval_hours', 4):
            scanner_config['scheduler']['scan_interval_hours'] = scan_interval
            config_changed = True
    
    with sched_col3:
        st.info("📊 Configure in System Settings → Main Board Policy")
    
    with sched_col4:
        merge_policy = st.selectbox(
            "🔄 Data Policy (deprecated)",
            options=['keep_existing', 'clear_and_restart'],
            index=0 if scheduler_config.get('data_merge_policy', 'keep_existing') == 'keep_existing' else 1,
            key="scheduler_merge_policy",
            help="Keep existing: Merge old data | Clear and restart: Delete old data",
            format_func=lambda x: "Keep Existing" if x == 'keep_existing' else "Clear & Restart"
        )
        if merge_policy != scheduler_config.get('data_merge_policy', 'keep_existing'):
            scanner_config['scheduler']['data_merge_policy'] = merge_policy
            config_changed = True
    
    with sched_col5:
        run_on_start = st.checkbox(
            "🚀 Run on Start",
            value=scheduler_config.get('run_on_start', False),
            key="scheduler_run_on_start",
            help="If enabled, scan immediately when scheduler starts. If disabled, wait for scheduled time."
        )
        if run_on_start != scheduler_config.get('run_on_start', False):
            scanner_config['scheduler']['run_on_start'] = run_on_start
            config_changed = True
    
    # Scheduler Status
    if scheduler_enabled:
        st.markdown("---")
        st.markdown("##### 📊 Scheduler Status")
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            # 실제 마지막 스캔 시간: exchanges.*.last_scan_time 중 최신 vs scheduler.last_scan_time
            last_scan_dt = None
            scan_source = ""
            
            # 1. exchanges.*.last_scan_time 중 가장 최근 시간 찾기
            for ex_id, ex_config in scanner_config.get('exchanges', {}).items():
                ex_last_scan = ex_config.get('last_scan_time')
                if ex_last_scan:
                    try:
                        ex_dt = datetime.fromisoformat(ex_last_scan.replace('Z', '+00:00'))
                        if not last_scan_dt or ex_dt > last_scan_dt:
                            last_scan_dt = ex_dt
                            scan_source = f"{ex_id} scan"
                    except:
                        pass
            
            # 2. scheduler.last_scan_time 확인 (자동 스케줄러)
            scheduler_last_scan = scheduler_config.get('last_scan_time')
            if scheduler_last_scan:
                try:
                    scheduler_dt = datetime.fromisoformat(scheduler_last_scan.replace('Z', '+00:00'))
                    if not last_scan_dt or scheduler_dt > last_scan_dt:
                        last_scan_dt = scheduler_dt
                        scan_source = "auto scheduler"
                except:
                    pass
            
            # 3. 표시
            if last_scan_dt:
                time_ago = datetime.now(timezone.utc) - last_scan_dt
                minutes_ago = int(time_ago.total_seconds() / 60)
                hours_ago = minutes_ago // 60
                mins_rem = minutes_ago % 60
                if hours_ago > 0:
                    time_str = f"{hours_ago}h {mins_rem}m ago"
                else:
                    time_str = f"{minutes_ago}m ago"
                st.metric("Last Scan", time_str, 
                         help=f"{last_scan_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}\nSource: {scan_source}")
            else:
                st.metric("Last Scan", "Never")
        
        with status_col2:
            next_scan_str = scheduler_config.get('next_scan_time')
            if next_scan_str:
                try:
                    next_dt = datetime.fromisoformat(next_scan_str.replace('Z', '+00:00'))
                    time_until = next_dt - datetime.now(timezone.utc)
                    minutes_until = int(time_until.total_seconds() / 60)
                    if minutes_until > 0:
                        st.metric("Next Scan", f"in {minutes_until} min", 
                                 help=next_dt.strftime('%Y-%m-%d %H:%M:%S UTC'))
                    else:
                        st.metric("Next Scan", "Now", 
                                 help=next_dt.strftime('%Y-%m-%d %H:%M:%S UTC'))
                except:
                    st.metric("Next Scan", "N/A")
            else:
                st.metric("Next Scan", "Not scheduled")
        
        with status_col3:
            history_days = scanner_config.get('global', {}).get('default_history_days', 2)
            expected_scans = (history_days * 24) // scan_interval
            st.metric("Expected Scans", f"{expected_scans} per period", 
                     help=f"{history_days} days × (24h ÷ {scan_interval}h)")
        
        # Active exchanges
        active_exchanges = [ex_id.upper() for ex_id, ex_cfg in scanner_config['exchanges'].items() if ex_cfg.get('enabled', True)]
        st.info(f"📌 Active Exchanges: {', '.join(active_exchanges)}")
    else:
        st.warning("⚠️ Scheduler is disabled. Enable it to start automatic scanning.")
    
    # Save config if changed
    if config_changed:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(scanner_config, f, indent=2, ensure_ascii=False)
        st.success("✅ Scheduler settings saved!")
        st.rerun()
    
    # 스케줄러 프로세스 상태 확인
    st.markdown("---")
    st.markdown("##### 🔄 Scheduler Process Status")
    
    import subprocess
    try:
        # Windows에서 Python 프로세스 확인
        result = subprocess.run(
            ['powershell', '-Command', 
             "Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object { Get-WmiObject Win32_Process -Filter \"ProcessId = $($_.Id)\" | Select-Object CommandLine }"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        processes = result.stdout
        batch_scheduler_running = 'scanner_scheduler' in processes

        if batch_scheduler_running:
            st.success("✅ All Scan Scheduler: **실행 중**")
        else:
            st.info("ℹ️ All Scan Scheduler: **중지됨** (수동 스캔으로 대체 가능)")

            # 스케줄러 시작 방법 안내 (expander로 감춤)
            with st.expander("📖 스케줄러 시작 방법 보기"):
                st.markdown("""
                프로덕션 환경에서는 `start_all_fixed.bat`를 실행하면
                모든 대시보드와 스케줄러가 자동으로 시작됩니다.

                개별 시작:
                - All Scan: `python scanner_scheduler.py start`
                """)
    except Exception as e:
        st.warning(f"⚠️ 프로세스 상태를 확인할 수 없습니다: {e}")


def _render_exchange_thresholds(scanner_config, config_file):
    """Render Exchange-Specific Thresholds."""
    st.markdown("#### ⚙️ Exchange-Specific Thresholds")
    st.caption("Customize spread, depth, and volume thresholds for each exchange")
    
    config_changed = False
    
    for exchange_id in ['gateio', 'mexc', 'kucoin', 'bitget']:
        ex_config = scanner_config['exchanges'][exchange_id]
        
        # Last scan time
        last_scan = ex_config.get('last_scan_time', None)
        if last_scan:
            try:
                last_dt = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                time_ago = datetime.now(timezone.utc) - last_dt
                minutes_ago = int(time_ago.total_seconds() / 60)
                time_str = f"{minutes_ago} min ago"
                expander_title = f"🔧 {exchange_id.upper()} Settings (Last scan: {time_str})"
            except:
                expander_title = f"🔧 {exchange_id.upper()} Settings"
        else:
            expander_title = f"🔧 {exchange_id.upper()} Settings (Never scanned)"
        
        with st.expander(expander_title, expanded=False):
            st.info("ℹ️ All 4 exchanges (Gate.io, MEXC, Kucoin, Bitget) are permanently enabled. To exclude an exchange, you must modify the code.")
            
            st.markdown("---")
            
            # Filter Logic Selection
            filter_logic = st.radio(
                "🔀 Filter Logic",
                options=['OR', 'AND'],
                index=0 if ex_config.get('filter_logic', 'OR') == 'OR' else 1,
                key=f"scanner_{exchange_id}_logic",
                help="OR: Token is flagged if ANY condition is met | AND: Token is flagged if ALL conditions are met",
                horizontal=True
            )
            if filter_logic != ex_config.get('filter_logic', 'OR'):
                scanner_config['exchanges'][exchange_id]['filter_logic'] = filter_logic
                config_changed = True
            
            st.caption(f"**Configure risk conditions (Priority Order: Depth → Spread → Volume) | Logic: {filter_logic}**")
            
            # 3 filters in priority order: 1. Depth (가장 중요), 2. Spread, 3. Volume
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            # 1️⃣ Depth Filter (가장 중요)
            with filter_col1:
                st.markdown("**1️⃣ 💧 Depth (±2%)**")
                depth_req = st.checkbox(
                    "Enable Filter",
                    value=ex_config.get('depth_required', True),
                    key=f"scanner_{exchange_id}_depth_req",
                    help="Flag if ±2% depth < threshold"
                )
                depth = st.number_input(
                    "Threshold (USD)",
                    min_value=10.0,
                    max_value=5000.0,
                    value=float(ex_config.get('depth_threshold', 1000.0)),
                    step=50.0,
                    key=f"scanner_{exchange_id}_depth",
                    help="Flag if ±2% depth < this value",
                    disabled=not depth_req
                )
                if depth_req != ex_config.get('depth_required', True):
                    scanner_config['exchanges'][exchange_id]['depth_required'] = depth_req
                    config_changed = True
                if depth != ex_config.get('depth_threshold', 1000.0):
                    scanner_config['exchanges'][exchange_id]['depth_threshold'] = depth
                    config_changed = True
            
            # 2️⃣ Spread Filter
            with filter_col2:
                st.markdown("**2️⃣ 📈 Spread**")
                spread_req = st.checkbox(
                    "Enable Filter",
                    value=ex_config.get('spread_required', True),
                    key=f"scanner_{exchange_id}_spread_req",
                    help="Flag if spread > threshold"
                )
                spread = st.number_input(
                    "Threshold (%)",
                    min_value=0.1,
                    max_value=10.0,
                    value=float(ex_config.get('spread_threshold', 1.0)),
                    step=0.1,
                    key=f"scanner_{exchange_id}_spread",
                    help="Flag if spread > this value",
                    disabled=not spread_req
                )
                if spread_req != ex_config.get('spread_required', True):
                    scanner_config['exchanges'][exchange_id]['spread_required'] = spread_req
                    config_changed = True
                if spread != ex_config.get('spread_threshold', 1.0):
                    scanner_config['exchanges'][exchange_id]['spread_threshold'] = spread
                    config_changed = True
            
            # 3️⃣ Volume Filter
            with filter_col3:
                st.markdown("**3️⃣ 📊 Volume**")
                volume_req = st.checkbox(
                    "Enable Filter",
                    value=ex_config.get('volume_required', False),
                    key=f"scanner_{exchange_id}_volume_req",
                    help="Flag if 24h volume < threshold"
                )
                volume = st.number_input(
                    "Threshold (USD/24h)",
                    min_value=1000.0,
                    max_value=100000.0,
                    value=float(ex_config.get('volume_threshold', 10000.0)),
                    step=1000.0,
                    key=f"scanner_{exchange_id}_volume",
                    help="Flag if 24h volume < this value",
                    disabled=not volume_req
                )
                if volume_req != ex_config.get('volume_required', False):
                    scanner_config['exchanges'][exchange_id]['volume_required'] = volume_req
                    config_changed = True
                if volume != ex_config.get('volume_threshold', 10000.0):
                    scanner_config['exchanges'][exchange_id]['volume_threshold'] = volume
                    config_changed = True
            
            # Filter summary
            active_filters = []
            if scanner_config['exchanges'][exchange_id].get('depth_required'):
                active_filters.append(f"Depth<${scanner_config['exchanges'][exchange_id]['depth_threshold']}")
            if scanner_config['exchanges'][exchange_id].get('spread_required'):
                active_filters.append(f"Spread>{scanner_config['exchanges'][exchange_id]['spread_threshold']}%")
            if scanner_config['exchanges'][exchange_id].get('volume_required'):
                active_filters.append(f"Vol<${scanner_config['exchanges'][exchange_id]['volume_threshold']}")
            
            logic = scanner_config['exchanges'][exchange_id].get('filter_logic', 'OR')
            
            if active_filters:
                st.info(f"🎯 **Active filters:** {f' {logic} '.join(active_filters)}")
            else:
                st.warning("⚠️ No filters enabled! All tokens will pass.")
    
    # Save button
    if config_changed:
        if st.button("💾 Save Scanner Configuration", type="primary"):
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(scanner_config, f, indent=2, ensure_ascii=False)
            st.success("✅ Configuration saved!")
            st.rerun()


def _render_manual_scan(scanner_config):
    """Render Manual Scan section."""
    st.markdown("#### 🚀 Manual Scan")
    st.caption("Run a manual scan for selected exchanges")
    
    enabled_exchanges = [ex for ex, cfg in scanner_config['exchanges'].items() if cfg['enabled']]
    
    # Whitelist option (상단에 배치)
    st.markdown("##### ⚪ Whitelist Options")
    include_whitelisted = st.checkbox(
        "Include whitelisted tokens in scan",
        value=False,
        key="include_whitelisted",
        help="If unchecked, major coins in whitelist will be excluded from scan to save time and API calls."
    )
    
    # Show whitelist summary
    if os.path.exists("data/whitelist.json"):
        with open("data/whitelist.json", 'r', encoding='utf-8') as f:
            whitelist = json.load(f)
        
        total_whitelisted = sum(len(whitelist.get(ex, [])) for ex in enabled_exchanges)
        st.caption(f"📊 Whitelisted tokens: {total_whitelisted} across {len(enabled_exchanges)} exchanges")
        
        if include_whitelisted:
            st.info("ℹ️ All tokens including whitelisted will be scanned")
        else:
            st.info(f"ℹ️ {total_whitelisted} whitelisted tokens will be excluded")
    
    st.markdown("---")
    
    # Exchange selection and scan button
    scan_col1, scan_col2 = st.columns([2, 1])
    
    with scan_col1:
        selected_exchanges = st.multiselect(
            "Select exchanges to scan:",
            options=enabled_exchanges,
            default=enabled_exchanges,
            format_func=lambda x: x.upper()
        )
    
    with scan_col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("▶️ Run Scan Now", type="primary", use_container_width=True):
            if selected_exchanges:
                st.info("🔄 스캔 완료 후 자동으로 평균이 계산됩니다. 'Scan Status (Live)' 섹션에서 실시간 진행 상황을 확인하세요")
                try:
                    # Run batch_scanner with logging in background
                    import subprocess
                    cmd = ['python', 'run_scanner_with_logging.py', '--exchanges'] + selected_exchanges
                    
                    # Add whitelist flag if checkbox is unchecked (default: exclude whitelist)
                    if not st.session_state.get('include_whitelisted', False):
                        cmd.append('--exclude-whitelist')
                    
                    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                    time.sleep(1)
                    st.success("✅ 스캔이 시작되었습니다! 새 콘솔 창에서 실시간 로그를 확인할 수 있습니다.")
                    st.info("📁 로그 파일은 logs/ 폴더에 자동 저장됩니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Scan failed: {e}")
            else:
                st.warning("⚠️ Please select at least one exchange")


def _render_scan_results():
    """Render Scan Results section."""
    st.markdown("#### 📊 Scan Results")
    
    # Scan Status (Live)
    _render_scan_status_live()
    
    st.markdown("---")
    
    # Scan Results Tabs
    result_tab1, result_tab2 = st.tabs(["📋 Latest Manual Scan", "📁 Logs"])

    with result_tab1:
        _render_latest_scan()

    with result_tab2:
        _render_logs()


def _render_scan_status_live():
    """Render live scan status."""
    st.markdown("##### 🔄 Scan Status (Live)")
    
    scan_status_file = "scan_status.json"
    should_auto_refresh = False  # Flag for auto-refresh
    
    if os.path.exists(scan_status_file):
        try:
            with open(scan_status_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # Empty file, reset to idle
                    scan_status = {"status": "idle", "current_exchange": None, "progress": "0/0", "progress_pct": 0, "found": 0, "timestamp": None}
                else:
                    scan_status = json.loads(content)
            
            status = scan_status.get('status', 'idle')
            
            if status == 'running' or status == 'completed':
                # Calculate time ago
                scan_timestamp = scan_status.get('timestamp', '')
                time_ago_str = ""
                if scan_timestamp:
                    try:
                        scan_dt = datetime.fromisoformat(scan_timestamp.replace('Z', '+00:00'))
                        time_ago = datetime.now(timezone.utc) - scan_dt
                        minutes_ago = int(time_ago.total_seconds() / 60)
                        
                        if minutes_ago < 1:
                            time_ago_str = " (just now)"
                        elif minutes_ago < 60:
                            time_ago_str = f" ({minutes_ago}m ago)"
                        else:
                            hours_ago = minutes_ago // 60
                            mins_remainder = minutes_ago % 60
                            time_ago_str = f" ({hours_ago}h {mins_remainder}m ago)"
                    except:
                        pass
                
                if status == 'running':
                    # Check if scan is actually finished (100%)
                    if scan_status.get('progress_pct', 0) >= 100:
                        # Scan completed, change status
                        scan_status['status'] = 'completed'
                        with open(scan_status_file, 'w', encoding='utf-8') as f:
                            json.dump(scan_status, f, indent=2)
                        status = 'completed'
                    else:
                        # Scan is actively running, enable auto-refresh
                        should_auto_refresh = True
                
                if status == 'running':
                    current_exchange = scan_status.get('current_exchange', 'unknown')
                    st.info(f"🔄 **Scanning in progress...** Current: **{current_exchange.upper()}**{time_ago_str}")
                else:
                    # For completed status, show correct count from total_found or found field
                    found_count = scan_status.get('total_found', scan_status.get('found', 0))
                    if found_count > 0:
                        st.success(f"✅ **Scan completed!** Total found: **{found_count} tokens**{time_ago_str}")
                    else:
                        st.success(f"✅ **Scan completed!** Check 'Latest Manual Scan' tab for results.{time_ago_str}")
                
                # Exchange-specific progress
                from batch_scanner import EXCHANGES
                scan_history_file = "scan_history.json"
                scan_history = {}
                if os.path.exists(scan_history_file):
                    try:
                        with open(scan_history_file, 'r', encoding='utf-8') as f:
                            scan_history = json.load(f)
                    except:
                        pass
                
                exchange_cols = st.columns(len(EXCHANGES))
                
                for idx, exchange_id in enumerate(EXCHANGES):
                    with exchange_cols[idx]:
                        ex_data = scan_history.get(exchange_id, {})
                        ex_status = ex_data.get('status', 'pending')
                        ex_progress = ex_data.get('progress', '0/0')
                        ex_pct = float(ex_data.get('progress_pct', 0))
                        ex_found = int(ex_data.get('found', 0))
                        ex_timestamp = ex_data.get('timestamp', '')
                        
                        # If any exchange is running, enable auto-refresh
                        if ex_status == 'running':
                            should_auto_refresh = True
                        
                        # Calculate time ago for each exchange
                        ex_time_ago = ""
                        if ex_timestamp and ex_status == 'completed':
                            try:
                                ex_dt = datetime.fromisoformat(ex_timestamp.replace('Z', '+00:00'))
                                ex_time_diff = datetime.now(timezone.utc) - ex_dt
                                ex_minutes = int(ex_time_diff.total_seconds() / 60)
                                ex_time_ago = f" ({ex_minutes} min ago)"
                            except:
                                pass
                        
                        st.markdown(f"**{exchange_id.upper()}**")
                        
                        if ex_status == 'completed':
                            st.caption(f"✅ {ex_progress} | **{ex_found} tokens**{ex_time_ago}")
                            st.progress(1.0)
                        elif ex_status == 'running':
                            st.caption(f"🔄 {ex_progress} ({ex_pct:.1f}%) | **{ex_found} found**")
                            st.progress(ex_pct / 100.0)
                        else:
                            st.caption(f"⏳ Waiting...")
                            st.progress(0.0)
                
                # Auto-refresh only if scan is actively running
                if should_auto_refresh:
                    time.sleep(2)
                    st.rerun()
            
            else:
                st.caption("⏸️ No scan activity. Click 'Run Scan Now' to start!")
        
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ Scan status file corrupted. Resetting...")
            # Reset scan status file
            with open(scan_status_file, 'w', encoding='utf-8') as f:
                json.dump({"status": "idle", "current_exchange": None, "progress": "0/0", "progress_pct": 0, "found": 0, "timestamp": None}, f, indent=2)
            st.info("✅ Scan status reset. Please refresh the page (F5).")
        except Exception as e:
            st.error(f"❌ Error reading scan status: {e}")
    else:
        st.caption("⏸️ No scan activity yet. Click 'Run Scan Now' to start!")


def _render_latest_scan():
    """Render latest manual scan results."""
    st.markdown("### 📋 Latest Manual Scan")
    
    latest_scan_file = "scan_history/latest.json"
    
    # Check if scan is in progress
    scan_status_file = "scan_status.json"
    if os.path.exists(scan_status_file):
        try:
            with open(scan_status_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content:
                scan_status = json.loads(content)
                if scan_status.get('status') == 'running':
                    st.info("🔄 Scan in progress...")
                    st.caption("Check the 'Scan Status (Live)' section above for real-time progress.")
                    return
        except (json.JSONDecodeError, IOError, ValueError):
            pass  # Ignore errors and continue
    
    if not os.path.exists(latest_scan_file):
        st.info("📭 No manual scan results yet. Click 'Run Scan Now' to start!")
        return
    
    try:
        with open(latest_scan_file, 'r', encoding='utf-8') as f:
            latest_data = json.load(f)
        
        tokens = latest_data.get('tokens', [])
        scan_time = latest_data.get('scan_time', 'Unknown')
        
        # Info
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
            # Filter
            exchange_filter = st.multiselect(
                "Filter by Exchange",
                options=['gateio', 'mexc', 'kucoin', 'bitget'],
                default=['gateio', 'mexc', 'kucoin', 'bitget'],
                key="latest_exchange_filter"
            )
            
            filtered_tokens = [t for t in tokens if t['exchange'] in exchange_filter]
            
            st.markdown(f"**Showing {len(filtered_tokens)} tokens** (sorted by ±2% depth ascending)")
            
            # Table
            token_df = pd.DataFrame([
                {
                    "Exchange": t['exchange'].upper(),
                    "Symbol": t['symbol'],
                    "Spread": f"{t.get('spread_pct', 0):.2f}%",
                    "±2% Depth": f"${t.get('depth_2pct', 0):.2f}",
                    "24h Volume": f"${t.get('quote_volume', 0):.2f}",
                    "Bid": f"${t.get('bid', 0):.8f}",
                    "Ask": f"${t.get('ask', 0):.8f}"
                }
                for t in filtered_tokens
            ])
            
            st.dataframe(token_df, use_container_width=True, height=400)
        else:
            st.info("📭 No tokens found in latest scan")
    
    except Exception as e:
        st.error(f"❌ Error loading latest scan: {e}")



def _render_logs():
    """Render log files viewer."""
    st.markdown("### 📁 Scanner Logs")
    st.caption("View scanner execution logs")
    
    log_dir = "logs"
    
    if not os.path.exists(log_dir):
        st.info("📭 No log files yet. Logs will appear here after running a scan.")
        return
    
    # 로그 파일 목록
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    
    if not log_files:
        st.info("📭 No log files found.")
        return
    
    # 최신 파일 먼저
    log_files.sort(reverse=True)
    
    # 로그 파일 선택
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_log = st.selectbox(
            "Select log file:",
            options=log_files,
            format_func=lambda x: f"{x} ({os.path.getsize(os.path.join(log_dir, x)) / 1024:.1f} KB)",
            key="log_file_select"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🗑️ Delete Selected", type="secondary", use_container_width=True):
            try:
                os.remove(os.path.join(log_dir, selected_log))
                st.success(f"✅ Deleted {selected_log}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to delete: {e}")
    
    if selected_log:
        log_path = os.path.join(log_dir, selected_log)
        
        # 로그 내용 읽기 (다중 인코딩 시도)
        try:
            log_content = None
            for encoding in ['utf-8', 'cp949', 'latin-1']:
                try:
                    with open(log_path, 'r', encoding=encoding) as f:
                        log_content = f.read()
                    break  # 성공하면 중단
                except UnicodeDecodeError:
                    continue  # 다음 인코딩 시도

            if log_content is None:
                st.error("❌ Failed to decode log file with UTF-8, CP949, or Latin-1")
                return

            # 파일 정보
            file_size = os.path.getsize(log_path)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(log_path))

            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("File Size", f"{file_size / 1024:.1f} KB")
            with info_col2:
                st.metric("Lines", len(log_content.split('\n')))
            with info_col3:
                st.metric("Modified", file_mtime.strftime('%Y-%m-%d %H:%M'))

            st.markdown("---")

            # 로그 내용 표시 (expander로 감싸기 - 큰 로그 대응)
            with st.expander("📄 **View Log Content** (click to expand)", expanded=False):
                st.code(log_content, language="log")

            # 다운로드 버튼
            st.download_button(
                label="📥 Download Log File",
                data=log_content,
                file_name=selected_log,
                mime="text/plain",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"❌ Failed to read log file: {e}")


def _get_default_scanner_config():
    """Get default scanner configuration."""
    return {
        "exchanges": {
            "gateio": {
                "enabled": True,
                "spread_threshold": 1.0,
                "spread_required": True,
                "depth_threshold": 1000.0,
                "depth_required": True,
                "volume_threshold": 10000.0,
                "volume_required": True,
                "last_scan_time": None
            },
            "mexc": {
                "enabled": True,
                "spread_threshold": 1.0,
                "spread_required": True,
                "depth_threshold": 1000.0,
                "depth_required": True,
                "volume_threshold": 10000.0,
                "volume_required": True,
                "last_scan_time": None
            },
            "kucoin": {
                "enabled": True,
                "spread_threshold": 1.0,
                "spread_required": True,
                "depth_threshold": 1000.0,
                "depth_required": True,
                "volume_threshold": 10000.0,
                "volume_required": False,
                "last_scan_time": None
            },
            "bitget": {
                "enabled": True,
                "spread_threshold": 1.0,
                "spread_required": True,
                "depth_threshold": 1000.0,
                "depth_required": True,
                "volume_threshold": 10000.0,
                "volume_required": True,
                "last_scan_time": None
            }
        },
        "global": {
            "default_scan_interval_hours": 4,
            "default_history_days": 2
        },
        "scheduler": {
            "enabled": True,
            "scan_interval_hours": 1,
            "next_scan_time": None,
            "last_scan_time": None,
            "utc_base_hour": 0,
            "auto_start_on_boot": False
        }
    }

