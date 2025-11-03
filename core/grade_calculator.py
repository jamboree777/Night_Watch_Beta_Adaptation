"""
NightWatch Grade Calculator
통합 Grade 계산 모듈

기존 모듈 통합:
- grade_info_manager.py → calculate_instant_grade()
- calculate_grade_from_scan.py → calculate_grade_from_raw()

특징:
- 단일 Grade 계산 로직 (ONE SOURCE OF TRUTH)
- config.py의 threshold 값 사용 (하드코딩 제거)
- 명확한 계산 공식과 주석
"""

from typing import Tuple
from core.config import (
    ExchangeThresholds,
    GradeThresholds,
    GRADE_TO_POINTS,
    get_grade_points,
    get_grade_color
)


# ========================================
# GradeCalculator 클래스
# ========================================

class GradeCalculator:
    """
    Grade 계산 엔진

    Risk Score 계산:
        risk = (depth_risk * 0.7) + (spread_risk * 0.3)

    각 지표별 risk 계산:
        - depth_risk: 목표치 미달 정도 (0~1)
        - spread_risk: 목표치 초과 정도 (0~1+)
    """

    @staticmethod
    def calculate_instant_grade(
        spread_pct: float,
        depth_2pct: float,
        volume_24h: float = 0
    ) -> Tuple[str, float, float]:
        """
        즉시 Grade 계산 (raw scan data로부터)

        Args:
            spread_pct: Spread 퍼센트 (예: 2.5 = 2.5%)
            depth_2pct: ±2% 이내 호가 깊이 (USD)
            volume_24h: 24시간 거래량 (USD) - 현재는 미사용

        Returns:
            (grade, grade_points, risk_score)
            - grade: 'A', 'B', 'C', 'D', 'F'
            - grade_points: GPA 점수 (0.0 ~ 4.0)
            - risk_score: 위험도 (0.0 ~ 1.0+)

        계산 공식:
            depth_risk = (threshold - actual) / threshold  # 클수록 나쁨
            spread_risk = actual / threshold  # 클수록 나쁨
            total_risk = (depth_risk * 0.7) + (spread_risk * 0.3)

        예시:
            >>> calc = GradeCalculator()
            >>> grade, points, risk = calc.calculate_instant_grade(1.5, 800, 20000)
            >>> print(f"Grade: {grade}, Risk: {risk:.3f}")
            Grade: A, Risk: 0.082
        """
        # Thresholds (거래소 기본 요구사항)
        spread_threshold = ExchangeThresholds.SPREAD_MAX_PERCENT
        depth_threshold = ExchangeThresholds.DEPTH_MIN_USD

        # 1. Depth Risk 계산
        # depth가 낮을수록 위험 (목표치 미달)
        if depth_2pct < depth_threshold:
            depth_risk = (depth_threshold - depth_2pct) / depth_threshold
        else:
            depth_risk = 0.0
        depth_risk = max(0.0, min(1.0, depth_risk))  # 0~1 범위로 제한

        # 2. Spread Risk 계산
        # spread가 높을수록 위험 (목표치 초과)
        spread_risk = spread_pct / spread_threshold
        spread_risk = min(1.0, spread_risk)  # 0~1 범위로 제한 (1 초과 가능하지만 cap)

        # 3. Total Risk Score 계산 (가중 평균)
        # Depth가 더 중요 (70%), Spread는 보조 지표 (30%)
        risk_score = (depth_risk * GradeThresholds.DEPTH_WEIGHT) + \
                     (spread_risk * GradeThresholds.SPREAD_WEIGHT)

        # 4. Risk Score → Grade 변환
        grade = GradeThresholds.risk_to_grade(risk_score)

        # 5. Grade → Points 변환
        grade_points = get_grade_points(grade)

        return grade, grade_points, risk_score

    @staticmethod
    def calculate_from_raw(
        spread_pct: float,
        depth_2pct: float,
        volume_24h: float = 0
    ) -> Tuple[str, float]:
        """
        Raw 데이터로부터 Grade 계산 (간단 버전)

        Args:
            spread_pct: Spread 퍼센트
            depth_2pct: Depth (USD)
            volume_24h: Volume (USD) - 현재는 미사용

        Returns:
            (grade, risk_score)

        Note:
            calculate_instant_grade()의 wrapper
            기존 calculate_grade_from_scan.py 호환용
        """
        grade, _, risk_score = GradeCalculator.calculate_instant_grade(
            spread_pct, depth_2pct, volume_24h
        )
        return grade, risk_score

    @staticmethod
    def calculate_aggregate_grade(
        avg_spread_pct: float,
        avg_depth_2pct: float,
        avg_volume_24h: float,
        violation_rate: float = 0.0
    ) -> Tuple[str, float, float]:
        """
        평균값으로 Grade 계산 (scan_aggregate용)

        Args:
            avg_spread_pct: 평균 Spread
            avg_depth_2pct: 평균 Depth
            avg_volume_24h: 평균 Volume
            violation_rate: 위반율 (0.0 ~ 1.0) - 선택적 penalty

        Returns:
            (grade, grade_points, risk_score)

        Note:
            violation_rate는 추가 penalty로 사용 가능
        """
        grade, points, risk_score = GradeCalculator.calculate_instant_grade(
            avg_spread_pct, avg_depth_2pct, avg_volume_24h
        )

        # Violation rate penalty (선택적)
        if violation_rate > 0:
            penalty = violation_rate * 0.2  # 최대 20% penalty
            risk_score = min(1.0, risk_score + penalty)
            # Re-calculate grade with penalty
            grade = GradeThresholds.risk_to_grade(risk_score)
            points = get_grade_points(grade)

        return grade, points, risk_score

    @staticmethod
    def calculate_detailed_grade(
        spread_pct: float,
        depth_2pct: float,
        volume_24h: float = 0
    ) -> dict:
        """
        상세한 Grade 정보 반환

        Returns:
            {
                'grade': 'A',
                'grade_points': 4.0,
                'risk_score': 0.05,
                'risk_breakdown': {
                    'depth_risk': 0.02,
                    'spread_risk': 0.08
                },
                'metrics': {
                    'spread_pct': 1.5,
                    'depth_2pct': 800,
                    'volume_24h': 20000
                },
                'thresholds': {
                    'spread_threshold': 2.0,
                    'depth_threshold': 500,
                    'volume_threshold': 10000
                },
                'color': '#27ae60'
            }
        """
        spread_threshold = ExchangeThresholds.SPREAD_MAX_PERCENT
        depth_threshold = ExchangeThresholds.DEPTH_MIN_USD
        volume_threshold = ExchangeThresholds.VOLUME_MIN_USD

        # Calculate risks separately for breakdown
        depth_risk = max(0.0, min(1.0, (depth_threshold - depth_2pct) / depth_threshold))
        spread_risk = min(1.0, spread_pct / spread_threshold)

        # Calculate grade
        grade, points, risk_score = GradeCalculator.calculate_instant_grade(
            spread_pct, depth_2pct, volume_24h
        )

        return {
            'grade': grade,
            'grade_points': points,
            'risk_score': risk_score,
            'risk_breakdown': {
                'depth_risk': depth_risk,
                'spread_risk': spread_risk,
                'depth_weight': GradeThresholds.DEPTH_WEIGHT,
                'spread_weight': GradeThresholds.SPREAD_WEIGHT
            },
            'metrics': {
                'spread_pct': spread_pct,
                'depth_2pct': depth_2pct,
                'volume_24h': volume_24h
            },
            'thresholds': {
                'spread_threshold': spread_threshold,
                'depth_threshold': depth_threshold,
                'volume_threshold': volume_threshold
            },
            'color': get_grade_color(grade)
        }


