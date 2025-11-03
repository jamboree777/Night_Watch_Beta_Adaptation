"""
Production System Control Module
===============================
프로덕션 환경을 위한 시스템 컨트롤 및 모니터링
"""

import streamlit as st
import os
import json
import subprocess
import sys
import psutil
import time
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def render_production_control():
    """프로덕션 환경용 시스템 컨트롤 UI"""
    st.title("🎛️ Production System Control")
    st.caption("클라우드 서버 환경을 위한 시스템 모니터링 및 제어")
    
    # 환경 정보
    render_environment_info()
    
    # 시스템 상태 모니터링
    render_system_monitoring()
    
    # 서비스 관리
    render_service_management()
    
    # 로그 관리
    render_log_management()
    
    # 배치 작업 관리
    render_batch_management()
    
    # 백업 및 복구
    render_backup_management()
    
    # 알림 설정
    render_notification_settings()


def render_environment_info():
    """환경 정보 표시"""
    st.subheader("🌍 Environment Information")
    
    # 환경 감지
    is_production = os.getenv('ENVIRONMENT', 'development') == 'production'
    is_docker = os.path.exists('/.dockerenv')
    is_cloud = os.getenv('CLOUD_PROVIDER') is not None
    
    env_col1, env_col2, env_col3, env_col4 = st.columns(4)
    
    with env_col1:
        st.metric("환경", "Production" if is_production else "Development")
    
    with env_col2:
        st.metric("컨테이너", "Docker" if is_docker else "Native")
    
    with env_col3:
        st.metric("클라우드", os.getenv('CLOUD_PROVIDER', 'Local'))
    
    with env_col4:
        st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}")
    
    # 시스템 정보
    st.markdown("---")
    st.markdown("#### 📋 System Details")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.text(f"OS: {os.name}")
        st.text(f"Platform: {sys.platform}")
        st.text(f"Working Directory: {os.getcwd()}")
    
    with info_col2:
        st.text(f"Hostname: {os.uname().nodename if hasattr(os, 'uname') else 'Unknown'}")
        st.text(f"User: {os.getenv('USER', 'Unknown')}")
        st.text(f"Process ID: {os.getpid()}")


def render_system_monitoring():
    """시스템 모니터링"""
    st.subheader("📊 System Monitoring")
    
    # CPU 및 메모리 사용률
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        monitor_col1, monitor_col2, monitor_col3, monitor_col4 = st.columns(4)
        
        with monitor_col1:
            st.metric("CPU 사용률", f"{cpu_percent}%")
        
        with monitor_col2:
            st.metric("메모리 사용률", f"{memory.percent}%")
        
        with monitor_col3:
            st.metric("디스크 사용률", f"{disk.percent}%")
        
        with monitor_col4:
            # 실행 중인 프로세스 수
            process_count = len(psutil.pids())
            st.metric("실행 프로세스", process_count)
        
        # 메모리 상세 정보
        st.markdown("#### 💾 Memory Details")
        mem_col1, mem_col2, mem_col3 = st.columns(3)
        
        with mem_col1:
            st.text(f"Total: {memory.total / (1024**3):.2f} GB")
        with mem_col2:
            st.text(f"Used: {memory.used / (1024**3):.2f} GB")
        with mem_col3:
            st.text(f"Available: {memory.available / (1024**3):.2f} GB")
        
    except Exception as e:
        st.error(f"시스템 모니터링 오류: {e}")


