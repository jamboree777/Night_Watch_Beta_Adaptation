"""
MEXC Assessment Zone Management
================================
관리자용 Assessment Zone 토큰 관리
"""

import streamlit as st
from datetime import datetime, timezone
import json
import os

def render_assessment_zone_management():
    """MEXC Assessment Zone 토큰 관리"""
    st.markdown("## 📊 MEXC Assessment Zone Management")
    
    st.info("""
    **MEXC Assessment Zone 관리**
    
    Assessment Zone은 MEXC 거래소의 특별 관리 구역으로,
    상장폐지 가능성이 있는 토큰들이 배치됩니다.
    
    현재 이 기능은 자동으로 감지되며, 별도 관리가 필요하지 않습니다:
    - `mexc_assessment` exchange로 자동 분류
    - 메인보드에 자동 표시 (AZ 태그)
    - Grade 시스템에서 별도 처리
    """)
    
    st.markdown("---")
    st.markdown("### 📋 Current Assessment Zone Tokens")
    
    # tokens_unified.json에서 Assessment Zone 토큰 로드
    try:
        with open('data/tokens_unified.json', 'r', encoding='utf-8') as f:
            tokens_db = json.load(f)
        
        az_tokens = [
            (token_id, data) for token_id, data in tokens_db.items()
            if data.get('exchange') in ['mexc_assessment', 'mexc_evaluation']
        ]
        
        if az_tokens:
            st.write(f"**Total Assessment Zone Tokens:** {len(az_tokens)}")
            
            # 테이블 형식으로 표시
            for token_id, token_data in az_tokens[:20]:  # 최대 20개만 표시
                exchange = token_data.get('exchange')
                symbol = token_data.get('symbol')
                grade = token_data.get('scan_aggregate', {}).get('grade', 'N/A')
                lifecycle_status = token_data.get('lifecycle', {}).get('status', 'NORMAL')
                
                col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
                with col1:
                    st.write(f"**{symbol}**")
                with col2:
                    st.write(f"Exchange: {exchange}")
                with col3:
                    st.write(f"Grade: {grade}")
                with col4:
                    st.write(f"Status: {lifecycle_status}")
            
            if len(az_tokens) > 20:
                st.info(f"+ {len(az_tokens) - 20} more tokens...")
        else:
            st.info("No Assessment Zone tokens found")
    
    except FileNotFoundError:
        st.error("tokens_unified.json not found")
    except Exception as e:
        st.error(f"Error loading tokens: {e}")
    
    st.markdown("---")
    st.markdown("### ℹ️ Information")
    st.markdown("""
    **Assessment Zone 자동 감지:**
    - Scanner가 `mexc_assessment` 거래소로 자동 분류
    - 메인보드 필터에서 "AZ (Assessment Zone)" 선택 가능
    - 높은 위험도로 자동 분류 (리스크 관리)
    
    **추가 관리 기능이 필요하면 요청해주세요.**
    """)