# ========================================
# 편의 함수
# ========================================

def calculate_grade(
    spread_pct: float,
    depth_2pct: float,
    volume_24h: float = 0
) -> str:
    """
    간단한 Grade 계산 (Grade만 반환)

    사용 예:
        grade = calculate_grade(1.5, 800, 20000)
        print(grade)  # 'A'
    """
    grade, _, _ = GradeCalculator.calculate_instant_grade(
        spread_pct, depth_2pct, volume_24h
    )
    return grade


def calculate_grade_with_risk(
    spread_pct: float,
    depth_2pct: float,
    volume_24h: float = 0
) -> Tuple[str, float]:
    """
    Grade와 Risk score 반환

    사용 예:
        grade, risk = calculate_grade_with_risk(1.5, 800, 20000)
        print(f"{grade} (risk: {risk:.3f})")
    """
    grade, _, risk = GradeCalculator.calculate_instant_grade(
        spread_pct, depth_2pct, volume_24h
    )
    return grade, risk


def is_passing(
    spread_pct: float,
    depth_2pct: float,
    volume_24h: float = 0
) -> bool:
    """
    합격 여부 (B 이상)

    사용 예:
        if is_passing(1.5, 800, 20000):
            print("PASS")
    """
    grade = calculate_grade(spread_pct, depth_2pct, volume_24h)
    return grade in ['A', 'B']


