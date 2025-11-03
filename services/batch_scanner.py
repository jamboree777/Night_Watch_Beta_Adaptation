"""
Batch Scanner for High-Risk Tokens
Scans Gate.io, MEXC, KuCoin, Bitget every 2 hours
Filters: Spread > 1% AND ±2% Depth < $500
"""

# UTF-8 인코딩 강제 (Windows cp949 문제 해결)
import sys
import io
if sys.platform == 'win32':
    # TeeOutput과 충돌하지 않도록 buffer 존재 여부 체크
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import ccxt
import json
import time
from datetime import datetime, timezone, timedelta
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from token_lifecycle import TokenLifecycle
from modules.token_manager import TokenManager
from modules.admin_honeymoon_manager import get_admin_honeymoon_manager
from logger_config import (
    get_scan_logger, get_average_logger, get_error_logger,
    log_scan_start, log_scan_progress, log_scan_complete,
    log_error, log_warning,
    log_average_start, log_average_progress, log_average_complete
)

# Core modules
from core.config import (
    FilePaths,
    ExchangeThresholds,
    TokenStatus,
    TimeSettings,
    ExchangeIds
)
from core.json_utils import load_json, save_json
from core.grade_calculator import GradeCalculator

def save_scan_record(token_id, exchange_id, symbol, scan_data):
    """
    스캔 기록 저장 (tokens_unified.json의 scan_history에 추가)
    
    Args:
        token_id: 토큰 ID (예: "gateio_CRE_USDT")
        exchange_id: 거래소
        symbol: 심볼
        scan_data: 스캔 데이터 (spread, depth, volume, violations 등)
    """
    # ⚠️ 변경: 더 이상 즉시 저장하지 않음 - 데이터만 반환
    # 호출자가 모든 토큰을 모아서 한 번에 ShardManager로 저장

    # 스캔 데이터 구성 (평균 데이터)
    scan_update = {
        'avg_spread_pct': scan_data.get('spread_pct'),
        'avg_depth_2pct': scan_data.get('total_2'),
        'avg_volume_24h': scan_data.get('avg_volume'),
        'grade': scan_data.get('grade', 'N/A'),
        'average_risk': scan_data.get('average_risk', 0),
        'violation_rate': scan_data.get('violation_rate', 0)
    }

    # 파싱
    parts = token_id.split('_')
    exchange = parts[0] if len(parts) > 0 else ''
    symbol = '/'.join(parts[1:]).upper() if len(parts) > 1 else ''

    # 반환값: ShardManager에서 사용할 데이터
    shard_data = {
        'token_id': token_id,
        'exchange': exchange,
        'symbol': symbol,
        'scan_aggregate': scan_update
    }
    
    # 기존 violation_history.json도 업데이트 (호환성 유지)
    history_file = 'violation_history.json'
    
    # 기존 히스토리 로드
    all_history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
        except:
            all_history = {}
    
    # 토큰 히스토리 초기화
    if token_id not in all_history:
        all_history[token_id] = {
            'exchange': exchange_id,
            'symbol': symbol,
            'scan_records': [],
            'retention_policy': {
                'max_age_days': 90,
                'auto_cleanup': True
            }
        }
    
    # 새 스캔 기록 추가
    all_history[token_id]['scan_records'].append(scan_data)
    
    # 저장
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(all_history, f, indent=2, ensure_ascii=False)

    # 반환: ShardManager에서 사용할 데이터
    return shard_data

def calculate_penalty_score(token_id, days=5):
    """
    토큰의 벌점 계산 (최근 N일간)
    
    Args:
        token_id: 토큰 ID
        days: 계산 기간 (기본 5일)
    
    Returns:
        (total_penalty, max_penalty, violation_rate)
    """
    history_file = 'violation_history.json'
    
    if not os.path.exists(history_file):
        return 0, 0, 0.0
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            all_history = json.load(f)
    except:
        return 0, 0, 0.0
    
    if token_id not in all_history:
        return 0, 0, 0.0
    
    # 최근 N일 데이터 필터링
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    
    records = all_history[token_id]['scan_records']
    recent_records = [
        r for r in records
        if datetime.fromisoformat(r['time'].replace('Z', '+00:00')) > cutoff
    ]
    
    if not recent_records:
        return 0, 0, 0.0
    
    # 벌점 계산
    total_penalty = sum(r.get('penalty', 0) for r in recent_records)
    
    # 최대 벌점 (스캔 횟수 × 2점)
    # 2시간 주기 → 하루 12회 → 5일 60회 → 최대 120점
    max_penalty = len(recent_records) * 2
    
    # 위반율
    violations_count = sum(1 for r in recent_records if r.get('violations'))
    violation_rate = violations_count / len(recent_records) if recent_records else 0.0
    
    return total_penalty, max_penalty, violation_rate


def calculate_hourly_risk_score(snapshot, exchange_thresholds):
    """
    시간당 리스크 점수 계산 (0~1, 높을수록 위험)
    
    Args:
        snapshot: {depth, spread, volume, bid, ask}
        exchange_thresholds: {depth_threshold, spread_threshold, volume_threshold}
    
    Returns:
        risk_t (float): 0~1 사이의 리스크 점수
    """
    def clamp(value, min_val=0.0, max_val=1.0):
        return max(min_val, min(max_val, value))
    
    depth = snapshot.get('depth', 0)
    spread = snapshot.get('spread', 0)  # % 단위로 들어옴 (예: 1.5 = 1.5%)
    volume = snapshot.get('volume', 0)
    
    # ✅ MIGRATION: Use ExchangeThresholds from core.config
    depth_min = exchange_thresholds.get('depth_threshold', ExchangeThresholds.DEPTH_MIN_USD)
    spread_max = exchange_thresholds.get('spread_threshold', ExchangeThresholds.SPREAD_MAX_PERCENT)
    volume_min = exchange_thresholds.get('volume_threshold', ExchangeThresholds.VOLUME_MIN_USD)
    
    # Required 설정 확인
    depth_required = exchange_thresholds.get('depth_required', True)
    spread_required = exchange_thresholds.get('spread_required', True)
    volume_required = exchange_thresholds.get('volume_required', False)
    
    # 각 메트릭별 점수 (0~1, 높을수록 위험)
    # 실제 경험치 기반 임계값 적용
    
    # Depth Score (가장 중요! - 500불 이하 임계, 1000불 이상 안정)
    if depth_required and depth_min > 0:
        if depth >= 1000:
            depth_score = 0.0  # 안정
        elif depth >= 500:
            # 500~1000: 선형 감소 (1.0 → 0.0)
            depth_score = (1000 - depth) / 500
        else:
            # < 500: 임계 (1.0)
            depth_score = 1.0
    else:
        depth_score = 0
    
    # Spread Score (1% 권장, 2% 임계)
    if spread_required and spread_max > 0:
        if spread < 1.0:
            spread_score = 0.0  # 안전
        elif spread < 2.0:
            # 1~2%: 선형 증가 (0.0 → 1.0)
            spread_score = (spread - 1.0) / 1.0
        else:
            # >= 2%: 임계 (1.0)
            spread_score = 1.0
    else:
        spread_score = 0
    
    # Volume Score (10,000 권장, 2,000 임계)
    if volume_required and volume_min > 0 and volume > 0:
        if volume >= 10000:
            volume_score = 0.0  # 권장
        elif volume >= 2000:
            # 2,000~10,000: 선형 감소 (1.0 → 0.0)
            volume_score = (10000 - volume) / 8000
        else:
            # < 2,000: 위험 (1.0)
            volume_score = 1.0
    else:
        volume_score = 0
    
    # 가중 평균: Depth 60%, Spread 25%, Volume 15%
    # volume_required=False이면 depth+spread만 계산 (재가중)
    if not volume_required or volume == 0:
        # Volume 무시, Depth 70%, Spread 30%로 재조정
        risk_t = (
            0.70 * depth_score +
            0.30 * spread_score
        )
    else:
        # 모두 포함
        risk_t = (
            0.60 * depth_score +
            0.25 * spread_score +
            0.15 * volume_score
        )
    
    return risk_t


def calculate_5day_average_risk(token_id, exchange_id, days=5):
    """
    5일 평균 리스크 점수 및 Grade 계산
    
    Args:
        token_id: 토큰 ID
        exchange_id: 거래소 ID
        days: 계산 기간 (기본 5일)
    
    Returns:
        dict: {average_risk, violation_rate, grade, sample_count}
    """
    history_file = 'violation_history.json'
    
    if not os.path.exists(history_file):
        return {'average_risk': 0, 'violation_rate': 0, 'grade': 'N/A', 'sample_count': 0}
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            all_history = json.load(f)
    except:
        return {'average_risk': 0, 'violation_rate': 0, 'grade': 'N/A', 'sample_count': 0}
    
    if token_id not in all_history:
        return {'average_risk': 0, 'violation_rate': 0, 'grade': 'N/A', 'sample_count': 0}
    
    # 거래소별 임계값 가져오기
    config_file = 'config/scanner_config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        exchange_thresholds = config['exchanges'].get(exchange_id, {})
    else:
        exchange_thresholds = {}
    
    # 최근 N일 데이터 필터링
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    
    records = all_history[token_id]['scan_records']
    recent_records = [
        r for r in records
        if datetime.fromisoformat(r['time'].replace('Z', '+00:00')) > cutoff
    ]
    
    if not recent_records:
        return {'average_risk': 0, 'violation_rate': 0, 'grade': 'N/A', 'sample_count': 0}
    
    # 각 스냅샷의 risk_t 계산
    risk_scores = []
    violations = 0
    
    for record in recent_records:
        snapshot = {
            'depth': record.get('depth', 0),
            'spread': record.get('spread', 0),
            'volume': record.get('volume', 0)
        }
        
        risk_t = calculate_hourly_risk_score(snapshot, exchange_thresholds)
        risk_scores.append(risk_t)
        
        # 위반 여부 (risk_t > 0이면 어떤 메트릭이라도 임계값 위반)
        if risk_t > 0:
            violations += 1
    
    # 평균 계산
    average_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    violation_rate = violations / len(recent_records) if recent_records else 0
    
    # Grade 분류
    grade = classify_risk_grade(average_risk, violation_rate)
    
    return {
        'average_risk': average_risk,
        'violation_rate': violation_rate,
        'grade': grade,
        'sample_count': len(recent_records)
    }