def render_service_management():
    """서비스 관리"""
    st.subheader("🔧 Service Management")
    
    # 서비스 상태 확인
    services = [
        ("Night Watch Main", "night_watch_board.py"),
        ("User Dashboard", "simple_user_dashboard.py"),
        ("Admin Dashboard", "crypto_dashboard.py"),
        ("Scan Coordinator", "scan_coordinator.py"),
        ("Premium Pool Collector", "premium_pool_collector.py")
    ]
    
    st.markdown("#### 🚀 Service Status")
    
    for service_name, script_name in services:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.text(service_name)
        
        with col2:
            # 프로세스 확인 (Windows/Linux 호환)
            try:
                # Check for scan_coordinator.py using coordinator_status.json
                if script_name == "scan_coordinator.py":
                    status_file = "coordinator_status.json"
                    if os.path.exists(status_file):
                        with open(status_file, 'r', encoding='utf-8') as f:
                            status_data = json.load(f)
                            last_heartbeat = status_data.get('last_heartbeat', '')
                            if last_heartbeat:
                                from datetime import datetime, timezone, timedelta
                                dt = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                                ago = datetime.now(timezone.utc) - dt
                                if ago.total_seconds() < 300:  # 5 minutes
                                    st.success("Running")
                                else:
                                    st.error("Stopped")
                            else:
                                st.error("Stopped")
                    else:
                        st.error("Stopped")
                else:
                    # Generic process check using psutil
                    is_running = False
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            cmdline = proc.info.get('cmdline', [])
                            if cmdline and script_name in ' '.join(cmdline):
                                is_running = True
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

                    if is_running:
                        st.success("Running")
                    else:
                        st.error("Stopped")
            except Exception as e:
                st.warning(f"Unknown: {str(e)[:30]}")
        
        with col3:
            if st.button("Restart", key=f"restart_{script_name}"):
                restart_service(script_name)
                st.rerun()
    
    # 전체 서비스 제어
    st.markdown("---")
    st.markdown("#### 🎮 Global Service Control")
    
    control_col1, control_col2, control_col3 = st.columns(3)
    
    with control_col1:
        if st.button("🔄 Restart All Services", type="primary"):
            restart_all_services()
            st.rerun()
    
    with control_col2:
        if st.button("⏹️ Stop All Services"):
            stop_all_services()
            st.rerun()
    
    with control_col3:
        if st.button("📊 Service Health Check"):
            perform_health_check()


def render_log_management():
    """로그 관리"""
    st.subheader("📝 Log Management")
    
    # 로그 파일 목록
    log_files = [
        "logs/scanner.log",
        "logs/average.log", 
        "logs/error.log",
        "logs/premium_pool.log",
        "logs/system.log"
    ]
    
    st.markdown("#### 📋 Available Log Files")
    
    for log_file in log_files:
        if os.path.exists(log_file):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.text(log_file)
            
            with col2:
                try:
                    size = os.path.getsize(log_file)
                    st.text(f"{size / 1024:.1f} KB")
                except:
                    st.text("N/A")
            
            with col3:
                if st.button("View", key=f"view_{log_file}"):
                    view_log_file(log_file)
        else:
            st.text(f"{log_file} (Not found)")
    
    # 로그 정리
    st.markdown("---")
    st.markdown("#### 🧹 Log Maintenance")
    
    log_col1, log_col2, log_col3 = st.columns(3)
    
    with log_col1:
        if st.button("🗑️ Clear Old Logs"):
            clear_old_logs()
            st.rerun()
    
    with log_col2:
        if st.button("📦 Archive Logs"):
            archive_logs()
            st.rerun()
    
    with log_col3:
        if st.button("📊 Log Statistics"):
            show_log_statistics()


def render_batch_management():
    """배치 작업 관리"""
    st.subheader("⏰ Batch Job Management")
    
    # 스케줄된 작업
    st.markdown("#### 📅 Scheduled Jobs")
    
    jobs = [
        ("Regular Scan", "Every 2 hours", "scan_coordinator.py"),
        ("Premium Pool", "Every 1 minute", "premium_pool_collector.py"),
        ("Token Age Check", "Daily", "batch_honeymoon_check.py")
    ]
    
    for job_name, schedule, script in jobs:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        with col1:
            st.text(job_name)
        
        with col2:
            st.text(schedule)
        
        with col3:
            if st.button("Run Now", key=f"run_{script}"):
                run_batch_job(script)
                st.rerun()
        
        with col4:
            if st.button("Stop", key=f"stop_{script}"):
                stop_batch_job(script)
                st.rerun()
    
    # 수동 배치 실행
    st.markdown("---")
    st.markdown("#### 🔧 Manual Batch Execution")
    
    batch_script = st.selectbox(
        "Select Batch Script",
        [
            "batch_scanner.py",
            "detect_missing_tokens.py",
            "batch_honeymoon_check.py",
            "check_token_ages.py"
        ]
    )
    
    if st.button("▶️ Execute Batch Script", type="primary"):
        execute_batch_script(batch_script)


def render_backup_management():
    """백업 및 복구"""
    st.subheader("💾 Backup & Recovery")
    
    # 백업 상태
    st.markdown("#### 📦 Backup Status")
    
    backup_col1, backup_col2, backup_col3 = st.columns(3)
    
    with backup_col1:
        if os.path.exists("backups"):
            backup_count = len([f for f in os.listdir("backups") if f.endswith('.json')])
            st.metric("Backup Files", backup_count)
        else:
            st.metric("Backup Files", 0)
    
    with backup_col2:
        if os.path.exists("data/tokens_unified.json"):
            file_size = os.path.getsize("data/tokens_unified.json") / (1024 * 1024)
            st.metric("DB Size", f"{file_size:.2f} MB")
        else:
            st.metric("DB Size", "N/A")
    
    with backup_col3:
        st.metric("Last Backup", "N/A")  # TODO: 실제 백업 시간 추적
    
    # 백업 작업
    st.markdown("---")
    st.markdown("#### 🔄 Backup Operations")
    
    backup_ops_col1, backup_ops_col2, backup_ops_col3 = st.columns(3)
    
    with backup_ops_col1:
        if st.button("💾 Create Backup"):
            create_backup()
            st.rerun()
    
    with backup_ops_col2:
        if st.button("🔄 Restore Backup"):
            restore_backup()
            st.rerun()
    
    with backup_ops_col3:
        if st.button("🗑️ Clean Old Backups"):
            clean_old_backups()
            st.rerun()


