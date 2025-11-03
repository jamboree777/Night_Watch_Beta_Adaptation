"""
On-Chain Data Collector for NightWatch Phase 3
Supports: Etherscan, BSCScan, PolygonScan
Features:
- Token balance tracking for exchange wallets
- Public name tag detection (exchange wallet discovery)
- Movement detection (>0.1% change alerts)
- Cross-exchange flow analysis
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from filelock import FileLock

class OnChainCollector:
    def __init__(self, config_path: str = 'config/api_config.json'):
        """Initialize with API keys from config"""
        self.config = self._load_config(config_path)
        # Unified V2 API - 모든 체인이 하나의 엔드포인트 사용
        self.apis = {
            'ETH': {
                'url': 'https://api.etherscan.io/v2/api',
                'key': self.config.get('etherscan_api_key', ''),
                'chainid': '1'
            },
            'BSC': {
                'url': 'https://api.etherscan.io/v2/api',  # Unified endpoint
                'key': self.config.get('bscscan_api_key', ''),
                'chainid': '56'
            },
            'POLYGON': {
                'url': 'https://api.etherscan.io/v2/api',  # Unified endpoint
                'key': self.config.get('polygonscan_api_key', ''),
                'chainid': '137'
            }
        }

        # Known exchange wallets (fallback if public tag API fails)
        self.known_exchange_wallets = {
            'ETH': {
                'gateio': '0x1C4b70a3968436B9A0a9cf5205c787eb81Bb558c',
                'mexc': '0x75e89d5979E4f6Fba9F97c104c2F0AFB3F1dcB88',
                'binance': '0x28C6c06298d514Db089934071355E5743bf21d60',
                'okx': '0x236F9F97e0E62388479bf9E5BA4889e46B0273C3'
            },
            'BSC': {
                'gateio': '0x0D0707963952f2fBA59dD06f2b425ace40b492Fe',
                'mexc': '0x3B3ae790Df4F312e745D270119c6052904FB6790',
                'binance': '0x8894E0a0c962CB723c1976a4421c95949bE2D4E3'
            }
        }

    def _load_config(self, config_path: str) -> Dict:
        """Load API configuration"""
        paths = [
            Path(config_path),
            Path('data') / config_path,
            Path('..') / config_path
        ]

        for path in paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"[WARN] Failed to load config from {path}: {e}")

        print(f"[WARN] Config file not found, using empty config")
        return {}

    def get_token_info(self, contract_address: str, chain: str) -> Optional[Dict]:
        """
        Get token info from blockchain explorer (V2 API)

        Args:
            contract_address: Token contract address
            chain: Chain name (ETH, BSC, POLYGON)

        Returns:
            {
                'name': 'Wrapped Bitcoin',
                'symbol': 'WBTC',
                'decimals': 18,
                'total_supply': '21000000000000000000000000',
                'verified': True
            }
        """
        if chain not in self.apis:
            print(f"[ERROR] Unsupported chain: {chain}")
            return None

        api_config = self.apis[chain]
        if not api_config['key']:
            print(f"[ERROR] No API key for {chain}")
            return None

        # Use V2 API endpoint for contract info
        # V2: module=contract, action=getsourcecode + chainid param
        params = {
            'chainid': api_config['chainid'],
            'module': 'contract',
            'action': 'getsourcecode',
            'address': contract_address,
            'apikey': api_config['key']
        }

        try:
            response = requests.get(api_config['url'], params=params, timeout=10)
            data = response.json()

            if data.get('status') == '1' and data.get('result'):
                result = data['result']
                token_data = result[0] if isinstance(result, list) else result

                # Extract token info from contract source
                contract_name = token_data.get('ContractName', 'Unknown')
                abi = token_data.get('ABI', 'Contract source code not verified')

                # For ERC20 tokens, we need to call additional endpoints
                # Try to get token name and symbol using stats API
                return {
                    'name': contract_name,
                    'symbol': contract_name[:10],  # Fallback
                    'decimals': 18,  # Default for most ERC20
                    'total_supply': '0',
                    'verified': abi != 'Contract source code not verified',
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            print(f"[ERROR] Failed to fetch token info for {contract_address}: {e}")

        return None

    def get_token_balance(self, contract_address: str, wallet_address: str,
                         chain: str) -> Optional[float]:
        """
        Get token balance of a wallet

        Args:
            contract_address: Token contract address
            wallet_address: Wallet address to check
            chain: Chain name

        Returns:
            Token balance (in human-readable format)
        """
        if chain not in self.apis:
            return None

        api_config = self.apis[chain]
        if not api_config['key']:
            print(f"[ERROR] No API key for {chain}")
            return None

        params = {
            'chainid': api_config['chainid'],
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': contract_address,
            'address': wallet_address,
            'tag': 'latest',
            'apikey': api_config['key']
        }

        try:
            response = requests.get(api_config['url'], params=params, timeout=10)
            data = response.json()

            if data.get('status') == '1':
                balance_raw = int(data.get('result', 0))

                # Get token decimals
                token_info = self.get_token_info(contract_address, chain)
                decimals = token_info.get('decimals', 18) if token_info else 18

                balance = balance_raw / (10 ** decimals)
                return balance
        except Exception as e:
            print(f"[ERROR] Failed to fetch balance: {e}")

        return None

    def find_exchange_wallets_by_tag(self, chain: str, exchange_name: str) -> List[str]:
        """
        Try to find exchange wallets using public name tags (Etherscan feature)

        Args:
            chain: Chain name
            exchange_name: Exchange name (e.g., 'gateio', 'mexc')

        Returns:
            List of wallet addresses with matching name tags
        """
        # Note: Etherscan's public tag API requires special permission
        # For now, we'll use the known wallet addresses
        if chain in self.known_exchange_wallets:
            wallet = self.known_exchange_wallets[chain].get(exchange_name.lower())
            if wallet:
                return [wallet]

        return []

    def get_all_exchange_balances(self, contract_address: str, chain: str) -> Dict[str, float]:
        """
        Get token balances across all known exchange wallets

        Args:
            contract_address: Token contract address
            chain: Chain name

        Returns:
            Dictionary of {exchange: balance}
        """
        balances = {}

        if chain not in self.known_exchange_wallets:
            return balances

        for exchange, wallet in self.known_exchange_wallets[chain].items():
            balance = self.get_token_balance(contract_address, wallet, chain)
            if balance is not None and balance > 0:
                balances[exchange] = balance
                print(f"[INFO] {exchange.upper()} {chain} wallet: {balance:,.2f} tokens")

        return balances

    def track_deposit_history(self, token_id: str, contract_address: str,
                             chain: str, exchange: str, current_price: float = 0):
        """
        Track deposit balance history with movement detection

        Args:
            token_id: Token ID in unified DB
            contract_address: Contract address
            chain: Chain name
            exchange: Exchange ID (e.g., 'gateio', 'mexc')
            current_price: Current token price in USD

        Returns:
            Dict with balance data and movement detection
        """
        # Get exchange wallet
        wallets = self.find_exchange_wallets_by_tag(chain, exchange)
        if not wallets:
            print(f"[WARN] No wallet found for {exchange} on {chain}")
            return None

        wallet_address = wallets[0]

        # Get current balance
        current_balance = self.get_token_balance(contract_address, wallet_address, chain)
        if current_balance is None:
            print(f"[ERROR] Failed to get balance for {token_id}")
            return None

        # Load deposit history
        history_dir = Path('deposit_history')
        history_dir.mkdir(exist_ok=True)

        history_file = history_dir / f"{token_id}_deposit_history.jsonl"

        # Get previous balance for movement detection
        previous_balance = None
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_record = json.loads(lines[-1])
                        previous_balance = last_record.get('balance')
            except Exception as e:
                print(f"[WARN] Failed to read previous balance: {e}")

        # Calculate movement
        movement_pct = 0
        movement_detected = False
        if previous_balance and previous_balance > 0:
            movement_pct = abs(current_balance - previous_balance) / previous_balance * 100
            movement_detected = movement_pct >= 0.1  # 0.1% threshold

        # Calculate market cap
        market_cap_usd = current_balance * current_price if current_price > 0 else 0

        # Append to history
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            'timestamp': timestamp,
            'balance': current_balance,
            'market_cap_usd': market_cap_usd,
            'price_usd': current_price,
            'wallet_address': wallet_address,
            'chain': chain,
            'movement_pct': movement_pct,
            'movement_detected': movement_detected
        }

        try:
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[ERROR] Failed to write deposit history: {e}")

        if movement_detected:
            print(f"[ALERT] 🚨 Large deposit movement detected for {token_id}: {movement_pct:.2f}%")

        return record

    def analyze_cross_exchange_flows(self, contract_address: str, chain: str) -> Dict:
        """
        Analyze token distribution across exchanges

        Args:
            contract_address: Token contract address
            chain: Chain name

        Returns:
            {
                'total_exchange_balance': float,
                'exchange_distribution': {exchange: balance},
                'percentage_distribution': {exchange: percentage}
            }
        """
        balances = self.get_all_exchange_balances(contract_address, chain)

        total = sum(balances.values())

        percentages = {}
        if total > 0:
            for exchange, balance in balances.items():
                percentages[exchange] = (balance / total) * 100

        return {
            'total_exchange_balance': total,
            'exchange_distribution': balances,
            'percentage_distribution': percentages,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def update_token_onchain_data(self, token_id: str, contract_address: str,
                                  chain: str, exchange: str):
        """
        Update token with on-chain data in tokens_unified.json

        Args:
            token_id: Token ID in unified DB
            contract_address: Contract address
            chain: Chain name
            exchange: Exchange ID
        """
        # Determine unified DB path
        unified_paths = [
            Path('data/unified/tokens_unified.json'),
            Path('data/tokens_unified.json')
        ]

        unified_path = None
        for path in unified_paths:
            if path.exists():
                unified_path = path
                break

        if not unified_path:
            print(f"[ERROR] tokens_unified.json not found")
            return

        lock_path = str(unified_path) + '.lock'

        try:
            with FileLock(lock_path, timeout=10):
                # Load tokens
                with open(unified_path, 'r', encoding='utf-8') as f:
                    tokens = json.load(f)

                if token_id not in tokens:
                    print(f"[ERROR] Token {token_id} not found in unified DB")
                    return

                # Get token info
                token_info = self.get_token_info(contract_address, chain)
                if not token_info:
                    print(f"[ERROR] Failed to fetch on-chain data for {contract_address}")
                    return

                # Get current price
                current_price = tokens[token_id].get('current_snapshot', {}).get('last_price', 0)

                # Track deposit history
                deposit_record = self.track_deposit_history(
                    token_id, contract_address, chain, exchange, current_price
                )

                # Update on_chain_data
                tokens[token_id]['on_chain_data'] = {
                    'contract_address': contract_address,
                    'chain': chain,
                    'total_supply': token_info.get('total_supply'),
                    'decimals': token_info.get('decimals'),
                    'verified': token_info.get('verified'),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }

                # Update exchange_deposit if balance tracking succeeded
                if deposit_record:
                    balance = deposit_record['balance']
                    market_cap = deposit_record['market_cap_usd']

                    # Calculate percentage of total supply
                    total_supply_human = int(token_info.get('total_supply', 0)) / (10 ** token_info.get('decimals', 18))
                    percentage = (balance / total_supply_human * 100) if total_supply_human > 0 else 0

                    tokens[token_id]['exchange_deposit'] = {
                        'current_balance': balance,
                        'market_cap_usd': market_cap,
                        'percentage_of_supply': percentage,
                        'wallet_address': deposit_record['wallet_address'],
                        'last_updated': deposit_record['timestamp'],
                        'data_source': f'{chain.lower()}scan',
                        'movement_detected': deposit_record['movement_detected'],
                        'movement_pct': deposit_record['movement_pct']
                    }

                # Save updated data
                with open(unified_path, 'w', encoding='utf-8') as f:
                    json.dump(tokens, f, indent=2, ensure_ascii=False)

                print(f"[SUCCESS] ✅ Updated on-chain data for {token_id}")

        except Exception as e:
            print(f"[ERROR] Failed to update token data: {e}")


def scan_premium_pool_onchain_data():
    """
    Scan all premium pool tokens and update on-chain data
    (To be called 12 times per day, same frequency as regular scans)
    """
    print(f"\n{'='*60}")
    print(f"🔗 On-Chain Data Collection - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    # Load premium pool
    premium_pool_paths = [
        Path('data/shards/premium_pool.json'),
        Path('premium_pool.json')
    ]

    premium_pool_path = None
    for path in premium_pool_paths:
        if path.exists():
            premium_pool_path = path
            break

    if not premium_pool_path:
        print("[ERROR] premium_pool.json not found")
        return

    try:
        with open(premium_pool_path, 'r', encoding='utf-8') as f:
            premium_tokens = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load premium_pool.json: {e}")
        return

    collector = OnChainCollector()

    # Load contract addresses from tokens_unified.json
    unified_paths = [
        Path('data/unified/tokens_unified.json'),
        Path('data/tokens_unified.json')
    ]

    unified_path = None
    for path in unified_paths:
        if path.exists():
            unified_path = path
            break

    if not unified_path:
        print("[ERROR] tokens_unified.json not found")
        return

    try:
        with open(unified_path, 'r', encoding='utf-8') as f:
            all_tokens = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load tokens_unified.json: {e}")
        return

    # Scan each premium pool token
    scanned_count = 0
    skipped_count = 0

    for token_id, token_data in premium_tokens.items():
        # Check if on_chain_data exists
        unified_token = all_tokens.get(token_id, {})
        on_chain_data = unified_token.get('on_chain_data', {})

        if not on_chain_data.get('contract_address'):
            print(f"[SKIP] {token_id}: No contract address configured")
            skipped_count += 1
            continue

        contract_address = on_chain_data['contract_address']
        chain = on_chain_data.get('chain', 'ETH')
        exchange = token_data.get('exchange', 'unknown')

        try:
            collector.update_token_onchain_data(token_id, contract_address, chain, exchange)
            scanned_count += 1

            # Rate limit: 5 calls/sec for free tier
            time.sleep(0.25)

        except Exception as e:
            print(f"[ERROR] Failed to scan {token_id}: {e}")

    print(f"\n{'='*60}")
    print(f"✅ On-Chain Scan Complete")
    print(f"   Scanned: {scanned_count} tokens")
    print(f"   Skipped: {skipped_count} tokens (no contract address)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Test with a single token
    collector = OnChainCollector()

    # Example: Track WBTC on Gate.io
    # collector.update_token_onchain_data(
    #     token_id='gateio_wbtc_usdt',
    #     contract_address='0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
    #     chain='ETH',
    #     exchange='gateio'
    # )

    # Or run full premium pool scan
    scan_premium_pool_onchain_data()