def _record_graduation(exchange, symbol, token_id, exit_time, reason, days_on_board):
    """
    퇴출 토큰 기록 (메인보드 Exit)
    
    Args:
        exchange: 거래소 ID
        symbol: 토큰 심볼
        token_id: 토큰 ID
        exit_time: 퇴출 시간
        reason: 퇴출 이유
        days_on_board: 메인보드 체류 일수
    """
    graduated_file = 'exited_tokens.json'
    
    try:
        # 기존 데이터 로드
        if os.path.exists(graduated_file):
            with open(graduated_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                'daily_exits': [],
                'statistics': {
                    'by_exchange': {
                        'gateio': {
                            'exchange_name': 'Gate.io',
                            'last_100_days': {
                                'total_delistings': 88,
                                'nightwatch_warned': 84,
                                'warning_accuracy': 0.955,
                                'days_advance_warning': 30
                            },
                            'premium_defender': {
                                'total_using_service': 0,
                                'survival_rate': 1.0
                            }
                        },
                        'mexc': {
                            'exchange_name': 'MEXC',
                            'last_100_days': {
                                'total_delistings': 0,
                                'nightwatch_warned': 0,
                                'warning_accuracy': 0.0,
                                'days_advance_warning': 30
                            },
                            'premium_defender': {
                                'total_using_service': 0,
                                'survival_rate': 1.0
                            }
                        },
                        'kucoin': {
                            'exchange_name': 'KuCoin',
                            'last_100_days': {
                                'total_delistings': 0,
                                'nightwatch_warned': 0,
                                'warning_accuracy': 0.0,
                                'days_advance_warning': 30
                            },
                            'premium_defender': {
                                'total_using_service': 0,
                                'survival_rate': 1.0
                            }
                        },
                        'bitget': {
                            'exchange_name': 'Bitget',
                            'last_100_days': {
                                'total_delistings': 0,
                                'nightwatch_warned': 0,
                                'warning_accuracy': 0.0,
                                'days_advance_warning': 30
                            },
                            'premium_defender': {
                                'total_using_service': 0,
                                'survival_rate': 1.0
                            }
                        }
                    }
                }
            }
        
        # 오늘 날짜
        today = datetime.now(timezone.utc).date().isoformat()
        
        # 퇴출 토큰 추가
        exit_record = {
            'token_id': token_id,
            'exchange': exchange,
            'symbol': symbol,
            'exit_time': exit_time,
            'exit_date': today,
            'reason': reason,
            'days_on_board': days_on_board
        }
        
        if 'daily_exits' not in data:
            data['daily_exits'] = []
        
        data['daily_exits'].append(exit_record)
        
        # 최근 30일만 유지
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        data['daily_exits'] = [
            g for g in data['daily_exits']
            if g.get('exit_date', '9999-99-99') >= cutoff_date
        ]
        
        # 저장
        with open(graduated_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"   [SUCCESS] Recorded exit: {exchange.upper()} {symbol}")
    
    except Exception as e:
        print(f"   [WARNING] Failed to record exit: {e}")


def _record_mainboard_change(change_type: str, exchange: str, symbol: str, grade: str, reason: str = None, days_on_board: int = None):
    """
    메인보드 진입/퇴출을 mainboard_changes.json에 기록
    
    ✅ 수정: Atomic write로 race condition 방지
    """
    try:
        filepath = 'mainboard_changes.json'
        
        # mainboard_changes.json 로드 (with validation)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    changes_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"   [WARNING] Corrupted mainboard_changes.json, creating new one: {e}")
                changes_data = {'recent_changes': []}
        else:
            changes_data = {'recent_changes': []}
        
        # 오늘 날짜
        today = datetime.now(timezone.utc).date().isoformat()
        
        # 오늘 날짜의 기록 찾기
        today_record = None
        for record in changes_data['recent_changes']:
            if record['date'] == today:
                today_record = record
                break
        
        # 오늘 기록이 없으면 생성
        if not today_record:
            today_record = {
                'date': today,
                'entries': [],
                'exits': []
            }
            changes_data['recent_changes'].append(today_record)
        
        # 변경 사항 추가
        if change_type == 'entry':
            today_record['entries'].append({
                'exchange': exchange,
                'symbol': symbol,
                'grade': grade,
                'reason': reason or ''
            })
        elif change_type == 'exit':
            today_record['exits'].append({
                'exchange': exchange,
                'symbol': symbol,
                'grade': grade,
                'reason': reason or '',
                'days_on_board': days_on_board or 0
            })
        
        # 7일 이상 된 기록 삭제
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        changes_data['recent_changes'] = [
            record for record in changes_data['recent_changes']
            if record['date'] >= cutoff_date
        ]
        
        # ✅ Atomic write (race condition 방지)
        temp_file = f'{filepath}.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(changes_data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        shutil.move(temp_file, filepath)
        
    except Exception as e:
        print(f"   ⚠️ Failed to record mainboard change: {e}")


def classify_risk_grade(avg_risk, violation_rate, is_st_tagged=False):
    """
    리스크 등급 분류 (9단계 - 수정된 GPA 시스템)
    
    Grade -> GPA 매핑:
    - F: 0.5 (Critical), D: 1.5 (High Risk)  ← 수정됨
    - C-: 1.7, C: 2.0, C+: 2.3 (Moderate Risk)
    - B-: 2.7, B: 3.0, B+: 3.3 (Low Risk)
    - A-: 3.7, A: 4.0 (Minimal Risk)
    
    ⚠️ ST (Special Treatment)는 등급이 아닌 위험 배지
       등급은 실제 데이터로 계산하고, ST는 별도 표시만 함
    
    Args:
        avg_risk: 평균 리스크 점수 (0~1)
        violation_rate: 위반율 (0~1)
        is_st_tagged: ST Tag 배지 여부 (등급에 영향 없음, 표시용)
    
    Returns:
        str: 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F'
    """
    # F – Critical: avg_risk > 0.80 OR violation_rate ≥ 85%
    # ✅ ST 배지는 등급에 영향 없음 (제거됨)
    if avg_risk > 0.80 or violation_rate >= 0.85:
        return 'F'
    
    # D – Danger: avg_risk > 0.60 OR violation_rate 60–85%
    elif avg_risk > 0.60 or (0.60 <= violation_rate < 0.85):
        return 'D'
    
    # C 등급 (Warning): avg_risk > 0.30 OR violation_rate 25–60%
    elif avg_risk > 0.30 or (0.25 <= violation_rate < 0.60):
        # C 등급 내 세분화
        if avg_risk > 0.50 or violation_rate >= 0.50:
            return 'C-'
        elif avg_risk > 0.40 or violation_rate >= 0.40:
            return 'C'
        else:
            return 'C+'
    
    # B 등급 (Good): avg_risk > 0.15 OR violation_rate 10–25%
    elif avg_risk > 0.15 or (0.10 <= violation_rate < 0.25):
        # B 등급 내 세분화
        if avg_risk > 0.25 or violation_rate >= 0.20:
            return 'B-'
        elif avg_risk > 0.20 or violation_rate >= 0.15:
            return 'B'
        else:
            return 'B+'
    
    # A 등급 (Stable): avg_risk ≤ 0.15 AND violation_rate < 0.10
    elif avg_risk <= 0.15 and violation_rate < 0.10:
        # A 등급 내 세분화
        if avg_risk > 0.10 or violation_rate >= 0.07:
            return 'A-'
        else:
            return 'A'  # A가 최고 등급 (미국 표준)
    
    # Default fallback (should not reach here)
    else:
        return 'A'

def sync_main_board_to_monitoring(main_board_tokens):
    """
    Main Board 토큰을 monitoring_configs.json에 동기화
    
    Args:
        main_board_tokens: Main Board 토큰 목록
    """
    config_file = 'monitoring_configs.json'
    
    # 기존 설정 로드
    monitoring_configs = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                monitoring_configs = json.load(f)
        except:
            monitoring_configs = {}
    
    # Main Board 토큰만 유지 (다른 설정은 보존)
    main_board_ids = set()
    
    for token in main_board_tokens:
        token_id = token['token_id']
        main_board_ids.add(token_id)
        
        # 새 토큰이거나 업데이트 필요
        if token_id not in monitoring_configs:
            parts = token_id.split('_', 1)
            if len(parts) == 2:
                exchange = parts[0]
                symbol = parts[1].replace('_', '/')
                
                monitoring_configs[token_id] = {
                    'exchange': exchange,
                    'symbol': symbol,
                    'started_at': token['posted_date'],
                    'status': 'active',
                    'description': f"{symbol} on {exchange} (Main Board - Penalty: {token['penalty']}/60)",
                    'penalty': token['penalty'],
                    'violation_rate_10d': token['violation_rate_10d'],
                    'is_chronic': token.get('is_chronic', False)
                }
        else:
            # 기존 토큰 업데이트
            monitoring_configs[token_id]['penalty'] = token['penalty']
            monitoring_configs[token_id]['violation_rate_10d'] = token['violation_rate_10d']
            monitoring_configs[token_id]['is_chronic'] = token.get('is_chronic', False)
            monitoring_configs[token_id]['description'] = f"{monitoring_configs[token_id]['symbol']} on {monitoring_configs[token_id]['exchange']} (Main Board - Penalty: {token['penalty']}/60)"
    
    # Main Board에서 제거된 토큰은 삭제
    tokens_to_remove = [
        tid for tid in monitoring_configs.keys()
        if tid not in main_board_ids and monitoring_configs[tid].get('description', '').find('Main Board') >= 0
    ]
    
    for token_id in tokens_to_remove:
        # 수동 추가된 토큰은 삭제하지 않음 (source='manual' 보호)
        if monitoring_configs[token_id].get('source') == 'manual':
            print(f"[PROTECTED] {token_id}: Manual addition - skipping auto-delete")
            continue
        
        del monitoring_configs[token_id]
        print(f"[REMOVED] {token_id}: Removed from Main Board monitoring")
    
    # 저장
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(monitoring_configs, f, indent=2, ensure_ascii=False)
    
    print(f"[SYNC] Main Board synchronized: {len(main_board_ids)} tokens")

