"""
Telegram Login & Integration Module
====================================
Telegram username-based login with messaging and payment integration
Features:
- User authentication via Telegram username
- Alert messaging to Telegram (future: via Bot API)
- Payment processing (future: Telegram Stars/Payments)
- User subscription management
"""

import streamlit as st
import json
import os
import random
import string
from datetime import datetime, timezone, timedelta

# Future integration placeholders
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", None)  # Set via environment
TELEGRAM_PAYMENT_TOKEN = os.getenv("TELEGRAM_PAYMENT_TOKEN", None)  # For payments


def init_session_state():
    """Initialize session state for login."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "telegram_username" not in st.session_state:
        st.session_state.telegram_username = None
    if "user_tier" not in st.session_state:
        st.session_state.user_tier = "free"  # free, pro, premium
    if "verification_pending" not in st.session_state:
        st.session_state.verification_pending = False
    if "verification_username" not in st.session_state:
        st.session_state.verification_username = None
    if "verification_code" not in st.session_state:
        st.session_state.verification_code = None


def load_users():
    """Load registered users from file."""
    users_file = "data/users.json"
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_users(users):
    """Save users to file."""
    users_file = "data/users.json"
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def register_user(telegram_username, tier="free", telegram_chat_id=None):
    """Register a new user."""
    users = load_users()
    
    # Remove @ if present
    telegram_username = telegram_username.lstrip('@')
    
    if telegram_username in users:
        return False, "User already exists"
    
    users[telegram_username] = {
        "telegram_username": telegram_username,
        "telegram_chat_id": telegram_chat_id,  # For direct messaging
        "tier": tier,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "watchlist": [],
        "alert_settings": {
            "enabled": True,
            "spread_threshold": 2.0,
            "depth_threshold": 500,
            "volume_threshold": 10000,
            "grade_alert": ["D", "F"]  # Alert on D and F grades
        },
        "payment_history": [],
        "subscription_expires": None
    }
    
    save_users(users)
    return True, "Registration successful"


def generate_verification_code():
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


def send_verification_code(telegram_username, code):
    """
    Send verification code to Telegram user.
    
    Args:
        telegram_username: User's Telegram username
        code: 6-digit verification code
    
    Returns:
        bool: True if sent successfully
    
    Note: For now, stores code in pending verifications file.
    TODO: Send via Telegram Bot API when available.
    """
    pending_file = "pending_verifications.json"
    pending = {}
    
    if os.path.exists(pending_file):
        try:
            with open(pending_file, 'r', encoding='utf-8') as f:
                pending = json.load(f)
        except:
            pending = {}
    
    # Store verification code with expiry time (10 minutes for better UX)
    pending[telegram_username] = {
        "code": code,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        with open(pending_file, 'w', encoding='utf-8') as f:
            json.dump(pending, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving verification code: {e}")
        return False


def verify_code(telegram_username, code):
    """
    Verify the entered code.
    
    Args:
        telegram_username: User's Telegram username
        code: Code entered by user
    
    Returns:
        tuple: (success: bool, message: str)
    """
    pending_file = "pending_verifications.json"
    
    if not os.path.exists(pending_file):
        return False, "No verification pending"
    
    try:
        with open(pending_file, 'r', encoding='utf-8') as f:
            pending = json.load(f)
    except:
        return False, "Verification error"
    
    if telegram_username not in pending:
        return False, "No verification pending for this user"
    
    verification = pending[telegram_username]
    
    # Check if code expired
    expires_at = datetime.fromisoformat(verification['expires_at'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    if now > expires_at:
        # Remove expired verification
        del pending[telegram_username]
        with open(pending_file, 'w', encoding='utf-8') as f:
            json.dump(pending, f, indent=2)
        return False, "Verification code expired. Please request a new one."
    
    # Check if code matches
    if verification['code'] != code:
        return False, "Invalid verification code"
    
    # Code is valid, remove from pending
    del pending[telegram_username]
    with open(pending_file, 'w', encoding='utf-8') as f:
        json.dump(pending, f, indent=2)
    
    return True, "Verification successful"


def login_user(telegram_username):
    """Login user with Telegram username."""
    users = load_users()
    
    # Remove @ if present for consistency
    clean_username = telegram_username.lstrip('@')
    
    # Try to find user with both @ and without @ versions
    user_key = None
    if clean_username in users:
        user_key = clean_username
    elif f"@{clean_username}" in users:
        user_key = f"@{clean_username}"
    
    if user_key is None:
        # Auto-register new users as free tier
        success, msg = register_user(clean_username, tier="free")
        if not success:
            return False, msg
        # Reload users after registration
        users = load_users()
        user_key = clean_username
    
    # Update last login
    users[user_key]["last_login"] = datetime.now(timezone.utc).isoformat()
    save_users(users)
    
    # Set session state
    st.session_state.logged_in = True
    st.session_state.telegram_username = clean_username  # Always store without @
    st.session_state.user_tier = users[user_key]["tier"]
    
    return True, f"Welcome back, @{clean_username}!"


def logout_user():
    """Logout current user."""
    st.session_state.logged_in = False
    st.session_state.telegram_username = None
    st.session_state.user_tier = "free"


def get_current_user():
    """Get current logged-in user info."""
    if not st.session_state.logged_in:
        return None
    
    users = load_users()
    username = st.session_state.telegram_username
    
    # Try to find user with both @ and without @ versions
    clean_username = username.lstrip('@')
    if clean_username in users:
        return users[clean_username]
    elif f"@{clean_username}" in users:
        return users[f"@{clean_username}"]
    elif username in users:
        return users[username]
    
    return None


def update_user_tier(telegram_username, new_tier):
    """Update user subscription tier."""
    users = load_users()
    
    clean_username = telegram_username.lstrip('@')
    
    # Try to find user with both @ and without @ versions
    user_key = None
    if clean_username in users:
        user_key = clean_username
    elif f"@{clean_username}" in users:
        user_key = f"@{clean_username}"
    
    if user_key is not None:
        users[user_key]["tier"] = new_tier
        save_users(users)
        
        # Update session if current user
        if st.session_state.telegram_username == clean_username:
            st.session_state.user_tier = new_tier
        
        return True
    return False


def render_login_page():
    """Render login page."""
    st.title("🔐 Night Watch Login")
    st.caption("Liquidity Threshold & Delisting Monitoring Plus Defense System")
    
    st.markdown("---")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 📱 Telegram Login")
        st.caption("Enter your Telegram username to continue")
        
        telegram_username = st.text_input(
            "Telegram Username",
            placeholder="@your_username or your_username",
            help="Your Telegram username (with or without @)"
        )
        
        col_login, col_help = st.columns([1, 1])
        
        with col_login:
            if st.button("🚀 Login / Sign Up", type="primary", use_container_width=True):
                if telegram_username:
                    telegram_username = telegram_username.strip()
                    success, msg = login_user(telegram_username)
                    
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("⚠️ Please enter your Telegram username")
        
        with col_help:
            with st.popover("❓ Help"):
                st.markdown("""
                **How to find your Telegram username:**
                1. Open Telegram app
                2. Go to Settings
                3. Your username is shown under your name
                4. It looks like: **@your_username**
                
                **Note:** If you don't have a username, you can set one in Telegram Settings.
                """)
        
        st.markdown("---")
        
        # Tier information
        st.markdown("### 🎯 Subscription Tiers")
        
        tier_col1, tier_col2, tier_col3 = st.columns(3)
        
        with tier_col1:
            st.markdown("""
            **FREE**
            - Main Board access
            - 10 watchlist tokens
            - 60min update interval
            """)
        
        with tier_col2:
            st.markdown("""
            **PRO** - $99/month
            - Everything in FREE
            - 5min update interval
            - Liquidity Analytics
            - Custom Monitoring
            - Micro Burst (5 snapshots)
            """)
        
        with tier_col3:
            st.markdown("""
            **PREMIUM** - $2000/month
            - Everything in PRO
            - Auto LP Machine
            - Delisting Defense
            - API auto/manual orders
            - AI liquidity supply
            - Micro Burst (20 snapshots)
            """)


def render_user_info():
    """Render user info in sidebar."""
    if st.session_state.logged_in:
        user = get_current_user()
        if user:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👤 User Info")
            
            # User tier badge
            tier_colors = {
                "free": "🆓",
                "pro": "⚡",
                "premium": "👑"
            }
            tier_emoji = tier_colors.get(user["tier"], "🆓")
            
            st.sidebar.markdown(f"**{tier_emoji} @{user['telegram_username']}**")
            st.sidebar.caption(f"Tier: {user['tier'].upper()}")
            
            # Logout button
            if st.sidebar.button("🚪 Logout", use_container_width=True):
                logout_user()
                st.rerun()
            
            st.sidebar.markdown("---")


def render_sidebar_login():
    """Render login/account interface in sidebar."""
    st.sidebar.markdown("---")
    
    if st.session_state.logged_in:
        # Show user account info
        user = get_current_user()
        if user:
            tier_colors = {
                "free": "🆓",
                "pro": "⚡",
                "premium": "👑"
            }
            tier_emoji = tier_colors.get(user["tier"], "🆓")
            
            st.sidebar.markdown("### 👤 Account")
            # Get username safely - try different possible keys
            username = user.get('telegram_username') or user.get('user_id') or st.session_state.get('telegram_username', 'Unknown')
            # Remove @ if present for display
            display_username = username.lstrip('@')
            st.sidebar.markdown(f"**{tier_emoji} @{display_username}**")
            st.sidebar.caption(f"Plan: {user['tier'].upper()}")
            
            # Upgrade button
            if user['tier'] != 'premium':
                if st.sidebar.button("⚡ Upgrade", use_container_width=True, key="sidebar_upgrade"):
                    st.session_state['show_login_modal'] = True
                    st.rerun()
            
            # Logout button
            if st.sidebar.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
                logout_user()
                st.rerun()
    else:
        # Show login button
        st.sidebar.markdown("### ☰ Menu")
        
        if st.sidebar.button("🔐 Login / Sign Up", type="primary", use_container_width=True, key="sidebar_login"):
            # Start verification flow in sidebar
            if 'sidebar_verification_pending' not in st.session_state:
                st.session_state['sidebar_verification_pending'] = False
            st.session_state['sidebar_verification_pending'] = not st.session_state.get('sidebar_verification_pending', False)
            st.rerun()
        
        # Verification flow in sidebar
        if st.session_state.get('sidebar_verification_pending', False):
            if st.session_state.get('verification_pending', False):
                # Show verification code input
                st.sidebar.markdown("---")
                st.sidebar.markdown("#### 📨 Verification")
                st.sidebar.caption(f"Code sent to @{st.session_state.verification_username}")
                
                # Display code (for development)
                if st.session_state.verification_code:
                    st.sidebar.info(f"🔑 Code: **{st.session_state.verification_code}**")
                
                verification_code = st.sidebar.text_input(
                    "6-digit Code",
                    placeholder="000000",
                    max_chars=6,
                    key="sidebar_verification_code"
                )
                
                if st.sidebar.button("✅ Verify", use_container_width=True, key="sidebar_verify"):
                    if verification_code and len(verification_code) == 6:
                        username = st.session_state.verification_username
                        success, msg = verify_code(username, verification_code)
                        
                        if success:
                            login_success, login_msg = login_user(username)
                            if login_success:
                                st.sidebar.success("✅ Welcome!")
                                st.session_state['verification_pending'] = False
                                st.session_state['sidebar_verification_pending'] = False
                                st.session_state['verification_username'] = None
                                st.session_state['verification_code'] = None
                                st.rerun()
                        else:
                            st.sidebar.error(msg)
                    else:
                        st.sidebar.warning("Enter 6-digit code")
                
                if st.sidebar.button("🔄 Resend", use_container_width=True, key="sidebar_resend"):
                    username = st.session_state.verification_username
                    new_code = generate_verification_code()
                    send_verification_code(username, new_code)
                    st.session_state.verification_code = new_code
                    st.sidebar.success("✅ Code sent!")
                    st.rerun()
                
                if st.sidebar.button("« Back", key="sidebar_back"):
                    st.session_state['verification_pending'] = False
                    st.session_state['sidebar_verification_pending'] = False
                    st.session_state['verification_username'] = None
                    st.session_state['verification_code'] = None
                    st.rerun()
            else:
                # Show username input
                st.sidebar.markdown("---")
                st.sidebar.markdown("#### 🔐 Login")
                
                telegram_username = st.sidebar.text_input(
                    "Telegram Username",
                    placeholder="@username",
                    key="sidebar_username"
                )
                
                if st.sidebar.button("📨 Send Code", use_container_width=True, key="sidebar_send_code"):
                    if telegram_username:
                        telegram_username = telegram_username.strip().lstrip('@')
                        
                        code = generate_verification_code()
                        send_verification_code(telegram_username, code)
                        
                        st.session_state['verification_pending'] = True
                        st.session_state['verification_username'] = telegram_username
                        st.session_state['verification_code'] = code
                        
                        st.sidebar.success("✅ Code sent!")
                        st.rerun()
                    else:
                        st.sidebar.warning("Enter username")
                
                if st.sidebar.button("✕ Cancel", key="sidebar_cancel"):
                    st.session_state['sidebar_verification_pending'] = False
                    st.rerun()
    
    st.sidebar.markdown("---")


def require_login(tier_required=None):
    """
    Decorator/function to require login for a page.
    
    Args:
        tier_required: Optional tier requirement ("free", "pro", "premium")
    
    Returns:
        bool: True if user has required access, False otherwise
    """
    if not st.session_state.logged_in:
        render_login_page()
        return False
    
    if tier_required:
        user_tier = st.session_state.user_tier
        tier_hierarchy = ["free", "pro", "premium"]
        
        required_level = tier_hierarchy.index(tier_required) if tier_required in tier_hierarchy else 0
        user_level = tier_hierarchy.index(user_tier) if user_tier in tier_hierarchy else 0
        
        if user_level < required_level:
            st.error(f"🔒 This feature requires {tier_required.upper()} tier or higher")
            st.info(f"Your current tier: {user_tier.upper()}")
            
            st.markdown("### ⚡ Upgrade Your Plan")
            if tier_required == "pro":
                st.markdown("**PRO Plan - $99/month**")
                st.markdown("- 5min update interval\n- Liquidity Analytics\n- Custom Monitoring\n- Micro Burst Analysis")
            elif tier_required == "premium":
                st.markdown("**PREMIUM Plan - $2000/month**")
                st.markdown("- Auto LP Machine\n- Delisting Defense\n- API Orders\n- AI Liquidity Supply")
            
            if st.button("📞 Contact Sales", type="primary"):
                st.info("📧 Contact: sales@nightwatch.io")
            
            return False
    
    return True


# ===========================
# TELEGRAM MESSAGING FUNCTIONS
# ===========================

def send_telegram_alert(telegram_username, message, alert_type="info"):
    """
    Send alert message to Telegram user.
    
    Args:
        telegram_username: User's Telegram username
        message: Alert message to send
        alert_type: Type of alert ("info", "warning", "critical")
    
    Returns:
        bool: True if sent successfully, False otherwise
    
    Note: Requires TELEGRAM_BOT_TOKEN to be set and user's chat_id to be known.
    For now, this stores alerts in user's alert history.
    """
    users = load_users()
    telegram_username = telegram_username.lstrip('@')
    
    if telegram_username not in users:
        return False
    
    user = users[telegram_username]
    
    # Check if alerts are enabled
    if not user.get("alert_settings", {}).get("enabled", True):
        return False
    
    # Store alert in history (for future retrieval)
    if "alert_history" not in user:
        user["alert_history"] = []
    
    alert = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": alert_type,
        "message": message,
        "delivered": False  # Will be True when actually sent via Bot API
    }
    
    user["alert_history"].append(alert)
    
    # Keep only last 100 alerts
    user["alert_history"] = user["alert_history"][-100:]
    
    users[telegram_username] = user
    save_users(users)
    
    # TODO: Actual Telegram Bot API call
    # if TELEGRAM_BOT_TOKEN and user.get("telegram_chat_id"):
    #     import requests
    #     url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    #     payload = {
    #         "chat_id": user["telegram_chat_id"],
    #         "text": f"🚨 {alert_type.upper()}: {message}",
    #         "parse_mode": "Markdown"
    #     }
    #     response = requests.post(url, json=payload)
    #     if response.status_code == 200:
    #         alert["delivered"] = True
    #         users[telegram_username]["alert_history"][-1] = alert
    #         save_users(users)
    #         return True
    
    return True  # Return True for now (stored in history)


def send_coin_alert(telegram_username, exchange, symbol, metrics):
    """
    Send coin-specific alert to user.
    
    Args:
        telegram_username: User's Telegram username
        exchange: Exchange name
        symbol: Trading pair symbol
        metrics: Dict with spread, depth, volume, grade
    """
    user = get_current_user() if st.session_state.telegram_username == telegram_username else None
    
    if not user:
        users = load_users()
        user = users.get(telegram_username.lstrip('@'))
    
    if not user:
        return False
    
    alert_settings = user.get("alert_settings", {})
    
    # Check if alert should be triggered
    should_alert = False
    alert_reasons = []
    
    spread = metrics.get("spread", 0)
    depth = metrics.get("depth_2pct", 0)
    volume = metrics.get("volume_24h", 0)
    grade = metrics.get("grade", "A")
    
    if spread > alert_settings.get("spread_threshold", 2.0):
        should_alert = True
        alert_reasons.append(f"High spread: {spread:.2f}%")
    
    if depth < alert_settings.get("depth_threshold", 500):
        should_alert = True
        alert_reasons.append(f"Low depth: ${depth:.0f}")
    
    if volume < alert_settings.get("volume_threshold", 10000):
        should_alert = True
        alert_reasons.append(f"Low volume: ${volume:.0f}")
    
    if grade in alert_settings.get("grade_alert", ["D", "F"]):
        should_alert = True
        alert_reasons.append(f"Risk grade: {grade}")
    
    if should_alert:
        message = f"""
