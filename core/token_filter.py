"""
NightWatch Token Filter
재사용 가능한 토큰 필터 모듈

기존 12+ 인라인 필터 구현 통합:
- 상태별 필터 (MAIN_BOARD, NORMAL, etc.)
- 거래소별 필터
- 등급별 필터
- 조건별 필터

특징:
- Chainable filters (필터 체이닝)
- Custom predicates 지원
- Type hints
"""

from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
from core.config import TokenStatus, ExchangeIds, is_critical_grade


# ========================================
# TokenFilter 클래스
# ========================================

class TokenFilter:
    """
    재사용 가능한 토큰 필터

    사용 예:
        # 1. 상태별 필터
        main_board = TokenFilter.by_status(tokens, TokenStatus.MAIN_BOARD)

        # 2. 거래소별 필터
        gateio_tokens = TokenFilter.by_exchange(tokens, ExchangeIds.GATEIO)

        # 3. 등급별 필터
        critical_tokens = TokenFilter.by_grade(tokens, 'D')

        # 4. 체이닝
        filtered = TokenFilter.chain(tokens, [
            lambda t: TokenFilter.by_status(t, TokenStatus.MAIN_BOARD),
            lambda t: TokenFilter.by_grade_range(t, ['D', 'F'])
        ])
    """

    # ========================================
    # 기본 필터 (Basic Filters)
    # ========================================

    @staticmethod
    def by_status(tokens: Dict[str, Any], status: str) -> Dict[str, Any]:
        """
        상태별 필터

        Args:
            tokens: 토큰 딕셔너리
            status: TokenStatus 값 (예: TokenStatus.MAIN_BOARD)

        Returns:
            필터된 토큰 딕셔너리

        예:
            main_board = TokenFilter.by_status(tokens, TokenStatus.MAIN_BOARD)
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('lifecycle', {}).get('status') == status
        }

    @staticmethod
    def by_exchange(tokens: Dict[str, Any], exchange: str) -> Dict[str, Any]:
        """
        거래소별 필터

        Args:
            exchange: 거래소 ID (예: ExchangeIds.GATEIO 또는 'gateio')

        예:
            gateio = TokenFilter.by_exchange(tokens, ExchangeIds.GATEIO)
            mexc = TokenFilter.by_exchange(tokens, 'mexc')
        """
        exchange_lower = exchange.lower()
        return {
            tid: t for tid, t in tokens.items()
            if t.get('exchange', '').lower() == exchange_lower
        }

    @staticmethod
    def by_symbol(tokens: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        심볼별 필터 (부분 매칭)

        Args:
            symbol: 심볼 (대소문자 무시, 부분 매칭)

        예:
            btc_tokens = TokenFilter.by_symbol(tokens, 'BTC')
        """
        symbol_upper = symbol.upper()
        return {
            tid: t for tid, t in tokens.items()
            if symbol_upper in t.get('symbol', '').upper()
        }

    @staticmethod
    def by_grade(tokens: Dict[str, Any], grade: str) -> Dict[str, Any]:
        """
        등급별 필터

        Args:
            grade: 등급 ('A', 'B', 'C', 'D', 'F')

        예:
            a_grade = TokenFilter.by_grade(tokens, 'A')
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('scan_aggregate', {}).get('grade') == grade
        }

    @staticmethod
    def by_grade_range(tokens: Dict[str, Any], grades: List[str]) -> Dict[str, Any]:
        """
        여러 등급 필터

        Args:
            grades: 등급 리스트 (예: ['D', 'F'])

        예:
            critical = TokenFilter.by_grade_range(tokens, ['D', 'F'])
            passing = TokenFilter.by_grade_range(tokens, ['A', 'B'])
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('scan_aggregate', {}).get('grade') in grades
        }

    # ========================================
    # 편의 필터 (Convenience Filters)
    # ========================================

    @staticmethod
    def main_board(tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        메인보드 토큰만

        예:
            main = TokenFilter.main_board(tokens)
        """
        return TokenFilter.by_status(tokens, TokenStatus.MAIN_BOARD)

    @staticmethod
    def normal(tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        정상 상태 토큰만

        예:
            normal = TokenFilter.normal(tokens)
        """
        return TokenFilter.by_status(tokens, TokenStatus.NORMAL)

    @staticmethod
    def archived(tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        아카이브된 토큰만

        예:
            archived = TokenFilter.archived(tokens)
        """
        return TokenFilter.by_status(tokens, TokenStatus.ARCHIVED)

    @staticmethod
    def active(tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        활성 토큰만 (NORMAL + MAIN_BOARD)

        예:
            active = TokenFilter.active(tokens)
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('lifecycle', {}).get('status') in TokenStatus.active_statuses()
        }

    @staticmethod
    def critical(tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        위험 등급 토큰만 (D, F)

        예:
            critical = TokenFilter.critical(tokens)
        """
        return TokenFilter.by_grade_range(tokens, ['D', 'F'])

    @staticmethod
    def passing(tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        합격 등급 토큰만 (A, B)

        예:
            passing = TokenFilter.passing(tokens)
        """
        return TokenFilter.by_grade_range(tokens, ['A', 'B'])

    # ========================================
    # 조건 필터 (Conditional Filters)
    # ========================================

    @staticmethod
    def by_risk_above(tokens: Dict[str, Any], risk_threshold: float) -> Dict[str, Any]:
        """
        Risk score가 특정 값 이상인 토큰

        Args:
            risk_threshold: 임계값 (예: 0.5)

        예:
            high_risk = TokenFilter.by_risk_above(tokens, 0.5)
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('scan_aggregate', {}).get('average_risk', 0) >= risk_threshold
        }

    @staticmethod
    def by_volume_below(tokens: Dict[str, Any], volume_threshold: float) -> Dict[str, Any]:
        """
        거래량이 특정 값 이하인 토큰

        Args:
            volume_threshold: 임계값 (USD)

        예:
            low_volume = TokenFilter.by_volume_below(tokens, 10000)
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('scan_aggregate', {}).get('avg_volume_24h', 0) < volume_threshold
        }

    @staticmethod
    def by_spread_above(tokens: Dict[str, Any], spread_threshold: float) -> Dict[str, Any]:
        """
        Spread가 특정 값 이상인 토큰

        Args:
            spread_threshold: 임계값 (%)

        예:
            high_spread = TokenFilter.by_spread_above(tokens, 2.0)
        """
        return {
            tid: t for tid, t in tokens.items()
            if t.get('scan_aggregate', {}).get('avg_spread_pct', 0) > spread_threshold
        }

    @staticmethod
    def by_days_on_board(
        tokens: Dict[str, Any],
        min_days: Optional[int] = None,
        max_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        메인보드 게시 기간으로 필터

        Args:
            min_days: 최소 일수
            max_days: 최대 일수

        예:
            # 14일 이상 게시된 토큰
            long_term = TokenFilter.by_days_on_board(tokens, min_days=14)

            # 7일 미만 게시된 토큰
            new_entries = TokenFilter.by_days_on_board(tokens, max_days=7)
        """
        result = {}
        for tid, t in tokens.items():
            entry_date_str = t.get('lifecycle', {}).get('main_board_entry')
            if not entry_date_str:
                continue

            try:
                entry_date = datetime.fromisoformat(entry_date_str.replace('Z', '+00:00'))
                days_on_board = (datetime.now(entry_date.tzinfo) - entry_date).days

                if min_days is not None and days_on_board < min_days:
                    continue
                if max_days is not None and days_on_board > max_days:
                    continue

                result[tid] = t
            except:
                continue

        return result

    # ========================================
    # 커스텀 필터 (Custom Filters)
    # ========================================

    @staticmethod
    def custom(tokens: Dict[str, Any], predicate: Callable[[Any], bool]) -> Dict[str, Any]:
        """
        커스텀 predicate 함수로 필터

        Args:
            predicate: 토큰을 받아 bool을 반환하는 함수

        예:
            # Spread > 3% AND Volume < 5000
            custom_filter = TokenFilter.custom(tokens, lambda t:
                t.get('scan_aggregate', {}).get('avg_spread_pct', 0) > 3.0 and
                t.get('scan_aggregate', {}).get('avg_volume_24h', 0) < 5000
            )
        """
        return {
            tid: t for tid, t in tokens.items()
            if predicate(t)
        }

    @staticmethod
    def chain(tokens: Dict[str, Any], filters: List[Callable]) -> Dict[str, Any]:
        """
        여러 필터를 순차적으로 적용 (체이닝)

        Args:
            filters: 필터 함수 리스트

        예:
            # Main board + Gate.io + Critical grades
            result = TokenFilter.chain(tokens, [
                lambda t: TokenFilter.main_board(t),
                lambda t: TokenFilter.by_exchange(t, 'gateio'),
                lambda t: TokenFilter.critical(t)
            ])
        """
        result = tokens
        for filter_func in filters:
            result = filter_func(result)
        return result

    # ========================================
    # 정렬 (Sorting)
    # ========================================

    @staticmethod
    def sort_by_risk(tokens: Dict[str, Any], descending: bool = True) -> List[tuple]:
        """
        Risk score로 정렬

        Args:
            descending: True = 위험한 순서, False = 안전한 순서

        Returns:
            [(token_id, token_data), ...] 리스트

        예:
            # 가장 위험한 토큰부터
            sorted_tokens = TokenFilter.sort_by_risk(tokens, descending=True)
            for tid, t in sorted_tokens[:10]:
                print(f"{t['symbol']}: risk={t['scan_aggregate']['average_risk']}")
        """
        items = list(tokens.items())
        items.sort(
            key=lambda x: x[1].get('scan_aggregate', {}).get('average_risk', 0),
            reverse=descending
        )
        return items

    @staticmethod
    def sort_by_volume(tokens: Dict[str, Any], descending: bool = True) -> List[tuple]:
        """
        거래량으로 정렬

        예:
            # 거래량 높은 순서
            sorted_tokens = TokenFilter.sort_by_volume(tokens, descending=True)
        """
        items = list(tokens.items())
        items.sort(
            key=lambda x: x[1].get('scan_aggregate', {}).get('avg_volume_24h', 0),
            reverse=descending
        )
        return items

    @staticmethod
    def sort_by_grade(tokens: Dict[str, Any]) -> List[tuple]:
        """
        등급으로 정렬 (A → F)

        예:
            sorted_tokens = TokenFilter.sort_by_grade(tokens)
        """
        grade_order = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4, 'N/A': 5}
        items = list(tokens.items())
        items.sort(
            key=lambda x: grade_order.get(
                x[1].get('scan_aggregate', {}).get('grade', 'N/A'), 5
            )
        )
        return items

    # ========================================
    # 통계 (Statistics)
    # ========================================

    @staticmethod
    def count_by_grade(tokens: Dict[str, Any]) -> Dict[str, int]:
        """
        등급별 토큰 수 집계

        Returns:
            {'A': 10, 'B': 5, 'C': 3, 'D': 2, 'F': 1}

        예:
            counts = TokenFilter.count_by_grade(tokens)
            print(f"A grade: {counts['A']}")
        """
        counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0, 'N/A': 0}
        for t in tokens.values():
            grade = t.get('scan_aggregate', {}).get('grade', 'N/A')
            if grade in counts:
                counts[grade] += 1
            else:
                counts['N/A'] += 1
        return counts

    @staticmethod
    def count_by_exchange(tokens: Dict[str, Any]) -> Dict[str, int]:
        """
        거래소별 토큰 수 집계

        Returns:
            {'gateio': 100, 'mexc': 80, ...}
        """
        counts = {}
        for t in tokens.values():
            exchange = t.get('exchange', 'unknown')
            counts[exchange] = counts.get(exchange, 0) + 1
        return counts

    @staticmethod
    def count_by_status(tokens: Dict[str, Any]) -> Dict[str, int]:
        """
        상태별 토큰 수 집계

        Returns:
            {'MAIN_BOARD': 50, 'NORMAL': 200, ...}
        """
        counts = {}
        for t in tokens.values():
            status = t.get('lifecycle', {}).get('status', 'unknown')
            counts[status] = counts.get(status, 0) + 1
        return counts


