# auth.py

from functools import wraps
from flask import redirect, url_for, session
from utils import get_user, check_login as db_check

def login_user(sess, username):
    user = get_user(username)
    if not user or not user.is_active:
        return False
    sess.update({
        'username': user.username,
        'is_admin': user.is_admin,
        'color'   : user.color
    })
    return True

def logout_user(sess):
    sess.clear()

def check_login(username, password):

    return db_check(username, password)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('stream'))
        return f(*args, **kwargs)
    return decorated