# 설정 로드
def load_config():
    """스캐너 설정 로드"""
    # ✅ MIGRATION: Use FilePaths and ExchangeThresholds from core.config
    config_file = FilePaths.SCANNER_CONFIG
    if os.path.exists(config_file):
        return load_json(config_file)
    else:
        # 기본 설정 (거래소 기본 요구사항 - ExchangeThresholds 사용)
        default_config = {
            "exchanges": {
                "gateio": {"enabled": True, "spread_threshold": ExchangeThresholds.SPREAD_MAX_PERCENT, "spread_required": True, "depth_threshold": ExchangeThresholds.DEPTH_MIN_USD, "depth_required": True, "volume_threshold": ExchangeThresholds.VOLUME_MIN_USD, "volume_required": False, "scan_interval_hours": 4, "history_days": 2},
                "mexc": {"enabled": True, "spread_threshold": ExchangeThresholds.SPREAD_MAX_PERCENT, "spread_required": True, "depth_threshold": ExchangeThresholds.DEPTH_MIN_USD, "depth_required": True, "volume_threshold": ExchangeThresholds.VOLUME_MIN_USD, "volume_required": False, "scan_interval_hours": 4, "history_days": 2},
                "kucoin": {"enabled": True, "spread_threshold": ExchangeThresholds.SPREAD_MAX_PERCENT, "spread_required": True, "depth_threshold": ExchangeThresholds.DEPTH_MIN_USD, "depth_required": True, "volume_threshold": ExchangeThresholds.VOLUME_MIN_USD, "volume_required": False, "scan_interval_hours": 4, "history_days": 2},
                "bitget": {"enabled": True, "spread_threshold": ExchangeThresholds.SPREAD_MAX_PERCENT, "spread_required": True, "depth_threshold": ExchangeThresholds.DEPTH_MIN_USD, "depth_required": True, "volume_threshold": ExchangeThresholds.VOLUME_MIN_USD, "volume_required": False, "scan_interval_hours": 4, "history_days": 2}
            },
            "global": {"default_scan_interval_hours": 4, "default_history_days": 5}
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config

CONFIG = load_config()
EXCHANGES = [ex for ex, cfg in CONFIG['exchanges'].items() if cfg.get('enabled', True)]
EXCLUDE_WHITELIST = False  # Will be set by command-line argument


def load_whitelist():
    """화이트리스트 로드 (블루칩 전용)"""
    whitelist_file = "data/bluechip_whitelist.json"
    if os.path.exists(whitelist_file):
        try:
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"gateio": [], "mexc": [], "kucoin": [], "bitget": []}
    return {"gateio": [], "mexc": [], "kucoin": [], "bitget": []}