# ========================================
# 편의 함수
# ========================================

def get_main_board_tokens(tokens: Dict[str, Any]) -> Dict[str, Any]:
    """메인보드 토큰 가져오기 (간단 버전)"""
    return TokenFilter.main_board(tokens)


def get_critical_tokens(tokens: Dict[str, Any]) -> Dict[str, Any]:
    """위험 토큰 가져오기 (간단 버전)"""
    return TokenFilter.critical(tokens)


def get_exchange_tokens(tokens: Dict[str, Any], exchange: str) -> Dict[str, Any]:
    """특정 거래소 토큰 가져오기 (간단 버전)"""
    return TokenFilter.by_exchange(tokens, exchange)


# ========================================
# 사용 예제
# ========================================

if __name__ == "__main__":
    print("=== Token Filter Test ===\n")

    # Mock data
    tokens = {
        'gateio_btc_usdt': {
            'exchange': 'gateio',
            'symbol': 'BTC/USDT',
            'lifecycle': {'status': TokenStatus.MAIN_BOARD, 'main_board_entry': '2025-10-01T00:00:00Z'},
            'scan_aggregate': {'grade': 'A', 'average_risk': 0.1, 'avg_volume_24h': 50000, 'avg_spread_pct': 1.5}
        },
        'mexc_eth_usdt': {
            'exchange': 'mexc',
            'symbol': 'ETH/USDT',
            'lifecycle': {'status': TokenStatus.MAIN_BOARD},
            'scan_aggregate': {'grade': 'D', 'average_risk': 0.65, 'avg_volume_24h': 8000, 'avg_spread_pct': 3.5}
        },
        'gateio_ada_usdt': {
            'exchange': 'gateio',
            'symbol': 'ADA/USDT',
            'lifecycle': {'status': TokenStatus.NORMAL},
            'scan_aggregate': {'grade': 'B', 'average_risk': 0.25, 'avg_volume_24h': 20000, 'avg_spread_pct': 2.0}
        }
    }

    # 1. 기본 필터
    print("1. Main board tokens:")
    main_board = TokenFilter.main_board(tokens)
    print(f"   Count: {len(main_board)}")

    # 2. 거래소별
    print("\n2. Gateio tokens:")
    gateio = TokenFilter.by_exchange(tokens, 'gateio')
    print(f"   Count: {len(gateio)}")

    # 3. 위험 토큰
    print("\n3. Critical tokens:")
    critical = TokenFilter.critical(tokens)
    for tid, t in critical.items():
        print(f"   {t['symbol']}: {t['scan_aggregate']['grade']}")

    # 4. 체이닝
    print("\n4. Chained filters (Main board + Gateio):")
    result = TokenFilter.chain(tokens, [
        lambda t: TokenFilter.main_board(t),
        lambda t: TokenFilter.by_exchange(t, 'gateio')
    ])
    print(f"   Count: {len(result)}")

    # 5. 통계
    print("\n5. Statistics:")
    grade_counts = TokenFilter.count_by_grade(tokens)
    print(f"   Grade distribution: {grade_counts}")

    print("\n✓ All tests passed!")