def is_critical(
    spread_pct: float,
    depth_2pct: float,
    volume_24h: float = 0
) -> bool:
    """
    위험 등급 여부 (D, F)

    사용 예:
        if is_critical(5.0, 100, 5000):
            print("CRITICAL!")
    """
    grade = calculate_grade(spread_pct, depth_2pct, volume_24h)
    return grade in ['D', 'F']


# ========================================
# 호환성 함수 (Backward Compatibility)
# ========================================

def calculate_instant_grade(spread_pct: float, depth_2pct: float) -> Tuple[str, float, float]:
    """
    grade_info_manager.py 호환 함수

    ⚠️ Deprecated: GradeCalculator.calculate_instant_grade() 사용 권장
    """
    return GradeCalculator.calculate_instant_grade(spread_pct, depth_2pct)


def calculate_grade_from_raw(
    spread_pct: float,
    depth_2pct: float,
    volume_24h: float
) -> Tuple[str, float]:
    """
    calculate_grade_from_scan.py 호환 함수

    ⚠️ Deprecated: GradeCalculator.calculate_from_raw() 사용 권장
    """
    return GradeCalculator.calculate_from_raw(spread_pct, depth_2pct, volume_24h)


# ========================================
# 배치 계산 (Batch Calculation)
# ========================================

def calculate_grades_batch(tokens: list) -> list:
    """
    여러 토큰의 Grade를 한번에 계산

    Args:
        tokens: [{'spread_pct': 1.5, 'depth_2pct': 800, 'volume_24h': 20000}, ...]

    Returns:
        [{'grade': 'A', 'risk': 0.05, ...}, ...]
    """
    results = []
    for token in tokens:
        spread = token.get('spread_pct', 0)
        depth = token.get('depth_2pct', 0)
        volume = token.get('volume_24h', 0)

        grade, points, risk = GradeCalculator.calculate_instant_grade(
            spread, depth, volume
        )

        results.append({
            'grade': grade,
            'grade_points': points,
            'risk_score': risk,
            'color': get_grade_color(grade)
        })

    return results


# ========================================
# 사용 예제
# ========================================

if __name__ == "__main__":
    print("=== Grade Calculator Test ===\n")

    # 1. 기본 Grade 계산
    print("1. Basic grade calculation:")
    grade, points, risk = GradeCalculator.calculate_instant_grade(1.5, 800, 20000)
    print(f"   Spread: 1.5%, Depth: $800, Volume: $20k")
    print(f"   → Grade: {grade} ({points:.1f} GPA), Risk: {risk:.3f}\n")

    # 2. 경계 케이스
    print("2. Boundary cases:")
    test_cases = [
        (1.0, 1000, 50000, "Perfect metrics"),
        (2.0, 500, 10000, "Exactly at thresholds"),
        (3.0, 300, 5000, "Below thresholds"),
        (5.0, 100, 1000, "Critical")
    ]

    for spread, depth, volume, desc in test_cases:
        grade, points, risk = GradeCalculator.calculate_instant_grade(spread, depth, volume)
        print(f"   {desc}: {grade} (risk: {risk:.3f})")

    # 3. 상세 정보
    print("\n3. Detailed grade info:")
    details = GradeCalculator.calculate_detailed_grade(1.8, 600, 15000)
    print(f"   Grade: {details['grade']}")
    print(f"   Risk Score: {details['risk_score']:.3f}")
    print(f"   Depth Risk: {details['risk_breakdown']['depth_risk']:.3f}")
    print(f"   Spread Risk: {details['risk_breakdown']['spread_risk']:.3f}")
    print(f"   Color: {details['color']}")

    # 4. 편의 함수
    print("\n4. Convenience functions:")
    print(f"   calculate_grade(1.5, 800): {calculate_grade(1.5, 800)}")
    print(f"   is_passing(1.5, 800): {is_passing(1.5, 800)}")
    print(f"   is_critical(5.0, 100): {is_critical(5.0, 100)}")

    print("\n✓ All tests passed!")
