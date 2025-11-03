#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google AdSense Helper Module
Streamlit 앱에 AdSense 광고를 통합하는 헬퍼 함수들
"""

import json
import os
import streamlit.components.v1 as components

def load_adsense_config():
    """AdSense 설정 파일을 로드합니다."""
    config_path = "config/adsense_config.json"
    if not os.path.exists(config_path):
        return {
            "enabled": False,
            "publisher_id": "",
            "ad_units": {}
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"[AdSense] 설정 파일 로드 실패: {e}")
        return {
            "enabled": False,
            "publisher_id": "",
            "ad_units": {}
        }

def get_adsense_head_script(publisher_id):
    """AdSense 헤드 스크립트를 반환합니다."""
    if not publisher_id:
        return ""
    
    return f"""
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-{publisher_id}"
         crossorigin="anonymous"></script>
    """

def render_adsense_ad(slot_id, ad_style=None, responsive=True):
    """
    AdSense 광고를 렌더링합니다.
    
    Args:
        slot_id: AdSense 광고 슬롯 ID
        ad_style: 광고 스타일 딕셔너리 (width, height 등)
        responsive: 반응형 광고 여부 (기본값: True)
    
    Returns:
        HTML 문자열 또는 None
    """
    if not slot_id:
        return None
    
    config = load_adsense_config()
    if not config.get("enabled", False):
        return None
    
    publisher_id = config.get("publisher_id", "")
    if not publisher_id:
        return None
    
    # 기본 스타일
    default_style = {
        "display": "block",
        "width": "336px",
        "height": "280px",
        "margin": "10px auto"
    }
    
    if ad_style:
        default_style.update(ad_style)
    
    style_str = "; ".join([f"{k}: {v}" for k, v in default_style.items()])
    
    # 반응형 광고인 경우
    if responsive:
        ad_html = f"""
        <ins class="adsbygoogle"
             style="{style_str}"
             data-ad-client="ca-pub-{publisher_id}"
             data-ad-slot="{slot_id}"
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
        <script>
             (adsbygoogle = window.adsbygoogle || []).push({{}});
        </script>
        """
    else:
        ad_html = f"""
        <ins class="adsbygoogle"
             style="{style_str}"
             data-ad-client="ca-pub-{publisher_id}"
             data-ad-slot="{slot_id}"></ins>
        <script>
             (adsbygoogle = window.adsbygoogle || []).push({{}});
        </script>
        """
    
    return ad_html

def render_adsense_head():
    """AdSense 헤드 스크립트를 렌더링합니다 (앱 시작 시 한 번만)."""
    config = load_adsense_config()
    if not config.get("enabled", False):
        return ""
    
    publisher_id = config.get("publisher_id", "")
    if not publisher_id:
        return ""
    
    script = get_adsense_head_script(publisher_id)
    if script:
        # Streamlit의 st.markdown을 사용하여 헤드에 스크립트 삽입
        return script
    return ""

def render_sidebar_ad():
    """사이드바에 AdSense 광고를 렌더링합니다."""
    config = load_adsense_config()
    if not config.get("enabled", False):
        return
    
    sidebar_config = config.get("ad_units", {}).get("sidebar", {})
    if not sidebar_config.get("enabled", False):
        return
    
    slot_id = sidebar_config.get("slot_id", "")
    if not slot_id:
        return
    
    ad_style = sidebar_config.get("style", {})
    ad_html = render_adsense_ad(slot_id, ad_style, responsive=True)
    
    if ad_html:
        components.html(ad_html, height=ad_style.get("height", 600))

def render_top_banner_ad():
    """상단 배너 AdSense 광고를 렌더링합니다."""
    config = load_adsense_config()
    if not config.get("enabled", False):
        return
    
    banner_config = config.get("ad_units", {}).get("top_banner", {})
    if not banner_config.get("enabled", False):
        return
    
    slot_id = banner_config.get("slot_id", "")
    if not slot_id:
        return
    
    ad_style = banner_config.get("style", {})
    ad_html = render_adsense_ad(slot_id, ad_style, responsive=True)
    
    if ad_html:
        components.html(ad_html, height=ad_style.get("height", 90))

def render_inline_ad():
    """인라인 AdSense 광고를 렌더링합니다."""
    config = load_adsense_config()
    if not config.get("enabled", False):
        return
    
    inline_config = config.get("ad_units", {}).get("inline", {})
    if not inline_config.get("enabled", False):
        return
    
    slot_id = inline_config.get("slot_id", "")
    if not slot_id:
        return
    
    ad_style = inline_config.get("style", {})
    ad_html = render_adsense_ad(slot_id, ad_style, responsive=True)
    
    if ad_html:
        components.html(ad_html, height=ad_style.get("height", 280))
