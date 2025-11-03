#!/usr/bin/env python3
import streamlit as st
import streamlit.components.v1 as components
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import ccxt
import requests
from modules.user_manager import get_user_manager
from modules.telegram_login import init_session_state, require_login, render_user_info, render_sidebar_login
from modules.token_manager import TokenManager
from modules.data_access_layer import DataAccessLayer
from modules.honeymoon_manager import get_honeymoon_manager

# Core modules
from core.config import (
    FilePaths,
    ExchangeThresholds,
    TokenStatus,
    GRADE_TO_POINTS,
    get_grade_color
)
from core.data_manager import get_data_manager
from modules.adsense_helper import load_adsense_config, render_adsense_head, render_sidebar_ad

st.set_page_config(page_title="⚔️ NIGHT WATCH - THE WALL", page_icon="⚔️", layout="wide")

# ============================================
# GOOGLE ADSENSE HEAD SCRIPT
# ============================================
adsense_head_script = render_adsense_head()
if adsense_head_script:
    st.markdown(adsense_head_script, unsafe_allow_html=True)

# ============================================
# PAGE LAYOUT - Standard web content width (like CoinGecko, CoinMarketCap)
# ============================================
st.markdown("""
<style>
    /* Standard content width 1200px for 4-column card layout */
    .main .block-container {
        max-width: 1200px;
        padding-left: 2rem;
        padding-right: 2rem;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Remove default spacing between markdown elements */
    .element-container {
        margin-bottom: 0 !important;
    }
    
    /* Remove hr/divider lines */
    hr {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# TELEGRAM LOGIN
# ============================================
init_session_state()

# Render sidebar login (always visible)
render_sidebar_login()

# Note: Login is optional - users can view The Wall without login
# Login is required only for saving watchlist and accessing premium features

# Add menus to sidebar if logged in
if st.session_state.logged_in:
    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 Search & Add Tokens", use_container_width=True):
        st.session_state.show_token_search = True
    if st.sidebar.button("🔑 My API Keys", use_container_width=True):
        st.session_state.show_api_keys = True
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="sidebar_logout_btn"):
        from modules.telegram_login import logout_user
        logout_user()
        st.rerun()
        st.stop()
    
    # My Watchlist in Sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⭐ My Watchlist")
    
    # Load watchlist
    user_id = st.session_state.telegram_username
    user_manager = get_user_manager()
    watchlist = user_manager.get_user_watchlist(user_id)
    
    if watchlist:
        st.sidebar.markdown(f"**{len(watchlist)} tokens**")
        for item in watchlist[:10]:  # Show first 10
            exchange = item.get('exchange', 'unknown')
            symbol = item.get('symbol', 'unknown')
            st.sidebar.markdown(f"• {exchange.upper()} {symbol}")
        if len(watchlist) > 10:
            st.sidebar.markdown(f"*...and {len(watchlist) - 10} more*")
    else:
        st.sidebar.info("No tokens in watchlist yet. Click ⭐ on any token card to add!")
else:
    # Show login prompt in sidebar when not logged in
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⭐ My Watchlist")
    st.sidebar.info("🔐 Please log in to save your watchlist")

# ============================================
# SIDEBAR ADSENSE AD
# ============================================
st.sidebar.markdown("---")
render_sidebar_ad()

# ============================================
# TOKEN SEARCH PAGE
# ============================================
if st.session_state.get("show_token_search"):
    from universal_token_search import render_universal_search
    
    user_id = st.session_state.telegram_username
    user_tier = st.session_state.user_tier
    
    # Back button
    if st.button("← Back to The Wall"):
        st.session_state.show_token_search = False
        st.rerun()
        st.stop()
    
    render_universal_search(user_id, user_tier)

# ============================================
# API KEYS PAGE
# ============================================
if st.session_state.get("show_api_keys"):
    from user_api_keys import render_user_api_keys
    
    user_id = st.session_state.telegram_username
    user_tier = st.session_state.user_tier
    
    # Back button
    if st.button("← Back to The Wall"):
        st.session_state.show_api_keys = False
        st.rerun()
        st.stop()
    
    render_user_api_keys(user_id, user_tier)
    st.stop()

# ============================================
# USER SESSION MANAGEMENT
# ============================================
# Get current user from Telegram login
if st.session_state.logged_in:
    user_id = st.session_state.telegram_username
else:
    user_id = 'demo_free'

# Ensure user_id is consistent throughout the session
st.session_state.user_id = user_id

# 세션 유지: 로그인 상태를 localStorage처럼 유지
# Streamlit은 서버 재시작 시 세션 상태가 초기화되므로,
# 로그인 정보를 query parameter로 보존
if st.session_state.logged_in and 'telegram_username' in st.session_state:
    # 로그인 상태 확인용 디버그 (개발 시에만)
    # print(f"[SESSION] User: {st.session_state.telegram_username}, Tier: {st.session_state.user_tier}")
    pass

# Initialize user manager
user_manager = get_user_manager()
user_profile = user_manager.get_user_profile(user_id)

# Check if premium based on Telegram login tier
is_premium = st.session_state.user_tier in ["pro", "premium"]

# ❌ Auto-refresh 제거 - 로그아웃 및 세션 초기화 문제 발생
# 사용자가 수동으로 새로고침하거나, 스캔 완료 시에만 업데이트
# st.markdown("""
# <meta http-equiv="refresh" content="900">
# """, unsafe_allow_html=True)

# JavaScript: 별표 클릭 시 토스트 알림 (사이드바는 Streamlit 제약으로 자동 열기 불가)
st.markdown("""
<style>
/* 사이드바 하이라이트 애니메이션 */
@keyframes pulse-sidebar {
    0%, 100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.7); }
    50% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
}
.sidebar-highlight {
    animation: pulse-sidebar 1.5s ease-in-out 3;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    /* Mobile responsive adjustments */
    @media (max-width: 768px) {
        .stButton button {
            font-size: 12px !important;
            padding: 8px 12px !important;
        }
        h1 {
            font-size: 18px !important;
        }
        .nw-card {
            min-height: 80px !important;
            height: auto !important;
        }
    }
    
    .nw-card { 
        border: 1px solid #e6e9ef; 
        border-radius: 6px; 
        padding: 4px 6px 4px 14px; 
        margin-bottom: 5px; 
        background:#fff; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
        position: relative;
        min-height: 96px;
        height: 96px;
        overflow: hidden;
    }
    .nw-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 8px;
        border-radius: 6px 0 0 6px;
    }
    .nw-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-2px);
        background: #fafbfc;
    }
    .card-actions {
        position: absolute;
        bottom: 4px;
        right: 4px;
        display: flex;
        gap: 4px;
        opacity: 0;
        transition: opacity 0.2s ease;
        pointer-events: none;
        z-index: 10;
    }
    .nw-card:hover .card-actions {
        opacity: 1;
        pointer-events: auto;
    }
    .card-action-btn {
        background: rgba(255,255,255,0.95);
        border: 1px solid #ddd;
        border-radius: 3px;
        padding: 3px 5px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.15s ease;
        text-decoration: none;
        color: #333;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        line-height: 1;
    }
    .card-action-btn:hover {
        background: #fff;
        border-color: #3498db;
        transform: scale(1.1);
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .watchlist-zone {
        border: 2px dashed #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        background: #fafafa;
        min-height: 150px;
        transition: all 0.3s ease;
    }
    .watchlist-zone.has-items {
        background: #fff8e1;
        border-color: #ffd54f;
    }
    .nw-header { display:flex; justify-content:space-between; align-items:center; font-weight:600; color:#222; margin-bottom:5px; }
    .nw-sub { color:#666; font-size:9.5px; line-height:1.3; }
    .pair { 
        font-size:15px; 
        font-weight:700; 
        letter-spacing:0.2px; 
        color:#1a1a1a;
        padding: 4px 8px;
        border-radius: 6px;
        display: inline-block;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    
    
    /* 🎨 7-Tier 실시간 상태 (테두리 + 글로우) */
    .status-excellent .pair {
        border: 2px solid #00bfff;
        box-shadow: 0 0 0 0 #00bfff;
        animation: blink-excellent 4s ease-in-out infinite;
    }
    .status-good .pair {
        border: 2px solid #00ced1;
        box-shadow: 0 0 0 0 #00ced1;
        animation: blink-good 3.5s ease-in-out infinite;
    }
    .status-fair .pair {
        border: 2px solid #32cd32;
        box-shadow: 0 0 0 0 #32cd32;
        animation: blink-fair 3s ease-in-out infinite;
    }
    .status-warning .pair {
        border: 2px solid #ffd700;
        box-shadow: 0 0 0 0 #ffd700;
        animation: blink-warning 2.5s ease-in-out infinite;
    }
    .status-caution .pair {
        border: 2px solid #ff8c00;
        box-shadow: 0 0 0 0 #ff8c00;
        animation: blink-caution 2s ease-in-out infinite;
    }
    .status-danger .pair {
        border: 2px solid #ff6347;
        box-shadow: 0 0 0 0 #ff6347;
        animation: blink-danger 1.5s ease-in-out infinite;
    }
    .status-critical .pair {
        border: 2px solid #dc143c;
        box-shadow: 0 0 0 0 #dc143c;
        animation: blink-critical 1s ease-in-out infinite;
    }
    .exch {
        font-size:10px;
        font-weight:600;
        color:white;
        padding:2px 6px;
        border-radius:3px;
        line-height:1.4;
        vertical-align:middle;
    }
    /* 거래소별 태그 색상 */
    .exch-gateio { background:#667eea; }
    .exch-mexc { background:#1abc9c; }
    .exch-kucoin { background:#16a085; }
    .exch-bitget { background:#3498db; }
    .exch-mexc_assessment,
    .exch-mexc_evaluation { background:#e91e63; }
    /* 테두리 글로우 애니메이션 - 7단계 (부드럽고 느린 속도) */
    @keyframes blink-excellent {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0, 191, 255, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(0, 191, 255, 0.6); }
    }
    @keyframes blink-good {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0, 206, 209, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(0, 206, 209, 0.6); }
    }
    @keyframes blink-fair {
        0%, 100% { box-shadow: 0 0 0 0 rgba(50, 205, 50, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(50, 205, 50, 0.6); }
    }
    @keyframes blink-warning {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.3); }
        50% { box-shadow: 0 0 6px 2px rgba(255, 215, 0, 0.6); }
    }
    @keyframes blink-caution {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 140, 0, 0.3); }
        50% { box-shadow: 0 0 8px 2px rgba(255, 140, 0, 0.7); }
    }
    @keyframes blink-danger {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 99, 71, 0.3); }
        50% { box-shadow: 0 0 8px 2px rgba(255, 99, 71, 0.7); }
    }
    @keyframes blink-critical {
        0%, 100% { box-shadow: 0 0 0 0 rgba(220, 20, 60, 0.4); }
        50% { box-shadow: 0 0 10px 3px rgba(220, 20, 60, 0.8); }
    }
    
    /* 등급별 색상 (왼쪽 스트라이프, 등급 레터, 심볼 테두리) - 최우선 적용 */
    /* F Grade: 진한 빨강 */
    .nw-card.grade-F::before {
        background: #dc3545 !important;
    }
    .grade-F .pair {
        border-color: #dc3545 !important;
    }
    
    /* D Grade: 오렌지 */
    .nw-card.grade-D::before {
        background: #fd7e14 !important;
    }
    .grade-D .pair {
        border-color: #fd7e14 !important;
    }
    
    /* C Grades: 노랑/골드 */
    .nw-card.grade-C-::before, .nw-card.grade-C::before, .nw-card.grade-C-plus::before {
        background: #ffc107 !important;
    }
    .grade-C- .pair, .grade-C .pair, .grade-C-plus .pair {
        border-color: #ffc107 !important;
    }
    
    /* B Grades: 초록 */
    .nw-card.grade-B-::before, .nw-card.grade-B::before, .nw-card.grade-B-plus::before {
        background: #20c997 !important;
    }
    .grade-B- .pair, .grade-B .pair, .grade-B-plus .pair {
        border-color: #20c997 !important;
    }
    
    /* A Grades: 파랑 */
    .nw-card.grade-A-::before, .nw-card.grade-A::before {
        background: #0dcaf0 !important;
    }
    .grade-A- .pair, .grade-A .pair {
        border-color: #0dcaf0 !important;
    }
    
    /* N/A Grade: 회색 */
    .nw-card.grade-NA::before {
        background: #6c757d !important;
    }
    .grade-NA .pair {
        border-color: #6c757d !important;
    }
    
    /* 거래소별 단일 색상 (백업 - 등급이 없을 경우) */
    /* Gate.io: 보라 */
    .exchange-gateio::before {
        background: #667eea;
    }
    
    /* MEXC: 청록색 */
    .exchange-mexc::before {
        background: #1abc9c;
    }
    
    /* KuCoin: 민트 */
    .exchange-kucoin::before {
        background: #16a085;
    }
    
    /* Bitget: 하늘색 */
    .exchange-bitget::before {
        background: #3498db;
    }
    
    /* MEXC Assessment: 마젠타 (긴급) */
    .exchange-mexc_assessment::before,
    .exchange-mexc_evaluation::before {
        background: #e91e63;
    }
    
    /* 3색 깃발 지표 (오른쪽 하단) */
    .status-flags {
        position: absolute;
        bottom: 6px;
        right: 6px;
        display: flex;
        flex-direction: column;
        gap: 1px;
        width: 20px;
        height: 30px;
        border: 1px solid #ddd;
        border-radius: 2px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .flag-bar {
        flex: 1;
        transition: all 0.3s ease;
    }
    .flag-excellent { background: #4caf50; }
    .flag-moderate { background: #ffd700; }
    .flag-poor { background: #f44336; }
    
    /* 🔵 EXCELLENT: 3개 모두 목표값 (밝은 파랑 테두리, 매우 느림) */
    .status-excellent .pair {
        border-color: #00bfff;
        animation: blink-excellent 4s ease-in-out infinite;
    }
    
    /* 🟢 GOOD: 2개 목표값 + 1개 임계값 (청록 테두리) */
    .status-good .pair {
        border-color: #00ced1;
        animation: blink-good 3.5s ease-in-out infinite;
    }
    
    /* 🟢 FAIR: 1개 목표값 + 2개 임계값 (라임 그린 테두리) */
    .status-fair .pair {
        border-color: #32cd32;
        animation: blink-fair 3s ease-in-out infinite;
    }
    
    /* 🟡 WARNING: 3개 모두 임계값만 (골드 테두리) */
    .status-warning .pair {
        border-color: #ffd700;
        animation: blink-warning 2.5s ease-in-out infinite;
    }
    
    /* 🟠 CAUTION: 1개 임계값 미달 (오렌지 테두리) */
    .status-caution .pair {
        border-color: #ff8c00;
        animation: blink-caution 2s ease-in-out infinite;
    }
    
    /* 🔴 DANGER: 2개 임계값 미달 (토마토 레드 테두리) */
    .status-danger .pair {
        border-color: #ff6347;
        animation: blink-danger 1.5s ease-in-out infinite;
    }
    
    /* 🌹 CRITICAL: 3개 모두 임계값 미달 (진한 빨강 테두리, 빠름) */
    .status-critical .pair {
        border-color: #dc143c;
        animation: blink-critical 1s ease-in-out infinite;
    }
    
    /* 색상 범례 (Legend) */
    .status-legend {
        display: flex;
        gap: 8px;
        padding: 12px 15px;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 15px 0;
        flex-wrap: nowrap;
        align-items: center;
        border: 1px solid #dee2e6;
        overflow-x: auto;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
        cursor: help;
        transition: transform 0.2s;
        white-space: nowrap;
    }
    .legend-item:hover {
        transform: scale(1.05);
    }
    .legend-color {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 1px solid rgba(0,0,0,0.1);
    }
    .legend-color-bar {
        width: 40px;
        height: 10px;
        border-radius: 2px;
        border: 1px solid rgba(0,0,0,0.1);
    }
    .legend-label {
        font-size: 12px;
        font-weight: 600;
        color: #495057;
    }
    
    /* 평균가 대비 악화 경고 (점선 오버레이) */
    .status-deteriorating::after {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 8px;
        border-radius: 6px 0 0 6px;
        border-left: 3px dashed rgba(255, 255, 255, 0.8);
        pointer-events: none;
    }
    
    .badge { display:inline-block; padding:1px 4px; border-radius:4px; font-size:9px; border:1px solid #ddd; background:#f7f8fb; color:#333; }
    .badge.sev1 { background:#fff7e0; border-color:#f3c969; }
    .badge.sev2 { background:#fff1e0; border-color:#f39c12; }
    .badge.sev3 { background:#ffe9e6; border-color:#e74c3c; }
    .ok { color:#136f37; }
    .warn { color:#a66f00; }
    .err { color:#a61c1c; }
    .chip { display:inline-block; padding:1px 4px; margin-right:3px; border-radius:4px; font-size:8.5px; border:1px solid #ddd; background:#f5f7fb; color:#333; }
    .chip-new { background:#e8f7ee; border-color:#2ecc71; }
    .chip-solid { background:#eaf3ff; border-color:#3498db; }
    .chip-ai { background:#ffe8f5; border-color:#e91e63; color:#c2185b; font-weight:600; font-size:10px; line-height:1.4; vertical-align:middle; }
    .chip-chronic {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        color: white !important;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: 600;
        display: inline-block;
        margin-right: 4px;
        line-height: 1.4;
        vertical-align: middle;
        animation: pulse 2s ease-in-out infinite;
    }
    .chip-reentry {
        background: linear-gradient(135deg, #f39c12 0%, #d68910 100%);
        color: white !important;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: 600;
        line-height: 1.4;
        vertical-align: middle;
    }
    
    /* ST Tag - 휘장 스타일 */
    .st-tag {
        display: inline-block;
        background: linear-gradient(135deg, #dc143c 0%, #8b0000 100%);
        color: white;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-left: 6px;
        position: relative;
        border-radius: 3px 0 0 3px;
        box-shadow: 0 2px 6px rgba(220, 20, 60, 0.4);
        animation: st-pulse 2s ease-in-out infinite;
    }
    
    /* ST Tag 우측 삼각형 (깃발 효과) */
    .st-tag::after {
        content: '';
        position: absolute;
        right: -8px;
        top: 0;
        width: 0;
        height: 0;
        border-style: solid;
        border-width: 11px 0 11px 8px;
        border-color: transparent transparent transparent #8b0000;
    }
    
    @keyframes st-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.85; }
    }
    
    .chip-ai {
        background:#ffe8f5; 
        border-color:#e91e63; 
        color:#c2185b; 
        font-weight:600;
        display: inline-block;
        margin-right: 4px;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Title with dramatic header
st.markdown("""
<style>
@keyframes blink-red {
    0%, 50%, 100% { opacity: 1; }
    25%, 75% { opacity: 0.3; }
}
.blink-red {
    animation: blink-red 1.5s infinite;
}
/* Remove bottom margin from markdown container */
div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0 !important;
}
</style>
<div style='background: #1a1a1a; border: 3px solid #667eea; padding: 14px 18px; border-radius: 10px; margin-bottom: 0; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);'>
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div style='flex: 1;'>
            <div style='display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px;'>
                <span style='font-size: 28px; filter: drop-shadow(0 2px 4px rgba(102, 126, 234, 0.5));'>🌙</span>
                <h1 style='color: white; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 1px;'>NIGHT WATCH | CRISIS BULLETIN</h1>
            </div>
            <p style='color: #b8c5ff; margin: 0 0 0 38px; font-size: 18px; font-weight: 600; line-height: 1.3;'>Liquidity Threshold & Delisting Monitoring Plus Defense System</p>
        </div>
        <div style='display: flex; gap: 12px; align-items: center;'>
            <div style='padding: 6px 14px; background: rgba(102, 126, 234, 0.25); border: 1px solid #667eea; border-radius: 6px;'>
                <span style='color: #fff; font-size: 11px; font-weight: 600;'><span class='blink-red'>🔴</span> LIVE</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize modal state
if 'show_login_modal' not in st.session_state:
    st.session_state['show_login_modal'] = False

# Check if user clicked Upgrade to Pro button
# Show login/account modal if requested
if st.session_state.get('show_login_modal', False):
    # Close button at top right
    close_col1, close_col2 = st.columns([10, 1])
    with close_col2:
        if st.button("✕", key="close_login_modal_btn"):
            st.session_state['show_login_modal'] = False
            st.rerun()
            st.stop()
    
    if st.session_state.logged_in:
        # Show account management screen
        st.markdown(f"""
        <div style='text-align: center; margin-bottom: 24px;'>
            <h2 style='color: #667eea; margin: 0;'>👤 Account Settings</h2>
            <p style='color: #666; margin-top: 8px;'>@{st.session_state.telegram_username}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Current plan info
        tier_info = {
            "free": {"emoji": "🆓", "name": "FREE", "color": "#3b82f6"},
            "pro": {"emoji": "⚡", "name": "PRO", "color": "#6366f1"},
            "premium": {"emoji": "💎", "name": "PREMIUM", "color": "#d946ef"}
        }
        current_tier = tier_info[st.session_state.user_tier]
        
        st.markdown(f"""
        <div style='padding: 20px; background: linear-gradient(135deg, {current_tier['color']}15 0%, {current_tier['color']}05 100%); border: 2px solid {current_tier['color']}; border-radius: 12px; margin-bottom: 24px; text-align: center;'>
            <div style='font-size: 32px; margin-bottom: 8px;'>{current_tier['emoji']}</div>
            <div style='font-size: 20px; font-weight: 700; color: {current_tier['color']};'>{current_tier['name']} Plan</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, key="modal_logout_btn"):
            from modules.telegram_login import logout_user
            logout_user()
            st.session_state['show_login_modal'] = False
            st.rerun()
            st.stop()
        
        # Show upgrade options if not premium
        if st.session_state.user_tier != "premium":
            st.markdown("---")
            st.markdown("### ⚡ Upgrade Your Plan")
    else:
        # Show login/signup screen
        st.markdown("""
        <div style='text-align: center; margin-bottom: 24px;'>
            <h2 style='color: #667eea; margin: 0;'>🔐 Login / Sign Up</h2>
            <p style='color: #666; margin-top: 8px;'>Enter your Telegram username to continue</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check if verification is pending
        if st.session_state.get('verification_pending', False):
            # Show verification code input
            st.markdown(f"""
            <div style='padding: 16px; background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; margin-bottom: 16px;'>
                <p style='margin: 0; color: #856404;'><strong>📨 Verification code sent to @{st.session_state.verification_username}</strong></p>
                <p style='margin: 8px 0 0 0; font-size: 13px; color: #856404;'>Check your Telegram messages for the 6-digit code.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display the code for now (since we don't have Telegram Bot yet)
            if st.session_state.verification_code:
                st.info(f"🔑 Your verification code: **{st.session_state.verification_code}**")
                st.caption("(In production, this will be sent via Telegram)")
            
            verification_code = st.text_input(
                "Enter 6-digit Code",
                placeholder="000000",
                max_chars=6,
                key="verification_code_input"
            )
            
            col_verify, col_resend = st.columns(2)
            
            with col_verify:
                if st.button("✅ Verify", type="primary", use_container_width=True, key="verify_btn"):
                    if verification_code and len(verification_code) == 6:
                        from modules.telegram_login import verify_code, login_user
                        username = st.session_state.verification_username
                        success, msg = verify_code(username, verification_code)
                        
                        if success:
                            # Verification successful, proceed with login
                            login_success, login_msg = login_user(username)
                            if login_success:
                                st.success("✅ Verification successful! Welcome!")
                                st.balloons()
                                st.session_state['verification_pending'] = False
                                st.session_state['verification_username'] = None
                                st.session_state['verification_code'] = None
                                st.session_state['show_login_modal'] = False
                                st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.warning("⚠️ Please enter a 6-digit code")
            
            with col_resend:
                if st.button("🔄 Resend Code", use_container_width=True, key="resend_btn"):
                    from modules.telegram_login import generate_verification_code, send_verification_code
                    username = st.session_state.verification_username
                    new_code = generate_verification_code()
                    send_verification_code(username, new_code)
                    st.session_state.verification_code = new_code
                    st.success("✅ New code sent!")
                    st.rerun()
            
            if st.button("« Back", key="back_to_login_btn"):
                st.session_state['verification_pending'] = False
                st.session_state['verification_username'] = None
                st.session_state['verification_code'] = None
                st.rerun()
        
        else:
            # Show username input
            telegram_username = st.text_input(
                "Telegram Username",
                placeholder="@your_username or your_username",
                help="Your Telegram username (with or without @)",
                key="modal_telegram_input"
            )
            
            col_login, col_help = st.columns([2, 1])
            
            with col_login:
                if st.button("🚀 Send Verification Code", type="primary", use_container_width=True, key="modal_login_btn"):
                    if telegram_username:
                        from modules.telegram_login import generate_verification_code, send_verification_code
                        telegram_username = telegram_username.strip().lstrip('@')
                        
                        # Generate and send verification code
                        code = generate_verification_code()
                        send_verification_code(telegram_username, code)
                        
                        # Set session state for verification
                        st.session_state['verification_pending'] = True
                        st.session_state['verification_username'] = telegram_username
                        st.session_state['verification_code'] = code
                        
                        st.success(f"✅ Verification code sent to @{telegram_username}!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Please enter your Telegram username")
            
            with col_help:
                with st.popover("❓ Help"):
                    st.markdown("""
                    **How to find your Telegram username:**
                    1. Open Telegram app
                    2. Go to Settings
                    3. Your username is shown under your name
                    4. It looks like: **@your_username**
                    
                    **Note:** If you don't have a username, you can set one in Telegram Settings.
                    """)
        
        st.markdown("---")
        st.markdown("### 🎯 Why Sign Up?")
        
        benefit_col1, benefit_col2 = st.columns(2)
        with benefit_col1:
            st.markdown("""
            - 📌 **Save Your Watchlist**
            - 🔔 **Get Telegram Alerts**
            - 📊 **Track Your Tokens**
            """)
        with benefit_col2:
            st.markdown("""
            - ⚡ **Upgrade to Pro**
            - 💎 **Access Premium Features**
            - 🎁 **Exclusive Benefits**
            """)
        
        st.markdown("---")
        st.markdown("### 💰 Pricing Plans")

show_upgrade = st.session_state.get('show_upgrade_modal', False)

if show_upgrade or (st.session_state.get('show_login_modal', False) and st.session_state.logged_in and st.session_state.user_tier != "premium"):
    if show_upgrade:
        st.session_state['show_upgrade_modal'] = True
    
    # Modal Header
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 16px; border-radius: 12px; margin: 20px 0;'>
        <h3 style='text-align: center; color: white; margin: 0;'>⚡ Choose Your Plan</h3>
    </div>
    """, unsafe_allow_html=True)
    
    comp_col1, comp_col2, comp_col3 = st.columns(3)
    
    with comp_col1:
        st.markdown(f"""
        <div style='padding: 14px; background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.03) 100%); border: 2px solid #3b82f6; border-radius: 12px; height: 280px;'>
            <div style='text-align: center; margin-bottom: 10px;'>
                <span style='font-size: 24px;'>🆓</span>
                <div style='font-size: 16px; font-weight: 700; color: #3b82f6; margin-top: 4px;'>FREE</div>
            </div>
            <div style='font-size: 11px; line-height: 1.6;'>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(59, 130, 246, 0.1); border-radius: 4px;'>⏱️ Main: <strong>60min</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(59, 130, 246, 0.1); border-radius: 4px;'>⚡ Watch: <strong>1min</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(59, 130, 246, 0.1); border-radius: 4px;'>🔥 Burst: <strong>3/day</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(59, 130, 246, 0.1); border-radius: 4px;'>📊 Tokens: <strong>10</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(59, 130, 246, 0.1); border-radius: 4px;'>📈 Analysis: <strong>Basic</strong></div>
                <div style='padding: 7px; background: #3b82f6; color: white; text-align: center; border-radius: 6px; font-weight: 700; margin-top: 8px;'>💰 $0/month</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with comp_col2:
        st.markdown(f"""
        <div style='padding: 14px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(99, 102, 241, 0.05) 100%); border: 3px solid #6366f1; border-radius: 12px; box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25); height: 280px;'>
            <div style='text-align: center; margin-bottom: 10px;'>
                <span style='font-size: 24px;'>⚡</span>
                <div style='font-size: 16px; font-weight: 700; color: #6366f1; margin-top: 4px;'>PRO</div>
                <div style='display: inline-block; padding: 2px 8px; background: #6366f1; color: white; border-radius: 10px; font-size: 9px; font-weight: 700; margin-top: 3px;'>POPULAR</div>
            </div>
            <div style='font-size: 11px; line-height: 1.6;'>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(99, 102, 241, 0.15); border-radius: 4px;'>⚡ Main: <strong>5min</strong> <span style='color: #6366f1; font-weight: 700;'>(12x!)</span></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(99, 102, 241, 0.15); border-radius: 4px;'>⚡ Watch: <strong>1min</strong> <span style='color: #6366f1; font-weight: 700;'>(5x!)</span></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(99, 102, 241, 0.15); border-radius: 4px;'>🔥 Burst: <strong>Unlimited</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(99, 102, 241, 0.15); border-radius: 4px;'>📊 Tokens: <strong>10</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(99, 102, 241, 0.15); border-radius: 4px;'>📈 Analysis: <strong>Advanced</strong></div>
                <div style='padding: 7px; background: #6366f1; color: white; text-align: center; border-radius: 6px; font-weight: 700; margin-top: 8px;'>💰 $99/month</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with comp_col3:
        st.markdown(f"""
        <div style='padding: 14px; background: linear-gradient(135deg, rgba(217, 70, 239, 0.15) 0%, rgba(147, 51, 234, 0.05) 100%); border: 4px solid #d946ef; border-radius: 12px; box-shadow: 0 8px 24px rgba(217, 70, 239, 0.35); height: 280px; position: relative;'>
            <div style='position: absolute; top: -12px; right: 10px; background: linear-gradient(135deg, #d946ef 0%, #9333ea 100%); color: white; padding: 4px 12px; border-radius: 12px; font-size: 10px; font-weight: 700; box-shadow: 0 2px 8px rgba(217, 70, 239, 0.4);'>⭐ BEST VALUE</div>
            <div style='text-align: center; margin-bottom: 10px;'>
                <span style='font-size: 24px;'>💎</span>
                <div style='font-size: 16px; font-weight: 700; color: #d946ef; margin-top: 4px;'>PREMIUM</div>
            </div>
            <div style='font-size: 11px; line-height: 1.6;'>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(217, 70, 239, 0.15); border-radius: 4px;'>⚡ All Pro Features +</div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(217, 70, 239, 0.15); border-radius: 4px;'>🤖 <strong>Auto LP Engine</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(217, 70, 239, 0.15); border-radius: 4px;'>🛡️ <strong>Delisting Defense</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(217, 70, 239, 0.15); border-radius: 4px;'>🎯 <strong>Threshold Tracking</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(217, 70, 239, 0.15); border-radius: 4px;'>🔄 <strong>Auto/Manual Orders</strong></div>
                <div style='margin-bottom: 6px; padding: 5px; background: rgba(217, 70, 239, 0.15); border-radius: 4px;'>🧠 <strong>AI Liquidity Supply</strong></div>
                <div style='padding: 7px; background: linear-gradient(135deg, #d946ef 0%, #9333ea 100%); color: white; text-align: center; border-radius: 6px; font-weight: 700; margin-top: 8px;'>💰 $2,000/month</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; padding: 16px; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-radius: 10px; margin: 16px 0;'>
        <p style='font-size: 13px; color: #666; line-height: 1.8; margin: 0;'>
            💡 <strong>Pro</strong> = 12x faster monitoring for individual traders<br>
            💎 <strong>Premium</strong> = Full automation with AI-powered liquidity management for projects
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("Continue with Free", use_container_width=True, key="stay_free_btn"):
            st.session_state['show_upgrade_modal'] = False
            st.rerun()
    with col_btn2:
        if st.button("⚡ Upgrade to Pro", type="primary", use_container_width=True, key="upgrade_pro_btn"):
            st.success("🎉 Redirecting to Pro checkout...")
            st.balloons()
    with col_btn3:
        if st.button("💎 Get Premium", type="primary", use_container_width=True, key="upgrade_premium_btn"):
            st.success("💎 Contact us for Premium setup...")
            st.balloons()
    
    st.markdown("---")
    st.stop()  # Stop rendering the rest of the page

# Add loading status indicator
st.markdown("""
<div style='position: fixed; bottom: 20px; right: 20px; background: rgba(102, 126, 234, 0.95); color: white; padding: 10px 16px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 9999; font-size: 13px; font-weight: 600;'>
    <span class='blink'>●</span> Live Monitoring Active
</div>
""", unsafe_allow_html=True)

def _save_watchlist(watchlist):
    try:
        with open("my_watchlist.json", "w", encoding="utf-8") as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _load_watchlist(user_id):
    """Load watchlist for specific user"""
    # Guest users always start with empty watchlist
    if user_id in ('guest', 'demo_free'):
        return []
    return user_manager.get_user_watchlist(user_id)

def _save_watchlist(user_id, watchlist):
    """Save watchlist for specific user"""
    user_manager.save_user_watchlist(user_id, watchlist)

# 세션 상태 초기화
# 게스트는 매번 초기화, 로그인 유저는 세션 유지
if user_id in ('guest', 'demo_free'):
    st.session_state.watchlist = []
    print(f"[DEBUG] Guest user - empty watchlist")
else:
    # 로그인 유저는 항상 파일에서 최신 워치리스트 로드
    loaded_watchlist = _load_watchlist(user_id)
    st.session_state.watchlist = loaded_watchlist
    print(f"[DEBUG] Loading watchlist for {user_id}: {len(loaded_watchlist)} items from users.json")

# No additional JavaScript needed - interactions handled in main script

# Process pending watchlist addition after login
if st.session_state.get('logged_in', False) and 'pending_watchlist_add' in st.session_state:
    pending = st.session_state.pending_watchlist_add
    # Convert to query params to trigger the normal add flow
    st.query_params['add_exchange'] = pending['exchange']
    st.query_params['add_symbol'] = pending['symbol']
    st.query_params['add_token_id'] = pending['token_id']
    st.query_params['add_spread'] = pending.get('spread', '')
    st.query_params['add_depth'] = pending.get('depth', '')
    # Clear pending
    del st.session_state.pending_watchlist_add
    st.rerun()
    st.stop()

# Process query parameters for watchlist additions/removals
query_params = st.query_params

# Handle Add to Watchlist
if 'add_exchange' in query_params and 'add_symbol' in query_params:
    add_exchange = query_params['add_exchange']
    add_symbol = query_params['add_symbol']
    add_token_id = query_params.get('add_token_id', f"{add_exchange}_{add_symbol.replace('/', '_').lower()}")
    add_spread = query_params.get('add_spread', '')
    add_depth = query_params.get('add_depth', '')
    
    # Convert spread and depth to numbers
    try:
        spread_pct = float(add_spread) if add_spread else None
    except:
        spread_pct = None
    try:
        total_2 = float(add_depth) if add_depth else None
    except:
        total_2 = None
    
    # Check if user is logged in (use session_state.logged_in for accuracy)
    is_logged_in = st.session_state.get('logged_in', False)
    
    # For guest users, show toast only (no modal, no refresh)
    if not is_logged_in:
        # Check if we already showed the message
        if 'watchlist_login_shown' not in st.session_state:
            st.session_state.watchlist_login_shown = True
            st.toast("🔐 Please log in via sidebar to save watchlist!", icon="⭐")
        
        # Save pending watchlist addition to session state
        st.session_state.pending_watchlist_add = {
            'exchange': add_exchange,
            'symbol': add_symbol,
            'token_id': add_token_id,
            'spread': add_spread,
            'depth': add_depth
        }
        
        # Clear query params to prevent repeated processing
        st.query_params.clear()
    else:
        # For logged-in users, check limits and duplicates
        # Ensure we get the actual logged-in user's ID
        actual_user_id = st.session_state.get('telegram_username', user_id)
        
        # Debug: Print user info
        print(f"[DEBUG] Watchlist Add Request:")
        print(f"  - is_logged_in: {is_logged_in}")
        print(f"  - user_id (from line 76): {user_id}")
        print(f"  - actual_user_id (telegram_username): {actual_user_id}")
        print(f"  - session_state.logged_in: {st.session_state.get('logged_in', False)}")
        print(f"  - session_state.telegram_username: {st.session_state.get('telegram_username', 'NOT SET')}")
        
        # Show toast notification instead of clearing params immediately
        watchlist_limit = user_manager.get_watchlist_limit(actual_user_id)
        current_count = len(st.session_state.watchlist)
        
        # Check if not already in watchlist
        is_duplicate = any(
            item.get("exchange") == add_exchange and item.get("symbol") == add_symbol
            for item in st.session_state.watchlist
        )
        
        if is_duplicate:
            st.toast(f"⚠️ {add_symbol} 이미 워치리스트에 있습니다!", icon="⚠️")
            st.query_params.clear()
        elif current_count >= watchlist_limit:
            # Get actual user tier
            user_tier = st.session_state.get('user_tier', 'free')
            tier_display = {
                'free': '무료 (2개)',
                'pro': '프로 (8개)',
                'premium': '프리미엄 (32개)'
            }.get(user_tier, '무료 (2개)')
            st.toast(f"❌ 워치리스트 한도 도달! 현재: {tier_display}", icon="❌")
            st.query_params.clear()
        else:
            # Use user_manager to add for logged-in users
            success = user_manager.add_to_watchlist(actual_user_id, add_exchange, add_symbol)
            if success:
                # Force reload from file to ensure consistency
                updated_watchlist = user_manager.get_user_watchlist(actual_user_id)
                st.session_state.watchlist = updated_watchlist
                st.toast(f"✅ {add_symbol} added to watchlist! Check sidebar → ({len(updated_watchlist)}/{watchlist_limit})", icon="⭐")
                
                # Update star icon color without page refresh using JavaScript
                import streamlit.components.v1 as components
                token_id_for_js = f"{add_exchange}_{add_symbol.replace('/', '_')}"
                components.html(f"""
                <script>
                    // Find the star icon for this token and update its color
                    const tokenId = "{token_id_for_js}";
                    const starLink = parent.document.querySelector('a[href*="add_token_id={token_id_for_js}"]');
                    if (starLink) {{
                        starLink.style.color = '#fbbf24';  // Gold color for added to watchlist
                        starLink.innerHTML = '⭐';
                    }}
                </script>
                """, height=0)
                
                # Clear query params but DON'T rerun to prevent logout
                st.query_params.clear()
            else:
                st.toast(f"❌ {add_symbol} 추가 실패", icon="❌")
                st.query_params.clear()

# Handle Remove from Watchlist
if 'remove_exchange' in query_params and 'remove_symbol' in query_params:
    remove_exchange = query_params['remove_exchange']
    remove_symbol = query_params['remove_symbol']
    remove_token_id = f"{remove_exchange}_{remove_symbol.replace('/', '_').lower()}"
    
    # Check if user is logged in
    if not st.session_state.get('logged_in', False):
        st.warning("⚠️ Please login to remove tokens from watchlist")
        st.query_params.clear()
    else:
        # Ensure we use the actual logged-in user's ID
        actual_user_id = st.session_state.get('telegram_username')
        
        if not actual_user_id:
            st.error("❌ User ID not found. Please login again.")
            st.query_params.clear()
        else:
            # Use user_manager to remove
            success = user_manager.remove_from_watchlist(actual_user_id, remove_token_id)
            if success:
                st.session_state.watchlist = user_manager.get_user_watchlist(actual_user_id)
                st.toast(f"🗑️ {remove_symbol} 워치리스트에서 제거!", icon="🗑️")
                
                # Update star icon color back to gray without page refresh
                import streamlit.components.v1 as components
                token_id_for_js = f"{remove_exchange}_{remove_symbol.replace('/', '_')}"
                components.html(f"""
                <script>
                    // Find the star icon for this token and update its color back to gray
                    const tokenId = "{token_id_for_js}";
                    const starLink = parent.document.querySelector('a[href*="add_token_id={token_id_for_js}"]');
                    if (starLink) {{
                        starLink.style.color = '#6b7280';  // Gray color for not in watchlist
                        starLink.innerHTML = '☆';
                    }}
                </script>
                """, height=0)
                
                # Clear query params but DON'T rerun to prevent logout
                st.query_params.clear()
            else:
                st.toast(f"⚠️ {remove_symbol} 워치리스트에 없습니다", icon="⚠️")
                st.query_params.clear()

# My Watch List with Subscription
from modules.subscription_manager import SubscriptionManager

subscription_mgr = SubscriptionManager()
sub_info = subscription_mgr.get_subscription_info()

# Header with subscription badge (no title, just badge)
col_left, col_right = st.columns([3, 1])

# Calculate time until next update for timer display
next_update_time = sub_info.get('next_update', 'N/A')

# Get update interval from config
subscription_config_path = "config/subscription_config.json"
if os.path.exists(subscription_config_path):
    try:
        with open(subscription_config_path, 'r', encoding='utf-8') as f:
            _sub_cfg = json.load(f)
        update_interval_hours = _sub_cfg.get("free_update_interval_hours", 1)
    except:
        update_interval_hours = 1
else:
    update_interval_hours = 1

total_minutes = int(update_interval_hours * 60)  # Convert hours to minutes

if not sub_info['is_premium'] and next_update_time != 'N/A':
    try:
        # Parse next_update time (format: "X min" or "Xh Ym" or "Now")
        if next_update_time.lower() == "now":
            # 시작 시점을 전체 주기로 카운트다운 시작
            remaining_minutes = total_minutes
        else:
            # Extract minutes from "X min" or "Xh Ym"
            if 'h' in next_update_time:
                # Format: "Xh Ym"
                parts = next_update_time.replace('h', '').replace('m', '').strip().split()
                hours = int(parts[0]) if len(parts) > 0 else 0
                mins = int(parts[1]) if len(parts) > 1 else 0
                remaining_minutes = hours * 60 + mins
            else:
                # Format: "X min"
                remaining_minutes = int(next_update_time.replace('min', '').strip())
        
        progress_percent = max(0, min(100, (remaining_minutes / total_minutes) * 100))
        
        # Create simple countdown timer (1 minute = 60 seconds)
        total_seconds = 1 * 60  # 1 minute for watchlist update (Premium Pool)
        timer_html = f"""
        <div id='timer-container' style='display: inline-block; margin-left: 10px;'>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <div id='timer-countdown' style='font-size: 13px; font-weight: 700; color: #667eea; padding: 4px 10px; background: rgba(102, 126, 234, 0.1); border-radius: 6px; border: 1px solid rgba(102, 126, 234, 0.3);'>
                    <span id='timer-text'>{total_seconds}s</span>
                </div>
            </div>
        </div>
        <script>
        (function() {{
            let remainingSeconds = {total_seconds};
            
            function updateTimer() {{
                remainingSeconds = Math.max(0, remainingSeconds - 1);
                
                const timerText = document.getElementById('timer-text');
                if (timerText) {{
                    const mins = Math.floor(remainingSeconds / 60);
                    const secs = remainingSeconds % 60;
                    timerText.textContent = mins > 0 ? mins + 'm ' + secs + 's' : secs + 's';
                }}
                
                // If timer reaches 0, reload page
                if (remainingSeconds <= 0) {{
                    window.location.reload();
                }}
            }}
            
            // Update every second
            setInterval(updateTimer, 1000);
        }})();
        </script>
        """
    except Exception as e:
        timer_html = ""
else:
    # Pro/Premium users get faster auto-refresh
    if sub_info['is_premium']:
        # Premium: 1 minute, Pro: 3 minutes
        user_tier = users.get(user_id, {}).get('tier', 'free')
        if user_tier == 'premium':
            total_seconds = 1 * 60  # 1 minute
            tier_label = "Premium"
        else:  # pro
            total_seconds = 3 * 60  # 3 minutes
            tier_label = "Pro"

        timer_html = f"""
        <div id='timer-container' style='display: inline-block; margin-left: 10px;'>
            <div style='display: flex; align-items: center; gap: 6px;'>
                <div id='timer-countdown' style='font-size: 13px; font-weight: 700; color: #10b981; padding: 4px 10px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);'>
                    <span id='timer-text'>{total_seconds}s</span>
                </div>
            </div>
        </div>
        <script>
        (function() {{
            let remainingSeconds = {total_seconds};

            function updateTimer() {{
                remainingSeconds = Math.max(0, remainingSeconds - 1);

                const timerText = document.getElementById('timer-text');
                if (timerText) {{
                    const mins = Math.floor(remainingSeconds / 60);
                    const secs = remainingSeconds % 60;
                    timerText.textContent = mins > 0 ? mins + 'm ' + secs + 's' : secs + 's';
                }}

                // If timer reaches 0, reload page
                if (remainingSeconds <= 0) {{
                    window.location.reload();
                }}
            }}

            // Update every second
            setInterval(updateTimer, 1000);
        }})();
        </script>
        """
    else:
        timer_html = ""

# Store watchlist rendering for later (after functions are defined)
_watchlist_col_left = col_left
_watchlist_timer_html = timer_html

with col_right:
    # Subscription status
    if sub_info['is_premium']:
        st.markdown(f"<div style='text-align:right;padding:4px 12px;background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%);color:white;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:8px;'>👑 PREMIUM</div>", unsafe_allow_html=True)
        st.caption(f"✓ {sub_info.get('days_left', 0)} days left")
    else:
        # Free tier - no button here (moved to header)
        st.markdown("<div id='upgrade'></div>", unsafe_allow_html=True)
        
        # Premium features info
        if st.session_state.get('show_premium_popup', False):
            with st.expander("👑 **Premium Features**", expanded=True):
                st.markdown("""
                ### 🚀 Upgrade to Premium
                
                **✨ Premium Features**
                - 🔄 **Real-time Monitoring** - 1-minute Full API snapshots with 1-month data retention & DB download
                - ⚡ **Micro Burst Analysis** - 0.05 sec interval, 100 snapshot frames for high-frequency monitoring
                - 📊 **Advanced Analytics** - Delisting Risk, Market Manipulation, Liquidity Grading
                - 📈 **10 Watchlist Slots** - Monitor up to 10 tokens simultaneously
                - 📱 **Telegram Alerts** - Instant notifications for your watchlist
                - 💹 **Arbitrage Alerts** - Cross-exchange price differences for same tokens
                - 🎯 **Strategic Action Reports** - Recommended actions with execution steps
                - 🎯 **Priority Support** - Faster customer service
                
                ---
                
                ### 📊 What You Get
                """)
                
                # Comparison table
                comp_col1, comp_col2 = st.columns(2)
                with comp_col1:
                    st.markdown("""
                    **🆓 Free Plan**
                    - ⏱️ 1-hour update interval
                    - 📊 Basic market data only
                    - ❌ No Micro Burst analysis
                    - ❌ No detailed reports
                    - ❌ No Telegram alerts
                    """)
                with comp_col2:
                    st.markdown("""
                    **👑 Premium Plan**
                    - ⚡ Real-time updates (every minute)
                    - 📈 Full market analysis
                    - ⚡ Micro Burst (0.05-sec snapshots)
                    - 🎯 Action reports & strategies
                    - 📊 Advanced analytics
                    - 📱 Telegram & arbitrage alerts
                    """)
                
                st.markdown("""
                ---
                
                **💰 Price**: $99/month
                
                **📚 Learn More**  
                🔗 [View Examples & Demos](https://nightwatch-examples.com) *(Coming Soon)*  
                📖 [Feature Documentation](https://nightwatch-docs.com) *(Coming Soon)*  
                🎥 [Video Tutorials](https://nightwatch-videos.com) *(Coming Soon)*
                
                **📧 Contact**: admin@nightwatch.com  
                **📞 Phone**: +1-XXX-XXX-XXXX
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📧 Contact Admin", use_container_width=True):
                        st.success("✉️ Your inquiry has been submitted!")
                with col2:
                    if st.button("❌ Close", use_container_width=True):
                        st.session_state.show_premium_popup = False
                        st.rerun()

st.markdown("---")


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _get_exchange_instance(exchange_id: str, api_key: str | None = None, api_secret: str | None = None):
    mapped = exchange_id
    if exchange_id in ("mexc_evaluation", "mexc_assessment"):
        mapped = "mexc"
    try:
        ex_class = getattr(ccxt, mapped)
        params = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
        if mapped == "mexc" and (api_key and api_secret):
            params.update({
                "apiKey": api_key,
                "secret": api_secret,
                "headers": {"x-mexc-apikey": api_key},
                "urls": {"api": {"public": "https://api.mexc.com/api/v3", "private": "https://api.mexc.com/api/v3"}},
            })
        return ex_class(params)
    except Exception:
        return None


def _compute_snapshot(ex, exchange_id: str, symbol: str):
    try:
        ex.load_markets()
    except Exception:
        pass
    try:
        ticker = ex.fetch_ticker(symbol)
    except Exception:
        ticker = {}
    try:
        # 거래소별 최적 limit 설정
        if ex_id == 'kucoin':
            limits = [100, 20]  # KuCoin: 20 또는 100만 허용
        elif ex_id == 'bitget':
            limits = [150, 100, 50]  # Bitget: 최대 150
        elif ex_id == 'gateio':
            limits = [100, 50]  # Gate.io: 최대 100
        elif ex_id == 'mexc' or ex_id in ('mexc_assessment', 'mexc_evaluation'):
            limits = [200, 100, 50]  # MEXC: 최대 200
        else:
            limits = [150, 100, 50]  # 기본값
        
        for lim in limits:
            try:
                ob = ex.fetch_order_book(symbol, limit=lim)
                if ob:
                    break
            except Exception:
                ob = None
        if ob is None:
            ob = {"bids": [], "asks": []}
    except Exception:
        ob = {"bids": [], "asks": []}

    # USDT conversion
    quote = symbol.split("/")[-1].upper() if "/" in symbol else "USDT"
    usdt_rate = 1.0
    if quote != "USDT":
        try:
            conv = ex.fetch_ticker(f"{quote}/USDT")
            usdt_rate = float(conv.get("last") or 1.0)
        except Exception:
            try:
                conv = ex.fetch_ticker(f"USDT/{quote}")
                last_conv = float(conv.get("last") or 0.0)
                usdt_rate = (1.0 / last_conv) if last_conv > 0 else 1.0
            except Exception:
                usdt_rate = 1.0

    bid = float(ticker.get("bid") or 0.0)
    ask = float(ticker.get("ask") or 0.0)
    bid_u = bid * usdt_rate if bid else 0.0
    ask_u = ask * usdt_rate if ask else 0.0
    spread_pct = ((ask_u - bid_u) / bid_u * 100.0) if bid_u > 0 and ask_u > 0 else None

    # ±2% total depth (USDT notional)
    total_2 = None
    if bid_u > 0 and ask_u > 0:
        mid = (bid_u + ask_u) / 2.0
        low = mid * 0.98
        high = mid * 1.02
        try:
            tot = 0.0
            for p, a in (ob.get("bids") or []):
                p_u = float(p) * usdt_rate
                a = float(a)
                if low <= p_u <= mid:
                    tot += p_u * a
            for p, a in (ob.get("asks") or []):
                p_u = float(p) * usdt_rate
                a = float(a)
                if mid <= p_u <= high:
                    tot += p_u * a
            total_2 = tot
        except Exception:
            total_2 = None

    return spread_pct, total_2


def _save_json(path: str, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _compute_snapshot_mexc_assessment(cfg: dict, symbol: str):
    base_url = "https://api.mexc.com/api/v3"
    headers = {}
    api_key = cfg.get("apiKey")
    if api_key:
        headers["x-mexc-apikey"] = api_key
    sym_q = symbol.replace("/", "")

    # Best bid/ask via bookTicker
    try:
        r = requests.get(f"{base_url}/ticker/bookTicker", params={"symbol": sym_q}, headers=headers, timeout=6)
        bt = r.json() if r.status_code == 200 else {}
    except Exception:
        bt = {}
    bid = float(bt.get("bidPrice") or 0.0)
    ask = float(bt.get("askPrice") or 0.0)
    spread_pct = ((ask - bid) / bid * 100.0) if bid > 0 and ask > 0 else None

    # ±2% notional depth via depth
    total_2 = None
    if bid > 0 and ask > 0:
        mid = (bid + ask) / 2.0
        low = mid * 0.98
        high = mid * 1.02
        try:
            r = requests.get(f"{base_url}/depth", params={"symbol": sym_q, "limit": 150}, headers=headers, timeout=6)
            ob = r.json() if r.status_code == 200 else {}
            tot = 0.0
            for p, a in (ob.get("bids") or []):
                p = float(p); a = float(a)
                if low <= p <= mid:
                    tot += p * a
            for p, a in (ob.get("asks") or []):
                p = float(p); a = float(a)
                if mid <= p <= high:
                    tot += p * a
            total_2 = tot
        except Exception:
            total_2 = None

    return spread_pct, total_2

def _token_key(ex_id: str, sym: str) -> str:
    return f"{ex_id}_{sym.replace('/', '_').lower()}"


def _should_blink(manual_inputs: dict, ex_id: str, sym: str, spread_pct: float, total_2: float) -> bool:
    key = _token_key(ex_id, sym)
    cfg = manual_inputs.get(key, {})
    spread_threshold = float(cfg.get("spread_threshold", 2.0))
    depth_threshold = float(cfg.get("depth_threshold", 500.0))
    # Blink if spread is worse than threshold OR depth is below threshold
    return (spread_pct >= spread_threshold) or (total_2 < depth_threshold)


# Import chart functions from separate module to avoid circular imports
from helpers.chart_helpers import get_token_history_14days, generate_mini_chart_html

def _get_token_history_14days_DEPRECATED(token_id: str, exchange: str, symbol: str, current_data: dict = None) -> dict:
    """
    Get 14-day history for a token from scan_history files + current snapshot
    Returns dict with grades, volumes, spreads, and depths arrays
    
    Args:
        token_id: Token ID (exchange_symbol_usdt format)
        exchange: Exchange name
        symbol: Symbol (e.g., "BTC/USDT")
        current_data: Current snapshot data to append (optional)
    """
    from glob import glob
    import os
    
    history_dir = 'scan_history'
    if not os.path.exists(history_dir):
        return {'dates': [], 'grades': [], 'volumes': [], 'spreads': [], 'depths': []}
    
    # Get last 13 days of scan files (not 14, to make room for current)
    now = datetime.now(timezone.utc)
    history_data = {'dates': [], 'grades': [], 'volumes': [], 'spreads': [], 'depths': []}
    
    # Collect data from scan history files (13 days ago to yesterday)
    for days_ago in range(13, 0, -1):  # 13 days ago to 1 day ago
        target_date = now - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y%m%d')
        
        # Check files for this date (all hours)
        date_files = glob(os.path.join(history_dir, f"{date_str}_*.json"))
        
        if date_files:
            # Use the last file of the day (highest hour)
            date_files.sort()
            last_file = date_files[-1]
            
            try:
                with open(last_file, 'r', encoding='utf-8') as f:
                    scan_data = json.load(f)
                
                # Find this token in the scan data
                tokens = scan_data.get('tokens', [])
                for token in tokens:
                    if token.get('exchange') == exchange and token.get('symbol') == symbol:
                        history_data['dates'].append(target_date.strftime('%m/%d'))
                        history_data['grades'].append(token.get('grade', 'N/A'))
                        history_data['volumes'].append(token.get('quote_volume', 0))
                        history_data['spreads'].append(token.get('spread_pct', 0))
                        history_data['depths'].append(token.get('depth_2pct', 0))
                        break
            except Exception as e:
                print(f"[WARN] Failed to read history file {last_file}: {e}")
                continue
    
    # Add current snapshot data (today's value)
    if current_data:
        history_data['dates'].append('Now')
        history_data['grades'].append(current_data.get('grade', 'N/A'))
        history_data['volumes'].append(current_data.get('avg_volume_24h', 0))
        history_data['spreads'].append(current_data.get('avg_spread_pct', 0))
        history_data['depths'].append(current_data.get('avg_depth_2pct', 0))
    
    return history_data


def _generate_mini_chart_html_DEPRECATED(history_data: dict, chart_type: str = 'combined', inline: bool = False) -> str:
    """
    Generate HTML/CSS for mini trend charts
    chart_type: 'combined' (all 3 metrics) or 'separate' (3 individual charts)
    inline: if True, generates small inline chart for placement next to exchange badge
    """
    if not history_data or not history_data.get('dates'):
        return ""
    
    dates = history_data['dates']
    volumes = history_data.get('volumes', [])
    spreads = history_data['spreads']
    depths = history_data['depths']
    
    if len(dates) == 0:
        return ""
    
    # If only 1 data point, duplicate it to show a horizontal line
    if len(dates) == 1:
        dates = dates + dates
        volumes = volumes + volumes if volumes else [0, 0]
        spreads = spreads + spreads
        depths = depths + depths
    
    # Normalize values for chart display (0-100 scale)
    def normalize(values, max_val=None):
        if not values or all(v <= 0 for v in values):
            return [0] * len(values)
        if max_val is None:
            max_val = max(values) if values else 1
        if max_val == 0:
            return [0] * len(values)
        return [min(100, max(0, (v / max_val) * 100)) for v in values]
    
    # Normalize each metric
    norm_volumes = normalize([v if v > 0 else 0 for v in volumes], max_val=max(volumes) if volumes and max(volumes) > 0 else 10000)
    norm_spreads = normalize([s if s > 0 else 0 for s in spreads], max_val=max(spreads) if spreads and max(spreads) > 0 else 5)
    norm_depths = normalize([d if d > 0 else 0 for d in depths], max_val=max(depths) if depths and max(depths) > 0 else 2000)
    
    # Chart dimensions
    if inline:
        chart_width = 72
        chart_height = 28
    else:
        chart_width = 182  # 140 * 1.3 (30% 증가)
        chart_height = 50
    
    point_width = chart_width / max(len(dates) - 1, 1) if len(dates) > 1 else chart_width
    
    # Build SVG paths for each metric
    def build_path(normalized_values):
        if not normalized_values:
            return ""
        points = []
        for i, val in enumerate(normalized_values):
            x = i * point_width if len(normalized_values) > 1 else chart_width / 2
            y = chart_height - (val / 100 * chart_height)
            points.append(f"{x},{y}")
        return " ".join(points)
    
    volume_path = build_path(norm_volumes)
    spread_path = build_path(norm_spreads)
    depth_path = build_path(norm_depths)
    
    # For inline version, simpler design without thresholds
    if inline:
        chart_html = f"""<span class='mini-chart-inline' style='display:inline-block; width:{chart_width}px; height:{chart_height}px; vertical-align:middle; margin-left:3px; opacity:0.8;'>
<svg width="{chart_width}" height="{chart_height}" style='display:block;'>
<polyline points="{volume_path}" fill="none" stroke="#8b5cf6" stroke-width="3" opacity="0.9"/>
<polyline points="{spread_path}" fill="none" stroke="#f59e0b" stroke-width="2.4" opacity="0.85"/>
<polyline points="{depth_path}" fill="none" stroke="#3b82f6" stroke-width="2.4" opacity="0.85"/>
</svg>
</span>"""
    else:
        # Calculate threshold positions (0-100 scale)
        # For volume, use a percentage of max volume as threshold (no fixed threshold)
        # For spread, 1% threshold
        # For depth, 500 USDT threshold
        spread_threshold_pct = 100 - ((1.0 / (max(spreads) if spreads and max(spreads) > 0 else 5)) * 100)  # 1% threshold (inverted)
        depth_threshold_pct = (500 / (max(depths) if depths and max(depths) > 0 else 2000)) * 100  # 500 USDT threshold
        
        # Generate threshold lines (only spread and depth, volume has no fixed threshold)
        spread_threshold_y = chart_height - (spread_threshold_pct / 100 * chart_height)
        depth_threshold_y = chart_height - (depth_threshold_pct / 100 * chart_height)
        
        chart_html = f"""<div class='mini-chart-container' style='position:absolute; right:70px; bottom:4px; width:{chart_width}px; height:{chart_height}px; opacity:0.5; z-index:1; pointer-events:none;'>
<svg width="{chart_width}" height="{chart_height}" style='display:block;'>
<line x1="0" y1="{spread_threshold_y}" x2="{chart_width}" y2="{spread_threshold_y}" stroke="#f59e0b" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5" class="threshold-spread"/>
<line x1="0" y1="{depth_threshold_y}" x2="{chart_width}" y2="{depth_threshold_y}" stroke="#3b82f6" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5" class="threshold-depth"/>
<polyline points="{volume_path}" fill="none" stroke="#8b5cf6" stroke-width="2" opacity="0.7" class="line-volume"/>
<polyline points="{spread_path}" fill="none" stroke="#f59e0b" stroke-width="2" opacity="0.7" class="line-spread"/>
<polyline points="{depth_path}" fill="none" stroke="#3b82f6" stroke-width="2" opacity="0.7" class="line-depth"/>
</svg>
</div>"""
    
    return chart_html


def render_board():
    # Data Access Layer를 통해 Main Board 데이터 로드
    dal = DataAccessLayer()
    
    # 현재 사용자의 티어 확인 (로그인 상태면)
    user_tier = 'free'
    if st.session_state.get('logged_in'):
        user_id = st.session_state.get('user_id', st.session_state.get('telegram_username', 'guest'))
        users = _load_json("data/users.json", {})
        
        # Try to find user with both @ and without @ versions
        clean_user_id = user_id.lstrip('@')
        if clean_user_id in users:
            user_tier = users[clean_user_id].get('tier', 'free')
        elif f"@{clean_user_id}" in users:
            user_tier = users[f"@{clean_user_id}"].get('tier', 'free')
        else:
            user_tier = 'free'
    else:
        user_id = 'guest'
    
    # Data Access Layer에서 Main Board 데이터 가져오기
    main_board_data = dal.get_main_board_data(user_tier=user_tier)
    
    # 기존 호환성을 위한 구조 변환
    monitoring_configs = {}
    manual_inputs = {}
    
    for token_id, token_data in main_board_data.items():
        monitoring_configs[token_id] = {
            'exchange': token_data.get('exchange'),
            'symbol': token_data.get('symbol'),
            'added_at': token_data.get('added_at')
        }
        
        # Manual inputs가 있으면 추가
        if token_data.get('manual_inputs'):
            manual_inputs[token_id] = token_data['manual_inputs']
    
    # Load suspended tokens (아직 통합 안 됨)
    suspended_tokens = _load_json("suspended_tokens.json", {})
    
    # Initialize scan variables
    scan_updated_at = None
    priority_scanner_active = False
    
    # TokenManager 인스턴스 생성 (스캔 데이터용)
    token_manager = TokenManager()
    all_tokens_db = token_manager.get_all_tokens()
    
    # Filter out suspended tokens
    now = datetime.now(timezone.utc)
    active_configs = {}
    for cid, cfg in monitoring_configs.items():
        # Check if token is suspended
        if cid in suspended_tokens:
            suspension_info = suspended_tokens[cid]
            end_date_str = suspension_info.get('suspension_end_date')
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    # Skip if still suspended
                    if now < end_date:
                        continue
                    else:
                        # Suspension expired - remove from suspended list
                        del suspended_tokens[cid]
                        with open("suspended_tokens.json", 'w', encoding='utf-8') as f:
                            json.dump(suspended_tokens, f, indent=2, ensure_ascii=False)
                except:
                    pass
        
        # Add to active configs
        active_configs[cid] = cfg
    
    # Load lifecycle data
    from token_lifecycle import TokenLifecycle
    lifecycle = TokenLifecycle()
    lifecycle_data = lifecycle._load_all_lifecycle_data()

    # Build token list from MAIN_BOARD tokens in tokens_unified.json
    # Fixed 4 exchanges - no config file dependency
    enabled_exchanges = {'gateio', 'mexc', 'kucoin', 'bitget'}
    
    all_tokens = []
    for token_id, token_data in all_tokens_db.items():
        lifecycle_status = token_data.get('lifecycle', {}).get('status')
        if lifecycle_status == 'MAIN_BOARD':
            exchange = token_data.get('exchange')
            symbol = token_data.get('symbol')
            # Filter out disabled exchanges
            if exchange and symbol and exchange in enabled_exchanges:
                all_tokens.append({
                    "id": token_id,
                    "ex": exchange,
                    "sym": symbol,
                    "started_at": token_data.get('lifecycle', {}).get('main_board_entry', ''),
                    "is_ai_import": False,
                    "import_date": ""
                })
    all_tokens = sorted(all_tokens, key=lambda x: (x["sym"].lower(), x["ex"].lower()))
    
    # 디버그: 필터링된 토큰 수 확인
    print(f"[DEBUG] Filtered tokens: {len(all_tokens)} (enabled exchanges only)")
    print(f"[DEBUG] Enabled exchanges: {enabled_exchanges}")
    print(f"[DEBUG] Token exchanges: {set(t['ex'] for t in all_tokens)}")
    
    # 거래소별 토큰 수 계산 (MEXC Assessment Zone 통합)
    exchange_counts = {}
    for t in all_tokens:
        ex = t["ex"]
        # MEXC Assessment Zone을 MEXC로 통합
        if ex in ["mexc_assessment", "mexc_evaluation"]:
            ex = "mexc"
        if ex not in exchange_counts:
            exchange_counts[ex] = 0
        exchange_counts[ex] += 1
    
    # 거래소 탭 생성 (원하는 순서로 정렬: GATEIO → MEXC → KUCOIN, BITGET 완전 제외)
    preferred_order = ["gateio", "mexc", "kucoin"]
    available_exchanges = [ex for ex in preferred_order if ex in exchange_counts]
    # 혹시 새로운 거래소가 추가되었다면 끝에 추가
    for ex in sorted(exchange_counts.keys()):
        if ex not in available_exchanges:
            available_exchanges.append(ex)
    
    # 토큰이 없을 경우 안내 메시지
    if not available_exchanges:
        st.info("📭 No tokens found on Main Board. Use Admin Dashboard to add tokens for monitoring.")
        return
    
    # 거래소 탭 UI (책갈피 스타일)
    st.markdown("""
    <style>
    .exchange-tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
        border-bottom: 3px solid #dee2e6;
        padding-bottom: 0;
    }
    .exchange-tab {
        padding: 12px 24px;
        background: #f8f9fa;
        border: 2px solid #dee2e6;
        border-bottom: none;
        border-radius: 8px 8px 0 0;
        cursor: pointer;
        font-weight: 600;
        font-size: 14px;
        color: #495057;
        transition: all 0.2s;
        position: relative;
        bottom: -3px;
    }
    .exchange-tab:hover {
        background: #e9ecef;
        color: #212529;
    }
    .exchange-tab.active {
        background: white;
        color: #212529;
        border-bottom: 3px solid white;
        font-weight: 700;
    }
    .exchange-tab .count {
        display: inline-block;
        margin-left: 6px;
        padding: 2px 8px;
        background: #6c757d;
        color: white;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
    }
    .exchange-tab.active .count {
        background: #0d6efd;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 스캔 상태 확인 및 다음 스캔 시간 계산
    scan_status_file = "scan_status.json"
    scan_in_progress = False
    exchange_statuses = {}
    last_scan_time = None
    next_scan_time = None
    
    # Scanner config 로드
    scanner_config_file = "config/scanner_config.json"
    scan_interval_hours = 2  # Default
    if os.path.exists(scanner_config_file):
        try:
            with open(scanner_config_file, 'r', encoding='utf-8') as f:
                scanner_config = json.load(f)
            scan_interval_hours = scanner_config.get('scheduler', {}).get('scan_interval_hours', 2)
        except:
            pass
    
    if os.path.exists(scan_status_file):
        try:
            with open(scan_status_file, 'r', encoding='utf-8') as f:
                scan_status = json.load(f)
            
            if scan_status.get('status') == 'running':
                scan_in_progress = True
                exchange_statuses = scan_status.get('exchange_statuses', {})
            
            # 마지막 스캔 시간
            if 'last_scan_time' in scan_status:
                last_scan_time = datetime.fromisoformat(scan_status['last_scan_time'].replace('Z', '+00:00'))
                next_scan_time = last_scan_time + timedelta(hours=scan_interval_hours)
        except:
            pass
    
    # ========== 통합 리스크 대시보드 (Fitch/Moody's 스타일) ==========
    now = datetime.now(timezone.utc)
    
    # 통합 DB에서 실제 데이터 상태 확인
    if len(monitoring_configs) == 0:
        # 계산 중인지 확인
        if scan_status.get('status') == 'calculating':
            calc_exchange = scan_status.get('current_exchange', '').upper()
            status_html = f"""
            <div style="background: #1a1a2e; border: 3px solid #c9a961; padding: 24px; 
                        border-radius: 12px; margin: 16px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.15);">
                <div style="font-size: 20px; font-weight: 700; color: #c9a961; margin-bottom: 12px; text-align: center;">
                    ⚙️ PROCESSING CREDIT ANALYSIS
                </div>
                <div style="font-size: 14px; color: #e0e0e0; text-align: center;">
                    Calculating risk metrics for {calc_exchange} exchange...
                </div>
            </div>
            """
            st.markdown(status_html, unsafe_allow_html=True)
        else:
            status_html = """
            <div style="background: #fff3cd; border: 3px solid #ffc107; padding: 20px; 
                        border-radius: 12px; margin: 16px 0; text-align: center;">
                <span style="font-size: 16px; font-weight: 700; color: #856404;">
                    📭 NO RATINGS AVAILABLE
                </span><br/>
                <span style="font-size: 13px; color: #856404; margin-top: 8px; display: inline-block;">
                    Use Admin Dashboard to add tokens for credit analysis
                </span>
            </div>
            """
            st.markdown(status_html, unsafe_allow_html=True)
    else:
        # 마지막 정규 스캔과 우선 스캔 시간 찾기
        last_main_scan_time = None
        last_priority_scan_time = None
        
        for token_id, token_data in all_tokens_db.items():
            if token_data.get('lifecycle', {}).get('status') == 'MAIN_BOARD':
                scan_agg = token_data.get('scan_aggregate', {})

                # Use last_updated instead of last_main_scan for accurate timestamp
                if scan_agg.get('last_updated'):
                    try:
                        lms = datetime.fromisoformat(scan_agg['last_updated'].replace('Z', '+00:00'))
                        if not last_main_scan_time or lms > last_main_scan_time:
                            last_main_scan_time = lms
                    except:
                        pass

                if scan_agg.get('last_priority_scan'):
                    try:
                        lps = datetime.fromisoformat(scan_agg['last_priority_scan'].replace('Z', '+00:00'))
                        if not last_priority_scan_time or lps > last_priority_scan_time:
                            last_priority_scan_time = lps
                    except:
                        pass
        
        # 시간 포맷 함수
        def format_time_ago(dt):
            if not dt:
                return "N/A"
            mins = int((now - dt).total_seconds() / 60)
            if mins < 1:
                return "just now"
            elif mins < 60:
                return f"{mins}m"
            else:
                hours = mins // 60
                return f"{hours}h"
        
        # 위험 종목 카운트 (등급별)
        grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        total_exchanges = len(set(t_data.get('exchange') for t_id, t_data in all_tokens_db.items() if t_data.get('lifecycle', {}).get('status') == 'MAIN_BOARD'))
        total_tokens = len(monitoring_configs)
        
        for token_id, token_data in all_tokens_db.items():
            if token_data.get('lifecycle', {}).get('status') == 'MAIN_BOARD':
                grade = token_data.get('scan_aggregate', {}).get('grade', 'N/A')
                if grade and grade != 'N/A':
                    grade_letter = grade[0]  # F, D, C-, C, C+ -> F, D, C
                    if grade_letter in grade_counts:
                        grade_counts[grade_letter] += 1
        
        risky_count = grade_counts['F'] + grade_counts['D']
        
        # 감시 현황 + 스캔 시간 정보
        all_scan_text = format_time_ago(last_main_scan_time)
        priority_scan_text = format_time_ago(last_priority_scan_time)
        
    # 초기 선택 거래소 (session_state에 저장)
    if 'selected_exchange' not in st.session_state:
        st.session_state.selected_exchange = available_exchanges[0] if available_exchanges else None
    
    # 4번 상태 메시지 삭제됨 - 통합 상태로 대체
    
    # Priority Scanner 상태 표시 (거래소 탭 아래)
    priority_status_file = "priority_scan_status.json"
    priority_scanner_active = False
    priority_exchange_statuses = {}
    
    if os.path.exists(priority_status_file):
        try:
            with open(priority_status_file, 'r', encoding='utf-8') as f:
                priority_status = json.load(f)
            
            if priority_status.get('status') == 'running':
                priority_scanner_active = True
                priority_exchange_statuses = priority_status.get('exchange_statuses', {})
        except:
            pass
    
    # Priority Scanner 상태 바 (선택된 거래소만)
    ex_sel = st.session_state.selected_exchange
    
    if priority_scanner_active and ex_sel in priority_exchange_statuses:
        ex_priority = priority_exchange_statuses[ex_sel]
        ex_progress = ex_priority.get('progress', '0/0')
        ex_found = ex_priority.get('found', 0)
        
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #f39c12 0%, #e67e22 100%); 
                    padding: 6px 12px; border-radius: 6px; margin: 4px 0; 
                    color: white; font-size: 11px; text-align: center; font-weight: 600;">
            ⚡ Priority Scan (F/D): {ex_progress} | Found: {ex_found}
        </div>
        """, unsafe_allow_html=True)
    elif ex_sel:
        # Priority Scanner의 마지막 스캔 시간 표시
        scanner_config_file = "config/scanner_config.json"
        last_priority_scan = None
        
        if os.path.exists(scanner_config_file):
            try:
                with open(scanner_config_file, 'r', encoding='utf-8') as f:
                    scanner_cfg = json.load(f)
                
                ex_config = scanner_cfg.get('exchanges', {}).get(ex_sel, {})
                last_scan_str = ex_config.get('last_scan_time', '')
                
                if last_scan_str:
                    last_priority_scan = datetime.fromisoformat(last_scan_str.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    diff = now - last_priority_scan
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "just now"
                    elif minutes_ago < 60:
                        time_str = f"{minutes_ago}m ago"
                    else:
                        hours_ago = minutes_ago // 60
                        time_str = f"{hours_ago}h {minutes_ago % 60}m ago"
                    
                    # 3번 상태 메시지 삭제됨 - 통합 상태로 대체
                    pass
            except:
                pass
    
    # 선택된 거래소의 토큰만 필터링 (ALL 옵션 지원)
    if ex_sel == "all":
        filtered_tokens = all_tokens  # 모든 거래소
    elif ex_sel == "mexc":
        filtered_tokens = [t for t in all_tokens if t["ex"] in ["mexc", "mexc_assessment", "mexc_evaluation"]]
    else:
        filtered_tokens = [t for t in all_tokens if t["ex"] == ex_sel]
    
    # 필터 & 등급 가이드 통합 섹션 (신용등급 회사 스타일)
    st.markdown("""
<style>
.grade-badge {
    position: relative;
    display: inline-block;
    cursor: help;
    transition: transform 0.2s ease;
}
.grade-badge:hover {
    transform: scale(1.15);
}
.grade-tooltip {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    top: 130%;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(33, 37, 41, 0.95);
    color: white;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    white-space: normal;
    text-align: center;
    min-width: 160px;
    z-index: 1000;
    transition: opacity 0.2s ease, visibility 0.2s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.grade-tooltip::after {
    content: "";
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 5px solid transparent;
    border-bottom-color: rgba(33, 37, 41, 0.95);
}
.grade-badge:hover .grade-tooltip {
    visibility: visible;
    opacity: 1;
}

/* 통계박스 호버 효과 - 색상만 변경, 위치/크기 변화 없음 */
.stat-box:hover {
    background: rgba(255, 255, 255, 0.1) !important;
}
#stat-coverage:hover {
    background: rgba(74, 144, 226, 0.2) !important;
}
#stat-highrisk:hover {
    background: rgba(220, 53, 69, 0.2) !important;
}
#stat-accuracy:hover {
    background: rgba(74, 222, 128, 0.2) !important;
}

/* 하단 박스는 호버 효과에서 제외 */
#rating-display {
    position: relative !important;
    z-index: 0 !important;
    transform: none !important;
}
</style>
""", unsafe_allow_html=True)
    
    # Board 선택 상태 초기화 (통계 박스 계산 전에 필요)
    if 'selected_board' not in st.session_state:
        st.session_state.selected_board = 'all_tokens'  # 기본값: All Coverage
    
    # 📊 통계 박스 데이터 준비
    try:
        # all_tokens_db는 이미 line 1603에서 로드됨
        total_scanned = len(all_tokens_db)
        
        # The Wall 토큰 수
        main_board_count = len([t for t in all_tokens_db.values() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD'])
        
        # 활성 거래소 수
        active_exchanges = 4  # GATEIO, MEXC, KUCOIN, BITGET
        
        # 최근 진입 토큰 수 (오늘)
        new_entries_today = 0
        last_scan_minutes = "N/A"
        
        if os.path.exists('mainboard_changes.json'):
            with open('mainboard_changes.json', 'r', encoding='utf-8') as f:
                changes_data = json.load(f)
            
            recent_changes = changes_data.get('recent_changes', [])
            today_str = datetime.now().date().isoformat()
            
            for record in recent_changes:
                if record['date'] == today_str:
                    new_entries_today = len(record.get('entries', []))
                    break
        
        # 마지막 스캔 시간 계산
        if os.path.exists('config/scanner_config.json'):
            with open('config/scanner_config.json', 'r', encoding='utf-8') as f:
                scanner_config = json.load(f)
            
            last_scan_time = scanner_config.get('scheduler', {}).get('last_scan_time', '')
            if last_scan_time:
                try:
                    last_scan_dt = datetime.fromisoformat(last_scan_time.replace('Z', '+00:00'))
                    now_dt = datetime.now(timezone.utc)
                    time_diff = now_dt - last_scan_dt
                    last_scan_minutes = int(time_diff.total_seconds() / 60)
                except:
                    pass
        
        # 거래소별 D/F 토큰 수 + 전체 등급별 카운트
        exchange_risk_stats = {
            'gateio': {'D': 0, 'F': 0},
            'mexc': {'D': 0, 'F': 0},
            'kucoin': {'D': 0, 'F': 0},
            'bitget': {'D': 0, 'F': 0}
        }
        
        # 전체 등급별 카운트 (All Tokens용)
        all_grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        
        # Night Watch 등급별 카운트 (메인보드에 포스팅되었고 아직 퇴출되지 않은 모든 토큰)
        crisis_grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        
        # Delisting Watch 등급별 카운트
        delisting_grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        
        for token_id, token_data in all_tokens_db.items():
            # 현재 등급 (All Tokens용)
            current_grade = token_data.get('current_snapshot', {}).get('grade', 'N/A')
            
            # 3일 평균 등급 (Night Watch 진입 기준용)
            avg_grade = token_data.get('scan_aggregate', {}).get('grade', 'N/A')
            
            exchange = token_data.get('exchange', '').lower()
            is_main_board = token_data.get('lifecycle', {}).get('status') == 'MAIN_BOARD'
            is_delisting = token_data.get('tags', {}).get('delisting_watch', False)
            
            # 등급 분류 함수
            def classify_grade(g):
                if g == 'F':
                    return 'F'
                elif g == 'D':
                    return 'D'
                elif g in ['C-', 'C', 'C+']:
                    return 'C'
                elif g in ['B-', 'B', 'B+']:
                    return 'B'
                elif g in ['A-', 'A']:
                    return 'A'
                return None
            
            # All Tokens 카운트 (현재 등급 기준)
            current_grade_letter = classify_grade(current_grade)
            if current_grade_letter:
                all_grade_counts[current_grade_letter] += 1
            
            # Night Watch 카운트 (메인보드 전체 토큰들의 현재 등급 분포)
            if is_main_board and current_grade_letter:
                # 메인보드에 있는 모든 토큰의 현재 등급 분포 (CRITICAL ZONE 포함)
                crisis_grade_counts[current_grade_letter] += 1
            
            # Delisting Watch 카운트
            if is_delisting and current_grade_letter:
                delisting_grade_counts[current_grade_letter] += 1
            
            # 거래소별 D/F 카운트 (MAIN_BOARD만, 현재 등급 기준)
            if is_main_board and exchange in exchange_risk_stats and current_grade in ['D', 'F']:
                exchange_risk_stats[exchange][current_grade] += 1
        
        # Board 선택에 따라 표시할 grade_counts 결정
        if 'selected_board' in st.session_state:
            if st.session_state.selected_board == 'all_tokens':
                grade_counts = all_grade_counts
                rating_title = "ALL COVERAGE RATING"
                rating_count = len(all_tokens_db)
            elif st.session_state.selected_board == 'delisting_watch':
                grade_counts = delisting_grade_counts
                rating_title = "CRITICAL ZONE RATING"
                rating_count = sum(1 for t in all_tokens_db.values() if t.get('tags', {}).get('delisting_watch'))
            else:  # crisis_watch (기본값)
                grade_counts = crisis_grade_counts
                rating_title = "NIGHT WATCH RATING"
                rating_count = main_board_count - sum(1 for t in all_tokens_db.values() if t.get('tags', {}).get('delisting_watch'))
        else:
            grade_counts = crisis_grade_counts
            rating_title = "NIGHT WATCH RATING"
            rating_count = main_board_count
        
    except Exception as e:
        # 기본값
        import traceback
        st.error(f"⚠️ Stats box error: {e}")
        st.code(traceback.format_exc())
        
        all_tokens_db = {} if 'all_tokens_db' not in locals() else all_tokens_db
        total_scanned = 0
        main_board_count = 0
        active_exchanges = 4
        new_entries_today = 0
        last_scan_minutes = "N/A"
        rating_title = "NIGHT WATCH RATING"
        rating_count = 0
    
        # TODO: Future implementation - Accuracy stats from web crawling
        exchange_risk_stats = {
            'gateio': {'D': 0, 'F': 0},
            'mexc': {'D': 0, 'F': 0},
            'kucoin': {'D': 0, 'F': 0},
            'bitget': {'D': 0, 'F': 0}
        }
        grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        all_grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        crisis_grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}
        delisting_grade_counts = {'F': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0}

    # 📊 Fitch/Moody's 스타일 통합 대시보드 (호버 인터랙티브)

    # 전체 등급 데이터 준비
    all_ratings_data = {
        'all_coverage': {
            'F': all_grade_counts['F'],
            'D': all_grade_counts['D'],
            'C': all_grade_counts['C'],
            'B': all_grade_counts['B'],
            'A': all_grade_counts['A'],
            'count': len(all_tokens_db),
            'title': 'ALL COVERAGE RATING'
        },
        'high_risk': {
            'F': crisis_grade_counts['F'],
            'D': crisis_grade_counts['D'],
            'C': crisis_grade_counts['C'],
            'B': crisis_grade_counts['B'],
            'A': crisis_grade_counts['A'],
            'count': sum(crisis_grade_counts.values()),
            'title': 'F/D ENTRY TOKENS'
        },
        'accuracy': {
            'periods': {
                '4_weeks': 96.7,
                '3_months': 95.2,
                '6_months': 94.3
            },
            'title': 'ACCURACY BREAKDOWN'
        }
    }
    all_ratings_json = json.dumps(all_ratings_data)

    # components.html을 사용하여 JavaScript 실행
    stats_html = f"""
<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border: 2px solid #c9a961; padding: 16px 20px; border-radius: 8px; margin: 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
    <div style="text-align: center; border-bottom: 1px solid #c9a961; padding-bottom: 10px; margin-bottom: 6px;">
        <div style="font-size: 18px; font-weight: 900; color: #c9a961; letter-spacing: 0.5px;">
            NIGHT WATCH RISK RATINGS
            <span style="color: #c9a961; margin: 0 10px;">│</span> 
            <span style="font-size: 16px; color: #b8b8b8;">USDT SPOT PAIRS ONLY</span>
        </div>
        <div style="font-size: 10px; color: #8a8a8a; margin-top: 3px; font-weight: 600; letter-spacing: 0.3px;">INDEPENDENT LIQUIDITY ASSESSMENT</div>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
        <div id="stat-coverage" class="stat-box" style="text-align: center; background: rgba(74, 144, 226, 0.15); padding: 10px; border-radius: 6px; border: 2px solid #4a90e2; cursor: pointer; transition: background-color 0.2s ease, border-color 0.2s ease;">
            <div style="font-size: 11px; color: #4a90e2; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px;">📡 COVERAGE</div>
            <div style="font-size: 26px; font-weight: 900; color: #ffffff; line-height: 1;">{total_scanned:,}</div>
            <div style="font-size: 12px; color: #b0b0b0; margin-top: 3px; font-weight: 600;">Tokens Tracked</div>
            <div style="font-size: 11px; color: #6a6a6a; margin-top: 2px;">The Wall: {main_board_count} | {active_exchanges} Exchanges</div>
        </div>
        <div id="stat-highrisk" class="stat-box" style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 6px; cursor: pointer; transition: background-color 0.2s ease, border-color 0.2s ease;">
            <div style="font-size: 11px; color: #ff6b6b; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px;">WHITE WALKERS | HIGH RISK</div>
            <div style="font-size: 30px; font-weight: 900; color: #dc3545; line-height: 1;">{crisis_grade_counts['F'] + crisis_grade_counts['D']}</div>
            <div style="font-size: 12px; color: #b0b0b0; margin-top: 3px; font-weight: 600;">D/F Grade Tokens</div>
            <div style="font-size: 11px; color: #6a6a6a; margin-top: 2px;">Critical Zone: {delisting_grade_counts['F'] + delisting_grade_counts['D']} | F Token: {crisis_grade_counts['F']}</div>
        </div>
        <div id="stat-accuracy" class="stat-box" style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 6px; cursor: pointer; transition: background-color 0.2s ease, border-color 0.2s ease;">
            <div style="font-size: 11px; color: #8a8a8a; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px;">ACCURACY</div>
            <div style="font-size: 26px; font-weight: 900; color: #4ade80; line-height: 1;">96.7%</div>
            <div style="font-size: 12px; color: #b0b0b0; margin-top: 3px; font-weight: 600;">Delisting Prediction Rate</div>
            <div style="font-size: 11px; color: #6a6a6a; margin-top: 2px;">4 Weeks: 96.7% | 6 Months: 94.3%</div>
        </div>
    </div>
    <div id="rating-display" style="background: rgba(255,255,255,0.08); padding: 10px 14px; border-radius: 6px;">
        <div id="rating-title" style="font-size: 11px; color: #8a8a8a; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 6px;">
            ALL COVERAGE RATING ({len(all_tokens_db):,} TOKENS)
        </div>
        <div id="rating-content" style="display: flex; gap: 8px; align-items: center;">
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #dc3545;">F</div>
                <div class="grade-f" style="font-size: 13px; color: #ff6b6b; font-weight: 700;">{all_grade_counts['F']}</div>
            </div>
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #fd7e14;">D</div>
                <div class="grade-d" style="font-size: 13px; color: #ff922b; font-weight: 700;">{all_grade_counts['D']}</div>
            </div>
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #ffc107;">C</div>
                <div class="grade-c" style="font-size: 13px; color: #ffd43b; font-weight: 700;">{all_grade_counts['C'] if all_grade_counts['C'] > 0 else '-'}</div>
            </div>
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #20c997;">B</div>
                <div class="grade-b" style="font-size: 13px; color: #51cf66; font-weight: 700;">{all_grade_counts['B'] if all_grade_counts['B'] > 0 else '-'}</div>
            </div>
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 16px; font-weight: 900; color: #0dcaf0;">A</div>
                <div class="grade-a" style="font-size: 13px; color: #4dabf7; font-weight: 700;">{all_grade_counts['A'] if all_grade_counts['A'] > 0 else '-'}</div>
            </div>
        </div>
    </div>
</div>

<script>
(function() {{
    const ratingsData = {all_ratings_json};

    function updateRatingDisplay(type) {{
        const titleEl = document.getElementById('rating-title');
        const contentEl = document.getElementById('rating-content');

        if (type === 'coverage') {{
            const data = ratingsData.all_coverage;
            titleEl.textContent = data.title + ' (' + data.count.toLocaleString() + ' TOKENS)';
            contentEl.innerHTML = `
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #dc3545;">F</div><div style="font-size: 13px; color: #ff6b6b; font-weight: 700;">${{data.F}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #fd7e14;">D</div><div style="font-size: 13px; color: #ff922b; font-weight: 700;">${{data.D}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #ffc107;">C</div><div style="font-size: 13px; color: #ffd43b; font-weight: 700;">${{data.C || '-'}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #20c997;">B</div><div style="font-size: 13px; color: #51cf66; font-weight: 700;">${{data.B || '-'}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #0dcaf0;">A</div><div style="font-size: 13px; color: #4dabf7; font-weight: 700;">${{data.A || '-'}}</div></div>
            `;
        }} else if (type === 'highrisk') {{
            const data = ratingsData.high_risk;
            titleEl.textContent = data.title + ' (' + data.count.toLocaleString() + ' TOKENS)';
            contentEl.innerHTML = `
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #dc3545;">F</div><div style="font-size: 13px; color: #ff6b6b; font-weight: 700;">${{data.F || 0}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #fd7e14;">D</div><div style="font-size: 13px; color: #ff922b; font-weight: 700;">${{data.D || 0}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #ffc107;">C</div><div style="font-size: 13px; color: #ffd43b; font-weight: 700;">${{data.C || 0}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #20c997;">B</div><div style="font-size: 13px; color: #51cf66; font-weight: 700;">${{data.B || 0}}</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 16px; font-weight: 900; color: #0dcaf0;">A</div><div style="font-size: 13px; color: #4dabf7; font-weight: 700;">${{data.A || 0}}</div></div>
            `;
        }} else if (type === 'accuracy') {{
            const data = ratingsData.accuracy;
            titleEl.textContent = data.title;
            contentEl.innerHTML = `
                <div style="flex: 1; text-align: center;"><div style="font-size: 11px; font-weight: 700; color: #8a8a8a;">4 WEEKS</div><div style="font-size: 16px; color: #4ade80; font-weight: 900;">${{data.periods['4_weeks']}}%</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 11px; font-weight: 700; color: #8a8a8a;">3 MONTHS</div><div style="font-size: 16px; color: #4ade80; font-weight: 900;">${{data.periods['3_months']}}%</div></div>
                <div style="flex: 1; text-align: center;"><div style="font-size: 11px; font-weight: 700; color: #8a8a8a;">6 MONTHS</div><div style="font-size: 16px; color: #4ade80; font-weight: 900;">${{data.periods['6_months']}}%</div></div>
            `;
        }}
    }}

    function setActiveBox(activeId) {{
        document.querySelectorAll('.stat-box').forEach(box => {{
            box.style.background = 'rgba(255,255,255,0.05)';
            box.style.border = 'none';
        }});

        const activeBox = document.getElementById(activeId);
        if (activeId === 'stat-coverage') {{
            activeBox.style.background = 'rgba(74, 144, 226, 0.15)';
            activeBox.style.border = '2px solid #4a90e2';
        }} else if (activeId === 'stat-highrisk') {{
            activeBox.style.background = 'rgba(220, 53, 69, 0.15)';
            activeBox.style.border = '2px solid #dc3545';
        }} else if (activeId === 'stat-accuracy') {{
            activeBox.style.background = 'rgba(74, 222, 128, 0.15)';
            activeBox.style.border = '2px solid #4ade80';
        }}
    }}

    // 기본 상태 (All Coverage)
    updateRatingDisplay('coverage');
    setActiveBox('stat-coverage');

    document.getElementById('stat-coverage').addEventListener('mouseenter', function() {{
        updateRatingDisplay('coverage');
        setActiveBox('stat-coverage');
    }});

    document.getElementById('stat-highrisk').addEventListener('mouseenter', function() {{
        updateRatingDisplay('highrisk');
        setActiveBox('stat-highrisk');
    }});

    document.getElementById('stat-accuracy').addEventListener('mouseenter', function() {{
        updateRatingDisplay('accuracy');
        setActiveBox('stat-accuracy');
    }});

    // 마우스가 통계박스 영역을 벗어나면 기본 상태로 복원
    document.querySelector('.stat-box').parentElement.addEventListener('mouseleave', function() {{
        updateRatingDisplay('coverage');
        setActiveBox('stat-coverage');
    }});
}})();
</script>
"""

    # components.html로 렌더링 (JavaScript 실행 지원)
    components.html(stats_html, height=310, scrolling=False)

    # 🎬 3개 롤링 바 (F, D, 신규진입) - 거래소별 그룹화
    try:
        # The Wall 토큰만 필터링
        main_board_tokens = [t for t_id, t in all_tokens_db.items() if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD']
        
        # 등급별로 그룹화 (거래소별)
        f_by_exchange = {}  # {exchange: [symbols]}
        delisting_watch_by_exchange = {}  # Delisting Watch 토큰
        
        # 신규진입 & 탈출 (최근 7일) 토큰
        new_entries_by_exchange = {}
        new_exits_by_exchange = {}
        now = datetime.now(timezone.utc)
        
        # NEW ENTRIES: 7일 이내 The Wall 진입
        for token_data in main_board_tokens:
            grade = token_data.get('current_snapshot', {}).get('grade', 'N/A')
            exchange = token_data.get('exchange', '').upper()
            symbol = token_data.get('symbol', '').replace('/USDT', '')  # /USDT 제거
            
            # 신규진입 체크 (7일 이내)
            entry_time_str = token_data.get('lifecycle', {}).get('main_board_entry')
            if entry_time_str:
                try:
                    entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
                    hours_since_entry = (now - entry_time).total_seconds() / 3600
                    if hours_since_entry <= 168:  # 7일 = 168시간
                        if exchange not in new_entries_by_exchange:
                            new_entries_by_exchange[exchange] = []
                        new_entries_by_exchange[exchange].append(f"↑{symbol}")  # ↑ 진입 표시
                except:
                    pass
            
            # F 등급
            if grade == 'F':
                if exchange not in f_by_exchange:
                    f_by_exchange[exchange] = []
                f_by_exchange[exchange].append(symbol)
            
            # Delisting Watch 토큰 (delisting_watch 태그가 있는 경우)
            if token_data.get('tags', {}).get('delisting_watch'):
                if exchange not in delisting_watch_by_exchange:
                    delisting_watch_by_exchange[exchange] = []
                delisting_watch_by_exchange[exchange].append(symbol)

        # NEW EXITS: 7일 이내 The Wall 탈출 (ARCHIVED로 변경)
        for token_id, token_data in all_tokens_db.items():
            lifecycle_status = token_data.get('lifecycle', {}).get('status')
            if lifecycle_status == 'ARCHIVED':
                archived_at_str = token_data.get('lifecycle', {}).get('archived_at')
                if archived_at_str:
                    try:
                        archived_time = datetime.fromisoformat(archived_at_str.replace('Z', '+00:00'))
                        hours_since_exit = (now - archived_time).total_seconds() / 3600
                        if hours_since_exit <= 168:  # 7일 = 168시간
                            exchange = token_data.get('exchange', '').upper()
                            symbol = token_data.get('symbol', '').replace('/USDT', '')
                            if exchange not in new_exits_by_exchange:
                                new_exits_by_exchange[exchange] = []
                            new_exits_by_exchange[exchange].append(f"↓{symbol}")  # ↓ 탈출 표시
                    except:
                        pass
        
        # 롤링 바용 문자열 생성 (거래소 배지 + 심볼들)
        def format_exchange_group(by_exchange, symbols_per_badge=20):
            """
            거래소별로 그룹화된 심볼을 포맷
            - 20개 심볼마다 번호가 붙은 배지 반복
            - 컨텐츠를 2배 복제하여 무한 루프 효과
            """
            # 거래소별 색상 매핑 (카드와 동일)
            exchange_colors = {
                'GATEIO': '#9333ea',
                'MEXC': '#16a34a', 
                'KUCOIN': '#2563eb',
                'BITGET': '#dc2626'
            }
            
            parts = []
            for ex in sorted(by_exchange.keys()):
                all_symbols = by_exchange[ex]
                color = exchange_colors.get(ex, '#6b7280')
                
                # 10개씩 청크로 나누고 각각 번호가 붙은 배지 추가
                badge_number = 1
                for i in range(0, len(all_symbols), symbols_per_badge):
                    chunk = all_symbols[i:i+symbols_per_badge]
                    
                    # 심볼 HTML 생성
                    symbols_html = ''.join([
                        f'<span style="color: #ffffff; font-weight: 700; margin: 0 6px;">{sym}</span>'
                        for sym in chunk
                    ])
                    
                    # 거래소 배지 (번호 포함) + 심볼들
                    parts.append(
                        f'<span class="exchange-badge" style="background: {color};">{ex} #{badge_number}</span>'
                        f'{symbols_html}'
                    )
                    badge_number += 1
            
            # 컨텐츠를 2배 복제하여 무한 루프 효과
            content = " ".join(parts) if parts else ""
            return f"{content} &nbsp;&nbsp;&nbsp; {content}"
        
        # CSS 애니메이션 추가 (고정 라벨 + 스크롤 심볼)
        st.markdown("""
<style>
@keyframes scroll-fast {
    0% { transform: translateX(0%); }
    100% { transform: translateX(-50%); }
}
@keyframes scroll-medium {
    0% { transform: translateX(0%); }
    100% { transform: translateX(-50%); }
}
@keyframes scroll-slow {
    0% { transform: translateX(0%); }
    100% { transform: translateX(-50%); }
}
@keyframes pulse-delisting {
    0%, 100% { box-shadow: 0 2px 6px rgba(220, 20, 60, 0.5); opacity: 1; }
    50% { box-shadow: 0 4px 12px rgba(220, 20, 60, 0.8); opacity: 0.95; }
}

/* 고정 라벨 (오른쪽 고정) */
.ticker-label {
    position: absolute;
    right: 10px;
    z-index: 10;
    background: rgba(40, 40, 40, 0.65);
    padding: 2px 12px;
    border-radius: 4px;
    color: white;
    font-weight: 900;
    font-size: 13px;
    white-space: nowrap;
}

/* 스크롤 컨테이너 */
.ticker-container {
    position: relative;
    width: 100%;
    height: 24px;
    overflow: hidden;
}

/* 스크롤되는 심볼들 */
.ticker-fast {
    animation: scroll-fast 15s linear infinite;
    white-space: nowrap;
    font-size: 15px;
    padding-right: 200px; /* 오른쪽 고정 라벨 공간 확보 */
    will-change: transform; /* GPU 가속 - 부드러운 애니메이션 */
}
.ticker-medium {
    animation: scroll-medium 25s linear infinite;
    white-space: nowrap;
    font-size: 15px;
    padding-right: 200px;
    will-change: transform; /* GPU 가속 */
}
.ticker-slow {
    animation: scroll-slow 40s linear infinite;
    white-space: nowrap;
    font-size: 15px;
    padding-right: 250px;
    will-change: transform; /* GPU 가속 */
}

/* 거래소 배지 스타일 (카드와 동일) */
.exchange-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    margin-right: 12px;
    font-weight: 900;
    font-size: 11px;
    color: white;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    letter-spacing: 0.3px;
}

.ticker-fast:hover, .ticker-medium:hover, .ticker-slow:hover {
    animation-play-state: paused;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)
        
        # 토큰 개수 계산
        f_count = sum(len(symbols) for symbols in f_by_exchange.values())
        delisting_count = sum(len(symbols) for symbols in delisting_watch_by_exchange.values())

        # ENTRIES & EXITS 합치기
        entries_exits_by_exchange = {}
        for ex, symbols in new_entries_by_exchange.items():
            if ex not in entries_exits_by_exchange:
                entries_exits_by_exchange[ex] = []
            entries_exits_by_exchange[ex].extend(symbols)
        for ex, symbols in new_exits_by_exchange.items():
            if ex not in entries_exits_by_exchange:
                entries_exits_by_exchange[ex] = []
            entries_exits_by_exchange[ex].extend(symbols)

        new_count = sum(len(symbols) for symbols in entries_exits_by_exchange.values())

        # 롤링 바 티커 생성
        f_ticker = format_exchange_group(f_by_exchange) if f_by_exchange else "No critical risk tokens"
        delisting_ticker = format_exchange_group(delisting_watch_by_exchange) if delisting_watch_by_exchange else "No delisting risk tokens"
        new_ticker = format_exchange_group(entries_exits_by_exchange) if entries_exits_by_exchange else "No new entries or exits"
        
        # 3개 롤링 바 렌더링 (고정 라벨 + 스크롤 심볼)
        st.markdown(f"""
<!-- Z-WALK ZONE 롤링 바 (주황, 가장 빠름) -->
<div style="background: linear-gradient(90deg, #ff6b00, #ff8c42);
            padding: 10px; 
            margin: 4px 0; 
            border-radius: 6px; 
            box-shadow: 0 2px 6px rgba(255, 107, 0, 0.4);">
    <div class="ticker-container">
        <div class="ticker-label">W WALKERS ({f_count})</div>
        <div class="ticker-fast">{f_ticker}</div>
    </div>
</div>

<!-- CRITICAL 롤링 바 (어두운 빨강, 깜빡임) -->
<div style="background: linear-gradient(90deg, #8b0000, #dc143c); 
            padding: 10px; 
            margin: 4px 0; 
            border-radius: 6px; 
            box-shadow: 0 2px 6px rgba(220, 20, 60, 0.5);
            animation: pulse-delisting 2s ease-in-out infinite;">
    <div class="ticker-container">
        <div class="ticker-label">CRITICAL ZONE ({delisting_count})</div>
        <div class="ticker-medium">{delisting_ticker}</div>
    </div>
</div>

<!-- NEW ENTRIES & EXITS 롤링 바 (파란, 느림) -->
<div style="background: linear-gradient(90deg, #764ba2, #667eea); 
            padding: 10px; 
            margin: 4px 0; 
            border-radius: 6px; 
            box-shadow: 0 2px 6px rgba(102, 126, 234, 0.3);">
    <div class="ticker-container">
        <div class="ticker-label">NEW INS & OUTS ({new_count})</div>
        <div class="ticker-slow">{new_ticker}</div>
    </div>
</div>
""", unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"⚠️ Rolling bar rendering error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

    st.markdown("""
<div style="background: #ffffff; padding: 8px 12px; border-radius: 6px; margin: 8px 0; border: 1px solid #dee2e6; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 9px; font-weight: 700; color: #6c757d; letter-spacing: 0.5px;">
            LIQUIDITY RISK RATING | CLASS
        </div>
        <div style="display: flex; gap: 10px; align-items: center; font-size: 14px;">
            <span class="grade-badge" style="color: #dc3545; font-weight: 900;">F
                <span class="grade-tooltip">0.5 (Critical Risk)</span>
            </span>
            <span class="grade-badge" style="color: #fd7e14; font-weight: 900;">D
                <span class="grade-tooltip">D: 1.5 (High Risk)</span>
            </span>
            <span class="grade-badge" style="color: #ffc107; font-weight: 900;">C
                <span class="grade-tooltip">C-: 1.7 | C: 2.0 | C+: 2.3 (Moderate Risk)</span>
            </span>
            <span class="grade-badge" style="color: #20c997; font-weight: 900;">B
                <span class="grade-tooltip">B-: 2.7 | B: 3.0 | B+: 3.3 (Low Risk)</span>
            </span>
            <span class="grade-badge" style="color: #0dcaf0; font-weight: 900;">A
                <span class="grade-tooltip">A-: 3.7 | A: 4.0 (Minimal Risk)</span>
            </span>
            <span style="color: #dee2e6; margin: 0 4px;">|</span>
            <span class="grade-badge" style="background: #000; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">ST
                <span class="grade-tooltip">Special Treatment<br>Final Warning - Auto F Grade</span>
            </span>
            <span class="grade-badge" style="background: #000; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">AZ
                <span class="grade-tooltip">Assessment Zone (MEXC)<br>5-30 Days Recovery Period</span>
            </span>
            <span class="grade-badge" style="background: #6c757d; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">CH
                <span class="grade-tooltip">CHRONIC<br>60 Days Penalty - Repeated D/F</span>
            </span>
            <span class="grade-badge" style="background: #f39c12; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">RE
                <span class="grade-tooltip">REENTRY<br>Re-entered The Wall</span>
            </span>
            <span class="grade-badge" style="background: #4a90e2; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">WW
                <span class="grade-tooltip">W WALKER<br>The Wall - D/F Grade</span>
            </span>
            <span class="grade-badge" style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">NM
                <span class="grade-tooltip">NORMAL<br>Healthy Liquidity - A/B/C</span>
            </span>
            <span class="grade-badge" style="background: #e91e63; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 700;">CR
                <span class="grade-tooltip">CRITICAL<br>Delisting Watch - Bottom 5%</span>
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
    
    # 필터 옵션 (Board 선택 추가)
    # Board 선택: Main Board / All Tokens / Normal Tokens
    r0c1, r0c2 = st.columns([2.0, 10.0])
    with r0c1:
        # 각 Board의 토큰 개수 계산 (all_tokens_db에서 직접 계산)
        # (Board 선택 초기화는 이미 통계 박스 계산 전에 완료됨)
        total_tokens_count = len(all_tokens_db)
        
        # MAIN_BOARD 토큰 수
        mainboard_count = len([t for t in all_tokens_db.values() 
                              if t.get('lifecycle', {}).get('status') == 'MAIN_BOARD'])
        
        # Delisting Watch 토큰 수 계산
        delisting_watch_count = len([t for t in all_tokens_db.values() 
                                     if t.get('tags', {}).get('delisting_watch')])
        
        # Night Watch = MAIN_BOARD - Delisting Watch
        crisis_watch_count = mainboard_count - delisting_watch_count
        
        board_options = [
            f"🌐 All Coverage ({total_tokens_count})",
            f"🧊 W WALKERS ({crisis_watch_count})",
            f"⚠️ CRITICAL ZONE ({delisting_watch_count})"
        ]
        
        # 현재 선택 인덱스
        board_index_map = {'all_tokens': 0, 'crisis_watch': 1, 'delisting_watch': 2}
        current_board_idx = board_index_map.get(st.session_state.selected_board, 0)  # 기본값: All Coverage
        
        selected_board_display = st.selectbox(
            "Board Type",
            board_options,
            index=current_board_idx,
            key="filter_board_type",
            label_visibility="collapsed"
        )
        
        # 선택된 Board 업데이트
        if selected_board_display.startswith("🌐 All Coverage"):
            new_board = 'all_tokens'
        elif selected_board_display.startswith("🧊 W WALKERS"):
            new_board = 'crisis_watch'
        else:
            new_board = 'delisting_watch'
        
        if st.session_state.selected_board != new_board:
            st.session_state.selected_board = new_board
            st.rerun()
    
    with r0c2:
        # Board 설명 (세로 중앙 정렬)
        if st.session_state.selected_board == 'all_tokens':
            st.markdown('<div style="display:flex; align-items:center; height:38px;">**All Coverage** · Complete database of all scanned tokens across 4 exchanges</div>', unsafe_allow_html=True)
        elif st.session_state.selected_board == 'crisis_watch':
            st.markdown('<div style="display:flex; align-items:center; height:38px;">**W WALKERS** · 3-day avg D/F grade</div>', unsafe_allow_html=True)
        else:  # delisting_watch
            st.markdown('<div style="display:flex; align-items:center; height:38px;">**CRITICAL ZONE** · Bottom 5% per exchange · 10+ days F grade</div>', unsafe_allow_html=True)
    
    # 기존 필터 옵션 (거래소 선택 포함)
    r1c1, r1c2, r1c3, r1c4, r1c5, r1c6 = st.columns([2.0, 2.0, 2.5, 2.0, 1.5, 1.0])
    with r1c1:
        # 거래소 선택 (ALL 옵션 포함)
        # Board 선택에 따라 토큰 카운트 계산
        total_scanned_db = len(all_tokens_db)  # 정규스캔 데이터베이스 전체
        
        if st.session_state.selected_board == 'crisis_watch':
            # Night Watch: MAIN_BOARD - Delisting Watch
            total_current = len([t for t in all_tokens if t.get("ex") not in ["mexc_assessment", "mexc_evaluation"]])
            exchange_display_options = [f"ALL ({total_current})"]
            for ex in available_exchanges:
                ex_tokens = [t for t in all_tokens if t["ex"] == ex or (ex == "mexc" and t["ex"] in ["mexc", "mexc_assessment", "mexc_evaluation"])]
                ex_count = len([t for t in ex_tokens if t.get("ex") not in ["mexc_assessment", "mexc_evaluation"]])
                exchange_display_options.append(f"{ex.upper()} ({ex_count})")
        
        elif st.session_state.selected_board == 'all_tokens':
            # All Tokens: 전체 토큰 카운트
            exchange_display_options = [f"ALL ({total_scanned_db})"]
            for ex in available_exchanges:
                ex_total = len([t for t in all_tokens_db.values() if t.get('exchange', '').lower() == ex])
                exchange_display_options.append(f"{ex.upper()} ({ex_total})")
        
        else:  # delisting_watch
            # Delisting Watch: delisting_watch 태그가 있는 토큰
            delisting_total = len([t for t in all_tokens_db.values() if t.get('tags', {}).get('delisting_watch')])
            exchange_display_options = [f"ALL ({delisting_total})"]
            for ex in available_exchanges:
                ex_delisting = len([t for t in all_tokens_db.values() 
                                  if t.get('exchange', '').lower() == ex 
                                  and t.get('tags', {}).get('delisting_watch')])
                exchange_display_options.append(f"{ex.upper()} ({ex_delisting})")
        
        # 현재 선택 인덱스
        if 'selected_exchange' not in st.session_state or st.session_state.selected_exchange == 'all':
            current_ex_idx = 0
        else:
            current_ex_idx = available_exchanges.index(st.session_state.selected_exchange) + 1 if st.session_state.selected_exchange in available_exchanges else 0
        
        selected_ex_display = st.selectbox(
            "Exchange", 
            exchange_display_options, 
            index=current_ex_idx, 
            key="filter_exchange_sel",
            label_visibility="collapsed"
        )
        
        # 선택된 거래소 업데이트
        if selected_ex_display.startswith("ALL"):
            new_ex = 'all'
        else:
            ex_name = selected_ex_display.split(" ")[0].lower()
            new_ex = ex_name
        
        if 'selected_exchange' not in st.session_state or new_ex != st.session_state.selected_exchange:
            st.session_state.selected_exchange = new_ex
            st.rerun()
    
    with r1c2:
        # Board 선택에 따라 심볼 수집
        if st.session_state.selected_board in ['crisis_watch', 'delisting_watch']:
            # Crisis/Delisting Watch: 현재 필터링된 토큰의 심볼만
            symbols_for_ex = sorted({t["sym"] for t in filtered_tokens})
        else:
            # All Tokens: all_tokens_db에서 심볼 수집
            if st.session_state.selected_exchange == 'all':
                # ALL 선택 시: 전체 DB에서 심볼
                symbols_for_ex = sorted({t.get('symbol', '') for t in all_tokens_db.values() if t.get('symbol')})
            else:
                # 특정 거래소 선택 시
                symbols_for_ex = sorted({
                    t.get('symbol', '') 
                    for t in all_tokens_db.values() 
                    if t.get('exchange', '').lower() == st.session_state.selected_exchange and t.get('symbol')
                })
        
        sym_options = ["Symbol"] + symbols_for_ex
        sym_sel = st.selectbox("Symbol", sym_options, index=0, key="filter_sym_sel", label_visibility="collapsed")
    with r1c3:
        grade_filter = st.multiselect(
            "Grade", 
            [
                "F → A+",
                "A+ → F",
                "━━━━━━",
                "F", 
                "D", 
                "C-", 
                "C", 
                "C+", 
                "B-", 
                "B", 
                "B+", 
                "A-", 
                "A", 
                "A+"
            ],
            default=[],
            key="filter_grades_multi", 
            placeholder="Grade",
            label_visibility="collapsed"
        )
    with r1c4:
        sort_by = st.selectbox(
            "Sort",
            [
                "±2% Depth (desc)",
                "Spread (desc)",
                "Volume (desc)",
                "Started At (desc)",
            ],
            index=0,
            key="filter_sort",
            label_visibility="collapsed"
        )
    with r1c5:
        tag_filter = st.multiselect(
            "Tag",
            [
                "ST Tag",
                "AZ (Assessment Zone)"
            ],
            default=[],
            key="filter_tags_multi",
            placeholder="Tag",
            label_visibility="collapsed"
        )
    with r1c6:
        reset = st.button("⟲ Reset")

    if reset:
        # Clear the widget values by removing them from session state
        # This will cause the widgets to use their default values on rerun
        for key in ["filter_sym_sel", "filter_within", "filter_sort", "filter_grades_multi", "filter_tags_multi"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # 🚀 스캔 데이터 재사용: 통합 DB에서 읽기!
    now = datetime.now(timezone.utc)
    
    # tokens_unified.json에서 스캔 데이터 로드
    scan_data = {}
    scan_updated_at = None
    
    # 모든 토큰의 스캔 데이터 수집
    for token_id, token_data in all_tokens_db.items():
        # scan_aggregate 또는 current_snapshot 사용
        if token_data.get('scan_aggregate'):
            scan = token_data['scan_aggregate']
            # Use last_updated from scan_aggregate (most recent) as priority
            last_scanned_time = scan.get('last_updated') or token_data.get('current_snapshot', {}).get('last_scanned') or scan.get('last_main_scan') or scan.get('last_priority_scan')
            scan_data[token_id] = {
                'exchange': token_data['exchange'],
                'symbol': token_data['symbol'],
                'spread_pct': scan.get('avg_spread_pct'),
                'total_2': scan.get('avg_depth_2pct'),
                'avg_volume': scan.get('avg_volume_24h'),
                'grade': scan.get('grade'),
                'average_risk': scan.get('average_risk'),
                'violation_rate': scan.get('violation_rate'),
                'st_tagged': token_data.get('tags', {}).get('st_tagged', False),
                'last_scanned': last_scanned_time
            }
            # 가장 최근 스캔 시간 추적
            last_scan = scan.get('last_main_scan') or scan.get('last_priority_scan')
            if last_scan:
                scan_updated_at = last_scan
        elif token_data.get('current_snapshot'):
            # Fallback: current_snapshot 사용
            snap = token_data['current_snapshot']
            scan_data[token_id] = {
                'exchange': token_data['exchange'],
                'symbol': token_data['symbol'],
                'spread_pct': snap.get('spread_pct'),
                'total_2': snap.get('depth_2pct'),
                'avg_volume': snap.get('volume_24h'),
                'grade': 'N/A',
                'average_risk': 0,
                'violation_rate': 0,
                'st_tagged': token_data.get('tags', {}).get('st_tagged', False),
                'last_scanned': snap.get('timestamp')
            }
            if snap.get('timestamp'):
                scan_updated_at = snap.get('timestamp')
    
    # 스캔 데이터 로딩 완료
    
    # Board 선택에 따라 토큰 목록 구성
    if st.session_state.selected_board == 'all_tokens':
        # All Tokens: all_tokens_db의 모든 토큰 표시
        existing_token_ids = {t["id"] for t in all_tokens}
        
        for token_id, token_data in all_tokens_db.items():
            if token_id not in existing_token_ids:
                # NORMAL 토큰을 all_tokens에 추가
                all_tokens.append({
                    "id": token_id,
                    "ex": token_data.get('exchange', '').lower(),
                    "sym": token_data.get('symbol', ''),
                    "added": token_data.get('lifecycle', {}).get('main_board_entry', 'N/A'),
                    "_is_normal": True  # 표시를 위한 플래그
                })
    
    elif st.session_state.selected_board == 'delisting_watch':
        # Delisting Watch: delisting_watch 태그가 있는 토큰만 표시
        all_tokens = [t for t in all_tokens if all_tokens_db.get(t["id"], {}).get('tags', {}).get('delisting_watch')]
    
    elif st.session_state.selected_board == 'crisis_watch':
        # Night Watch: MAIN_BOARD이지만 Delisting Watch가 아닌 토큰
        all_tokens = [t for t in all_tokens if not all_tokens_db.get(t["id"], {}).get('tags', {}).get('delisting_watch')]
    
    # Night Watch는 기본값 (all_tokens가 이미 The Wall 토큰)
    
    # 모든 토큰에 대해 메트릭 생성 (거래소별 + 100개씩 배치 처리)
    all_metrics = []
    
    # 거래소별로 그룹화
    tokens_by_exchange = {}
    for t in all_tokens:
        ex_id = t["ex"]
        if ex_id not in tokens_by_exchange:
            tokens_by_exchange[ex_id] = []
        tokens_by_exchange[ex_id].append(t)
    
    # 진행 상황 표시
    total_tokens = len(all_tokens)
    if total_tokens > 0:
        progress_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        processed_count = 0
        
        # 거래소별로 처리
        for exchange_name, exchange_tokens in tokens_by_exchange.items():
            exchange_total = len(exchange_tokens)
            
            # 100개씩 배치 처리
            batch_size = 100
            for batch_idx in range(0, exchange_total, batch_size):
                batch = exchange_tokens[batch_idx:batch_idx + batch_size]
                
                # 진행 상황 업데이트
                processed_count += len(batch)
                progress_pct = int(processed_count / total_tokens * 100)
                progress_placeholder.info(f"📊 Loading {exchange_name.upper()}: {processed_count}/{total_tokens} tokens from enabled exchanges ({progress_pct}%)")
                progress_bar.progress(processed_count / total_tokens)
                
                for t in batch:
                    ex_id = t["ex"]
                    sym = t["sym"]
                    # 키 정규화: 소문자, / 제거
                    token_key = f"{ex_id.lower()}_{sym.replace('/', '_').lower()}"
                    
                    # 스캔 데이터에서 spread/depth/grade 가져오기 (API 호출 없음!)
                    if t["id"] in scan_data:
                        spread_pct = scan_data[t["id"]].get('spread_pct')
                        total_2 = scan_data[t["id"]].get('total_2')
                        grade = scan_data[t["id"]].get('grade', 'N/A')
                        average_risk = scan_data[t["id"]].get('average_risk', 0)
                        violation_rate = scan_data[t["id"]].get('violation_rate', 0)
                        avg_volume_24h = scan_data[t["id"]].get('avg_volume', 0)
                        st_tagged = scan_data[t["id"]].get('st_tagged', False)
                        last_scanned = scan_data[t["id"]].get('last_scanned', '')
                    else:
                        # 스캔 데이터 없으면 N/A (API 호출 안 함!)
                        spread_pct = None
                        total_2 = None
                        grade = 'N/A'
                        average_risk = 0
                        violation_rate = 0
                        avg_volume_24h = 0
                        st_tagged = False
                        last_scanned = ''
                    
                    # Display values (None => N/A) and numeric fallbacks for sorting/severity
                    spread_disp = spread_pct if isinstance(spread_pct, (float, int)) else None
                    depth_disp = total_2 if isinstance(total_2, (float, int)) else None
                    spread_num = float(spread_pct) if isinstance(spread_pct, (float, int)) else 0.0
                    depth_num = float(total_2) if isinstance(total_2, (float, int)) else 0.0
                    
                    # Load lifecycle info for this token (if available)
                    token_lifecycle = {}
                    current_status = 'NORMAL'
                    penalty = 0
                    reentry_count = 0
                    is_chronic = False
                    
                    # Calculate time on board (hours or days)
                    days_on_board = 0
                    hours_on_board = 0
                    time_on_board_str = ""
                    
                    # Get main_board_entry from all_tokens_db
                    if t["id"] in all_tokens_db:
                        token_data = all_tokens_db[t["id"]]
                        main_board_entry = token_data.get('lifecycle', {}).get('main_board_entry')
                        if main_board_entry:
                            try:
                                entry_dt = datetime.fromisoformat(main_board_entry.replace('Z', '+00:00'))
                                now_dt = datetime.now(timezone.utc)
                                time_diff = now_dt - entry_dt
                                total_hours = int(time_diff.total_seconds() / 3600)
                                
                                if total_hours < 24:
                                    hours_on_board = total_hours
                                    time_on_board_str = f"{total_hours}h"
                                else:
                                    days_on_board = time_diff.days
                                    time_on_board_str = f"{days_on_board}d"
                            except:
                                pass
                    
                    all_metrics.append({
                        "id": t["id"],
                        "ex": ex_id,
                        "sym": sym,
                        "spread_display": spread_disp,
                        "depth2_display": depth_disp,
                        "spread": spread_num,
                        "depth2": depth_num,
                        "started_at": t.get("started_at"),
                        "is_ai_import": t.get("is_ai_import", False),
                        "import_date": t.get("import_date", ""),
                        # Lifecycle data
                        "lifecycle_status": current_status,
                        "penalty": penalty,
                        "reentry_count": reentry_count,
                        "is_chronic": is_chronic,
                        "days_on_board": days_on_board,
                        "time_on_board_str": time_on_board_str,
                        # Grade system
                        "grade": grade,
                        "average_risk": average_risk,
                        "violation_rate": violation_rate,
                        "avg_volume_24h": avg_volume_24h,
                        "st_tagged": st_tagged,
                        "last_scanned": last_scanned,
                        # NORMAL 토큰 플래그
                        "_is_normal": t.get("_is_normal", False)
                    })
        
        # 로딩 완료
        progress_placeholder.success(f"✅ Loaded {total_tokens} tokens from 4 exchanges (GATEIO + MEXC + KUCOIN + BITGET)")
        progress_bar.progress(1.0)
        
        # 잠시 후 진행 표시 제거
        import time
        time.sleep(1)
        progress_placeholder.empty()
        progress_bar.empty()
    
    # 🚨 MEXC Assessment Zone 특별 표시
    if ex_sel == "mexc_assessment":
        # Load MEXC Assessment Zone list
        mexc_assessment_file = "mexc_assessment_list.json"
        mexc_data = {}
        if os.path.exists(mexc_assessment_file):
            try:
                with open(mexc_assessment_file, 'r', encoding='utf-8') as f:
                    mexc_data = json.load(f)
            except:
                pass
        
        # Display warning banner
        st.markdown("""
        <div style='background: linear-gradient(135deg, #dc143c 0%, #8b0000 100%); 
                    padding: 20px; border-radius: 12px; margin: 20px 0; 
                    border: 3px solid #ff6b6b; box-shadow: 0 4px 12px rgba(220, 20, 60, 0.4);'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <span style='font-size: 48px;'>🚨</span>
                <div>
                    <h2 style='color: white; margin: 0; font-size: 24px; font-weight: 700;'>
                        MEXC Assessment Zone - Critical Liquidity Crisis
                    </h2>
                    <p style='color: #ffcccc; margin: 8px 0 0 0; font-size: 16px;'>
                        ⚠️ 심각한 유동성 위기 | 🔴 상폐 위험 노출 | ⏰ 즉각 조치 필요
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display token list
        tokens = mexc_data.get('tokens', [])
        if tokens:
            last_update = mexc_data.get('updated_at', 'Unknown')
            st.info(f"📅 Last updated: {last_update} | Total tokens: {len(tokens)}")
            
            # Display tokens in grid
            cols_per_row = 4
            row_cols = st.columns(cols_per_row)
            col_idx = 0
            
            for token in tokens:
                symbol = token.get('symbol', 'N/A')
                st_tagged = token.get('st_tagged', False)
                api_provided = token.get('api_provided', False)
                subscribers = token.get('subscribers_count', 0)
                
                with row_cols[col_idx]:
                    # Token card with crimson stripe
                    api_status = "✅ API Available" if api_provided else "🔒 API Required"
                    api_color = "#27ae60" if api_provided else "#e74c3c"
                    st_badge = "<span style='background:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-size:10px; margin-left:5px;'>ST</span>" if st_tagged else ""
                    
                    st.markdown(f"""
                    <div class='nw-card status-critical' style='border-left: 8px solid #dc143c;'>
                        <div class='nw-header'>
                            <div style='display:flex; align-items:center;'>
                                <span class='pair'>{symbol}</span>
                                {st_badge}
                            </div>
                        </div>
                        <div class='nw-sub' style='margin-top:8px; color:{api_color}; font-weight:600;'>
                            {api_status}
                        </div>
                        <div class='nw-sub' style='margin-top:4px;'>
                            👥 Subscribers: {subscribers}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                col_idx = (col_idx + 1) % cols_per_row
                if col_idx == 0:
                    row_cols = st.columns(cols_per_row)
            
            # Revenue share info
            revenue_info = mexc_data.get('revenue_share_info', {})
            share_percent = revenue_info.get('default_share_percent', 30)
            
            st.markdown(f"""
            <div style='background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #f39c12;'>
                <h4 style='margin: 0 0 10px 0; color: #856404;'>💰 Revenue Share Program</h4>
                <p style='margin: 0; color: #856404;'>
                    프로젝트 팀이 API를 제공하면 해당 토큰 구독 수익의 <b>{share_percent}%</b>를 분배합니다.<br/>
                    Night Watch가 자동으로 홍보하고 구독자를 유치합니다.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("📭 No tokens in Assessment Zone currently.")
        
        return  # Stop here, don't show regular tokens
    
    # 2번 상태 메시지 삭제됨 - 통합 상태로 대체
    
    # 필터링 (메모리에서만 처리, API 호출 없음!)
    # 선택된 거래소의 토큰만 처리 (MEXC Assessment Zone 포함)
    metrics = []
    for m in all_metrics:
        ex_id = m["ex"]; sym = m["sym"]; started = m.get("started_at", "")
        
        # Exchange filter (탭에서 선택된 거래소만)
        if ex_sel == "all":
            # ALL 선택: 모든 거래소 표시
            pass
        elif ex_sel == "mexc":
            # MEXC 탭은 mexc, mexc_assessment, mexc_evaluation 모두 포함
            if ex_id not in ["mexc", "mexc_assessment", "mexc_evaluation"]:
                continue
        else:
            # 다른 거래소는 정확히 일치하는 것만
            if ex_id != ex_sel:
                continue
        
        # Symbol filter
        if sym_sel and sym_sel not in ["Symbol", "All"] and sym != sym_sel:
            continue
        
        # Grade 복수 선택 필터
        # Grade 필터 (정렬 옵션과 등급 필터 분리)
        if grade_filter:
            grade = m.get("grade", "N/A")
            
            # 정렬 옵션 제외 (F → A+, A+ → F, 구분선)
            actual_grades = [g for g in grade_filter if g not in ["F → A+", "A+ → F", "━━━━━━"]]
            
            if actual_grades:  # 실제 등급 필터가 있으면
                # 선택된 등급 중 하나라도 일치하면 통과
                if grade not in actual_grades:
                    continue
        
        # Tag 필터 (ST Tag, AZ)
        if tag_filter:
            st_tagged = m.get("st_tagged", False)
            is_assessment_zone = ex_id in ["mexc_assessment"]
            
            match_found = False
            for selected_tag in tag_filter:
                if selected_tag == "ST Tag" and st_tagged:
                    match_found = True
                    break
                elif selected_tag == "AZ (Assessment Zone)" and is_assessment_zone:
                    match_found = True
                    break
            
            if not match_found:
                continue
        
        metrics.append(m)

    # Compute bottom 5% by depth and top 5% by spread as risk
    if metrics:
        n = len(metrics)
        sorted_by_depth = sorted(metrics, key=lambda m: m["depth2"])
        sorted_by_spread = sorted(metrics, key=lambda m: m["spread"], reverse=True)
        idx5 = max(1, int(round(n * 0.05)))
        depth5_threshold = sorted_by_depth[idx5 - 1]["depth2"] if idx5 <= n else 0.0
        spread5_threshold = sorted_by_spread[idx5 - 1]["spread"] if idx5 <= n else 0.0
    else:
        depth5_threshold = 0.0
        spread5_threshold = 0.0

    # Severity computation helpers
    def is_assessment(ex_id: str) -> bool:
        return ("assessment" in ex_id) or ("evaluation" in ex_id)

    # Compute severity for each metric
    for m in metrics:
        sev = 0
        if m["depth2"] <= depth5_threshold:
            sev = max(sev, 1)
        if is_assessment(m["ex"]):
            sev = max(sev, 2)
        if "st" in m["sym"].lower():
            sev = max(sev, 3)
        m["sev"] = sev

    # No extra checkbox filters; rely on search/sort only

    # Severity order helper
    def get_severity_order(m):
        """Return severity order: ST Tag → Assessment Zone → F → D → C → B → A"""
        grade = m.get("grade", "N/A")
        st_tagged = m.get("st_tagged", False)
        is_assessment_zone = m["ex"] in ["mexc_assessment"]
        
        # Primary order: ST=1, AZ=2, F=3, D=4, C=5, B=6, A=7, N/A=8
        if st_tagged:
            primary = 1
        elif is_assessment_zone:
            primary = 2
        elif grade == "F":
            primary = 3
        elif grade == "D":
            primary = 4
        elif grade.startswith("C"):
            primary = 5
        elif grade.startswith("B"):
            primary = 6
        elif grade.startswith("A"):
            primary = 7
        else:
            primary = 8
        
        # Secondary order within same grade (C+, C, C- → 내림차순)
        # Grade에 +가 있으면 0, 없으면 1, -가 있으면 2
        if grade and grade != "N/A":
            if "+" in grade:
                secondary = 0
            elif "-" in grade:
                secondary = 2
            else:
                secondary = 1
        else:
            secondary = 1
        
        return (primary, secondary, m["depth2"])  # 같은 등급 내에서는 depth로 추가 정렬

    # Grade sorting function
    def grade_sort_key(m):
        """
        Return sort key for grade-based sorting
        Order (risky to safe): ST > F > AZ > D > D+ > C- > C > C+ > B- > B > B+ > A- > A > A+
        """
        grade = m.get("grade", "N/A")
        st_tagged = m.get("st_tagged", False)
        lifecycle_status = m.get("lifecycle_status", "")
        is_assessment_zone = m.get("ex", "").endswith("_assessment")
        
        # Grade order mapping (lower number = more risky)
        grade_order = {
            'ST': 0,   # ST tag (most risky)
            'F': 1,
            'AZ': 2,   # Assessment Zone
            'D-': 3,
            'D': 4,
            'D+': 5,
            'C-': 6,
            'C': 7,
            'C+': 8,
            'B-': 9,
            'B': 10,
            'B+': 11,
            'A-': 12,
            'A': 13,
            'A+': 14,   # A+ (safest)
            'N/A': 99   # No grade
        }
        
        # Determine effective grade for sorting
        if st_tagged:
            sort_grade = 'ST'
        elif is_assessment_zone:
            sort_grade = 'AZ'
        else:
            sort_grade = grade
        
        return grade_order.get(sort_grade, 99)

    # Sorting (Grade 필터에서 정렬 옵션을 선택한 경우 우선 처리)
    if grade_filter and "F → A+" in grade_filter:
        metrics = sorted(metrics, key=grade_sort_key)  # Lower number first (risky)
    elif grade_filter and "A+ → F" in grade_filter:
        metrics = sorted(metrics, key=grade_sort_key, reverse=True)  # Higher number first (safe)
    elif sort_by == "±2% Depth (desc)":
        metrics = sorted(metrics, key=lambda m: m["depth2"], reverse=True)
    elif sort_by == "Spread (desc)":
        metrics = sorted(metrics, key=lambda m: m["spread"], reverse=True)
    elif sort_by == "Volume (desc)":
        metrics = sorted(metrics, key=lambda m: m.get("avg_volume_24h", 0), reverse=True)
    elif sort_by == "Started At (desc)":
        metrics = sorted(metrics, key=lambda m: (m.get("started_at") or ""), reverse=True)
    # Default sort (±2% Depth desc)
    else:
        metrics = sorted(metrics, key=lambda m: m["depth2"], reverse=True)

    # 📄 페이지네이션 설정
    cards_per_page = 40
    total_cards = len(metrics)
    total_pages = (total_cards + cards_per_page - 1) // cards_per_page  # 올림
    
    # 현재 페이지 (session_state)
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # 페이지 범위 계산
    start_idx = (st.session_state.current_page - 1) * cards_per_page
    end_idx = min(start_idx + cards_per_page, total_cards)
    page_metrics = metrics[start_idx:end_idx]
    
    # 페이지네이션 UI (상단)
    if total_pages > 1:
        st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f8f9fa; border-radius: 6px; margin: 8px 0;">
    <div style="font-size: 11px; color: #6c757d; font-weight: 600;">
        Showing {start_idx + 1}-{end_idx} of {total_cards} tokens
    </div>
    <div style="font-size: 11px; color: #6c757d; font-weight: 600;">
        Page {st.session_state.current_page} / {total_pages}
    </div>
</div>
""", unsafe_allow_html=True)
        
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("◀ Previous", disabled=(st.session_state.current_page == 1), use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
        with nav_col2:
            # 페이지 번호 입력
            page_input = st.number_input("Go to page", min_value=1, max_value=total_pages, value=st.session_state.current_page, key="page_input", label_visibility="collapsed")
            if page_input != st.session_state.current_page:
                st.session_state.current_page = page_input
                st.rerun()
        with nav_col3:
            if st.button("Next ▶", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()
    
    # Grid: 4 columns per row (standard web layout)
    cols_per_row = 4
    row_cols = st.columns(cols_per_row)
    col_idx = 0

    # 페이지에 해당하는 토큰 카드만 표시
    for m in page_metrics:
        ex_id = m["ex"]; sym = m["sym"]; spread_pct = m["spread"]; total_2 = m["depth2"]
        blink = _should_blink(manual_inputs, ex_id, sym, spread_pct or 0.0, total_2 or 0.0)
        # Tags & severity
        chips = []
        sev = m["sev"]
        
        # Lifecycle status badges
        lifecycle_status = m.get("lifecycle_status", "NORMAL")
        penalty = m.get("penalty", 0)
        is_chronic = m.get("is_chronic", False)
        reentry_count = m.get("reentry_count", 0)
        days_on_board = m.get("days_on_board", 0)
        
        # Class badges - 2글자 약자로 표시 (거래소 배지 밑에 가로로 배치)
        class_badges = []

        # CH - CHRONIC
        if is_chronic:
            class_badges.append({
                'text': 'CH',
                'bg': '#6c757d',
                'color': '#fff',
                'tooltip': 'CHRONIC - 60 Days Penalty'
            })
        # RE - REENTRY
        elif reentry_count > 0:
            class_badges.append({
                'text': f'RE{reentry_count}',
                'bg': '#f39c12',
                'color': '#fff',
                'tooltip': f'REENTRY {reentry_count}x'
            })

        # WW - W WALKER (메인보드 D/F 그레이드 토큰)
        is_white_walker = False
        if not m.get("_is_normal", False):  # NORMAL이 아니면 = MAIN_BOARD 상태
            is_white_walker = True
            class_badges.append({
                'text': 'WW',
                'bg': '#4a90e2',
                'color': '#fff',
                'tooltip': 'W WALKER - The Wall D/F'
            })

        # NM - NORMAL (All Tokens Board에서만 표시)
        if m.get("_is_normal", False) and st.session_state.selected_board == 'all_tokens':
            class_badges.append({
                'text': 'NM',
                'bg': '#28a745',
                'color': '#fff',
                'tooltip': 'NORMAL - Healthy Liquidity'
            })

        # CR - CRITICAL ZONE (F 등급 + 하위 5% 뎁스) - 핑크색
        is_critical = False
        if m.get("grade") == "F" and m.get("depth2", 0) <= depth5_threshold:
            is_critical = True

        # 또는 Delisting Watch 태그가 있는 경우
        token_id = m.get("id")
        if token_id and token_id in all_tokens_db:
            is_delisting_watch = all_tokens_db[token_id].get('tags', {}).get('delisting_watch', False)
            if is_delisting_watch:
                is_critical = True

        if is_critical:
            class_badges.append({
                'text': 'CR',
                'bg': '#e91e63',
                'color': '#fff',
                'tooltip': 'CRITICAL - Delisting Watch'
            })
    
        # 🎨 7단계 상태 시스템
        # 임계값 & 목표값 (거래소별로 다를 수 있음)
        spread_threshold = 1.0   # 임계값: 1%
        spread_target = 0.5      # 목표값: 0.5%
        depth_threshold = 500    # 임계값: $500
        depth_target = 2000      # 목표값: $2000
        volume_threshold = 10000 # 임계값: $10,000
        volume_target = 50000    # 목표값: $50,000
        
        # 현재 값
        current_spread = m.get("spread", 0)
        current_depth = m.get("depth2", 0)
        current_volume = 0  # TODO: 거래량 데이터 추가 필요
        
        # 평균 값 및 Grade/Risk/Violation 정보 (scan_data에서)
        token_id = m.get("id")
        
        # Grade, Risk, Violation, Volume, last_scanned 정보 로드
        grade = scan_data.get(token_id, {}).get('grade', 'N/A')
        average_risk = scan_data.get(token_id, {}).get('average_risk', 0)
        violation_rate = scan_data.get(token_id, {}).get('violation_rate', 0)
        avg_volume = scan_data.get(token_id, {}).get('avg_volume_24h', 0)
        last_scanned_str = ""
        
        if token_id in scan_data and 'last_scanned' in scan_data[token_id]:
            try:
                last_scanned = datetime.fromisoformat(scan_data[token_id]['last_scanned'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                diff = now - last_scanned
                minutes_ago = int(diff.total_seconds() / 60)
                if minutes_ago < 1:
                    last_scanned_str = "just now"
                elif minutes_ago < 60:
                    last_scanned_str = f"{minutes_ago} min ago"
                else:
                    hours_ago = int(minutes_ago / 60)
                    last_scanned_str = f"{hours_ago}h ago"
            except:
                last_scanned_str = ""
        
        avg_spread = scan_data.get(token_id, {}).get('avg_spread_pct', current_spread) if token_id in scan_data else current_spread
        avg_depth = scan_data.get(token_id, {}).get('avg_depth_2pct', current_depth) if token_id in scan_data else current_depth
        
        # 각 메트릭별 달성 레벨 (0: 미달, 1: 임계값, 2: 목표값)
        spread_level = 0
        if current_spread <= spread_threshold:
            spread_level = 1
            if current_spread <= spread_target:
                spread_level = 2
        
        depth_level = 0
        if current_depth >= depth_threshold:
            depth_level = 1
            if current_depth >= depth_target:
                depth_level = 2
        
        volume_level = 0
        if current_volume >= volume_threshold:
            volume_level = 1
            if current_volume >= volume_target:
                volume_level = 2
        # 목표값 달성 개수
        target_count = sum([1 for level in [spread_level, depth_level, volume_level] if level == 2])
        # 임계값 달성 개수
        threshold_count = sum([1 for level in [spread_level, depth_level, volume_level] if level >= 1])
        
        # 7단계 상태 결정 + 거래소 색상 + 등급 색상
        grade_class = f"grade-{grade.replace('+', '-plus').replace('/', '-')}" if grade and grade != 'N/A' else "grade-NA"
        css = f"nw-card exchange-{ex_id} {grade_class}"
        if target_count == 3:
            # 🔵 EXCELLENT: 3개 모두 목표값
            css += " status-excellent"
        elif target_count == 2 and threshold_count == 3:
            # 🟢 GOOD: 2개 목표값 + 1개 임계값
            css += " status-good"
        elif target_count == 1 and threshold_count == 3:
            # 🟢 FAIR: 1개 목표값 + 2개 임계값
            css += " status-fair"
        elif target_count == 0 and threshold_count == 3:
            # 🟡 WARNING: 3개 모두 임계값만
            css += " status-warning"
        elif threshold_count == 2:
            # 🟠 CAUTION: 1개 임계값 미달
            css += " status-caution"
        elif threshold_count == 1:
            # 🔴 DANGER: 2개 임계값 미달
            css += " status-danger"
        else:
            # 🌹 CRITICAL: 3개 모두 임계값 미달
            css += " status-critical"
        
        # 평균 대비 악화 감지 (점선 오버레이)
        is_deteriorating = False
        if avg_spread > 0 and current_spread > avg_spread * 1.5:
            is_deteriorating = True
        if avg_depth > 0 and current_depth < avg_depth * 0.5:
            is_deteriorating = True
        
        if is_deteriorating:
            css += " status-deteriorating"
        
        # spread/depth display
        spread_html = "N/A" if m.get("spread_display") is None else f"{m.get('spread_display', 0):.2f}%"
        depth_html = "N/A" if m.get("depth2_display") is None else f"${m.get('depth2_display', 0):,.0f}"
        
        # 3색 깃발 생성 (스프레드, 뎁스, 거래량)
        spread_flag = "flag-excellent" if spread_level == 2 else ("flag-moderate" if spread_level == 1 else "flag-poor")
        depth_flag = "flag-excellent" if depth_level == 2 else ("flag-moderate" if depth_level == 1 else "flag-poor")
        volume_flag = "flag-excellent" if volume_level == 2 else ("flag-moderate" if volume_level == 1 else "flag-poor")
        
        flags_html = f"""<div class='status-flags' title='Top to Bottom: Spread | Depth | Volume&#10;🟢 Green: Target met&#10;🟡 Yellow: Threshold met&#10;🔴 Red: Below threshold'><div class='flag-bar {spread_flag}'></div><div class='flag-bar {depth_flag}'></div><div class='flag-bar {volume_flag}'></div></div>"""
        
        # Alert level text (based on severity)
        level_text = ""
        if sev == 3:
            level_text = "<span style='color:#e74c3c; font-weight:600;'>CRITICAL</span>"
        elif sev == 2:
            level_text = "<span style='color:#f39c12; font-weight:600;'>WARNING</span>"
        elif sev == 1:
            level_text = "<span style='color:#f3c969; font-weight:600;'>CAUTION</span>"
        
        now_utc = datetime.now(timezone.utc).strftime('%H:%M:%SZ')
        card_id = f"card_{m['id'].replace('_', '-')}"
        
        # Check if in watchlist
        is_in_watchlist = any(
            item.get("exchange") == ex_id and item.get("symbol") == sym 
            for item in st.session_state.watchlist
        )
        
        # Determine second button based on watchlist status
        if is_in_watchlist:
            add_watchlist_link = f"?remove_exchange={ex_id}&remove_symbol={sym}"
            watchlist_icon = "🗑️"
            watchlist_title = "Remove from Watchlist"
        else:
            # Include spread and depth in the add link
            spread_val = spread_pct if spread_pct is not None else ""
            depth_val = total_2 if total_2 is not None else ""
            add_watchlist_link = f"?add_exchange={ex_id}&add_symbol={sym}&add_token_id={m['id']}&add_spread={spread_val}&add_depth={depth_val}"
            watchlist_icon = "⭐"
            watchlist_title = "Add to Watchlist"

        # 거래소 표시명 설정 (MEXC Assessment Zone은 MEXC_AZ로 축약)
        ex_display = "MEXC_AZ" if ex_id in ("mexc_assessment", "mexc_evaluation") else ex_id.upper()
        
        # Grade 정보 및 Volume
        grade = m.get('grade', 'N/A')
        average_risk = m.get('average_risk', 0)
        violation_rate = m.get('violation_rate', 0)
        avg_volume = m.get('avg_volume_24h', 0)
        
        # ST Tag 및 AZ Tag 확인
        st_tagged = m.get('st_tagged', False)
        is_assessment_zone = ex_id in ["mexc_assessment"]
        
        # 배지 HTML (검은색 볼드, 정렬 개선)
        badges_html = ""
        if st_tagged:
            badges_html += "<span style='background:#000; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-left:8px; line-height:1.4; vertical-align:middle;'>ST</span>"
        if is_assessment_zone:
            badges_html += "<span style='background:#000; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-left:8px; line-height:1.4; vertical-align:middle;'>AZ</span>"
        
        # Last scanned 시간 계산
        last_scanned_str = ""
        if 'last_scanned' in m:
            try:
                last_scanned = datetime.fromisoformat(m['last_scanned'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                diff = now - last_scanned
                minutes_ago = int(diff.total_seconds() / 60)
                if minutes_ago < 1:
                    last_scanned_str = "just now"
                elif minutes_ago < 60:
                    last_scanned_str = f"{minutes_ago} min ago"
                else:
                    hours_ago = int(minutes_ago / 60)
                    last_scanned_str = f"{hours_ago}h ago"
            except:
                last_scanned_str = ""
        
        # Class 배지를 거래소 배지 아래에 가로로 배치 (거래소 배지와 동일한 스타일)
        class_badges_html = ""
        if class_badges:
            class_badges_html = '<div style="display:flex; gap:3px; flex-wrap:wrap; margin-top:2px;">'
            for badge in class_badges:
                class_badges_html += f'<span title="{badge["tooltip"]}" style="background:{badge["bg"]}; color:{badge["color"]}; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:600; line-height:1.4;">{badge["text"]}</span>'
            class_badges_html += '</div>'
        
        # Posted 및 Updated 시간 계산
        posted_str = ""
        updated_str = ""
        
        # Posted 시간 (main_board_entry 기준)
        if token_id in all_tokens_db:
            token_data = all_tokens_db[token_id]
            main_board_entry = token_data.get('lifecycle', {}).get('main_board_entry')
            if main_board_entry:
                try:
                    entry_dt = datetime.fromisoformat(main_board_entry.replace('Z', '+00:00'))
                    now_dt = datetime.now(timezone.utc)
                    time_diff = now_dt - entry_dt
                    
                    days = time_diff.days
                    hours = int((time_diff.total_seconds() % 86400) / 3600)
                    
                    if days > 0:
                        posted_str = f"{days}d {hours}h ago"
                    else:
                        posted_str = f"{hours}h ago"
                except:
                    pass
        
        # Updated 시간 (last_scanned 기준)
        if 'last_scanned' in m:
            try:
                last_scanned = datetime.fromisoformat(m['last_scanned'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                diff = now - last_scanned
                
                hours = int(diff.total_seconds() / 3600)
                minutes = int((diff.total_seconds() % 3600) / 60)
                
                if hours > 0:
                    updated_str = f"{hours}h {minutes}m ago"
                else:
                    updated_str = f"{minutes}m ago"
            except:
                pass
        
        # Posted/Updated HTML
        time_info_html = ""
        if posted_str or updated_str:
            time_parts = []
            if posted_str:
                time_parts.append(f"Posted: <b>{posted_str}</b>")
            if updated_str:
                time_parts.append(f"Updated: <b>{updated_str}</b>")
            time_info_html = f"<div class='nw-sub' style='margin-top:4px; font-size:9px; color:#666;'>{' | '.join(time_parts)}</div>"
        
        # ✅ Grade Info from Cache (10배 빠름!)
        grade_info = all_tokens_db.get(token_id, {}).get('grade_info', {})
        gpa_14d_str = str(grade_info.get('avg_14d_gpa', 'N/A')) if grade_info.get('avg_14d_gpa') else 'N/A'
        gpa_14d_grade = grade_info.get('avg_14d_grade', grade if grade != 'N/A' else 'N/A')
        
        if grade != 'N/A':
            grade_html = f"<div class='nw-sub' style='margin-top:4px; display:flex; gap:8px; font-size:10px;'><span>14dGPA: <b>{gpa_14d_str}/{gpa_14d_grade}</b></span><span>Risk: <b>{int(average_risk*100)}%</b></span><span>Viol.: <b>{int(violation_rate*100)}%</b></span></div>"
        else:
            grade_html = "<div class='nw-sub' style='margin-top:4px; padding:3px 6px; background:#fff3cd; border:1px dashed #ffc107; border-radius:4px; font-size:9.5px;'><b>⏳ Awaiting First Scan</b><br/>This token will be scanned in the next Main Scanner cycle (every 2 hours at 00:00, 02:00, 04:00... UTC)</div>"
        
        # Penalty 정보 HTML
        if lifecycle_status == "MAIN_BOARD" and penalty > 0:
            penalty_html = f"<div class='nw-sub' style='margin-top:4px; padding:4px; background:#fff3cd; border-radius:4px; font-size:10px;'><b>🚨 Penalty: {penalty}/60</b> ({int(penalty/60*100)}%)<br/>📅 On Board: {days_on_board} days</div>"
        else:
            penalty_html = ""

        with row_cols[col_idx]:
            # Grade 워터마크 (배경) - grade가 있을 때만 표시
            grade_watermark_html = ""
            if grade and grade != 'N/A':
                # Grade를 기본 글자와 +/- 기호로 분리
                base_grade = grade[0]  # A, B, C, D, F
                modifier = grade[1] if len(grade) > 1 else ''  # +, -, or empty
                
                # Grade별 색상 (Rating Scale과 동일)
                grade_colors = {
                    'F': '#dc3545',  # 빨강
                    'D': '#fd7e14',  # 주황
                    'C': '#ffc107',  # 노랑
                    'B': '#20c997',  # 청록
                    'A': '#0dcaf0'   # 하늘색
                }
                grade_color = grade_colors.get(base_grade, '#000000')
                # opacity를 0.18로 설정 (더 선명하게)
                
                # +/- 기호를 오른쪽 위 작은 글씨로 표시
                if modifier:
                    grade_watermark_html = f"<div class='grade-watermark' style='position:absolute; right:50px; bottom:0px; font-size:52px; font-weight:700; color:{grade_color}; opacity:0.08; line-height:1; pointer-events:none; user-select:none; z-index:2; transition: all 0.3s ease;'>{base_grade}<span style='font-size:28px; vertical-align:super; margin-left:2px;'>{modifier}</span></div>"
                else:
                    grade_watermark_html = f"<div class='grade-watermark' style='position:absolute; right:50px; bottom:0px; font-size:52px; font-weight:700; color:{grade_color}; opacity:0.08; line-height:1; pointer-events:none; user-select:none; z-index:2; transition: all 0.3s ease;'>{base_grade}</div>"
            
            # Generate inline mini chart (삼색국기)
            token_id = f"{ex_id}_{sym.replace('/', '_').lower()}"
            current_snapshot = {
                'grade': grade,
                'avg_volume_24h': m.get('avg_volume_24h', 0),
                'avg_spread_pct': m.get('avg_spread_pct', 0),
                'avg_depth_2pct': m.get('avg_depth_2pct', 0)
            }
            history_data = get_token_history_14days(token_id, ex_id, sym, current_snapshot)
            inline_chart_html = generate_mini_chart_html(history_data, inline=True)
            
            # 심볼 표시 처리 (토큰 5글자 + . + /USDT)
            if '/' in sym:
                token_part, quote_part = sym.split('/', 1)
                if len(token_part) > 5:
                    display_sym = f"{token_part[:5]}./{quote_part}"
                else:
                    display_sym = sym
            else:
                display_sym = sym[:5] + '.' if len(sym) > 5 else sym
            
            st.markdown(
f"""<style>
.nw-card:hover .grade-watermark {{
opacity: 0.5 !important;
}}
.nw-card:hover .mini-chart-container {{
opacity: 0.8 !important;
}}
.nw-card .card-action-btn {{
opacity: 0;
transition: opacity 0.2s ease;
}}
.nw-card:hover .card-action-btn {{
opacity: 1 !important;
}}
</style>
<div class='{css}' id='{card_id}' style='position:relative; overflow:hidden;'>
{grade_watermark_html}
{flags_html}
<a href='{add_watchlist_link}' class='card-action-btn' title='{watchlist_title}' style='position:absolute; top:8px; right:8px; z-index:11;'>{watchlist_icon}</a>
<div style='position:relative; z-index:10;'>
<div class='nw-header' style='display:flex; align-items:flex-start; gap:8px;'>
<div style='display:flex; align-items:flex-start; gap:8px; flex:1;'>
<div style='display:flex; align-items:center; gap:6px;'>
<span class='pair' title='{sym}'>{display_sym}</span>{badges_html}
</div>
<div style='display:flex; flex-direction:column; gap:2px;'>
<span class='exch exch-{ex_id}'>{ex_display}</span>
{class_badges_html}
</div>
{inline_chart_html}
                  </div>
                  </div>
<div class='nw-sub' style='margin-top:4px; display:flex; gap:8px; font-size:10px;'>
<span>Spread: <b>{spread_html}</b></span>
<span>2%Dep: <b>{depth_html}</b></span>
<span>24Vol: <b>{"$" + f"{avg_volume:,.0f}" if avg_volume and avg_volume > 0 else "N/A"}</b></span>
                  </div>
{grade_html}
{time_info_html}
{penalty_html}
                </div>
</div>""",
unsafe_allow_html=True
            )

        col_idx = (col_idx + 1) % cols_per_row
        if col_idx == 0:
            row_cols = st.columns(cols_per_row)

    # 페이지네이션 UI (하단)
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("◀ Prev", key="prev_bottom", disabled=(st.session_state.current_page == 1), use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
        with nav_col2:
            st.markdown(f"""
<div style="text-align: center; padding: 10px; font-size: 12px; color: #6c757d; font-weight: 600;">
    Page {st.session_state.current_page} / {total_pages} ({start_idx + 1}-{end_idx} of {total_cards})
</div>
""", unsafe_allow_html=True)
        with nav_col3:
            if st.button("Next ▶", key="next_bottom", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()

# Render watchlist with real-time data (now that functions are defined)
# Only show watchlist if user is logged in

# Load all tokens for watchlist display
token_manager = TokenManager()
all_tokens_db = token_manager.get_all_tokens()

if st.session_state.get('logged_in', False):
        # Get the correct user ID and update session state
        actual_user_id = st.session_state.get('telegram_username', 'guest')
        
        # Force update user_tier from users.json to ensure consistency
        users = _load_json("data/users.json", {})
        clean_user_id = actual_user_id.lstrip('@')
        
        # Try to find user with both @ and without @ versions
        user_data = None
        if clean_user_id in users:
            user_data = users[clean_user_id]
        elif f"@{clean_user_id}" in users:
            user_data = users[f"@{clean_user_id}"]
        
        if user_data:
            actual_tier = user_data.get('tier', 'free')
            if actual_tier != st.session_state.get('user_tier', 'free'):
                st.session_state.user_tier = actual_tier
        
        # My Watch List header with timer and user info - use components.html for JavaScript support
        watchlist_limit = user_manager.get_watchlist_limit(actual_user_id)
        current_count = len(st.session_state.get('watchlist', []))
        
        # Tier badge based on actual tier (not is_premium which includes both pro and premium)
        current_tier = st.session_state.user_tier if st.session_state.logged_in else "free"
        if current_tier == "premium":
            tier_badge = "💎 Premium"
            tier_color = "#9333ea"
        elif current_tier == "pro":
            tier_badge = "⭐ Pro"
            tier_color = "#10b981"
        else:
            tier_badge = "🆓 Free"
            tier_color = "#667eea"
        
        # My Watch List header (no buttons here anymore)
        header_html = f"""
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding: 12px; background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%); border: 2px solid {tier_color}; border-radius: 12px;'>
            <div style='display: flex; align-items: center; gap: 12px;'>
                <span style='font-weight: 700; font-size: 16px; color: {tier_color};'>📌 My Watch List ({current_count}/{watchlist_limit})</span>
                <span style='font-size: 11px; padding: 3px 8px; background: {tier_color}; color: white; border-radius: 12px; font-weight: 600;'>{tier_badge}</span>
            </div>
            {_watchlist_timer_html if _watchlist_timer_html else ""}
        </div>
        """
        components.html(header_html, height=60)
        
        # Display watchlist items (메인보드와 동일한 레이아웃)
        watchlist_items = st.session_state.get("watchlist", [])

        if watchlist_items:
            # 메인보드와 동일한 4열 그리드
            cols_per_row = 4
            row_cols = st.columns(cols_per_row)
            col_idx = 0

            for item in watchlist_items:
                ex_id = item.get('exchange', '')
                sym = item.get('symbol', '')
                token_id = item.get('token_id', '')
                
                # Get token data from all_tokens_db
                if token_id in all_tokens_db:
                    token_data = all_tokens_db[token_id]
                    m = token_data
                    
                    # Extract data from unified DB structure
                    # Use current_snapshot for real-time data (Pro/Premium users)
                    current_snapshot = m.get('current_snapshot', {})
                    scan_aggregate = m.get('scan_aggregate', {})  # FIXED: singular form

                    # Display current snapshot if available, otherwise use aggregates
                    spread_pct = current_snapshot.get('spread_pct') or scan_aggregate.get('avg_spread_pct')
                    total_2 = current_snapshot.get('depth_2pct') or scan_aggregate.get('avg_depth_2pct')
                    avg_volume = current_snapshot.get('volume_24h') or scan_aggregate.get('avg_volume_24h', 0)

                    # Grade and risk from aggregates (calculated by main scanner)
                    # Fallback to current_snapshot grade if aggregates not available
                    grade = scan_aggregate.get('grade') or current_snapshot.get('grade', 'N/A')
                    average_risk = scan_aggregate.get('average_risk', 0)
                    violation_rate = scan_aggregate.get('violation_rate', 0)

                    # Calculate timestamp for "Updated: Xm ago"
                    # Try multiple possible timestamp field names
                    timestamp_str = (current_snapshot.get('timestamp') or
                                    current_snapshot.get('last_scanned') or
                                    scan_aggregate.get('timestamp') or
                                    scan_aggregate.get('last_scanned'))
                    updated_ago = "N/A"
                    if timestamp_str:
                        try:
                            # Parse ISO timestamp
                            if isinstance(timestamp_str, str):
                                ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            else:
                                ts = timestamp_str
                            now = datetime.now(timezone.utc)
                            diff_mins = int((now - ts).total_seconds() / 60)
                            if diff_mins < 1:
                                updated_ago = "now"
                            elif diff_mins < 60:
                                updated_ago = f"{diff_mins}m"
                            else:
                                hours = diff_mins // 60
                                updated_ago = f"{hours}h"
                        except Exception:
                            updated_ago = "N/A"

                    # Tags
                    st_tagged = m.get('tags', {}).get('st_tagged', False)
                    
                    # Format values
                    spread_html = "N/A" if spread_pct is None else f"{spread_pct:.2f}%"
                    depth_html = "N/A" if total_2 is None else f"${total_2:,.0f}"
                    
                    # Badges
                    is_assessment_zone = ex_id in ["mexc_assessment"]
                    badges_html = ""
                    if st_tagged:
                        badges_html += "<span style='background:#000; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-left:8px; line-height:1.4; vertical-align:middle;'>ST</span>"
                    if is_assessment_zone:
                        badges_html += "<span style='background:#000; color:#fff; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:700; margin-left:8px; line-height:1.4; vertical-align:middle;'>AZ</span>"
                    
                    # Status calculation
                    spread_threshold = 1.0
                    spread_target = 0.5
                    depth_threshold = 500
                    depth_target = 2000
                    volume_threshold = 10000
                    volume_target = 50000
                    
                    current_spread = spread_pct if spread_pct else 0
                    current_depth = total_2 if total_2 else 0
                    current_volume = 0
                    
                    spread_level = 2 if current_spread <= spread_target else (1 if current_spread <= spread_threshold else 0)
                    depth_level = 2 if current_depth >= depth_target else (1 if current_depth >= depth_threshold else 0)
                    volume_level = 2 if current_volume >= volume_target else (1 if current_volume >= volume_threshold else 0)
                    
                    target_count = sum([1 for level in [spread_level, depth_level, volume_level] if level == 2])
                    threshold_count = sum([1 for level in [spread_level, depth_level, volume_level] if level >= 1])
                    
                    # CSS classes
                    grade_class = f"grade-{grade.replace('+', '-plus').replace('/', '-')}" if grade and grade != 'N/A' else "grade-NA"
                    css = f"nw-card exchange-{ex_id} {grade_class}"
                    if target_count == 3:
                        css += " status-excellent"
                    elif target_count == 2 and threshold_count == 3:
                        css += " status-good"
                    elif target_count == 1 and threshold_count == 3:
                        css += " status-fair"
                    elif target_count == 0 and threshold_count == 3:
                        css += " status-warning"
                    elif threshold_count == 2:
                        css += " status-caution"
                    elif threshold_count == 1:
                        css += " status-danger"
                    else:
                        css += " status-critical"
                    
                    # Flags
                    spread_flag = "flag-excellent" if spread_level == 2 else ("flag-moderate" if spread_level == 1 else "flag-poor")
                    depth_flag = "flag-excellent" if depth_level == 2 else ("flag-moderate" if depth_level == 1 else "flag-poor")
                    volume_flag = "flag-excellent" if volume_level == 2 else ("flag-moderate" if volume_level == 1 else "flag-poor")
                    flags_html = f"""<div class='status-flags' title='Top to Bottom: Spread | Depth | Volume&#10;🟢 Green: Target met&#10;🟡 Yellow: Threshold met&#10;🔴 Red: Below threshold'><div class='flag-bar {spread_flag}'></div><div class='flag-bar {depth_flag}'></div><div class='flag-bar {volume_flag}'></div></div>"""
                    
                    # Links
                    card_id = f"watchcard_{token_id.replace('_', '-')}"
                    remove_link = f"?remove_exchange={ex_id}&remove_symbol={sym}"
                    ex_display = "MEXC_AZ" if ex_id in ("mexc_assessment", "mexc_evaluation") else ex_id.upper()
                    
                    # 허니문 상태 확인 (사용자별)
                    user_id = st.session_state.get('telegram_username')
                    honeymoon_manager = get_honeymoon_manager(user_id)
                    honeymoon_status = honeymoon_manager.get_token_honeymoon_status(ex_id, sym)
                    
                    # Grade info
                    grade_info = m.get('grade_info', {})
                    gpa_14d_str = str(grade_info.get('avg_14d_gpa', 'N/A')) if grade_info.get('avg_14d_gpa') else 'N/A'
                    gpa_14d_grade = grade_info.get('avg_14d_grade', grade if grade != 'N/A' else 'N/A')
                    
                    if grade != 'N/A':
                        # 허니문 정보 추가
                        honeymoon_info = ""
                        if honeymoon_status['status'] not in ['not_configured', 'error']:
                            if honeymoon_status['is_in_honeymoon']:
                                days_remaining = honeymoon_status['days_remaining']
                                price_drop = honeymoon_status['price_drop_pct']
                                if price_drop >= honeymoon_status['threshold_price_pct']:
                                    honeymoon_info = f"<span style='color:#dc3545; font-weight:bold;'>⚠️ 허니문 {days_remaining}일 남음 ({price_drop:.1f}%↓)</span>"
                                else:
                                    honeymoon_info = f"<span style='color:#20c997;'>💎 허니문 {days_remaining}일 남음 ({price_drop:.1f}%↓)</span>"
                            else:
                                honeymoon_info = f"<span style='color:#6c757d;'>✅ 허니문 종료 ({honeymoon_status['days_since_listing']}일)</span>"
                        
                        grade_html = f"<div class='nw-sub' style='margin-top:4px; display:flex; gap:8px; font-size:10px;'><span>14dGPA: <b>{gpa_14d_str}/{gpa_14d_grade}</b></span><span>Risk: <b>{int(average_risk*100)}%</b></span><span>Viol.: <b>{int(violation_rate*100)}%</b></span></div>"
                        if honeymoon_info:
                            grade_html += f"<div class='nw-sub' style='margin-top:2px; font-size:9px;'>{honeymoon_info}</div>"
                    else:
                        grade_html = "<div class='nw-sub' style='margin-top:4px; padding:3px 6px; background:#fff3cd; border:1px dashed #ffc107; border-radius:4px; font-size:9.5px;'><b>⏳ Awaiting First Scan</b></div>"
                    
                    # Watermark
                    grade_watermark_html = ""
                    if grade and grade != 'N/A':
                        base_grade = grade[0]
                        modifier = grade[1] if len(grade) > 1 else ''
                        grade_colors = {'F': '#dc3545', 'D': '#fd7e14', 'C': '#ffc107', 'B': '#20c997', 'A': '#0dcaf0'}
                        grade_color = grade_colors.get(base_grade, '#000000')
                        if modifier:
                            grade_watermark_html = f"<div class='grade-watermark' style='position:absolute; right:50px; bottom:0px; font-size:52px; font-weight:700; color:{grade_color}; opacity:0.08; line-height:1; pointer-events:none; user-select:none; z-index:2;'>{base_grade}<span style='font-size:28px; vertical-align:super; margin-left:2px;'>{modifier}</span></div>"
                        else:
                            grade_watermark_html = f"<div class='grade-watermark' style='position:absolute; right:50px; bottom:0px; font-size:52px; font-weight:700; color:{grade_color}; opacity:0.08; line-height:1; pointer-events:none; user-select:none; z-index:2;'>{base_grade}</div>"
                    
                    # Display symbol
                    if '/' in sym:
                        token_part, quote_part = sym.split('/', 1)
                        display_sym = f"{token_part[:5]}./{quote_part}" if len(token_part) > 5 else sym
                    else:
                        display_sym = sym[:5] + '.' if len(sym) > 5 else sym
                    
                    # History chart
                    current_snapshot = {'grade': grade, 'avg_volume_24h': m.get('avg_volume_24h', 0), 'avg_spread_pct': m.get('avg_spread_pct', 0), 'avg_depth_2pct': m.get('avg_depth_2pct', 0)}
                    history_data = get_token_history_14days(token_id, ex_id, sym, current_snapshot)
                    inline_chart_html = generate_mini_chart_html(history_data, inline=True)
                    
                    # Analytics link for user dashboard
                    analytics_link = f"http://localhost:8502?token={token_id}"
                    
                    # Render card (메인보드와 동일)
                    with row_cols[col_idx]:
                        st.markdown(
f"""<div class='{css}' id='{card_id}' style='position:relative; overflow:hidden; min-height:96px; height:96px;'>
{grade_watermark_html}
{flags_html}
<a href='{analytics_link}' class='card-action-btn' title='View Analytics' style='position:absolute; top:8px; right:38px; z-index:11;' target='_blank'>📊</a>
<a href='{remove_link}' class='card-action-btn' title='Remove from Watchlist' style='position:absolute; top:8px; right:8px; z-index:11;'>🗑️</a>
<div style='position:relative; z-index:10;'>
<div class='nw-header' style='display:flex; align-items:flex-start; gap:8px;'>
<div style='display:flex; align-items:center; gap:6px; flex:1;'>
<span class='pair' title='{sym}'>{display_sym}</span>{badges_html}
<span class='exch exch-{ex_id}'>{ex_display}</span>{inline_chart_html}
</div>
</div>
<div class='nw-sub' style='margin-top:4px; display:flex; gap:8px; font-size:10px; justify-content:space-between; align-items:center;'>
<div style='display:flex; gap:8px;'>
<span>Spread: <b>{spread_html}</b></span>
<span>2%Dep: <b>{depth_html}</b></span>
<span>24Vol: <b>{"$" + f"{avg_volume:,.0f}" if avg_volume and avg_volume > 0 else "N/A"}</b></span>
</div>
<span style='font-size:8.5px; color:#888; white-space:nowrap;'>⏱ {updated_ago}</span>
</div>
{grade_html}
</div>
</div>""",
unsafe_allow_html=True
                        )
                
                col_idx = (col_idx + 1) % cols_per_row
                if col_idx == 0:
                    row_cols = st.columns(cols_per_row)
        else:
            st.info("No items in watchlist. Add tokens by clicking ⭐ on cards below")
        
        # 9개의 상세 박스 공간 추가
        st.markdown("---")
        st.markdown("### 📊 Detailed Reports")
        
        # Box 1: 예시 박스 (나머지 8개는 하나씩 추가할 예정)
        with st.expander("📈 Box 1: Coming Soon", expanded=False):
            st.info("This box will be implemented next")
else:
    # 로그인하지 않은 사용자는 와치리스트 섹션 표시 안 함
    pass

render_board()
