# utils.py
from models import db, User, Setting 
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
import time, hmac, hashlib
from functools import lru_cache
import secrets

@lru_cache
def _hls_secret() -> bytes:
    s = Setting.query.first()

    if not s:
        s = Setting()
        db.session.add(s)

    if not s.hls_secret:
        s.hls_secret = secrets.token_urlsafe(32)
        db.session.commit()

    return s.hls_secret.encode()

def clear_hls_secret_cache():
    _hls_secret.cache_clear()

def generate_hls_token(username: str, expires_in: int = 60) -> str:
    expiry = int(time.time()) + expires_in
    msg = f"{username}:{expiry}".encode()
    signature = hmac.new(_hls_secret(), msg, hashlib.sha256).hexdigest()
    return f"{expiry}:{signature}"

def validate_hls_token(username: str, token: str) -> bool:
    try:
        expiry, signature = token.split(":")
        expiry = int(expiry)
        if expiry < time.time():
            return False
        msg = f"{username}:{expiry}".encode()
        expected = hmac.new(_hls_secret(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False

def create_user(username, password, *, is_admin=False,
                color="#000000", is_active=True) -> bool:
    try:
        user = User(username=username,
                    password=generate_password_hash(password),
                    is_admin=is_admin,
                    color=color,
                    is_active=is_active)
        db.session.add(user)
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False


def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        db.session.delete(user)
        db.session.commit()

def check_login(username, password) -> bool:
    user = User.query.filter_by(username=username).first()
    return bool(user and user.is_active and check_password_hash(user.password, password))


def update_user_password(username, new_password) -> bool:
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    user.password = generate_password_hash(new_password)
    db.session.commit()
    return True

def update_user_color(username, color):
    user = User.query.filter_by(username=username).first()
    if user:
        user.color = color
        db.session.commit()


def set_user_active(username, active: bool) -> bool:
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    user.is_active = active
    db.session.commit()
    return True

def get_user(username):
    return User.query.filter_by(username=username).first()

def get_all_users():
    return User.query.all()
