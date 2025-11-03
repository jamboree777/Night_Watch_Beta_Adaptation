"""
NightWatch Configuration
ONE SOURCE OF TRUTH - 모든 설정과 상수

⚠️ 이 파일의 값들은 시스템 전체에서 사용됩니다.
   변경 시 충분한 테스트 후 적용하세요.
"""

from enum import Enum
from typing import Dict


# ========================================
# 파일 경로 (File Paths)
# ========================================

class FilePaths:
    """모든 파일 경로를 한 곳에서 관리"""

    # Main data files
    TOKENS_UNIFIED = "data/unified/tokens_unified.json"
    SCANNER_CONFIG = "config/scanner_config.json"

    # Config files
    HONEYMOON_CONFIG = "honeymoon_config.json"
    MONITORING_CONFIG = "monitoring_config.json"  # 향후 제거 예정
    SUSPENDED_TOKENS = "suspended_tokens.json"

    # History directories
    SCAN_HISTORY_DIR = "scan_history"
    GRADE_HISTORY_DIR = "grade_history"

    # Backup directories
    BACKUP_DIR = "backups"
    TEMP_DIR = "temp"


# ========================================
# 거래소 기본 요구사항 (Exchange Requirements)
# ========================================

class ExchangeThresholds:
    """
    거래소의 기본 상장 요구사항

    ⚠️ 주의: 이 값들은 거래소의 실제 요구사항입니다.
           변경하면 등급 시스템 전체가 영향받습니다!
    """

    # Spread (스프레드)
    SPREAD_MAX_PERCENT = 2.0  # 2%를 넘지 말 것

    # Volume (거래량)
    VOLUME_MIN_USD = 10000  # $10,000를 넘을 것

    # Depth (호가 깊이)
    DEPTH_MIN_USD = 500  # $500를 넘겨야 함 (±2% 이내)

    # Market Cap (시가총액)
    MARKET_CAP_MIN_USD = 50000  # $50,000를 넘겨야 함 (상장 요구사항)

    @classmethod
    def to_dict(cls) -> Dict[str, float]:
        """Dict 형태로 반환 (호환성용)"""
        return {
            'spread_threshold': cls.SPREAD_MAX_PERCENT,
            'volume_threshold': cls.VOLUME_MIN_USD,
            'depth_threshold': cls.DEPTH_MIN_USD,
            'market_cap_threshold': cls.MARKET_CAP_MIN_USD
        }


# ========================================
# Grade 임계값 (Grade Thresholds)
# ========================================

class GradeThresholds:
    """
    Grade 계산을 위한 Risk Score 임계값

    Risk Score 범위: 0.0 ~ 1.0+
    - 0.0 = 완벽 (모든 조건 충족)
    - 1.0+ = 매우 위험 (여러 조건 위반)
    """

    # Risk Score → Grade 매핑
    GRADE_A_MAX_RISK = 0.15  # A: risk ≤ 0.15
    GRADE_B_MAX_RISK = 0.30  # B: 0.15 < risk ≤ 0.30
    GRADE_C_MAX_RISK = 0.50  # C: 0.30 < risk ≤ 0.50
    GRADE_D_MAX_RISK = 0.70  # D: 0.50 < risk ≤ 0.70
    # F: risk > 0.70

    # Risk 계산 가중치 (합계 = 1.0)
    DEPTH_WEIGHT = 0.70  # 70% - Depth가 가장 중요
    SPREAD_WEIGHT = 0.30  # 30% - Spread는 보조 지표

    @classmethod
    def risk_to_grade(cls, risk_score: float) -> str:
        """Risk score를 Grade로 변환"""
        if risk_score <= cls.GRADE_A_MAX_RISK:
            return 'A'
        elif risk_score <= cls.GRADE_B_MAX_RISK:
            return 'B'
        elif risk_score <= cls.GRADE_C_MAX_RISK:
            return 'C'
        elif risk_score <= cls.GRADE_D_MAX_RISK:
            return 'D'
        else:
            return 'F'


# ========================================
# Grade 상세 범위 (세밀한 등급용)
# ========================================

class DetailedGradeRanges:
    """
    A+, A, A-, B+, B, B- 등 세밀한 등급 범위
    (GPA 계산용)
    """

    RANGES = [
        (4.3, 5.0, 'A+'),
        (3.85, 4.3, 'A'),
        (3.55, 3.85, 'A-'),
        (3.15, 3.55, 'B+'),
        (2.85, 3.15, 'B'),
        (2.55, 2.85, 'B-'),
        (2.15, 2.55, 'C+'),
        (1.85, 2.15, 'C'),
        (1.65, 1.85, 'C-'),
        (1.0, 1.65, 'D'),
        (0, 1.0, 'F')
    ]

    @classmethod
    def gpa_to_grade(cls, gpa: float) -> str:
        """GPA를 세밀한 Grade로 변환"""
        for min_gpa, max_gpa, grade in cls.RANGES:
            if min_gpa <= gpa < max_gpa:
                return grade
        return 'F'


# ========================================
# Grade 매핑 (Grade Mappings)
# ========================================

# Grade → GPA 점수
GRADE_TO_POINTS: Dict[str, float] = {
    'A+': 4.3,
    'A': 4.0,
    'A-': 3.7,
    'B+': 3.3,
    'B': 3.0,
    'B-': 2.7,
    'C+': 2.3,
    'C': 2.0,
    'C-': 1.7,
    'D': 1.0,
    'F': 0.0,
    'N/A': 0.0
}