def load_api_keys():
    """거래소 API 키 로드 (Private API 사용)"""
    api_keys_file = "config/exchange_api_keys.json"
    if os.path.exists(api_keys_file):
        try:
            with open(api_keys_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_api_keys(api_keys_data):
    """API 키 사용 정보 저장 (로테이션 추적)"""
    api_keys_file = "config/exchange_api_keys.json"
    try:
        with open(api_keys_file, 'w', encoding='utf-8') as f:
            json.dump(api_keys_data, f, indent=2, ensure_ascii=False)
    except:
        pass


def get_next_api_key(exchange_id):
    """
    거래소별 다음 사용할 API 키 가져오기 (라운드 로빈 로테이션)
    - Active한 키만 선택
    - 만료되지 않은 키만 선택
    - 사용 횟수가 적은 순서로 선택
    """
    api_keys_data = load_api_keys()
    
    if exchange_id not in api_keys_data:
        return None
    
    exchange_data = api_keys_data[exchange_id]
    
    # 구 데이터 구조 지원 (단일 API)
    if "keys" not in exchange_data:
        # 단일 API 키 구조
        if exchange_data.get('apiKey') and exchange_data.get('secret'):
            return exchange_data
        return None
    
    # 복수 API 키 구조
    keys_list = exchange_data.get("keys", [])
    if not keys_list:
        return None
    
    # Active하고 만료되지 않은 키만 필터링
    now = datetime.now(timezone.utc)
    
    available_keys = []
    for key_data in keys_list:
        # Active 체크
        if not key_data.get("active", True):
            continue
        
        # 만료일 체크
        expires_at = key_data.get("expires_at")
        if expires_at:
            try:
                expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if now >= expiry_date:
                    # 만료된 키는 자동으로 비활성화
                    key_data["active"] = False
                    continue
            except:
                pass
        
        available_keys.append(key_data)
    
    if not available_keys:
        return None
    
    # 사용 횟수가 적은 순서로 정렬 (라운드 로빈)
    available_keys.sort(key=lambda x: x.get("usage_count", 0))
    
    # 가장 적게 사용된 키 선택
    selected_key = available_keys[0]
    
    # 사용 횟수 증가
    selected_key["usage_count"] = selected_key.get("usage_count", 0) + 1
    selected_key["last_used"] = datetime.now(timezone.utc).isoformat()
    
    # 변경 사항 저장
    save_api_keys(api_keys_data)
    
    return selected_key


def update_scan_status(status_data):
    """스캔 상태 파일 업데이트 (파일 잠금 방지)"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open('scan_status.json', 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
            return True
        except PermissionError:
            # 파일이 다른 프로세스에 의해 잠겨있음
            import time
            time.sleep(0.1)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[WARNING] Failed to update scan_status.json: {e}")
            break
    return False

def init_exchange(exchange_id, use_private_api=False):
    """
    거래소 인스턴스 생성
    
    Args:
        exchange_id: 거래소 ID
        use_private_api: Private API 사용 여부 (기본값: False = Public API 사용)
    """
    try:
        ex_class = getattr(ccxt, exchange_id)
        
        exchange_config = {
            'enableRateLimit': True,
            'timeout': 30000,  # 30초 타임아웃 (밀리초 단위)
            'options': {'defaultType': 'spot'}
        }
        
        # Private API 사용이 명시적으로 요청된 경우에만
        if use_private_api:
            selected_key = get_next_api_key(exchange_id)
            
            if selected_key:
                if selected_key.get('apiKey') and selected_key.get('secret'):
                    exchange_config['apiKey'] = selected_key['apiKey']
                    exchange_config['secret'] = selected_key['secret']
                    
                    # KuCoin은 password 필요
                    if exchange_id == 'kucoin' and selected_key.get('password'):
                        exchange_config['password'] = selected_key['password']
                    
                    # API 키 이름 표시 (복수 API인 경우)
                    key_name = selected_key.get('name', 'Private API')
                    masked_key = selected_key['apiKey'][:8] + "..."
                    print(f"   🔑 Using Private API: '{key_name}' ({masked_key}) - Rate Limit: 10x faster")
                else:
                    print(f"   ⚠️  Private API requested but no valid keys found - Using Public API")
            else:
                print(f"   ⚠️  Private API requested but no keys available - Using Public API")
        else:
            print(f"   🌐 Using Public API (CCXT default)")
        
        return ex_class(exchange_config)
    except Exception as e:
        print(f"[ERROR] {exchange_id} init failed: {e}")
        return None

def calc_depth_2pct(bids, asks, bid, ask):
    """±2% 유동성 계산"""
    if not bid or not ask or not bids or not asks:
        return 0.0
    
    mid = (bid + ask) / 2.0
    low = mid * 0.98
    high = mid * 1.02
    
    bid_liq = 0.0
    ask_liq = 0.0
    
    # Ticker bid가 orderbook에 없으면 추가
    ticker_bid_in_ob = any(abs(float(p) - bid) < 0.00000001 for p, a in bids)
    ticker_ask_in_ob = any(abs(float(p) - ask) < 0.00000001 for p, a in asks)
    
    for p, a in bids:
        p, a = float(p), float(a)
        if low <= p <= high:
            bid_liq += p * a
    
    for p, a in asks:
        p, a = float(p), float(a)
        if low <= p <= high:
            ask_liq += p * a
    
    # Fallback: ticker bid/ask 추가
    if low <= bid <= high and not ticker_bid_in_ob:
        est_vol = sum(float(a) for p, a in bids[:3]) / 3 if bids else 1000
        bid_liq += bid * est_vol
    
    if low <= ask <= high and not ticker_ask_in_ob:
        est_vol = sum(float(a) for p, a in asks[:3]) / 3 if asks else 1000
        ask_liq += ask * est_vol
    
    return bid_liq + ask_liq

def update_exchange_status(exchange_id, status, progress='0/0', progress_pct=0, found=0):
    """거래소별 스캔 상태 업데이트 (파일 잠금 방지)"""
    history_file = 'scan_history.json'
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # 기존 데이터 로드 (거래소 상태만 업데이트, 다른 데이터 유지)
            history = {}
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            history = json.loads(content)
                except json.JSONDecodeError:
                    print(f"[WARNING] {history_file} corrupted, creating new")
                    history = {}
            
            # 거래소 상태 업데이트
            history[exchange_id] = {
                'status': status,
                'progress': progress,
                'progress_pct': progress_pct,
                'found': found,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # 파일 저장
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            
            return True
            
        except PermissionError:
            # 파일이 다른 프로세스에 의해 잠겨있음
            import time
            time.sleep(0.1)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[WARNING] Failed to update exchange status for {exchange_id}: {e}")
            break
    
    return False

def _update_exchange_last_scan_time(exchange_id):
    """거래소별 마지막 스캔 시간 업데이트 (scanner_config.json)"""
    try:
        config_file = 'config/scanner_config.json'
        if not os.path.exists(config_file):
            return
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 거래소별 마지막 스캔 시간 저장
        if 'exchanges' in config and exchange_id in config['exchanges']:
            config['exchanges'][exchange_id]['last_scan_time'] = datetime.now(timezone.utc).isoformat()
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARNING] Failed to update last scan time for {exchange_id}: {e}")

def _remove_from_delisting_suspects(exchange_id, symbol):
    """
    스캔 성공한 토큰을 상폐 의심 목록에서 즉시 제거
    
    Args:
        exchange_id: 거래소 ID (예: 'gateio')
        symbol: 심볼 (예: 'BTC/USDT')
    """
    try:
        suspects_file = 'delisting_suspects.json'
        if not os.path.exists(suspects_file):
            return
        
        with open(suspects_file, 'r', encoding='utf-8') as f:
            suspects_data = json.load(f)
        
        suspects = suspects_data.get('suspects', [])
        
        # 해당 토큰 찾기
        token_id = f"{exchange_id}_{symbol.replace('/', '_').lower()}"
        
        # 제거 전 개수
        before_count = len(suspects)
        
        # 필터링 (해당 토큰 제외)
        suspects_data['suspects'] = [
            s for s in suspects 
            if not (s.get('token_id') == token_id or 
                   (s.get('exchange') == exchange_id and s.get('symbol') == symbol))
        ]
        
        # 제거된 경우에만 저장 및 로그
        if len(suspects_data['suspects']) < before_count:
            with open(suspects_file, 'w', encoding='utf-8') as f:
                json.dump(suspects_data, f, indent=2, ensure_ascii=False)
            # 조용히 제거 (스캔 로그가 너무 길어지지 않도록)
            
    except Exception as e:
        # 에러는 조용히 무시 (스캔 프로세스 방해 안함)
        pass


def _remove_from_assessment_zone(exchange_id, symbol):
    """
    정규 스캔에서 발견된 MEXC 토큰을 평가존 리스트에서 즉시 제거
    
    Args:
        exchange_id: 거래소 ID (예: 'mexc')
        symbol: 심볼 (예: 'BTC/USDT')
    """
    try:
        zone_file = 'assessment_zone_list.json'
        if not os.path.exists(zone_file):
            return
        
        with open(zone_file, 'r', encoding='utf-8') as f:
            zone_data = json.load(f)
        
        mexc_zone = zone_data.get('mexc', {})
        tokens = mexc_zone.get('tokens', [])
        
        # 해당 토큰 찾기
        token_id = f"{exchange_id}_{symbol.replace('/', '_').lower()}"
        
        # 제거 전 개수
        before_count = len(tokens)
        
        # 필터링 (해당 토큰 제외)
        mexc_zone['tokens'] = [
            t for t in tokens 
            if not (t.get('token_id') == token_id or t.get('symbol') == symbol)
        ]
        
        # 제거된 경우에만 저장 및 로그
        if len(mexc_zone['tokens']) < before_count:
            zone_data['mexc'] = mexc_zone
            with open(zone_file, 'w', encoding='utf-8') as f:
                json.dump(zone_data, f, indent=2, ensure_ascii=False)
            
            print(f"   [AUTO GRADUATED] {symbol}: Removed from Assessment Zone (found in regular scan)")
            
            # tokens_unified.json에서도 상태 변경
            from modules.token_manager import TokenManager
            tm = TokenManager()
            token = tm.get_token_by_id(token_id)
            if token and token.get('lifecycle', {}).get('status') == 'ASSESSMENT_ZONE':
                lifecycle = token.get('lifecycle', {})
                lifecycle['status'] = 'NORMAL'
                lifecycle['assessment_zone_exit'] = datetime.now(timezone.utc).isoformat()
                lifecycle['exit_reason'] = 'Auto graduated (found in regular scan)'
                tm.update_token(exchange_id, symbol, {'lifecycle': lifecycle}, source='auto_graduation')
            
    except Exception as e:
        # 에러는 조용히 무시 (스캔 프로세스 방해 안함)
        pass


def scan_exchange(exchange_id, use_private_api=False):
    """
    단일 거래소 스캔
    
    Args:
        exchange_id: 거래소 ID
        use_private_api: Private API 사용 여부 (기본값: False)
    """
    print(f"\nScanning {exchange_id.upper()}...")
    
    # 거래소별 설정 로드
    ex_config = CONFIG['exchanges'].get(exchange_id, {})
    spread_threshold = ex_config.get('spread_threshold', 2.0)
    spread_required = ex_config.get('spread_required', True)
    depth_threshold = ex_config.get('depth_threshold', 500.0)
    depth_required = ex_config.get('depth_required', True)
    volume_threshold = ex_config.get('volume_threshold', 10000.0)
    volume_required = ex_config.get('volume_required', False)
    
    # 위험 조건 표시 (우선순위 순서: Depth → Spread → Volume)
    filter_logic = ex_config.get('filter_logic', 'OR')
    risk_filters = []
    if depth_required:
        risk_filters.append(f"Depth<${depth_threshold}")
    if spread_required:
        risk_filters.append(f"Spread>{spread_threshold}%")
    if volume_required:
        risk_filters.append(f"Vol<${volume_threshold}")
    
    print(f"   Risk filters ({filter_logic}): {f' {filter_logic} '.join(risk_filters) if risk_filters else 'None'}")
    
    # 거래소 상태: 시작
    update_exchange_status(exchange_id, 'running', '0/0', 0, 0)
    
    ex = init_exchange(exchange_id, use_private_api=use_private_api)
    if not ex:
        update_exchange_status(exchange_id, 'failed', '0/0', 0, 0)
        return []
    
    results = []
    try:
        # Direct CCXT API call - simple and stable
        markets = ex.load_markets()
        
        # 현물만 필터링 (선물/스왑/옵션 제외)
        usdt_pairs = [
            symbol for symbol, market in markets.items()
            if '/USDT' in symbol
            and market.get('spot') == True
            and market.get('type') == 'spot'
        ]
        
        # 레버리지 토큰 제외 (3L, 3S, 5L, 5S, 2L, 2S, UP, DOWN 등)
        leverage_suffixes = ['3L/USDT', '3S/USDT', '5L/USDT', '5S/USDT', '2L/USDT', '2S/USDT', 
                            'UP/USDT', 'DOWN/USDT', 'BULL/USDT', 'BEAR/USDT']
        original_count = len(usdt_pairs)
        usdt_pairs = [s for s in usdt_pairs if not any(s.endswith(suffix) for suffix in leverage_suffixes)]
        leverage_excluded = original_count - len(usdt_pairs)
        if leverage_excluded > 0:
            print(f"   ⚠️ Excluded {leverage_excluded} leverage tokens ({len(usdt_pairs)} remaining)")
        
        # 화이트리스트 제외 (기본적으로 활성화)
        whitelist = load_whitelist()
        whitelisted_symbols = set(whitelist.get(exchange_id, []))
        original_count = len(usdt_pairs)
        usdt_pairs = [s for s in usdt_pairs if s not in whitelisted_symbols]
        excluded_count = original_count - len(usdt_pairs)
        if excluded_count > 0:
            print(f"   ⚪ Excluded {excluded_count} whitelisted tokens ({len(usdt_pairs)} remaining)")
        
        total_pairs = len(usdt_pairs)
        print(f"   Found {total_pairs} USDT spot pairs")
        print(f"   [{'='*50}] 0/{total_pairs}")
        
        for idx, symbol in enumerate(usdt_pairs, 1):
            # 진행률 표시바 업데이트 (2% 단위 또는 최소 50개마다)
            update_interval = max(50, total_pairs // 50)  # 최소 50개마다, 최대 2% 단위
            if idx % update_interval == 0 or idx == total_pairs:
                progress_pct = (idx / total_pairs) * 100
                filled = int(progress_pct / 2)  # 50칸 기준
                bar = '=' * filled + '>' + ' ' * (50 - filled - 1)
                print(f"\r   [{bar}] {idx}/{total_pairs} ({progress_pct:.1f}%) - Found: {len(results)}", end='', flush=True)
                
                # 전체 상태 파일 업데이트
                update_scan_status({
                    "status": "running",
                    "current_exchange": exchange_id,
                    "progress": f"{idx}/{total_pairs}",
                    "progress_pct": round(progress_pct, 1),
                    "found": len(results),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # 거래소별 상태 업데이트
                update_exchange_status(
                    exchange_id, 
                    'running', 
                    f"{idx}/{total_pairs}", 
                    round(progress_pct, 1), 
                    len(results)
                )
            

            try:
                # 🎯 허니문 체크 (관리자 전역 설정 기반)
                admin_honeymoon_manager = get_admin_honeymoon_manager()
                honeymoon_status = admin_honeymoon_manager.get_global_token_honeymoon_status(exchange_id, symbol)
                
                # 허니문이 종료된 토큰은 스캔 제외
                if honeymoon_status['status'] == 'honeymoon_ended':
                    print(f"\n   ⏭️ {symbol}: 허니문 종료 (상장 후 {honeymoon_status['days_since_listing']}일), 스캔 제외")
                    continue
                
                # 🚨 ST 태그 체크 (Special Treatment = 상폐 예고)
                market_info = markets[symbol]
                info = market_info.get('info', {})
                is_st_tagged = False
                st_reason = None
                
                # Gate.io: st_tag field
                if exchange_id == 'gateio' and info.get('st_tag') in [True, 'True', '1', 1]:
                    is_st_tagged = True
                    st_reason = "Gate.io ST Tagged (Delisting Risk)"
                
                # MEXC: st field (Assessment Zone에 포함)
                elif exchange_id == 'mexc' and info.get('st') in [True, 'True', '1', 1]:
                    is_st_tagged = True
                    st_reason = "MEXC ST Tagged (Assessment Zone)"
                
                # KuCoin: st field
                elif exchange_id == 'kucoin' and info.get('st') in [True, 'True', '1', 1]:
                    is_st_tagged = True
                    st_reason = "KuCoin ST Tagged (Delisting Risk)"
                
                # Bitget: Innovation Zone indicators (DISABLED - too many false positives)
                # elif exchange_id == 'bitget':
                #     buy_ratio = float(info.get('buyLimitPriceRatio', 0))
                #     status = info.get('status', 'online')
                #     symbol_name = info.get('symbolName', '')
                #     
                #     if buy_ratio > 0.02 or status == 'gray' or 'NEW' in symbol_name.upper():
                #         is_st_tagged = True
                #         reasons = []
                #         if buy_ratio > 0.02:
                #             reasons.append(f"High volatility ({buy_ratio*100:.0f}%)")
                #         if status == 'gray':
                #             reasons.append("Gray zone")
                #         if 'NEW' in symbol_name.upper():
                #             reasons.append("New listing")
                #         st_reason = f"Bitget Innovation Zone: {', '.join(reasons)}"
                
                # Ticker 조회 (타임아웃 처리 추가)
                try:
                    ticker = ex.fetch_ticker(symbol)
                    bid = float(ticker.get('bid') or 0)
                    ask = float(ticker.get('ask') or 0)
                    quote_volume = float(ticker.get('quoteVolume') or 0)
                    
                    if not bid or not ask:
                        continue
                        
                except ccxt.RequestTimeout:
                    print(f"   [TIMEOUT] {symbol} ticker timeout, skipping...")
                    time.sleep(2)
                    continue
                except ccxt.NetworkError:
                    print(f"   [NETWORK] {symbol} ticker network error, skipping...")
                    time.sleep(2)
                    continue
                except ccxt.ExchangeError as e:
                    error_msg = str(e).lower()
                    if 'not found' not in error_msg and 'invalid symbol' not in error_msg:
                        print(f"   [EXCHANGE ERROR] {symbol} ticker: {e}")
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    print(f"   [ERROR] {symbol} ticker error: {type(e).__name__}")
                    continue
                
                # 스프레드 계산 (정밀도 그대로 사용, % 표시만 소수점 2자리)
                spread_pct = round(((ask - bid) / bid * 100), 2) if bid else 0
                
                # 🚨 ST 태그가 있으면 필터 무시하고 바로 추가
                if is_st_tagged:
                    # Orderbook 조회 (depth 계산용)
                    if exchange_id == 'kucoin':
                        limit = 100
                    elif exchange_id == 'bitget':
                        limit = 100
                    elif exchange_id == 'gateio':
                        limit = 100
                    elif exchange_id == 'mexc':
                        limit = 200
                    else:
                        limit = 50
                    
                    try:
                        ob = ex.fetch_order_book(symbol, limit=limit)
                        depth_2pct = calc_depth_2pct(
                            ob.get('bids', []),
                            ob.get('asks', []),
                            bid,
                            ask
                        )
                    except:
                        depth_2pct = 0
                    
                    # ST 태그 토큰은 무조건 추가
                    results.append({
                        'exchange': exchange_id,
                        'symbol': symbol,
                        'spread_pct': round(spread_pct, 3),
                        'depth_2pct': round(depth_2pct, 2),
                        'quote_volume': round(quote_volume, 2),
                        'bid': bid,
                        'ask': ask,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'st_tagged': True,
                        'st_reason': st_reason,
                        'honeymoon_status': honeymoon_status  # 허니문 상태 추가
                    })
                    
                    print(f"\n   [ST TAG] {symbol}: {st_reason}")
                    time.sleep(0.1)
                    continue
                
                # 일반 필터 체크 (ST 태그가 없는 경우만)
                # OR 조건: 하나라도 위험하면 추가
                
                # Orderbook 조회 (항상 필요)
                if exchange_id == 'kucoin':
                    limit = 100  # KuCoin: 20 또는 100 (100이 더 정확)
                elif exchange_id == 'bitget':
                    limit = 100  # Bitget: 최대 150 (100 사용)
                elif exchange_id == 'gateio':
                    limit = 100  # Gate.io: 최대 100
                elif exchange_id == 'mexc':
                    limit = 200  # MEXC: 최대 200
                else:
                    limit = 50   # 기본값
                
                # Orderbook 조회 (타임아웃 처리)
                try:
                    ob = ex.fetch_order_book(symbol, limit=limit)
                    depth_2pct = calc_depth_2pct(
                        ob.get('bids', []),
                        ob.get('asks', []),
                        bid,
                        ask
                    )
                except ccxt.RateLimitExceeded:
                    # Rate Limit 에러: 긴 대기 후 재시도
                    wait_time = min(60, 10 * (1 + scanned // 50))
                    print(f"   [RATE LIMIT] {symbol}: Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                except ccxt.RequestTimeout:
                    print(f"   [TIMEOUT] {symbol} orderbook timeout, skipping...")
                    time.sleep(2)  # Cool down
                    continue
                except ccxt.NetworkError:
                    print(f"   [NETWORK] {symbol} network error, skipping...")
                    time.sleep(2)
                    continue
                except ccxt.ExchangeError as e:
                    # 거래소 특정 에러 조용히 처리
                    error_msg = str(e).lower()
                    if 'not found' not in error_msg and 'invalid symbol' not in error_msg:
                        print(f"   [EXCHANGE ERROR] {symbol}: {e}")
                    time.sleep(0.5)
                    continue
                
                # 위험 조건 체크 (AND/OR 로직)
                filter_logic = ex_config.get('filter_logic', 'OR')
                
                risk_checks = []
                risk_reasons = []
                
                # 1. 유동성 위험 (가장 중요)
                if depth_required:
                    depth_risk = depth_2pct < depth_threshold
                    risk_checks.append(depth_risk)
                    if depth_risk:
                        risk_reasons.append(f"Low depth: ${depth_2pct:.2f}")
                
                # 2. 스프레드 위험
                if spread_required:
                    spread_risk = spread_pct > spread_threshold
                    risk_checks.append(spread_risk)
                    if spread_risk:
                        risk_reasons.append(f"High spread: {spread_pct:.2f}%")
                
                # 3. 거래량 위험
                if volume_required:
                    volume_risk = quote_volume < volume_threshold
                    risk_checks.append(volume_risk)
                    if volume_risk:
                        risk_reasons.append(f"Low volume: ${quote_volume:.2f}")
                
                # 로직에 따라 판단
                if filter_logic == 'OR':
                    is_risky = any(risk_checks)  # 하나라도 위험하면
                else:  # AND
                    is_risky = all(risk_checks)  # 모두 위험해야
                
                # 📊 모든 토큰 데이터를 results에 추가 (평균 계산용)
                token_data = {
                    'exchange': exchange_id,
                    'symbol': symbol,
                    'spread_pct': round(spread_pct, 3),
                    'depth_2pct': round(depth_2pct, 2),
                    'quote_volume': round(quote_volume, 2),
                    'bid': bid,
                    'ask': ask,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'risk_reasons': risk_reasons,
                    'is_risky': is_risky,  # 위험 여부 플래그 추가
                    'honeymoon_status': honeymoon_status  # 허니문 상태 추가
                }
                
                results.append(token_data)
                
                # 🧹 스캔 성공한 토큰은 상폐 의심 목록에서 즉시 제거
                _remove_from_delisting_suspects(exchange_id, symbol)
                
                # 🎓 MEXC 평가존에서 발견된 토큰은 즉시 제거 (자동 졸업)
                if exchange_id == 'mexc':
                    _remove_from_assessment_zone(exchange_id, symbol)
                
                # 위험한 토큰만 화면에 출력
                if is_risky and risk_checks:
                    print(f"\n   [RISK] {symbol}: {' | '.join(risk_reasons)}")
                
                time.sleep(0.1)  # Rate limit
                
            except ccxt.RateLimitExceeded as e:
                # Rate Limit 에러: 대기 시간을 점진적으로 증가
                wait_time = min(60, 5 * (1 + scanned // 100))  # 최대 60초
                print(f"   [RATE LIMIT] {symbol}: Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            except ccxt.RequestTimeout as e:
                print(f"   [TIMEOUT] {symbol}: {e}")
                time.sleep(2)
                continue
            except ccxt.NetworkError as e:
                print(f"   [NETWORK] {symbol}: {e}")
                time.sleep(2)
                continue
            except ccxt.ExchangeError as e:
                # 거래소 특정 에러 (예: 심볼 없음, 일시적 서비스 중단)
                error_msg = str(e).lower()
                if 'not found' in error_msg or 'invalid symbol' in error_msg:
                    # 심볼 오류는 조용히 스킵
                    continue
                else:
                    print(f"   [EXCHANGE ERROR] {symbol}: {e}")
                    time.sleep(1)
                    continue
            except Exception as e:
                print(f"   [ERROR] {symbol}: {type(e).__name__} - {e}")
                continue
        
        risky_count = sum(1 for r in results if r.get('is_risky', False))
        print(f"\n   [OK] {exchange_id.upper()}: Scanned {len(results)} tokens, {risky_count} high-risk")
        
        # 거래소 스캔 완료 상태 업데이트
        update_exchange_status(exchange_id, 'completed', f"{total_pairs}/{total_pairs}", 100, len(results))
        
        # 거래소별 마지막 스캔 시간 즉시 업데이트
        _update_exchange_last_scan_time(exchange_id)
        
    except Exception as e:
        print(f"[ERROR] {exchange_id.upper()} scan failed: {e}")
        update_exchange_status(exchange_id, 'failed', '0/0', 0, 0)
    
    return results

def _save_raw_scan_to_history(all_results):
    """Raw 스캔 결과를 scan_history/ 디렉토리에 즉시 저장 (평균 계산 전)"""
    if not all_results:
        return

    # scan_history 디렉토리 생성
    history_dir = 'scan_history'
    os.makedirs(history_dir, exist_ok=True)

    # 현재 시간으로 파일명 생성 (예: 20251030_21.json)
    now = datetime.now(timezone.utc)
    filename = now.strftime('%Y%m%d_%H') + '.json'
    filepath = os.path.join(history_dir, filename)

    # Raw 스캔 결과를 히스토리 형식으로 변환
    history_data = {
        'timestamp': now.isoformat(),
        'scanner_type': 'raw',  # raw scan results임을 표시
        'tokens': []
    }

    for result in all_results:
        # Raw scan result에서 필요한 필드 추출
        exchange = result.get('exchange', '')
        symbol = result.get('symbol', '')

        if not exchange or not symbol:
            continue

        # 히스토리 형식으로 저장 (raw scan data)
        history_data['tokens'].append({
            'exchange': exchange,
            'symbol': symbol,
            'depth_2pct': result.get('depth_2pct', 0),
            'spread_pct': result.get('spread_pct', 0),
            'quote_volume': result.get('quote_volume', 0),
            'bid': result.get('bid', 0),
            'ask': result.get('ask', 0),
            'depth_threshold': result.get('depth_threshold', 500),
            'spread_threshold': result.get('spread_threshold', 2.0),
            'volume_threshold': result.get('volume_threshold', 10000),
            'is_risky': result.get('is_risky', False),
            'st_tagged': result.get('st_tagged', False)
        })

    # 파일 저장
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Raw scan history saved: {filename} ({len(history_data['tokens'])} tokens)")

        # latest.json도 업데이트
        latest_path = os.path.join(history_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving raw scan history: {e}")


def _save_scan_to_history(all_results):
    """스캔 결과를 scan_history/ 디렉토리에 저장"""
    if not all_results:
        return
    
    # scan_history 디렉토리 생성
    history_dir = 'scan_history'
    os.makedirs(history_dir, exist_ok=True)
    
    # 현재 시간으로 파일명 생성 (예: 20251017_09.json)
    now = datetime.now(timezone.utc)
    filename = now.strftime('%Y%m%d_%H') + '.json'
    filepath = os.path.join(history_dir, filename)
    
    # 스캔 결과를 히스토리 형식으로 변환 (평균 계산 후 호출됨)
    history_data = {
        'timestamp': now.isoformat(),
        'scanner_type': 'main',
        'tokens': []
    }
    
    for result in all_results:
        # 스캔 결과에서 직접 데이터 가져오기 (tokens_unified.json 업데이트 전)
        exchange = result.get('exchange', '')
        symbol = result.get('symbol', '')
        
        if not exchange or not symbol:
            continue
        
        # 히스토리 형식으로 저장 (평균 계산 완료된 데이터)
        history_data['tokens'].append({
            'exchange': exchange,
            'symbol': symbol,
            'depth_2pct': result.get('avg_depth_2pct', 0),  # 평균 depth
            'spread_pct': result.get('avg_spread_pct', 0),  # 평균 spread
            'quote_volume': result.get('avg_volume_24h', 0),  # 평균 volume
            'depth_threshold': 500,
            'spread_threshold': 2.0,
            'volume_threshold': 10000,
            'grade': result.get('grade', 'N/A'),
            'average_risk': result.get('average_risk', 0),
            'violation_rate': result.get('violation_rate', 0)
        })
    
    # 파일 저장
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Scan history saved: {filename}")
        
        # latest.json도 업데이트
        latest_path = os.path.join(history_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)

        # 🆕 ShardManager를 사용하여 regular_scan shard에 저장
        print(f"\n[SHARD] Saving to regular_scan shard...")
        try:
            from core.shard_manager import get_shard_manager

            shard_manager = get_shard_manager()

            # all_results를 shard 형식으로 변환
            shard_data = {}
            for result in all_results:
                exchange = result.get('exchange', '')
                symbol = result.get('symbol', '')
                if not exchange or not symbol:
                    continue

                token_id = f"{exchange}_{symbol}".replace('/', '_').lower()
                shard_data[token_id] = {
                    'token_id': token_id,
                    'exchange': exchange,
                    'symbol': symbol,
                    'scan_aggregate': {
                        'avg_spread_pct': result.get('avg_spread_pct', 0),
                        'avg_depth_2pct': result.get('avg_depth_2pct', 0),
                        'avg_volume_24h': result.get('avg_volume_24h', 0),
                        'grade': result.get('grade', 'N/A'),
                        'average_risk': result.get('average_risk', 0),
                        'violation_rate': result.get('violation_rate', 0)
                    }
                }

            # Bulk update
            shard_manager.bulk_update_regular_scan(shard_data)
            print(f"[SHARD] OK Saved {len(shard_data)} tokens to regular_scan shard")

            # 🆕 Merger 트리거: unified DB 업데이트
            print(f"[MERGER] Triggering shard merge...")
            from shard_merger import merge_shards
            if merge_shards():
                print(f"[MERGER] OK Merge completed - unified DB updated")
            else:
                print(f"[MERGER] Merge skipped or failed")

        except Exception as e:
            print(f"[SHARD] ERROR: Failed to save to shard: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Error saving scan history: {e}")


def run_batch_scan(selected_exchanges=None, use_private_api=False):
    """
    배치 스캔 실행 (토큰 생명주기 통합)
    
    Args:
        selected_exchanges: 스캔할 거래소 리스트 (예: ['gateio', 'mexc'])
                          None이면 모든 활성화된 거래소 스캔
        use_private_api: Private API 사용 여부 (기본값: False = Public API)
    """
    # 토큰 생명주기 관리자 초기화
    lifecycle = TokenLifecycle()
    
    # 스캔 시작 시 상태 초기화
    update_scan_status({
        "status": "running",
        "current_exchange": "initializing",
        "progress": "0/0",
        "progress_pct": 0,
        "found": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    print(f"\n{'='*60}")
    print(f"Starting Batch Scan - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}")
    
    all_results = []
    tracked_tokens = []  # 추적 중인 토큰 목록
    
    # 스캔할 거래소 결정
    if selected_exchanges:
        exchanges_to_scan = [ex for ex in selected_exchanges if ex in EXCHANGES]
        print(f"[SELECTIVE SCAN] Scanning selected exchanges: {', '.join([ex.upper() for ex in exchanges_to_scan])}")
    else:
        exchanges_to_scan = EXCHANGES
        print(f"[FULL SCAN] Scanning all enabled exchanges")
    
    # 환경별 스캔 모드 결정
    deployment_config = {}
    if os.path.exists('deployment_config.json'):
        try:
            with open('deployment_config.json', 'r', encoding='utf-8') as f:
                deployment_config = json.load(f)
        except:
            pass
    
    environment = deployment_config.get('environment', 'development')
    scan_mode = deployment_config.get('scanning', {}).get(environment, {}).get('mode', 'sequential')
    
    api_mode = "Private API (10x faster)" if use_private_api else "Public API (CCXT default)"
    print(f"\n[SCAN MODE] {scan_mode.upper()} ({environment} environment)")
    print(f"[API MODE] Using {api_mode}")
    
    if scan_mode == 'parallel':
        # 🔄 프로덕션: 병렬 스캔 (모든 거래소 동시)
        print(f"[PARALLEL SCAN] Starting {len(exchanges_to_scan)} exchanges in parallel...")
        all_results = _run_parallel_scan(exchanges_to_scan, use_private_api)
    else:
        # 🔄 개발: 순차 스캔 (거래소별 스캔 → 계산 → 업데이트)
        print(f"[SEQUENTIAL SCAN] Scanning {len(exchanges_to_scan)} exchanges one by one...")
        all_results = _run_sequential_scan(exchanges_to_scan, use_private_api)
    
    # 스캔 완료 (순차 모드는 이미 업데이트 완료, 병렬 모드는 아래에서 계산)
    if scan_mode == 'parallel':
        # 병렬 모드: 모든 스캔 완료 후 한번에 계산
        print(f"\n{'='*60}")
        print(f"All exchanges scanned. Starting average calculation...")
        print(f"{'='*60}")
    
    # 스캔 완료 후 상태 업데이트
    update_scan_status({
        "status": "completed",
        "total_found": len(all_results),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    # scheduler.last_scan_time 업데이트
    try:
        config_file = 'config/scanner_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if 'scheduler' not in config:
                config['scheduler'] = {}

            config['scheduler']['last_scan_time'] = datetime.now(timezone.utc).isoformat()

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"[INFO] Updated scheduler.last_scan_time in scanner_config.json")
    except Exception as e:
        print(f"[WARNING] Failed to update scheduler.last_scan_time: {e}")

    # Note: scan_history는 평균 계산 후 저장됨 (calculate_2day_average_by_exchange에서)
    
    print(f"\n{'='*60}")
    print(f"Batch Scan Completed")
    print(f"  Total tokens found: {len(all_results)}")
    print(f"{'='*60}\n")


def _run_sequential_scan(exchanges_to_scan, use_private_api=False):
    """개발 환경: 거래소별 순차 스캔 → 계산 → 업데이트"""
    all_results = []

    for idx, exchange_id in enumerate(exchanges_to_scan, 1):
        print(f"\n[{idx}/{len(exchanges_to_scan)}] Processing {exchange_id.upper()}")

        # Step 1: 스캔
        results = scan_exchange(exchange_id, use_private_api)
        all_results.extend(results)

        # 📝 Raw scan results를 scan_history에 저장 (평균 계산 전)
        _save_raw_scan_to_history(all_results)

        # Step 2: 평균 계산
        update_scan_status({
            "status": "calculating",
            "current_exchange": exchange_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        calculate_2day_average_by_exchange(target_exchange=exchange_id)

        print(f"{exchange_id.upper()} completed: {len(results)} found")

    return all_results


def _run_parallel_scan(exchanges_to_scan, use_private_api=False):
    """프로덕션 환경: 병렬 스캔"""
    all_results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(scan_exchange, ex, use_private_api): ex for ex in exchanges_to_scan}
        for future in as_completed(futures):
            exchange_id = futures[future]
            try:
                results = future.result(timeout=600)
                all_results.extend(results)
            except Exception as e:
                print(f"[ERROR] {exchange_id}: {e}")

    # 📝 Raw scan results를 즉시 scan_history에 저장 (평균 계산 전)
    _save_raw_scan_to_history(all_results)

    # 평균 계산 (scan_history에서 데이터 읽어서 평균 계산 후 다시 저장)
    calculate_2day_average_by_exchange()
    return all_results


def calculate_2day_average_by_exchange(target_exchange=None):
    """과거 N일간 평균 계산 (거래소별 순차 처리 + 자동 승인)"""
    scan_dir = 'scan_history'
    if not os.path.exists(scan_dir):
        return []
    
    # 거래소별 최대 history_days 찾기 (global 설정 사용)
    default_history_days = CONFIG.get('global', {}).get('default_history_days', 5)
    max_history_days = max(
        CONFIG['exchanges'][ex].get('history_days', default_history_days) 
        for ex in EXCHANGES
    )
    
    # 과거 N일 파일 찾기
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_history_days)
    
    token_data = {}  # {exchange_symbol: [depth values]}
    latest_scan_time = {}  # {exchange_symbol: latest_scan_timestamp}
    st_tag_by_scan = {}  # {exchange_symbol: {timestamp: st_tagged}}
    
    # 파일 목록을 시간순으로 정렬
    scan_files = []
    for filename in os.listdir(scan_dir):
        if not filename.endswith('.json') or filename == 'latest.json':
            continue
        try:
            date_str = filename.replace('.json', '')
            file_time = datetime.strptime(date_str, '%Y%m%d_%H').replace(tzinfo=timezone.utc)
            if file_time >= cutoff:
                scan_files.append((file_time, filename))
        except:
            continue
    
    # 시간순 정렬 (오래된 것부터)
    scan_files.sort(key=lambda x: x[0])
    
    # 가장 최신 스캔 시간 찾기
    global_latest_scan = max(scan_files, key=lambda x: x[0])[0] if scan_files else None
    
    for file_time, filename in scan_files:
        try:
            
            # 파일 로드
            filepath = os.path.join(scan_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 토큰별 데이터 수집
            for token in data.get('tokens', []):
                # target_exchange 필터링
                if target_exchange and token['exchange'] != target_exchange:
                    continue
                    
                key = f"{token['exchange']}_{token['symbol']}"
                
                # 필드 누락 체크
                spread_pct = token.get('spread_pct')
                depth_2pct = token.get('depth_2pct')
                
                if spread_pct is None or depth_2pct is None:
                    # 데이터 누락, skip
                    continue
                
                if key not in token_data:
                    token_data[key] = {
                        'exchange': token['exchange'],
                        'symbol': token['symbol'],
                        'spread_values': [],
                        'depth_values': [],
                        'volume_values': [],  # 🔧 Volume 데이터 수집
                        'is_st_tagged': False,  # 기본값 False
                        'latest_bid': 0,
                        'latest_ask': 0
                    }
                
                token_data[key]['spread_values'].append(spread_pct)
                token_data[key]['depth_values'].append(depth_2pct)
                token_data[key]['volume_values'].append(token.get('quote_volume', 0))  # 🔧 Volume 저장
                
                # 최신 스캔 시간 추적 및 현재가 업데이트
                if key not in latest_scan_time or file_time > latest_scan_time[key]:
                    latest_scan_time[key] = file_time
                    token_data[key]['latest_bid'] = token.get('bid', 0)
                    token_data[key]['latest_ask'] = token.get('ask', 0)
                
                # ST Tag 정보 저장 (스캔 시간별로)
                if key not in st_tag_by_scan:
                    st_tag_by_scan[key] = {}
                st_tag_by_scan[key][file_time] = token.get('st_tagged', False)
        
        except Exception:
            continue
    
    # 거래소별로 토큰 그룹화
    tokens_by_exchange = {}
    for key, data in token_data.items():
        exchange = data['exchange']
        if exchange not in tokens_by_exchange:
            tokens_by_exchange[exchange] = []
        tokens_by_exchange[exchange].append((key, data))
    
    # 평균 계산 (거래소별로 순차 처리 + 자동 승인)
    all_averaged_tokens = []
    total_tokens = len(token_data)
    processed_count = 0
    
    print(f"[INFO] Processing {total_tokens} tokens across {len(tokens_by_exchange)} exchanges...")
    print("=" * 60)
    
    # 진행 상황 파일 생성
    progress_file = 'average_calculation_progress.json'
    
    for exchange in sorted(tokens_by_exchange.keys()):
        exchange_tokens = tokens_by_exchange[exchange]
        exchange_total = len(exchange_tokens)
        exchange_averaged = []
        
        print(f"\n🏦 {exchange.upper()}: Processing {exchange_total} tokens...")
        
        for idx, (key, data) in enumerate(exchange_tokens, 1):
            processed_count += 1
            
            # 거래소별 진행률 표시 (10개마다 또는 마지막)
            if idx % 10 == 0 or idx == exchange_total:
                progress_pct = processed_count * 100 // total_tokens
                print(f"   {exchange}: {idx}/{exchange_total} ({idx*100//exchange_total}%) | Total: {processed_count}/{total_tokens} ({progress_pct}%)")
                
                # 진행 상황을 파일에 저장 (Admin Dashboard에서 읽을 수 있도록)
                try:
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'status': 'calculating',
                            'current_exchange': exchange,
                            'exchange_progress': f"{idx}/{exchange_total}",
                            'total_progress': f"{processed_count}/{total_tokens}",
                            'progress_pct': progress_pct,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }, f, indent=2)
                except:
                    pass
            
            # 🔍 데이터 유효성 검사
            if not data['spread_values'] or not data['depth_values']:
                # 빈 데이터, skip
                print(f"⚠️ Warning: Empty data for {data['exchange']}_{data['symbol']}, skipping...")
                continue
            
            if len(data['spread_values']) != len(data['depth_values']):
                # 데이터 불일치, skip
                print(f"⚠️ Warning: Data mismatch for {data['exchange']}_{data['symbol']}, skipping...")
                continue
            
            avg_spread = sum(data['spread_values']) / len(data['spread_values'])
            avg_depth = sum(data['depth_values']) / len(data['depth_values'])
            avg_volume = sum(data.get('volume_values', [0])) / len(data.get('volume_values', [1])) if data.get('volume_values') else 0  # 🔧 평균 Volume 계산
            
            # ST Tag는 최신 스캔 결과만 사용
            # 최신 글로벌 스캔에 토큰이 없으면 ST Tag는 False (더 이상 위험하지 않음)
            is_st_tagged = False
            if key in latest_scan_time and key in st_tag_by_scan:
                latest_time = latest_scan_time[key]
                # 토큰의 최신 스캔이 글로벌 최신 스캔과 같은 경우에만 ST Tag 적용
                if global_latest_scan and latest_time == global_latest_scan:
                    is_st_tagged = st_tag_by_scan[key].get(latest_time, False)
                # 그렇지 않으면 최신 스캔에서 제외된 것이므로 ST Tag = False
            
            # 거래소별 임계값 가져오기
            exchange_config = CONFIG['exchanges'].get(data['exchange'], {})
            depth_threshold = exchange_config.get('depth_threshold', 500)
            spread_threshold = exchange_config.get('spread_threshold', 2.0)
            volume_threshold = exchange_config.get('volume_threshold', 10000)
            
            # 🔧 scan_history 데이터로 직접 violation_rate 계산
            violations_count = 0
            risk_scores = []
            
            for i in range(len(data['depth_values'])):
                depth_val = data['depth_values'][i]
                spread_val = data['spread_values'][i]
                volume_val = data.get('volume_values', [])[i] if i < len(data.get('volume_values', [])) else 0  # 🔧 Volume 읽기
                
                # 각 스냅샷의 리스크 점수 계산
                snapshot = {
                    'depth': depth_val,
                    'spread': spread_val,  # 이미 % 단위 (calculate_hourly_risk_score에서 처리)
                    'volume': volume_val  # 🔧 실제 Volume 데이터 사용
                }
                
                risk_t = calculate_hourly_risk_score(snapshot, exchange_config)
                risk_scores.append(risk_t)
                
                # 위반 여부 체크: risk_t 기반 (통합 리스크 점수)
                # risk_t > 0.30 (30%) 이상이면 위반으로 간주
                # - Grade C 경계선 (average_risk 0.30)을 기준으로 사용
                # - 순간적으로 C grade 이하의 위험도를 보이면 위반
                if risk_t > 0.30:
                    violations_count += 1
            
            # 평균 리스크 및 위반율 계산
            average_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
            violation_rate = violations_count / len(data['depth_values']) if data['depth_values'] else 0
            
            # 🚨 디버깅: 0% 문제 확인 (디버그 출력 비활성화 - 성능 개선)
            # if violation_rate == 0 and average_risk == 0:
            #     print(f"\n⚠️ Debug: {data['exchange']}_{data['symbol']}")
            #     print(f"   avg_depth={avg_depth:.2f}, avg_spread={avg_spread:.2f}%, avg_volume=${avg_volume:,.2f}")
            #     print(f"   depth_threshold={depth_threshold}, spread_threshold={spread_threshold}%, volume_threshold=${volume_threshold:,.2f}")
            #     print(f"   depth_required={exchange_config.get('depth_required', 'N/A')}")
            #     print(f"   spread_required={exchange_config.get('spread_required', 'N/A')}")
            #     print(f"   volume_required={exchange_config.get('volume_required', 'N/A')}")
            #     print(f"   violations={violations_count}/{len(data['depth_values'])}")
            #     print(f"   sample values: depth={data['depth_values'][:3]}, spread={data['spread_values'][:3]}, volume={data['volume_values'][:3]}")
            #     print(f"   risk_scores={risk_scores[:3]}")
            #     
            #     # 수동 체크
            #     for i in range(min(3, len(data['depth_values']))):
            #         d = data['depth_values'][i]
            #         s = data['spread_values'][i]
            #         print(f"   Sample {i+1}: depth={d} < {depth_threshold}? {d < depth_threshold}, spread={s} > {spread_threshold}? {s > spread_threshold}")
            
            # Grade 계산 (새로 계산된 값 사용)
            risk_analysis = {
                'average_risk': average_risk,
                'violation_rate': violation_rate,
                'sample_count': len(data['depth_values'])
            }
            
            # ST Tag 정보를 Grade 계산에 반영
            grade = classify_risk_grade(
                risk_analysis['average_risk'], 
                risk_analysis['violation_rate'],
                is_st_tagged=is_st_tagged
            )
            
            # ✅ 모든 등급 토큰 저장 (수동 승인 절차 없음)
            # ST 태그와 등급에 관계없이 모든 토큰을 저장하고
            # lifecycle 관리에서 메인보드 진입/퇴출 처리
            
            token_info = {
                'exchange': data['exchange'],
                'symbol': data['symbol'],
                'avg_spread_pct': round(avg_spread, 3),
                'avg_depth_2pct': round(avg_depth, 2),
                'avg_volume_24h': round(avg_volume, 2),  # 🔧 평균 Volume 추가
                'sample_count': len(data['depth_values']),
                'data_status': 'partial' if len(data['depth_values']) < 12 else 'full',
                'st_tagged': is_st_tagged,  # ST Tag 정보 포함
                # 새로운 Grade 시스템 추가
                'average_risk': round(risk_analysis['average_risk'], 3),
                'violation_rate': round(risk_analysis['violation_rate'], 3),
                'grade': grade,
                # 현재가 정보 (X-CAP 계산용)
                'bid': data.get('latest_bid', 0),
                'ask': data.get('latest_ask', 0),
                # 마지막 스캔 시간 추가
                'last_scanned': datetime.now(timezone.utc).isoformat()
            }
            
            exchange_averaged.append(token_info)
            all_averaged_tokens.append(token_info)
        
        # 거래소별 통계 출력 (approved 필드 제거됨)
        
        grade_counts = {}
        for t in exchange_averaged:
            g = t['grade']
            grade_counts[g] = grade_counts.get(g, 0) + 1
        
        print(f"   ✅ {exchange.upper()} completed: {exchange_total} tokens processed")
        print(f"      └─ Grades: {', '.join([f'{g}={count}' for g, count in sorted(grade_counts.items())])}")
    
    print("\n" + "=" * 60)
    print(f"✅ All exchanges completed! Total: {total_tokens} tokens processed")
    
    # Grade 우선 정렬 (F → D → C → B → A), 같은 Grade 내에서는 ±2% 뎁스 오름차순
    grade_order = {'F': 0, 'D': 1, 'C': 2, 'B': 3, 'A': 4, 'N/A': 5}
    all_averaged_tokens.sort(key=lambda x: (grade_order.get(x['grade'], 5), x['avg_depth_2pct']))
    
    # 전체 통계 출력 (approved 필드 제거됨)
    
    print("\n[INFO] Summary:")
    print(f"   Total tokens: {len(all_averaged_tokens)}")
    
    # V2: tokens_unified.json만 사용 (high_risk_tokens.json 저장 제거)
    print(f"\n💾 Data saved to tokens_unified.json via TokenManager")
    
    # 📝 평균 계산된 데이터를 scan_history에 저장
    _save_scan_to_history(all_averaged_tokens)
    
    # 🔄 아카이브 상태 토큰 중 Grade D/F 재진입 체크
    lifecycle = TokenLifecycle()
    lifecycle.check_archived_tokens_for_reentry(all_averaged_tokens)

    # 🔄 메인보드 토큰 중 Grade A/B/C 개선 체크 (자동 ARCHIVED 전환)
    print(f"\n🔍 Checking MAIN_BOARD tokens for improvement...")
    tm_temp = TokenManager()
    all_tokens_temp = tm_temp._load_db()
    archived_count = 0
    for token_id, token in all_tokens_temp.items():
        status = token.get('lifecycle', {}).get('status')
        grade = token.get('scan_aggregate', {}).get('grade', 'N/A')
        if status == 'MAIN_BOARD' and grade in ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-']:
            all_tokens_temp[token_id]['lifecycle']['status'] = 'ARCHIVED'
            all_tokens_temp[token_id]['lifecycle']['archived_at'] = datetime.now(timezone.utc).isoformat()
            archived_count += 1
    if archived_count > 0:
        tm_temp._save_db(all_tokens_temp)
        print(f"   ✅ Archived {archived_count} improved tokens (Grade A/B/C)")

        # monitoring_configs.json도 업데이트
        try:
            with open('monitoring_configs.json', 'r', encoding='utf-8') as f:
                monitoring_configs = json.load(f)

            removed_count = 0
            tokens_to_remove = [tid for tid in monitoring_configs.keys()
                              if tid in all_tokens_temp and
                              all_tokens_temp[tid].get('lifecycle', {}).get('status') == 'ARCHIVED']

            for token_id in tokens_to_remove:
                del monitoring_configs[token_id]
                removed_count += 1

            with open('monitoring_configs.json', 'w', encoding='utf-8') as f:
                json.dump(monitoring_configs, f, indent=2, ensure_ascii=False)

            print(f"   ✅ Removed {removed_count} ARCHIVED tokens from monitoring")
        except Exception as e:
            print(f"   ⚠️ Could not update monitoring_configs: {e}")

    # 🚀 모든 토큰을 tokens_unified.json에 저장 (근본적으로 재구성)
    from batch_scanner_refactored_section import save_averaged_tokens_to_db

    result = save_averaged_tokens_to_db(all_averaged_tokens)

    updated_count = result['updated_count']
    saved_count = 0  # 평균 계산에서는 신규 생성 없음
    main_board_count = result['main_board_entries']
    
    # 📊 scan_history에 계산된 grade 업데이트
    print("\n📊 Updating scan_history with calculated grades...")
    try:
        from update_scan_history_with_grades import update_current_scan_with_grades
        update_current_scan_with_grades(all_averaged_tokens)
    except Exception as e:
        print(f"   ⚠️ Could not update scan history with grades: {e}")
    
    # 🎯 Grade Info Cache 업데이트
    print("\n🎯 Building Grade Info Cache...")
    try:
        from grade_info_manager import GradeInfoManager
        grade_manager = GradeInfoManager()
        tm = TokenManager()

        # 모든 토큰에 대해 grade_info 생성
        all_tokens = tm._load_db()
        updated_cache_count = 0
        
        failed_tokens = []
        for token in all_averaged_tokens:
            exchange = token['exchange']
            symbol = token['symbol']
            token_id = f"{exchange}_{symbol.replace('/', '_')}".lower()

            if token_id not in all_tokens:
                continue

            try:
                # 순간 데이터 준비
                instant_data = {
                    'spread_pct': token.get('avg_spread_pct', 0),
                    'depth_2pct': token.get('avg_depth_2pct', 0),
                    'avg_volume_24h': token.get('avg_volume_24h', 0)
                }

                # grade_info 생성
                grade_info = grade_manager.build_grade_info(exchange, symbol, instant_data)

                # tokens_unified.json 업데이트
                all_tokens[token_id]['grade_info'] = grade_info
                updated_cache_count += 1

            except Exception as e:
                # 개별 토큰 처리 실패 시 로깅하고 계속 진행
                failed_tokens.append(f"{exchange}_{symbol}")
                print(f"   ⚠️ Failed to build grade_info for {exchange} {symbol}: {e}")
                # 다음 정규 스캔에서 재시도되므로 continue
                continue
        
        # 저장
        tm._save_db(all_tokens)
        print(f"   ✅ Updated grade_info for {updated_cache_count} tokens")
        if failed_tokens:
            print(f"   ⚠️ Failed tokens ({len(failed_tokens)}): Will retry in next scan")
            # 관리자 체크용: 처음 10개만 출력
            for token in failed_tokens[:10]:
                print(f"      - {token}")
            if len(failed_tokens) > 10:
                print(f"      ... and {len(failed_tokens) - 10} more")

    except Exception as e:
        print(f"   ⚠️ Could not update grade cache: {e}")
        import traceback
        traceback.print_exc()
    
    # 진행 상황 파일 삭제 (완료)
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except:
        pass
    
    # 🧹 스캔 완료 후 상폐 의심 목록 자동 정리
    print("\n🧹 Cleaning delisting suspects list...")
    try:
        import subprocess
        result = subprocess.run(['python', 'clean_delisting_suspects.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # 결과에서 "Removed: X" 라인 찾기
            for line in result.stdout.split('\n'):
                if 'Removed:' in line or 'Kept:' in line or 'remaining' in line:
                    print(f"   {line.strip()}")
        else:
            print(f"   ⚠️ Warning: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️ Could not clean delisting suspects: {e}")
    
    # 🎓 평가존 졸업 체크 (정규 스캔 데이터로 자동 판별)
    print("\n🎓 Checking MEXC Assessment Zone exits...")
    try:
        from detect_missing_tokens import check_assessment_zone_exits

        # tokens_unified.json 다시 로드 (최신 상태)
        tm = TokenManager()
        all_tokens = tm._load_db()
        exited_tokens = check_assessment_zone_exits(all_tokens)
        
        if exited_tokens:
            print(f"   ✅ Processed {len(exited_tokens)} Assessment Zone exits")
        else:
            print(f"   ℹ️ No Assessment Zone exits detected")
    except Exception as e:
        print(f"   ⚠️ Could not check Assessment Zone exits: {e}")

    # 📊 크리티컬 존 계산 (10일 기준)
    print("\n📊 Calculating Critical Zone (10+ days)...")
    print("="*60)
    try:
        from calculate_critical_zone import calculate_critical_zone
        critical_tokens = calculate_critical_zone()
        print(f"   ✅ Critical Zone calculated: {len(critical_tokens)} tokens")
    except Exception as e:
        print(f"   ⚠️ Could not calculate Critical Zone: {e}")
        import traceback
        traceback.print_exc()

    # 📅 최근 이벤트 생성 (1주일 내)
    print("\n📅 Generating Recent Events (last 7 days)...")
    print("="*60)
    try:
        from generate_recent_events import generate_recent_events
        events = generate_recent_events()
        print(f"   ✅ Recent events generated: {len(events)} events")
    except Exception as e:
        print(f"   ⚠️ Could not generate recent events: {e}")
        import traceback
        traceback.print_exc()

    # 🧹 오래된 데이터 자동 정리
    print("\n🧹 Cleaning up old data...")
    try:
        import subprocess
        result = subprocess.run(['python', 'cleanup_old_data.py'], 
                              capture_output=True, text=True, timeout=60,
                              encoding='utf-8', errors='replace')
        if result.returncode == 0:
            # 결과 출력
            for line in result.stdout.split('\n'):
                if 'Deleted' in line or 'freed' in line or 'Cleaning' in line:
                    print(f"   {line.strip()}")
        else:
            print(f"   ⚠️ Cleanup warning: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️ Could not run cleanup: {e}")
    
    return all_averaged_tokens


def calculate_2day_average():
    """과거 N일간 평균 계산 (기존 함수 - 하위 호환성)"""
    return calculate_2day_average_by_exchange()

if __name__ == '__main__':
    # 🔒 Process Lock: 중복 실행 방지
    LOCK_FILE = '.batch_scanner.lock'

    if os.path.exists(LOCK_FILE):
        # Lock 파일 생성 시간 확인
        lock_age = time.time() - os.path.getmtime(LOCK_FILE)
        if lock_age < 3600:  # 1시간 이내
            print(f"❌ Another batch_scanner instance is already running!")
            print(f"   Lock file: {LOCK_FILE} (age: {lock_age:.0f}s)")
            print(f"   If this is a stale lock, delete the file manually.")
            sys.exit(1)
        else:
            # 1시간 이상 된 lock은 stale로 간주
            print(f"⚠️  Removing stale lock file (age: {lock_age:.0f}s)")
            os.remove(LOCK_FILE)

    # Lock 파일 생성
    with open(LOCK_FILE, 'w') as f:
        f.write(f"PID: {os.getpid()}\nStarted: {datetime.now()}\n")

    try:
        # 단일 실행
        import sys
        import argparse

        parser = argparse.ArgumentParser(description='Night Watch Batch Scanner')
        parser.add_argument('--exchanges', nargs='+',
                           choices=['gateio', 'mexc', 'kucoin', 'bitget'],
                           help='Select specific exchanges to scan (default: all)')
        parser.add_argument('--exclude-whitelist', action='store_true',
                           help='Exclude whitelisted tokens from scan')
        parser.add_argument('--use-private-api', action='store_true',
                           help='Use Private API keys for faster rate limits (default: Public API)')
        parser.add_argument('--calculate-average', action='store_true',
                           help='Calculate averages and update Main Board (without scanning)')

        args = parser.parse_args()

        # 화이트리스트 제외 플래그 설정
        EXCLUDE_WHITELIST = args.exclude_whitelist

        if EXCLUDE_WHITELIST:
            whitelist = load_whitelist()
            total_whitelisted = sum(len(whitelist.get(ex, [])) for ex in (args.exchanges or EXCHANGES))
            print(f"\n⚪ Whitelist exclusion enabled: {total_whitelisted} tokens will be skipped")

        # Private API 사용 여부
        use_private_api = args.use_private_api

        # --calculate-average 옵션: 평균 계산만 실행
        if args.calculate_average:
            print("\n" + "="*60)
            print("Running Average Calculation & Main Board Update")
            print("="*60 + "\n")
            calculate_2day_average_by_exchange(target_exchange=None)
        else:
            # 선택된 거래소로 스캔 실행 (평균 계산 자동 포함)
            run_batch_scan(selected_exchanges=args.exchanges, use_private_api=use_private_api)

    finally:
        # Lock 파일 삭제
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            print(f"\n🔓 Released lock: {LOCK_FILE}")

