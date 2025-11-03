"""
System Control Module
=====================
System-wide control and monitoring features for Night Watch.
"""

import streamlit as st
import os
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def render_system_control():
    """Render System Control section."""
    st.title("🎛️ System Control")
    st.caption("System-wide monitoring and control features")

    # 환경 정보
    is_production = os.getenv('ENVIRONMENT', 'development') == 'production'
    is_docker = os.path.exists('/.dockerenv')

    env_col1, env_col2, env_col3 = st.columns(3)
    with env_col1:
        st.metric("Environment", "Production" if is_production else "Development")
    with env_col2:
        st.metric("Container", "Docker" if is_docker else "Native")
    with env_col3:
        st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}")

    st.markdown("---")

    # 시스템 상태
    st.subheader("📊 System Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("System Status", "🟢 Running")

    with col2:
        # 데이터베이스 크기 (tokens_unified.json)
        try:
            db_file = Path(__file__).parent.parent / "data/tokens_unified.json"
            if db_file.exists():
                db_size = db_file.stat().st_size / (1024 * 1024)
                st.metric("Database Size", f"{db_size:.2f} MB")
            else:
                st.metric("Database Size", "File not found")
        except Exception as e:
            st.metric("Database Size", f"Error: {str(e)[:20]}")

    with col3:
        # 토큰 수 확인 (tokens_unified.json에서) - using absolute path
        try:
            tokens_file = Path(__file__).parent.parent / "data/tokens_unified.json"
            if tokens_file.exists():
                with open(tokens_file, 'r', encoding='utf-8') as f:
                    tokens = json.load(f)
                token_count = len(tokens)
                st.metric("Tracked Tokens", f"{token_count:,}")
            else:
                st.metric("Tracked Tokens", "File not found")
        except Exception as e:
            st.metric("Tracked Tokens", f"Error: {str(e)[:20]}")

    st.markdown("---")

    # 시스템 제어
    st.subheader("⚙️ System Controls")

    st.markdown("**🧹 Clear Streamlit Cache**")
    st.caption("Clear Streamlit internal cache for UI refresh")
    if st.button("Clear Streamlit Cache", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.success("✅ Streamlit 캐시가 삭제되었습니다!")

    st.markdown("---")

    # 시스템 정보
    st.subheader("ℹ️ System Information")

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown("**Application**")
        st.text(f"Version: 1.0 Beta")
        st.text(f"Environment: {'Production' if is_production else 'Development'}")
        st.text(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with info_col2:
        st.markdown("**Directories**")
        directories = ["data", "logs", "admin_modules", "users"]
        for directory in directories:
            exists = "✅" if os.path.exists(directory) else "❌"
            st.text(f"{exists} {directory}/")