# Grade → Color (UI용)
GRADE_TO_COLOR: Dict[str, str] = {
    'A+': '#10b981',  # Emerald
    'A': '#27ae60',   # Green
    'A-': '#2ecc71',  # Light green
    'B+': '#3498db',  # Blue
    'B': '#3498db',   # Blue
    'B-': '#5dade2',  # Light blue
    'C+': '#f39c12',  # Orange
    'C': '#f39c12',   # Orange
    'C-': '#f39c12',  # Orange
    'D': '#e67e22',   # Dark orange
    'F': '#e74c3c',   # Red
    'N/A': '#95a5a6'  # Gray
}

# Grade → 설명
GRADE_TO_DESCRIPTION: Dict[str, str] = {
    'A': '우수 - 모든 조건 충족',
    'B': '양호 - 대부분 조건 충족',
    'C': '보통 - 일부 조건 미달',
    'D': '주의 - 여러 조건 미달',
    'F': '위험 - 대부분 조건 위반'
}


# ========================================
# Token 상태 (Token Status)
# ========================================

class TokenStatus:
    """
    Token lifecycle 상태

    ⚠️ 문자열 하드코딩 금지!
       예: if status == "MAIN_BOARD"  ❌
           if status == TokenStatus.MAIN_BOARD  ✅
    """
    NORMAL = "NORMAL"  # 정상 - 모니터링 중
    MAIN_BOARD = "MAIN_BOARD"  # 메인보드 게시 중
    ARCHIVED = "ARCHIVED"  # 퇴출됨 - 아카이브
    DELISTED = "DELISTED"  # 거래소에서 상장폐지됨

    # 향후 제거 예정 (deprecated)
    MONITORING = "MONITORING"  # NORMAL과 동일, 하위 호환용

    @classmethod
    def all_statuses(cls) -> list:
        """모든 상태 목록"""
        return [cls.NORMAL, cls.MAIN_BOARD, cls.ARCHIVED, cls.DELISTED]

    @classmethod
    def active_statuses(cls) -> list:
        """활성 상태 목록 (퇴출/상장폐지 제외)"""
        return [cls.NORMAL, cls.MAIN_BOARD]


# ========================================
# 시간 설정 (Time Settings)
# ========================================

class TimeSettings:
    """시간 관련 설정"""

    # Honeymoon period
    HONEYMOON_DAYS = 240  # 신규 토큰 유예 기간

    # Main board lifecycle
    ENTRY_HISTORY_DAYS = 7  # 진입 평가 기간
    EXIT_HISTORY_DAYS = 14  # 퇴출 평가 기간
    MIN_STAY_DAYS = 14  # 최소 게시 기간

    # Scanning
    SCAN_INTERVAL_HOURS = 4  # 스캔 주기
    DEFAULT_HISTORY_DAYS = 3  # 기본 히스토리 기간

    # Cache
    CACHE_VALIDITY_HOURS = 2  # 캐시 유효 기간


# ========================================
# 거래소 설정 (Exchange Settings)
# ========================================

class ExchangeIds:
    """지원하는 거래소 ID"""
    GATEIO = "gateio"
    MEXC = "mexc"
    KUCOIN = "kucoin"
    BITGET = "bitget"

    @classmethod
    def all_exchanges(cls) -> list:
        """모든 거래소 목록"""
        return [cls.GATEIO, cls.MEXC, cls.KUCOIN, cls.BITGET]


# ========================================
# API 설정 (API Settings)
# ========================================

class APISettings:
    """API 관련 설정"""

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 60
    REQUEST_TIMEOUT_SECONDS = 30

    # Retry
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5


# ========================================
# UI 설정 (UI Settings)
# ========================================

class UISettings:
    """Streamlit UI 설정"""

    # Page config
    PAGE_TITLE = "NightWatch Dashboard"
    PAGE_ICON = "🌙"
    LAYOUT = "wide"

    # Colors
    PRIMARY_COLOR = "#3498db"
    WARNING_COLOR = "#f39c12"
    DANGER_COLOR = "#e74c3c"
    SUCCESS_COLOR = "#27ae60"

    # Chart sizes
    MINI_CHART_WIDTH = 120
    MINI_CHART_HEIGHT = 40
    FULL_CHART_HEIGHT = 300


# ========================================
# 알림 설정 (Notification Settings)
# ========================================

class NotificationSettings:
    """알림 관련 설정"""

    # Telegram
    TELEGRAM_ENABLED = True

    # Grade change alerts
    ALERT_ON_GRADE_DROP = True
    ALERT_GRADE_THRESHOLD = 'D'  # D 이하일 때 알림

    # Volume alerts
    ALERT_ON_LOW_VOLUME = True
    LOW_VOLUME_THRESHOLD = ExchangeThresholds.VOLUME_MIN_USD


# ========================================
# 헬퍼 함수 (Helper Functions)
# ========================================

def get_grade_color(grade: str) -> str:
    """Grade에 해당하는 색상 반환"""
    return GRADE_TO_COLOR.get(grade, GRADE_TO_COLOR['N/A'])


def get_grade_points(grade: str) -> float:
    """Grade에 해당하는 GPA 점수 반환"""
    return GRADE_TO_POINTS.get(grade, 0.0)


def is_passing_grade(grade: str) -> bool:
    """합격 등급 여부 (B 이상)"""
    passing_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-']
    return grade in passing_grades


def is_critical_grade(grade: str) -> bool:
    """위험 등급 여부 (D, F)"""
    return grade in ['D', 'F']


# ========================================
# 버전 정보
# ========================================

__version__ = "1.0.0"
__last_updated__ = "2025-10-31"

# 변경 이력
CHANGELOG = """
v1.0.0 (2025-10-31)
- ✅ Initial release - ONE SOURCE OF TRUTH 구현
- ✅ 거래소 기본 요구사항 통합 (Spread 2%, Volume $10k, Depth $500)
- ✅ Grade threshold 통합
- ✅ Token status enum 통합
- ✅ 모든 하드코딩 제거
"""
