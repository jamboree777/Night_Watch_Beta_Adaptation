"""
Delisting Check Module
======================
상폐 의심 토큰 감지 및 관리
"""

import streamlit as st
import json
import os
from datetime import datetime, timezone, timedelta
from modules.token_manager import TokenManager

def load_delisting_suspects():
    """상폐 의심 토큰 목록 로드"""
    suspects_file = "delisting_suspects.json"
    if os.path.exists(suspects_file):
        try:
            with open(suspects_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"suspects": [], "confirmed_delistings": []}
    return {"suspects": [], "confirmed_delistings": []}

def save_delisting_suspects(data):
    """상폐 의심 토큰 목록 저장"""
    suspects_file = "delisting_suspects.json"
    with open(suspects_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _record_delisting(exchange, symbol, token_id, was_on_main_board, chronicle_file):
    """
    상폐 기록 (graduated_tokens.json에 추가)
    
    Args:
        exchange: 거래소 ID
        symbol: 토큰 심볼
        token_id: 토큰 ID
        was_on_main_board: Main Board 포스팅 여부
        chronicle_file: Chronicle 파일 경로 (있으면)
    """
    records_file = 'graduated_tokens.json'
    
    try:
        # 기존 데이터 로드
        if os.path.exists(records_file):
            with open(records_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                'daily_graduates': [],
                'delisting_records': {
                    'gateio': [],
                    'mexc': [],
                    'kucoin': [],
                    'bitget': []
                },
                'statistics': {'by_exchange': {}}
            }
        
        # delisting_records가 없으면 추가
        if 'delisting_records' not in data:
            data['delisting_records'] = {
                'gateio': [],
                'mexc': [],
                'kucoin': [],
                'bitget': []
            }
        
        # 상폐 기록 추가
        delisting_record = {
            'token_id': token_id,
            'symbol': symbol,
            'delisted_at': datetime.now(timezone.utc).isoformat(),
            'was_on_main_board': was_on_main_board,
            'chronicle_file': chronicle_file
        }
        
        exchange_lower = exchange.lower()
        if exchange_lower not in data['delisting_records']:
            data['delisting_records'][exchange_lower] = []
        
        data['delisting_records'][exchange_lower].append(delisting_record)
        
        # 100일 이전 기록 삭제
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        for ex_id in data['delisting_records']:
            data['delisting_records'][ex_id] = [
                r for r in data['delisting_records'][ex_id]
                if r.get('delisted_at', '9999') >= cutoff_date
            ]
        
        # 통계 자동 업데이트
        if 'statistics' not in data:
            data['statistics'] = {'by_exchange': {}}
        if 'by_exchange' not in data['statistics']:
            data['statistics']['by_exchange'] = {}
        
        if exchange_lower not in data['statistics']['by_exchange']:
            data['statistics']['by_exchange'][exchange_lower] = {
                'exchange_name': exchange.upper(),
                'last_100_days': {},
                'premium_defender': {}
            }
        
        # 최근 100일 통계 재계산
        recent_100_days = data['delisting_records'][exchange_lower]
        warned_count = len([r for r in recent_100_days if r.get('was_on_main_board', False)])
        
        data['statistics']['by_exchange'][exchange_lower]['last_100_days'] = {
            'total_delistings': len(recent_100_days),
            'nightwatch_warned': warned_count,
            'warning_accuracy': warned_count / len(recent_100_days) if recent_100_days else 0,
            'days_advance_warning': 30
        }
        
        # 저장
        with open(records_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Delisting recorded: {exchange.upper()} {symbol} (Main Board: {was_on_main_board})")
    
    except Exception as e:
        print(f"Failed to record delisting: {e}")


def generate_delisting_chronicle(token_id, exchange, symbol):
    """
    상폐 토큰 크로니클 생성
    - 위기보드 진입부터 상폐까지 모든 수치 변화 기록
    - 향후 구현: scan_history, violation_history 등에서 데이터 수집
    """
    chronicle = {
        'token_id': token_id,
        'exchange': exchange,
        'symbol': symbol,
        'chronicle_generated_at': datetime.now(timezone.utc).isoformat(),
        'timeline': [],
        'summary': {},
        'data_files': []
    }
    
    # TODO: 실제 구현 시 다음 데이터 수집
    # 1. tokens_unified.json에서 모든 스캔 기록
    # 2. scan_history.json에서 위반 히스토리
    # 3. violation_history.json (if exists)
    # 4. 메인보드 진입/퇴출 이력
    # 5. 그레이드 변천사 (F -> D -> C 등)
    
    chronicle['timeline'].append({
        'date': datetime.now(timezone.utc).isoformat(),
        'event': '상폐 확정',
        'details': 'Chronicle generation - Implementation pending'
    })
    
    chronicle['summary'] = {
        'first_detected': None,
        'main_board_entry': None,
        'delisting_confirmed': datetime.now(timezone.utc).isoformat(),
        'total_days_monitored': 0,
        'grade_history': [],
        'max_risk': 0,
        'max_violation_rate': 0
    }
    
    # 크로니클 파일 저장 (향후 구현)
    chronicle_dir = "delisting_chronicles"
    os.makedirs(chronicle_dir, exist_ok=True)
    
    chronicle_file = os.path.join(chronicle_dir, f"{token_id}_chronicle.json")
    with open(chronicle_file, 'w', encoding='utf-8') as f:
        json.dump(chronicle, f, indent=2, ensure_ascii=False)
    
    return chronicle_file

def check_missing_tokens():
    """
    워치리스트/메인보드 토큰 중 데이터가 없는 것 감지
    - scan_aggregate가 없음
    - current_snapshot이 24시간 이상 오래됨
    - tokens_unified.json에 아예 없음
    """
    tm = TokenManager()
    all_tokens = tm.get_all_tokens()
    
    now = datetime.now(timezone.utc)
    missing_tokens = []
    
    # 1. users.json에서 모든 워치리스트 토큰 수집
    users_file = "data/users.json"
    watchlist_token_ids = set()
    
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                for user_id, user_data in users.items():
                    for token_info in user_data.get('watchlist', []):
                        token_id = f"{token_info['exchange']}_{token_info['symbol']}".replace('/', '_').lower()
                        watchlist_token_ids.add((token_id, token_info['exchange'], token_info['symbol']))
        except:
            pass
    
    # 2. 메인보드 토큰도 확인
    for token_id, token_data in all_tokens.items():
        lifecycle_status = token_data.get('lifecycle', {}).get('status')
        if lifecycle_status in ['MAIN_BOARD', 'MONITORING']:
            exchange = token_data.get('exchange', '')
            symbol = token_data.get('symbol', '')
            watchlist_token_ids.add((token_id, exchange, symbol))
    
    # 3. 각 토큰 상태 확인
    for token_id, exchange, symbol in watchlist_token_ids:
        token = all_tokens.get(token_id)
        
        issue_type = None
        last_seen = None
        days_missing = 0
        
        if not token:
            # 토큰이 DB에 아예 없음
            issue_type = "not_in_db"
            days_missing = 999  # 알 수 없음
        else:
            # scan_aggregate 확인
            scan_aggregate = token.get('scan_aggregate', {})
            current_snapshot = token.get('current_snapshot', {})
            
            has_scan_data = scan_aggregate and scan_aggregate.get('avg_spread_pct') is not None
            
            # 최신 데이터 시간 확인
            last_scan = scan_aggregate.get('last_main_scan') or scan_aggregate.get('last_priority_scan')
            last_snapshot = current_snapshot.get('timestamp')
            
            if last_scan:
                try:
                    last_seen_time = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                    days_missing = (now - last_seen_time).days
                    last_seen = last_scan
                except:
                    pass
            elif last_snapshot:
                try:
                    last_seen_time = datetime.fromisoformat(last_snapshot.replace('Z', '+00:00'))
                    days_missing = (now - last_seen_time).days
                    last_seen = last_snapshot
                except:
                    pass
            
            # 문제 유형 판단
            if not has_scan_data and days_missing > 1:
                issue_type = "no_scan_data"
            elif days_missing > 7:
                issue_type = "data_outdated"
        
        if issue_type:
            missing_tokens.append({
                'token_id': token_id,
                'exchange': exchange,
                'symbol': symbol,
                'issue_type': issue_type,
                'last_seen': last_seen,
                'days_missing': days_missing,
                'detected_at': now.isoformat()
            })
    
    return missing_tokens

def render_delisting_check():
    """상폐 확인 UI"""
    st.header("🔍 Delisting Check")
    st.caption("상폐 의심 토큰 감지 및 관리")
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚠️ 상폐 의심 토큰",
        "📊 MEXC Assessment Zone",
        "✅ 상폐 확정",
        "🔧 수동 관리"
    ])
    
    # ==================== TAB 1: 상폐 의심 토큰 ====================
    with tab1:
        st.subheader("⚠️ 데이터 누락 토큰")
        st.caption("워치리스트/메인보드에 있지만 스캔 데이터가 없는 토큰")
        
        if st.button("🔍 지금 확인하기", type="primary"):
            with st.spinner("토큰 상태 확인 중..."):
                missing_tokens = check_missing_tokens()
                
                if missing_tokens:
                    # delisting_suspects.json에 저장
                    suspects_data = load_delisting_suspects()
                    
                    # 기존 suspects 업데이트 (중복 제거)
                    existing_ids = {s['token_id'] for s in suspects_data['suspects']}
                    new_suspects = [t for t in missing_tokens if t['token_id'] not in existing_ids]
                    
                    suspects_data['suspects'].extend(new_suspects)
                    suspects_data['last_check'] = datetime.now(timezone.utc).isoformat()
                    
                    save_delisting_suspects(suspects_data)
                    
                    st.success(f"✅ 확인 완료! {len(missing_tokens)}개 토큰 발견")
                else:
                    st.info("✅ 모든 토큰이 정상입니다!")
        
        # 저장된 상폐 의심 목록 표시
        suspects_data = load_delisting_suspects()
        suspects = suspects_data.get('suspects', [])
        
        if suspects:
            st.markdown("---")
            
            # 거래소별 필터링
            col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 2])
            
            with col_filter1:
                exchange_filter = st.multiselect(
                    "Exchange Filter:",
                    options=['gateio', 'mexc', 'kucoin', 'bitget'],
                    default=['gateio', 'mexc', 'kucoin', 'bitget'],
                    key='delisting_exchange_filter'
                )
            
            with col_filter2:
                # 거래소별 통계
                exchange_counts = {}
                for s in suspects:
                    ex = s['exchange']
                    exchange_counts[ex] = exchange_counts.get(ex, 0) + 1
                
                st.metric("Total Suspects", len(suspects))
            
            with col_filter3:
                # 다운로드 버튼
                if st.button("📥 Download by Exchange"):
                    import subprocess
                    subprocess.run(['python', '-c', 
                        "import json; from collections import defaultdict; "
                        "suspects = json.load(open('delisting_suspects.json', encoding='utf-8'))['suspects']; "
                        "by_ex = defaultdict(list); "
                        "[by_ex[s['exchange']].append(s) for s in suspects]; "
                        "output = {ex: sorted([{'symbol': s['symbol'], 'token_id': s['token_id'], 'detected_at': s['detected_at'], 'reason': s['reason']} for s in tokens], key=lambda x: x['symbol']) for ex, tokens in by_ex.items()}; "
                        "output['_summary'] = {'total': len(suspects), 'by_exchange': {ex: len(tokens) for ex, tokens in by_ex.items()}}; "
                        "json.dump(output, open('delisting_suspects_by_exchange.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False);"
                    ])
                    st.success("✅ File created: delisting_suspects_by_exchange.json")
            
            # 거래소별 통계 표시
            st.markdown("**By Exchange:**")
            cols_stats = st.columns(4)
            for i, (ex, count) in enumerate(sorted(exchange_counts.items())):
                with cols_stats[i]:
                    st.metric(ex.upper(), count)
            
            # 필터 적용
            suspects = [s for s in suspects if s['exchange'] in exchange_filter]
            st.markdown(f"**Showing {len(suspects)} tokens**")
            
            # 문제 유형별 그룹핑
            issue_types = {
                'assessment_zone_exit': '⚠️ 평가존 퇴출 - 상폐 의심 (정규 스캔에 없음)',
                'not_in_db': '❌ DB에 없음 (상폐 가능성 높음)',
                'no_scan_data': '⚠️ 스캔 데이터 없음',
                'data_outdated': '🕐 데이터 오래됨 (7일+)',
                'data_missing': '🔍 데이터 누락 (12시간+)'
            }
            
            for issue_type, label in issue_types.items():
                filtered = [s for s in suspects if s['issue_type'] == issue_type]
                
                if filtered:
                    with st.expander(f"{label} ({len(filtered)}개)", expanded=(issue_type == 'not_in_db')):
                        for suspect_idx, suspect in enumerate(filtered):
                            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                            
                            with col1:
                                st.write(f"**{suspect['exchange'].upper()}**")
                                st.caption(suspect['symbol'])
                            
                            with col2:
                                days = suspect.get('days_missing', 0)
                                if days == 999:
                                    st.error("데이터 없음")
                                elif days > 30:
                                    st.error(f"{days}일 전")
                                elif days > 7:
                                    st.warning(f"{days}일 전")
                                else:
                                    st.info(f"{days}일 전")
                            
                            with col3:
                                # 평가존 퇴출은 정규 스캔에 없으면 상폐 의심이므로 졸업 버튼 불필요
                                # (자동 졸업은 detect_missing_tokens.py에서 처리됨)
                                
                                if st.button("✅ 상폐 확정", key=f"confirm_{issue_type}_{suspect_idx}_{suspect['token_id']}"):
                                    # Main Board 포스팅 여부 확인
                                    token_id = suspect['token_id']
                                    exchange = suspect['exchange']
                                    symbol = suspect['symbol']
                                    
                                    # tokens_unified.json에서 확인
                                    was_on_main_board = False
                                    chronicle_file = None
                                    
                                    if os.path.exists('data/tokens_unified.json'):
                                        try:
                                            with open('data/tokens_unified.json', 'r', encoding='utf-8') as f:
                                                all_tokens = json.load(f)
                                            
                                            token_data = all_tokens.get(token_id, {})
                                            lifecycle = token_data.get('lifecycle', {})
                                            
                                            # Main Board 이력 확인
                                            if lifecycle.get('main_board_entry') or lifecycle.get('status') == 'MAIN_BOARD':
                                                was_on_main_board = True
                                                # Chronicle 생성
                                                chronicle_file = generate_delisting_chronicle(token_id, exchange, symbol)
                                        except Exception as e:
                                            st.error(f"Error checking Main Board status: {e}")
                                    
                                    # graduated_tokens.json에 상폐 기록
                                    _record_delisting(exchange, symbol, token_id, was_on_main_board, chronicle_file)
                                    
                                    # 상폐 확정 목록으로 이동
                                    confirmed_record = {
                                        **suspect,
                                        'confirmed_at': datetime.now(timezone.utc).isoformat(),
                                        'confirmed_by': 'admin',
                                        'was_on_main_board': was_on_main_board,
                                        'chronicle_file': chronicle_file,
                                        'chronicle_expires_at': (datetime.now(timezone.utc) + timedelta(days=90)).isoformat() if chronicle_file else None
                                    }
                                    
                                    suspects_data['confirmed_delistings'].append(confirmed_record)
                                    suspects_data['suspects'] = [s for s in suspects_data['suspects'] if s['token_id'] != suspect['token_id']]
                                    save_delisting_suspects(suspects_data)
                                    
                                    if chronicle_file:
                                        st.success(f"✅ 상폐 확정 (Chronicle 생성): {chronicle_file}")
                                    else:
                                        st.success(f"✅ 상폐 확정 (간단 기록)")
                                    st.rerun()
                            
                            with col4:
                                if st.button("❌ 무시", key=f"ignore_{issue_type}_{suspect_idx}_{suspect['token_id']}"):
                                    # 의심 목록에서 제거
                                    suspects_data['suspects'] = [s for s in suspects_data['suspects'] if s['token_id'] != suspect['token_id']]
                                    save_delisting_suspects(suspects_data)
                                    st.rerun()
        else:
            st.info("💡 현재 상폐 의심 토큰이 없습니다.")
    
    # ==================== TAB 2: MEXC Assessment Zone ====================
    with tab2:
        st.subheader("📊 MEXC Assessment Zone Management")
        st.caption("MEXC 평가존 토큰 관리 - 정규 스캔에서 사라진 MEXC 토큰을 평가존으로 이동")
        
        # Assessment Zone로 이동 가능한 MEXC 토큰 필터링
        suspects_data = load_delisting_suspects()
        suspects = suspects_data.get('suspects', [])
        
        mexc_suspects = [s for s in suspects if s.get('exchange', '').lower() == 'mexc']
        
        if mexc_suspects:
            st.info(f"📊 MEXC 토큰 중 데이터 누락: {len(mexc_suspects)}개")
            
            # 거래소별 통계
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total MEXC Suspects", len(mexc_suspects))
            with col2:
                # Assessment Zone 파일 로드
                az_file = 'assessment_zone_list.json'
                if os.path.exists(az_file):
                    with open(az_file, 'r', encoding='utf-8') as f:
                        az_data = json.load(f)
                    current_az_count = len(az_data.get('tokens', []))
                else:
                    current_az_count = 0
                st.metric("Current AZ Tokens", current_az_count)
            
            st.markdown("---")
            
            # MEXC 의심 토큰 표시
            for idx, suspect in enumerate(mexc_suspects):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"**{suspect['symbol']}**")
                    st.caption(f"Token ID: {suspect['token_id']}")
                
                with col2:
                    # 데이터 누락 시작 시간 (detected_at)
                    detected_at = suspect.get('detected_at', 'N/A')
                    if detected_at != 'N/A':
                        try:
                            detected_time = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
                            time_str = detected_time.strftime('%Y-%m-%d %H:%M UTC')
                        except:
                            time_str = detected_at[:19]
                    else:
                        time_str = 'Unknown'
                    
                    st.caption(f"Missing since: {time_str}")
                
                with col3:
                    if st.button("📊 → AZ", key=f"to_az_{idx}_{suspect['token_id']}"):
                        # Assessment Zone으로 이동
                        token_id = suspect['token_id']
                        symbol = suspect['symbol']
                        detected_at = suspect.get('detected_at')
                        
                        # assessment_zone_list.json에 추가
                        az_file = 'assessment_zone_list.json'
                        if os.path.exists(az_file):
                            with open(az_file, 'r', encoding='utf-8') as f:
                                az_data = json.load(f)
                        else:
                            az_data = {'tokens': [], 'last_updated': None}
                        
                        # 중복 체크
                        existing = [t for t in az_data['tokens'] if t['token_id'] == token_id]
                        if not existing:
                            az_data['tokens'].append({
                                'token_id': token_id,
                                'symbol': symbol,
                                'added_at': datetime.now(timezone.utc).isoformat(),
                                'missing_since': detected_at,  # 정보를 못받기 시작한 시점
                                'added_by': 'admin_delisting_check'
                            })
                            az_data['last_updated'] = datetime.now(timezone.utc).isoformat()
                            
                            with open(az_file, 'w', encoding='utf-8') as f:
                                json.dump(az_data, f, indent=2, ensure_ascii=False)
                        
                        # tokens_unified.json 업데이트 (status = ASSESSMENT_ZONE)
                        tm = TokenManager()
                        token_data = tm.get_token_by_id(token_id)
                        if token_data:
                            tm.update_token(token_data.get('exchange'), token_data.get('symbol'), {
                                'lifecycle': {
                                    'status': 'ASSESSMENT_ZONE',
                                    'assessment_zone_entry': detected_at  # 데이터 누락 시작 시간
                                }
                            })
                        
                        # suspects에서 제거
                        suspects_data['suspects'] = [s for s in suspects_data['suspects'] if s['token_id'] != token_id]
                        save_delisting_suspects(suspects_data)
                        
                        st.success(f"✅ {symbol} moved to Assessment Zone (since {time_str})")
                        st.rerun()
                
                with col4:
                    if st.button("❌ 무시", key=f"ignore_mexc_{idx}_{suspect['token_id']}"):
                        # 의심 목록에서 제거
                        suspects_data['suspects'] = [s for s in suspects_data['suspects'] if s['token_id'] != suspect['token_id']]
                        save_delisting_suspects(suspects_data)
                        st.success("✅ Ignored")
                        st.rerun()
        else:
            st.info("✅ No MEXC tokens with missing data")
    
    # ==================== TAB 3: 상폐 확정 ====================
    with tab3:
        st.subheader("✅ 상폐 확정 토큰")
        st.caption("관리자가 상폐로 확정한 토큰 목록")
        
        confirmed = suspects_data.get('confirmed_delistings', [])
        
        if confirmed:
            st.markdown(f"**총 {len(confirmed)}개 상폐 토큰**")
            
            for idx, delisted in enumerate(confirmed):
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                
                with col1:
                    st.write(f"**{delisted['exchange'].upper()}**")
                    st.caption(delisted['symbol'])
                
                with col2:
                    confirmed_date = delisted.get('confirmed_at', '')
                    expires_at = delisted.get('chronicle_expires_at', '')
                    if confirmed_date:
                        try:
                            dt = datetime.fromisoformat(confirmed_date.replace('Z', '+00:00'))
                            st.caption(f"확정: {dt.strftime('%Y-%m-%d')}")
                        except:
                            st.caption("확정일 불명")
                    
                    # 만료일 표시
                    if expires_at:
                        try:
                            exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            days_left = (exp_dt - datetime.now(timezone.utc)).days
                            if days_left > 0:
                                st.caption(f"⏰ {days_left}일 남음")
                            else:
                                st.caption("⏰ 만료됨")
                        except:
                            pass
                
                with col3:
                    # 크로니클 다운로드
                    chronicle_file = delisted.get('chronicle_file', '')
                    if chronicle_file and os.path.exists(chronicle_file):
                        with open(chronicle_file, 'r', encoding='utf-8') as f:
                            chronicle_data = f.read()
                        
                        st.download_button(
                            label="📥 크로니클",
                            data=chronicle_data,
                            file_name=f"{delisted['token_id']}_chronicle.json",
                            mime="application/json",
                            key=f"download_confirmed_{idx}_{delisted['token_id']}"
                        )
                    else:
                        st.caption("크로니클 없음")
                
                with col4:
                    if st.button("🗑️ 완전 삭제", key=f"delete_confirmed_{idx}_{delisted['token_id']}"):
                        if st.button(f"⚠️ 정말 삭제? (재확인)", key=f"confirm_delete_confirmed_{idx}_{delisted['token_id']}"):
                            # tokens_unified.json에서 삭제
                            tm = TokenManager()
                            # TODO: TokenManager에 delete 메서드 추가 필요
                            st.warning("⚠️ 삭제 기능은 향후 구현 예정")
                
                with col5:
                    if st.button("↩️ 복원", key=f"restore_confirmed_{idx}_{delisted['token_id']}"):
                        # 의심 목록으로 되돌리기
                        suspects_data['suspects'].append(delisted)
                        suspects_data['confirmed_delistings'] = [d for d in suspects_data['confirmed_delistings'] if d['token_id'] != delisted['token_id']]
                        save_delisting_suspects(suspects_data)
                        st.rerun()
        else:
            st.info("💡 상폐 확정된 토큰이 없습니다.")
    
    # ==================== TAB 4: 수동 관리 ====================
    with tab4:
        st.subheader("🔧 수동 토큰 관리")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**토큰 수동 추가**")
            add_exchange = st.selectbox(
                "거래소",
                ["gateio", "mexc", "kucoin", "bitget"],
                key="add_exchange"
            )
            add_symbol = st.text_input(
                "심볼 (예: BTC/USDT)",
                key="add_symbol"
            )
            
            if st.button("➕ 토큰 추가", key="manual_add"):
                if add_symbol:
                    st.warning("⚠️ 토큰 수동 추가 기능은 향후 구현 예정")
                else:
                    st.error("❌ 심볼을 입력하세요")
        
        with col2:
            st.markdown("**토큰 수동 삭제**")
            del_exchange = st.selectbox(
                "거래소",
                ["gateio", "mexc", "kucoin", "bitget"],
                key="del_exchange"
            )
            del_symbol = st.text_input(
                "심볼 (예: BSTR/USDT)",
                key="del_symbol"
            )
            
            if st.button("🗑️ 토큰 삭제", key="manual_delete"):
                if del_symbol:
                    token_id = f"{del_exchange}_{del_symbol.replace('/', '_')}".lower()
                    
                    # 상폐 의심 목록에 추가
                    suspects_data['suspects'].append({
                        'token_id': token_id,
                        'exchange': del_exchange,
                        'symbol': del_symbol,
                        'issue_type': 'manual_mark',
                        'last_seen': None,
                        'days_missing': 0,
                        'detected_at': datetime.now(timezone.utc).isoformat()
                    })
                    save_delisting_suspects(suspects_data)
                    st.success(f"✅ {del_symbol}을 상폐 의심 목록에 추가했습니다")
                else:
                    st.error("❌ 심볼을 입력하세요")
        
        st.markdown("---")
        
        # 자동 체크 설정
        st.markdown("**⏰ 자동 상폐 체크 설정**")
        st.info("""
        💡 **자동 체크 기능 (향후 구현)**
        - 매일 정해진 시간에 자동으로 상폐 의심 토큰 체크
        - 의심 토큰 발견 시 Telegram/Email 알림
        - 3일 연속 데이터 없으면 자동으로 상폐 의심 등록
        """)
        
        auto_check_enabled = st.checkbox("자동 체크 활성화 (미구현)", value=False)
        if auto_check_enabled:
            st.time_input("체크 시간 (UTC)", value=None, key="check_time")