🚨 **ALERT: {symbol} on {exchange}**

{chr(10).join(['• ' + r for r in alert_reasons])}

Grade: {grade}
Spread: {spread:.2f}%
±2% Depth: ${depth:.0f}
24h Volume: ${volume:.0f}

🔗 Check details: http://localhost:8502/?token={symbol}&exchange={exchange}
"""
        
        alert_type = "critical" if grade == "F" else "warning" if grade == "D" else "info"
        return send_telegram_alert(telegram_username, message, alert_type)
    
    return False


# ===========================
# PAYMENT PROCESSING FUNCTIONS
# ===========================

def create_payment_invoice(telegram_username, plan="pro", duration_months=1):
    """
    Create payment invoice for subscription upgrade.
    
    Args:
        telegram_username: User's Telegram username
        plan: Subscription plan ("pro" or "premium")
        duration_months: Subscription duration in months
    
    Returns:
        dict: Invoice details or None if failed
    
    Note: For future Telegram Payments API integration
    """
    users = load_users()
    telegram_username = telegram_username.lstrip('@')
    
    if telegram_username not in users:
        return None
    
    prices = {
        "pro": 99,
        "premium": 2000
    }
    
    if plan not in prices:
        return None
    
    total_amount = prices[plan] * duration_months
    
    invoice = {
        "invoice_id": f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "telegram_username": telegram_username,
        "plan": plan,
        "duration_months": duration_months,
        "amount": total_amount,
        "currency": "USD",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    }
    
    # Store invoice
    invoices_file = "invoices.json"
    invoices = {}
    if os.path.exists(invoices_file):
        try:
            with open(invoices_file, 'r', encoding='utf-8') as f:
                invoices = json.load(f)
        except:
            invoices = {}
    
    invoices[invoice["invoice_id"]] = invoice
    
    with open(invoices_file, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, indent=2)
    
    # TODO: Telegram Payments API integration
    # if TELEGRAM_PAYMENT_TOKEN and user.get("telegram_chat_id"):
    #     # Send invoice via Bot API
    #     pass
    
    return invoice


def process_payment(invoice_id, payment_method="telegram"):
    """
    Process payment for an invoice.
    
    Args:
        invoice_id: Invoice ID to process
        payment_method: Payment method used
    
    Returns:
        bool: True if payment successful
    """
    invoices_file = "invoices.json"
    if not os.path.exists(invoices_file):
        return False
    
    try:
        with open(invoices_file, 'r', encoding='utf-8') as f:
            invoices = json.load(f)
    except:
        return False
    
    if invoice_id not in invoices:
        return False
    
    invoice = invoices[invoice_id]
    
    if invoice["status"] != "pending":
        return False
    
    # Update invoice status
    invoice["status"] = "paid"
    invoice["paid_at"] = datetime.now(timezone.utc).isoformat()
    invoice["payment_method"] = payment_method
    
    invoices[invoice_id] = invoice
    
    with open(invoices_file, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, indent=2)
    
    # Update user tier and subscription
    telegram_username = invoice["telegram_username"]
    plan = invoice["plan"]
    duration_months = invoice["duration_months"]
    
    users = load_users()
    if telegram_username in users:
        user = users[telegram_username]
        user["tier"] = plan
        
        # Calculate subscription expiry
        if user.get("subscription_expires"):
            try:
                expires = datetime.fromisoformat(user["subscription_expires"].replace('Z', '+00:00'))
            except:
                expires = datetime.now(timezone.utc)
        else:
            expires = datetime.now(timezone.utc)
        
        new_expires = expires + timedelta(days=30 * duration_months)
        user["subscription_expires"] = new_expires.isoformat()
        
        # Add to payment history
        if "payment_history" not in user:
            user["payment_history"] = []
        
        user["payment_history"].append({
            "invoice_id": invoice_id,
            "plan": plan,
            "amount": invoice["amount"],
            "duration_months": duration_months,
            "paid_at": invoice["paid_at"]
        })
        
        users[telegram_username] = user
        save_users(users)
        
        # Send confirmation message
        send_telegram_alert(
            telegram_username,
            f"✅ Payment successful! Your {plan.upper()} subscription is now active until {new_expires.strftime('%Y-%m-%d')}.",
            "info"
        )
        
        return True
    
    return False


def check_subscription_status(telegram_username):
    """
    Check if user's subscription is still valid.
    
    Returns:
        bool: True if subscription is active
    """
    users = load_users()
    clean_username = telegram_username.lstrip('@')
    
    # Try to find user with both @ and without @ versions
    user_key = None
    if clean_username in users:
        user_key = clean_username
    elif f"@{clean_username}" in users:
        user_key = f"@{clean_username}"
    
    if user_key is None:
        return False
    
    user = users[user_key]
    
    # Free tier is always active
    if user["tier"] == "free":
        return True
    
    # Check subscription expiry
    if not user.get("subscription_expires"):
        # No expiry set, downgrade to free
        user["tier"] = "free"
        users[user_key] = user
        save_users(users)
        return False
    
    try:
        expires = datetime.fromisoformat(user["subscription_expires"].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if now > expires:
            # Subscription expired, downgrade to free
            user["tier"] = "free"
            users[user_key] = user
            save_users(users)
            
            send_telegram_alert(
                clean_username,
                "⚠️ Your subscription has expired. You have been downgraded to FREE tier.",
                "warning"
            )
            
            return False
        
        return True
    
    except:
        return False

