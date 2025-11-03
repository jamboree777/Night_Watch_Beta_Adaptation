"""
Graduation Popup Component
===========================
Crisis Board 졸업 토큰을 축하하는 팝업
"""

import streamlit as st
import json
import os
from datetime import datetime, timezone


def render_graduation_popup():
    """
    오늘 졸업한 토큰들을 팝업으로 표시
    
    Returns:
        bool: 졸업 토큰이 있으면 True
    """
    graduated_file = 'graduated_tokens.json'
    
    if not os.path.exists(graduated_file):
        return False
    
    try:
        with open(graduated_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return False
    
    # 오늘 졸업한 토큰들
    today = datetime.now(timezone.utc).date().isoformat()
    today_graduates = [
        g for g in data.get('daily_graduates', [])
        if g.get('exit_date') == today
    ]
    
    if not today_graduates:
        return False
    
    # 통계 데이터 - 졸업한 토큰의 거래소 통계 사용
    stats = data.get('statistics', {})
    by_exchange = stats.get('by_exchange', {})
    
    # 팝업 스타일
    st.markdown("""
    <style>
    .graduation-popup {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .graduation-title {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
        text-align: center;
    }
    .graduation-token {
        background: rgba(255,255,255,0.1);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #ffd700;
    }
    .graduation-stats {
        background: rgba(255,255,255,0.15);
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }
    .stat-item {
        margin: 8px 0;
        font-size: 16px;
    }
    .highlight {
        color: #ffd700;
        font-weight: bold;
        font-size: 20px;
    }
    .cta-button {
        background: #ffd700;
        color: #667eea;
        padding: 12px 24px;
        border-radius: 25px;
        text-align: center;
        font-weight: bold;
        margin-top: 15px;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 팝업 내용
    st.markdown('<div class="graduation-popup">', unsafe_allow_html=True)
    
    st.markdown(f'<div class="graduation-title">🎉 Crisis Board 졸업을 축하합니다!</div>', unsafe_allow_html=True)
    
    # 졸업 토큰 목록
    for grad in today_graduates:
        exchange = grad.get('exchange', '').upper()
        symbol = grad.get('symbol', '')
        days = grad.get('days_on_board', 0)
        reason = grad.get('reason', '')
        
        st.markdown(f"""
        <div class="graduation-token">
            <div style="font-size: 20px; font-weight: bold;">{exchange} {symbol}</div>
            <div style="font-size: 14px; margin-top: 5px;">메인보드 {days}일 체류 후 졸업</div>
            <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">{reason}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 졸업한 토큰의 거래소별 통계 수집
    exchanges_in_graduates = set(g.get('exchange', '').lower() for g in today_graduates)
    
    # 거래소별 통계 표시
    stats_html = '<div class="graduation-stats">'
    stats_html += '<div style="font-size: 20px; font-weight: bold; margin-bottom: 15px;">📊 Night Watch 실적</div>'
    
    for exchange_id in exchanges_in_graduates:
        if exchange_id not in by_exchange:
            continue
        
        ex_data = by_exchange[exchange_id]
        ex_name = ex_data.get('exchange_name', exchange_id.upper())
        last_100 = ex_data.get('last_100_days', {})
        premium = ex_data.get('premium_defender', {})
        
        total_delistings = last_100.get('total_delistings', 0)
        warned_count = last_100.get('nightwatch_warned', 0)
        warning_accuracy = last_100.get('warning_accuracy', 0) * 100
        days_advance = last_100.get('days_advance_warning', 30)
        survival_rate = premium.get('survival_rate', 1.0) * 100
        
        if total_delistings > 0:
            stats_html += f"""
            <div class="stat-item" style="margin: 15px 0; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <div style="font-weight: bold; margin-bottom: 8px;">{ex_name}</div>
                <div>과거 100일간 {ex_name} 거래소에서 상폐된 USDT SPOT PAIRS 중 
                <span class="highlight">{warning_accuracy:.0f}%</span>를 
                (<span class="highlight">{warned_count}개/{total_delistings}개 상폐</span>) 
                나이트 워치가 상폐 <span class="highlight">{days_advance}일 이전</span>에 경고 포스팅을 하고 
                관리필요성을 팀과 커뮤니티에 알렸습니다.</div>
                <div style="margin-top: 5px;">프리미엄 유동성 디펜더 서비스로 대응중인 프로젝트들은 
                <span class="highlight">{survival_rate:.0f}% 생존</span>했습니다.</div>
            </div>
            """
    
    stats_html += """
        <div class="cta-button" style="margin-top: 20px;">
            💡 프리미엄 유동성 디펜더 서비스로 자동 방어를 실행하세요!
        </div>
    </div>
    """
    
    st.markdown(stats_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return True


def get_today_graduates_count():
    """오늘 졸업한 토큰 수 반환"""
    graduated_file = 'graduated_tokens.json'
    
    if not os.path.exists(graduated_file):
        return 0
    
    try:
        with open(graduated_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        today = datetime.now(timezone.utc).date().isoformat()
        today_graduates = [
            g for g in data.get('daily_graduates', [])
            if g.get('exit_date') == today
        ]
        
        return len(today_graduates)
    except:
        return 0












