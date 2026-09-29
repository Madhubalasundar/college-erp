"""
Security utilities for the College ERP.
Provides CSRF protection, rate limiting, and other security helpers.
"""
import secrets
import hmac
import time
from functools import wraps
from flask import request, flash, redirect, url_for, session


# ---------------------------------------------------------------
# Rate limiting (simple in-memory implementation)
# ---------------------------------------------------------------

_login_attempts = {}  # {ip_address: [timestamp, ...]}


def _get_client_key():
    """Get a key for rate limiting based on client IP."""
    return request.remote_addr or "unknown"


def rate_limit(max_attempts=5, window=300):
    """
    Rate limit decorator for login attempts.

    Args:
        max_attempts: Maximum number of attempts allowed within the window.
        window: Time window in seconds (default: 5 minutes).
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            key = _get_client_key()
            now = time.time()

            # Initialize if needed
            if key not in _login_attempts:
                _login_attempts[key] = []

            # Remove attempts outside the window
            _login_attempts[key] = [
                t for t in _login_attempts[key] if now - t < window
            ]

            # Check if limit exceeded
            if len(_login_attempts[key]) >= max_attempts:
                flash(
                    "Too many failed attempts. Please try again in a few minutes.",
                    "danger",
                )
                return redirect(url_for("auth.student_login"))

            return f(*args, **kwargs)
        return wrapped
    return decorator


def record_failed_attempt():
    """Record a failed login attempt for rate limiting."""
    key = _get_client_key()
    now = time.time()

    if key not in _login_attempts:
        _login_attempts[key] = []

    _login_attempts[key].append(now)


def clear_failed_attempts():
    """Clear failed login attempts (call on successful login)."""
    key = _get_client_key()
    if key in _login_attempts:
        _login_attempts[key] = []


# ---------------------------------------------------------------
# CSRF protection
# ---------------------------------------------------------------


def generate_csrf_token():
    """Generate a CSRF token for forms."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token():
    """
    Validate the CSRF token from a form submission.
    Returns True if valid, False otherwise.
    """
    token = session.pop("_csrf_token", None)
    form_token = request.form.get("_csrf_token")

    if not token or not form_token:
        return False

    return hmac.compare_digest(token, form_token)
