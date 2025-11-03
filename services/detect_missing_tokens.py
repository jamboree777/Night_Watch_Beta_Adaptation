"""
상폐 의심 토큰 자동 탐지
- 매일 정규 스캔 후 실행
- 12시간 이상 데이터 없는 토큰 → delisting_suspects.json 추가
"""

import json
import os
from datetime import datetime, timezone, timedelta


def load_delisting_suspects():
    """기존 상폐 의심 목록 로드"""
    suspects_file = "delisting_suspects.json"
    
    if os.path.exists(suspects_file):
        try:
            with open(suspects_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    return {
        'suspects': [],
        'confirmed_delistings': [],
        'ignored': []
    }


def save_delisting_suspects(data):
    """상폐 의심 목록 저장"""
    suspects_file = "delisting_suspects.json"
    with open(suspects_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_mexc_assessment_zone(token_id, symbol):
    """
    MEXC 평가존 리스트에 있는지 확인
    
    Returns:
        bool: 평가존 리스트에 있으면 True
    """
    zone_file = "assessment_zone_list.json"
    
    if not os.path.exists(zone_file):
        return False
    
    try:
        with open(zone_file, 'r', encoding='utf-8') as f:
            zone_data = json.load(f)
        
        mexc_zone = zone_data.get('mexc', {})
        tokens = mexc_zone.get('tokens', [])
        
        # token_id 또는 symbol로 확인
        for token in tokens:
            if token.get('token_id') == token_id or token.get('symbol') == symbol:
                return True
        
        return False
    except:
        return False


def move_to_assessment_zone(token_id, exchange, symbol):
    """
    토큰을 평가존으로 이전
    - tokens_unified.json의 lifecycle.status를 'ASSESSMENT_ZONE'으로 변경
    - daily_assessment_zone_changes.json에 기록
    """
    # 1. tokens_unified.json 업데이트
    if os.path.exists('data/tokens_unified.json'):
        try:
            with open('data/tokens_unified.json', 'r', encoding='utf-8') as f:
                all_tokens = json.load(f)
            
            if token_id in all_tokens:
                lifecycle = all_tokens[token_id].get('lifecycle', {})
                old_status = lifecycle.get('status', 'NORMAL')
                
                # ASSESSMENT_ZONE으로 변경
                lifecycle['status'] = 'ASSESSMENT_ZONE'
                lifecycle['assessment_zone_entry'] = datetime.now(timezone.utc).isoformat()
                lifecycle['previous_status'] = old_status
                
                all_tokens[token_id]['lifecycle'] = lifecycle
                
                # 저장
                with open('data/tokens_unified.json', 'w', encoding='utf-8') as f:
                    json.dump(all_tokens, f, indent=2, ensure_ascii=False)
                
                print(f"  Updated lifecycle.status → ASSESSMENT_ZONE for {token_id}")
        except Exception as e:
            print(f"  Error updating tokens_unified.json: {e}")
    
    # 2. daily_assessment_zone_changes.json 업데이트
    changes_file = "daily_assessment_zone_changes.json"
    
    try:
        if os.path.exists(changes_file):
            with open(changes_file, 'r', encoding='utf-8') as f:
                changes_data = json.load(f)
        else:
            changes_data = {'changes': []}
        
        today = datetime.now(timezone.utc).date().isoformat()
        
        # 오늘 날짜의 변화 찾기
        today_change = None
        for change in changes_data['changes']:
            if change.get('date') == today:
                today_change = change
                break
        
        # 오늘 날짜 변화가 없으면 생성
        if not today_change:
            today_change = {
                'date': today,
                'entered': [],
                'exited': []
            }
            changes_data['changes'].append(today_change)
        
        # entered 리스트에 추가 (중복 체크)
        if symbol not in today_change['entered']:
            today_change['entered'].append(symbol)
        
        # 저장
        with open(changes_file, 'w', encoding='utf-8') as f:
            json.dump(changes_data, f, indent=2, ensure_ascii=False)
        
        print(f"  Recorded to daily_assessment_zone_changes.json")
    except Exception as e:
        print(f"  Error updating daily changes: {e}")


def check_assessment_zone_exits(all_tokens):
    """
    평가존에서 퇴출된 토큰 확인 및 자동 판별
    
    로직:
    1. tokens_unified.json에서 lifecycle.status == 'ASSESSMENT_ZONE'인 토큰 찾기
    2. assessment_zone_list.json에서 해당 토큰이 사라졌는지 확인
    3. 사라졌으면:
       a) 정규 스캔 결과 확인 (last_scanned 12시간 이내)
          - 있음 → 🎓 자동 졸업 (NORMAL 상태로)
          - 없음 → ⚠️ 상폐 의심 (Delisting Check 추가)
    
    Returns:
        list: 퇴출된 토큰 정보
    """
    zone_file = "assessment_zone_list.json"
    
    if not os.path.exists(zone_file):
        return []
    
    try:
        with open(zone_file, 'r', encoding='utf-8') as f:
            zone_data = json.load(f)
    except:
        return []
    
    mexc_zone = zone_data.get('mexc', {})
    zone_token_ids = {t['token_id'] for t in mexc_zone.get('tokens', []) if t.get('status') == 'active'}
    
    # 평가존 상태인데 리스트에 없는 토큰 찾기
    exited_tokens = []
    graduated_tokens = []
    suspects_data = load_delisting_suspects()
    now = datetime.now(timezone.utc)
    
    for token_id, token_data in all_tokens.items():
        lifecycle = token_data.get('lifecycle', {})
        
        if lifecycle.get('status') == 'ASSESSMENT_ZONE':
            # 평가존 리스트에 없으면 퇴출
            if token_id not in zone_token_ids:
                parts = token_id.split('_')
                if len(parts) >= 3:
                    exchange = parts[0]
                    symbol = f"{parts[1].upper()}/{parts[2].upper()}"
                    
                    # 정규 스캔 결과 확인 (last_scanned)
                    current_snapshot = token_data.get('current_snapshot', {})
                    last_scanned = current_snapshot.get('last_scanned')
                    
                    has_recent_data = False
                    if last_scanned:
                        try:
                            last_scan_time = datetime.fromisoformat(last_scanned.replace('Z', '+00:00'))
                            hours_since_scan = (now - last_scan_time).total_seconds() / 3600
                            
                            # 12시간 이내 데이터 → 졸업
                            if hours_since_scan <= 12:
                                has_recent_data = True
                        except:
                            pass
                    
                    if has_recent_data:
                        # 🎓 자동 졸업 처리
                        lifecycle['status'] = 'NORMAL'
                        lifecycle['assessment_zone_exit'] = now.isoformat()
                        lifecycle['exit_reason'] = 'Graduated from Assessment Zone (auto)'
                        token_data['lifecycle'] = lifecycle
                        
                        graduated_tokens.append({
                            'token_id': token_id,
                            'symbol': symbol,
                            'exchange': exchange
                        })
                        
                        print(f"[AUTO GRADUATED] {exchange.upper()} {symbol}: Graduated from Assessment Zone (detected in regular scan)")
                        
                        # daily_assessment_zone_changes.json 업데이트
                        _record_assessment_zone_exit(symbol)
                    else:
                        # ⚠️ 상폐 의심 (관리자 확인 필요)
                        suspect_record = {
                            'token_id': token_id,
                            'exchange': exchange,
                            'symbol': symbol,
                            'detected_at': now.isoformat(),
                            'last_scanned': last_scanned or 'N/A',
                            'days_missing': 0,
                            'reason': 'Exited from Assessment Zone - Not in regular scan (Delisting suspected)',
                            'issue_type': 'assessment_zone_exit'
                        }
                        
                        suspects_data['suspects'].append(suspect_record)
                        exited_tokens.append(suspect_record)
                        
                        print(f"[ASSESSMENT EXIT - SUSPECT] {exchange.upper()} {symbol}: Removed from Assessment Zone, no recent scan data")
                        
                        # daily_assessment_zone_changes.json 업데이트
                        _record_assessment_zone_exit(symbol)
    
    # tokens_unified.json 업데이트 (졸업한 토큰)
    if graduated_tokens:
        try:
            with open('data/tokens_unified.json', 'w', encoding='utf-8') as f:
                json.dump(all_tokens, f, indent=2, ensure_ascii=False)
            print(f"  ✅ Updated tokens_unified.json: {len(graduated_tokens)} tokens graduated")
        except Exception as e:
            print(f"  ❌ Error updating tokens_unified.json: {e}")
    
    # suspects 저장
    if exited_tokens:
        save_delisting_suspects(suspects_data)
    
    return exited_tokens


def _record_assessment_zone_exit(symbol):
    """평가존 퇴출 기록"""
    changes_file = "daily_assessment_zone_changes.json"
    
    try:
        if os.path.exists(changes_file):
            with open(changes_file, 'r', encoding='utf-8') as f:
                changes_data = json.load(f)
        else:
            changes_data = {'changes': []}
        
        today = datetime.now(timezone.utc).date().isoformat()
        
        # 오늘 날짜의 변화 찾기
        today_change = None
        for change in changes_data['changes']:
            if change.get('date') == today:
                today_change = change
                break
        
        # 오늘 날짜 변화가 없으면 생성
        if not today_change:
            today_change = {
                'date': today,
                'entered': [],
                'exited': []
            }
            changes_data['changes'].append(today_change)
        
        # exited 리스트에 추가 (중복 체크)
        if symbol not in today_change['exited']:
            today_change['exited'].append(symbol)
        
        # 저장
        with open(changes_file, 'w', encoding='utf-8') as f:
            json.dump(changes_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  Error recording assessment zone exit: {e}")


def detect_missing_tokens():
    """
    12시간 이상 데이터 없는 토큰 탐지
    
    조건:
    - tokens_unified.json에 있는 모든 토큰
    - current_snapshot.last_scanned가 12시간 이상 오래됨
    - 단, ignored 목록에 없는 토큰만
    """
    
    # 1. tokens_unified.json 로드
    if not os.path.exists('data/tokens_unified.json'):
        print("tokens_unified.json not found")
        return
    
    try:
        with open('data/tokens_unified.json', 'r', encoding='utf-8') as f:
            all_tokens = json.load(f)
    except Exception as e:
        print(f"Error loading tokens_unified.json: {e}")
        return
    
    # 2. 기존 suspects 로드
    suspects_data = load_delisting_suspects()
    existing_suspects = {s['token_id'] for s in suspects_data['suspects']}
    ignored_tokens = {i['token_id'] for i in suspects_data.get('ignored', [])}
    
    # 3. 12시간 기준
    threshold_hours = 12
    now = datetime.now(timezone.utc)
    
    new_suspects = []
    total_checked = 0
    
    # 4. 모든 토큰 검사
    for token_id, token_data in all_tokens.items():
        total_checked += 1
        
        # 이미 확인된 토큰은 스킵
        if token_id in existing_suspects or token_id in ignored_tokens:
            continue
        
        # 토큰 정보 추출
        parts = token_id.split('_')
        if len(parts) < 3:
            continue
        
        exchange = parts[0]
        symbol = f"{parts[1].upper()}/{parts[2].upper()}"
        
        # last_scanned 확인
        current_snapshot = token_data.get('current_snapshot', {})
        last_scanned = current_snapshot.get('last_scanned')
        
        is_stale = False
        reason = ""
        days_missing = 0
        
        if not last_scanned:
            is_stale = True
            reason = "No last_scanned timestamp"
            days_missing = 999
        else:
            try:
                last_scan_time = datetime.fromisoformat(last_scanned.replace('Z', '+00:00'))
                hours_since_scan = (now - last_scan_time).total_seconds() / 3600
                
                if hours_since_scan > threshold_hours:
                    is_stale = True
                    days_missing = int(hours_since_scan / 24)
                    reason = f"Data stale for {hours_since_scan:.1f} hours"
            except Exception as e:
                is_stale = True
                reason = f"Parse error: {e}"
                days_missing = 999
        
        # 🔍 MEXC 평가존 확인 (공용 API에서 사라진 토큰)
        if is_stale and exchange == 'mexc':
            # 평가존 리스트 확인
            in_assessment_zone = check_mexc_assessment_zone(token_id, symbol)
            
            if in_assessment_zone:
                # 평가존으로 이전
                move_to_assessment_zone(token_id, exchange, symbol)
                print(f"[ASSESSMENT ZONE] {exchange.upper()} {symbol}: Moved to Assessment Zone")
                continue  # suspects에 추가하지 않음
        
        # 상폐 의심 토큰 추가
        if is_stale:
            suspect_record = {
                'token_id': token_id,
                'exchange': exchange,
                'symbol': symbol,
                'detected_at': now.isoformat(),
                'last_scanned': last_scanned or 'N/A',
                'days_missing': days_missing,
                'reason': reason,
                'issue_type': 'data_missing'
            }
            
            new_suspects.append(suspect_record)
            print(f"[SUSPECT] {exchange.upper()} {symbol}: {reason}")
    
    # 5. 평가존 퇴출 확인 (평가존에 있던 토큰이 리스트에서 사라짐)
    assessment_zone_exits = check_assessment_zone_exits(all_tokens)
    
    # 6. 새 suspects 추가
    if new_suspects:
        suspects_data['suspects'].extend(new_suspects)
        save_delisting_suspects(suspects_data)
        
        print(f"\n{'='*60}")
        print(f"Detection Summary:")
        print(f"  Total tokens checked: {total_checked}")
        print(f"  New suspects found: {len(new_suspects)}")
        print(f"  Assessment zone exits: {len(assessment_zone_exits)}")
        print(f"  Total suspects: {len(suspects_data['suspects'])}")
        print(f"{'='*60}\n")
        
        # 거래소별 분류
        by_exchange = {}
        for suspect in new_suspects:
            ex = suspect['exchange'].upper()
            if ex not in by_exchange:
                by_exchange[ex] = []
            by_exchange[ex].append(suspect['symbol'])
        
        print("By Exchange:")
        for ex, symbols in sorted(by_exchange.items()):
            print(f"  {ex}: {len(symbols)} tokens")
            for sym in symbols[:5]:  # 처음 5개만 표시
                print(f"    - {sym}")
            if len(symbols) > 5:
                print(f"    ... and {len(symbols) - 5} more")
        
        print(f"\nAdmin action required: Check 'Delisting Check' in Admin Dashboard")
    else:
        print(f"\nNo new missing tokens detected (checked {total_checked} tokens)")
    
    return len(new_suspects)


if __name__ == '__main__':
    detect_missing_tokens()











