web: python -m streamlit run apps/crypto_dashboard.py --server.port $PORT --server.address 0.0.0.0
worker: python services/scanner_scheduler.py start
worker2: python services/premium_pool_collector.py --continuous