def render_notification_settings():
    """알림 설정"""
    st.subheader("🔔 Notification Settings")
    
    # 알림 채널
    st.markdown("#### 📡 Notification Channels")
    
    notif_col1, notif_col2 = st.columns(2)
    
    with notif_col1:
        st.checkbox("Email Notifications", value=True)
        st.checkbox("Telegram Bot", value=True)
        st.checkbox("Discord Webhook", value=False)
    
    with notif_col2:
        st.checkbox("System Log Alerts", value=True)
        st.checkbox("Error Notifications", value=True)
        st.checkbox("Performance Alerts", value=False)
    
    # 알림 조건
    st.markdown("---")
    st.markdown("#### ⚠️ Alert Conditions")
    
    alert_col1, alert_col2 = st.columns(2)
    
    with alert_col1:
        st.number_input("CPU Usage Threshold (%)", min_value=50, max_value=100, value=80)
        st.number_input("Memory Usage Threshold (%)", min_value=50, max_value=100, value=85)
    
    with alert_col2:
        st.number_input("Disk Usage Threshold (%)", min_value=50, max_value=100, value=90)
        st.number_input("Error Rate Threshold (%)", min_value=1, max_value=50, value=5)


# 헬퍼 함수들
def restart_service(script_name):
    """서비스 재시작"""
    try:
        # 프로세스 종료
        subprocess.run(['pkill', '-f', script_name], check=False)
        time.sleep(2)
        
        # 서비스 시작
        subprocess.Popen([sys.executable, script_name], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        st.success(f"{script_name} restarted successfully!")
    except Exception as e:
        st.error(f"Failed to restart {script_name}: {e}")


def restart_all_services():
    """모든 서비스 재시작"""
    st.info("Restarting all services...")
    # 구현 필요


def stop_all_services():
    """모든 서비스 중지"""
    st.info("Stopping all services...")
    # 구현 필요


def perform_health_check():
    """헬스 체크 수행"""
    st.info("Performing health check...")
    # 구현 필요


def view_log_file(log_file):
    """로그 파일 보기"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        st.text_area(f"Log Content: {log_file}", content, height=400)
    except Exception as e:
        st.error(f"Failed to read log file: {e}")


def clear_old_logs():
    """오래된 로그 정리"""
    st.info("Clearing old logs...")
    # 구현 필요


def archive_logs():
    """로그 아카이브"""
    st.info("Archiving logs...")
    # 구현 필요


def show_log_statistics():
    """로그 통계 표시"""
    st.info("Showing log statistics...")
    # 구현 필요


def run_batch_job(script):
    """배치 작업 실행"""
    try:
        subprocess.Popen([sys.executable, script])
        st.success(f"Started {script}")
    except Exception as e:
        st.error(f"Failed to start {script}: {e}")


def stop_batch_job(script):
    """배치 작업 중지"""
    try:
        subprocess.run(['pkill', '-f', script])
        st.success(f"Stopped {script}")
    except Exception as e:
        st.error(f"Failed to stop {script}: {e}")


def execute_batch_script(script):
    """배치 스크립트 실행"""
    try:
        result = subprocess.run([sys.executable, script], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            st.success(f"Batch script {script} completed successfully!")
            if result.stdout:
                st.text("Output:")
                st.text(result.stdout)
        else:
            st.error(f"Batch script {script} failed!")
            if result.stderr:
                st.text("Error:")
                st.text(result.stderr)
    except subprocess.TimeoutExpired:
        st.error("Batch script timed out!")
    except Exception as e:
        st.error(f"Failed to execute {script}: {e}")


def create_backup():
    """백업 생성"""
    st.info("Creating backup...")
    # 구현 필요


def restore_backup():
    """백업 복구"""
    st.info("Restoring backup...")
    # 구현 필요


def clean_old_backups():
    """오래된 백업 정리"""
    st.info("Cleaning old backups...")
    # 구현 필요
