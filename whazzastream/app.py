import os
import requests
import json
from flask import (
    Flask, render_template, redirect, url_for,
    request, session, flash, jsonify, abort
)
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash
from auth import (
    check_login, login_user, logout_user,
    login_required, admin_required
)
from chat import handle_chat_messages
from models import db, User, Message, StreamKey, Setting
from smilies import handle_smilie_upload, delete_smilie, get_all_smilies
from configparser import ConfigParser
from urllib.parse import quote_plus
from utils import validate_hls_token, generate_hls_token, clear_hls_secret_cache
from datetime import date, datetime, timedelta
from shop import shop_bp
from lang  import init_i18n


CFG_PATH = "config/config.cfg"
config = ConfigParser(interpolation=None)
config.read(CFG_PATH)

def _get_cfg(section, key, default=None):
    return (config[section].get(key, default)
            if config.has_section(section) else default)

db_user  = _get_cfg("database", "user")
db_pass  = quote_plus(_get_cfg("database", "password", ""))
db_host  = _get_cfg("database", "host")
db_port  = _get_cfg("database", "port", "3306")
db_name  = _get_cfg("database", "database")

admin_user  = _get_cfg("admin", "username") or os.getenv("INIT_ADMIN_USER", "admin")
admin_pass  = _get_cfg("admin", "password") or ""
admin_color = _get_cfg("admin", "color") or "#000000"

discord_webhook = _get_cfg("discord", "webhook")

stream_base_url = _get_cfg("stream", "base_url", "http://localhost:8090")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

init_i18n(app)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280
}

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")
handle_chat_messages(socketio)

app.register_blueprint(shop_bp)

ONLINE_USERS: set[str] = set()
SID_MAP: dict[str, str]  = {}

app.jinja_env.globals["datetime"] = datetime

def send_user_list():
    users = User.query.order_by(User.username).all()
    socketio.emit(
        "online_users",
        [
            {"username": u.username, "online": u.username in ONLINE_USERS, "color": u.color}
            for u in users
        ]
    )

@app.route("/api/online_users")
def api_online_users():
    users = User.query.order_by(User.username).all()
    return jsonify([
        {"username": u.username, "color": u.color}
        for u in users if u.username in ONLINE_USERS
    ])

@socketio.on("user_online")
def user_online(data):
    username = data.get("username")
    if username:
        ONLINE_USERS.add(username)
        SID_MAP[request.sid] = username
        send_user_list()

@socketio.on("disconnect")
def user_left():
    username = SID_MAP.pop(request.sid, None)
    if username:
        ONLINE_USERS.discard(username)
        send_user_list()

def get_current_user():
    uname = session.get("username")
    return User.query.filter_by(username=uname).first() if uname else None

def send_discord_embed(text: str, color: int = 0xFF0000) -> None:
    config.read(CFG_PATH)
    webhook    = _get_cfg("discord", "webhook")
    bot_name   = _get_cfg("discord", "username", "WhazzaStream Bot")
    avatar_url = _get_cfg("discord", "avatar_url", "")
    if not webhook:
        raise RuntimeError("DISCORD_WEBHOOK nicht gesetzt")
    payload = {
        "username": bot_name,
        "avatar_url": avatar_url,
        "embeds": [{"description": text, "color": color}]
    }
    requests.post(webhook, json=payload, timeout=5).raise_for_status()

def _require_json(req):
    try:
        return req.get_json(force=True)
    except Exception:
        return {}

def sanitize_config(path: str = CFG_PATH) -> None:
    cfg = ConfigParser(interpolation=None)
    cfg.read(path)
    if cfg.has_section("admin"):
        cfg.remove_section("admin")
        with open(path, "w") as fh:
            cfg.write(fh)

def is_valid_stream_key(key: str) -> bool:
    return StreamKey.query.filter_by(key=key).first() is not None

@app.route("/rtmp/auth", methods=["GET", "POST"])
def rtmp_auth():
    if is_valid_stream_key(request.values.get("name", "").strip()):
        return "OK", 200
    abort(403)

@app.route("/rtmp/done", methods=["GET", "POST"])
def rtmp_done():
    return "", 204

@app.route("/")
def home():
    return redirect(url_for("stream" if "username" in session else "login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and not user.is_active:
            flash("Account gesperrt – bitte an den Admin wenden.", "error")
            return render_template("login.html")

        if check_login(username, password):
            login_user(session, username)
            current_year=datetime.utcnow().year
            today   = date.today()
            setting = Setting.query.first()
            daily_bonus = (
                setting.daily_bonus if setting and setting.daily_bonus is not None else 20
            )

            if user and user.last_daily_bonus != today:
                user.points += daily_bonus
                user.last_daily_bonus = today
                db.session.commit()
                flash(f"Tagesbonus: +{daily_bonus} Münzen", "success")

            return redirect(url_for("stream"))

        flash("Login fehlgeschlagen", "error")
        return render_template("login.html")

    return render_template("login.html")

@app.route("/logout")
def logout():
    lang = session.get("lang", "de")
    logout_user(session) 
    session["lang"] = lang
    return redirect(url_for("login", lang=lang))

@app.route("/stream")
@login_required
def stream():
    lang = request.args.get("lang", session.get("lang", "de"))
    session["lang"] = lang

    user   = get_current_user()
    points = user.points if user else 0

    total_tokens = sum(user.effect_inventory.values()) if user else 0

    setting = Setting.query.first() or Setting()
    suffix  = setting.stream_suffix or "whazzaStream"
    token   = generate_hls_token(session["username"], expires_in=60)

    return render_template(
        "stream.html",
        username        = session["username"],
        user_color      = user.color if user else "#000000",
        points          = points,
        effect_tokens   = total_tokens,
        stream_suffix   = suffix,
        access_token    = token,
        stream_base_url = stream_base_url,
        bonus_interval  = setting.stream_bonus_interval or 30,
        bonus_points    = setting.stream_bonus_points  or 20,
	    user_font       = user.font or "",
        all_smilies     = get_all_smilies(),
        is_admin        = user.is_admin if user else False
    )

def is_stream_live() -> bool:

    return True

@app.route("/api/stream_heartbeat", methods=["POST"])
@login_required
def stream_heartbeat():
    user = get_current_user()

    if not is_stream_live():
        return jsonify(success=False, message="Stream nicht live"), 400

    setting  = Setting.query.first()
    interval = setting.stream_bonus_interval if setting else 30
    bonus    = setting.stream_bonus_points  if setting else 20

    now = datetime.utcnow()

    if (not user.last_stream_bonus or
        (now - user.last_stream_bonus) >= timedelta(minutes=interval)):

        user.points += bonus
        user.last_stream_bonus = now
        db.session.commit()

        return jsonify(
            success=True,
            message=f"+{bonus} Münzen fürs Zuschauen",
            points=user.points
        )

    return jsonify(
        success=False,
        message="Noch kein Bonus verfügbar",
        points=user.points
    )

@app.route("/admin")
@admin_required
def admin_panel():
    config.read(CFG_PATH)
    
    setting = Setting.query.first() or Setting()

    return render_template(
        "admin.html",
        users=User.query.order_by(User.username).all(),
        online=ONLINE_USERS,
        smilies=get_all_smilies(),
        stream_keys=StreamKey.query.order_by(StreamKey.key).all(),
        stream_suffix=setting.stream_suffix,
        smilie_cost=setting.smilie_cost or 50,
        current_webhook=_get_cfg("discord", "webhook", ""),
        current_botname=_get_cfg("discord", "username", "WhazzaStream Bot"),
        current_avatar=_get_cfg("discord", "avatar_url", ""),
        setting=setting
    )

@app.route("/admin/create_user", methods=["POST"])
@admin_required
def create_user():
    username = request.form["username"].strip()
    if User.query.filter_by(username=username).first():
        flash("Benutzername existiert bereits!", "error")
    else:
        db.session.add(User(
            username=username,
            password=generate_password_hash(request.form["password"]),
            is_admin="is_admin" in request.form,
            is_active=True,
            color=request.form.get("color", "#000000")
        ))
        db.session.commit()
        flash("Benutzer erfolgreich angelegt", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete_user/<username>")
@admin_required
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if user and not user.is_admin:
        db.session.delete(user)
        db.session.commit()
        flash("Benutzer gelöscht", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/change_pw/<username>", methods=["POST"])
@admin_required
def change_pw(username):
    data = _require_json(request)
    new_pw = data.get("new_pw", "").strip()
    user = User.query.filter_by(username=username).first()
    if user and new_pw:
        user.password = generate_password_hash(new_pw)
        db.session.commit()
        return "", 204
    return jsonify({"error": "Bad request"}), 400

@app.route("/admin/toggle_user/<username>", methods=["POST"])
@admin_required
def toggle_user(username):
    state = _require_json(request).get("active")
    if state is None:
        return jsonify({"error": "Bad request"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or user.is_admin:
        return jsonify({"error": "not found"}), 404
    user.is_active = bool(state)
    db.session.commit()
    if not user.is_active and username in ONLINE_USERS:
        ONLINE_USERS.discard(username)
        for sid, u in list(SID_MAP.items()):
            if u == username:
                socketio.emit("force_logout", to=sid)
                SID_MAP.pop(sid, None)
        send_user_list()
    return "", 204

@app.route("/admin/clear_chat", methods=["POST"])
@admin_required
def clear_chat():
    Message.query.delete()
    db.session.commit()
    flash("Chatverlauf gelöscht", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/send_discord", methods=["POST"])
@admin_required
def admin_send_discord():
    text = request.form.get("discord_text", "").strip()
    if text:
        try:
            send_discord_embed(text)
            flash("Nachricht an Discord gesendet ✔", "success")
        except Exception as e:
            flash(f"Discord-Fehler: {e}", "error")
    return redirect(url_for("admin_panel"))

@app.route("/admin/upload_smilie", methods=["POST"])
@admin_required
def upload_smilie():
    return handle_smilie_upload()

@app.route("/admin/delete_smilie/<name>")
@admin_required
def admin_delete_smilie(name):
    return delete_smilie(name)

@app.route("/admin/update_smilie_cost", methods=["POST"])
@admin_required
def update_smilie_cost():
    try:
        new_cost = int(request.form.get("smilie_cost", "0"))
        daily_bonus = int(request.form.get("daily_bonus", "20"))
        stream_bonus = int(request.form.get("stream_bonus_points", "20"))
        interval = int(request.form.get("stream_bonus_interval", "30"))
        if new_cost < 0 or daily_bonus < 0 or stream_bonus < 0 or interval < 1:
            raise ValueError
    except ValueError:
        flash("Ungültige Eingabewerte", "error")
        return redirect(url_for("admin_panel"))

    setting = Setting.query.first() or Setting()
    setting.smilie_cost = new_cost
    setting.daily_bonus = daily_bonus
    setting.stream_bonus_points = stream_bonus
    setting.stream_bonus_interval = interval
    db.session.add(setting)
    db.session.commit()
    flash("Belohnungseinstellungen gespeichert ✔", "success")
    return redirect(url_for("admin_panel"))

@app.route('/admin/update_smilie_prices', methods=['POST'])
@admin_required
def update_smilie_prices():
    updates = {
        k: int(v.strip())
        for k, v in request.form.items()
        if v.strip().isdigit()
    }
    if not updates:
        flash('Keine gültigen Preise übertragen', 'warning')
        return redirect(url_for('admin_panel'))

    json_path = os.path.join(app.static_folder, 'smilies.json')
    try:
        data = {}
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        smilies = data.get('smilies', {})
        if isinstance(smilies, list):
            smilies = {n: 50 for n in smilies}

        smilies.update(updates)
        data['smilies'] = smilies

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        flash('Smilie-Preise gespeichert ✔', 'success')

    except Exception as e:
        flash(f'Fehler beim Schreiben der JSON-Datei: {e}', 'error')

    return redirect(url_for('admin_panel'))


@app.route("/admin/add_stream_key", methods=["POST"])
@admin_required
def add_stream_key():
    new_key = request.form.get("stream_key", "").strip()
    if not new_key:
        flash("Kein Key übermittelt", "error")
    elif StreamKey.query.filter_by(key=new_key).first():
        flash("Dieser Stream-Key existiert bereits", "warning")
    else:
        db.session.add(StreamKey(key=new_key))
        db.session.commit()
        flash(f"Neuer Stream-Key „{new_key}“ angelegt", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete_stream_key/<int:key_id>")
@admin_required
def delete_stream_key(key_id):
    sk = StreamKey.query.get(key_id)
    if sk:
        db.session.delete(sk)
        db.session.commit()
        flash(f"Stream-Key „{sk.key}“ gelöscht", "success")
    else:
        flash("Stream-Key nicht gefunden", "error")
    return redirect(url_for("admin_panel"))

@app.route("/admin/update_stream_suffix", methods=["POST"])
@admin_required
def update_stream_suffix():
    new_suffix = request.form.get("stream_suffix", "").strip()
    if new_suffix:
        setting = Setting.query.first() or Setting()
        setting.stream_suffix = new_suffix
        db.session.add(setting)
        db.session.commit()
        flash("Stream-Endung aktualisiert ✔", "success")
    else:
        flash("Keine gültige Endung eingegeben!", "error")
    return redirect(url_for("admin_panel"))

@app.route("/admin/update_discord_webhook", methods=["POST"])
@admin_required
def update_discord_webhook():
    new_webhook = request.form.get("webhook_url", "").strip()
    new_botname = request.form.get("webhook_username", "").strip()
    new_avatar  = request.form.get("webhook_avatar", "").strip()
    if new_webhook:
        cfg = ConfigParser(interpolation=None)
        cfg.read(CFG_PATH)
        if not cfg.has_section("discord"):
            cfg.add_section("discord")
        cfg.set("discord", "webhook", new_webhook)
        cfg.set("discord", "username", new_botname or "WhazzaStream Bot")
        cfg.set("discord", "avatar_url", new_avatar)
        with open(CFG_PATH, "w") as f:
            cfg.write(f)
        flash("Discord-Einstellungen gespeichert ✔", "success")
    else:
        flash("Ungültiger Webhook-Link", "error")
    return redirect(url_for("admin_panel"))


@app.route("/admin/update_hls_secret", methods=["POST"])
@admin_required
def update_hls_secret():
    new_secret = request.form.get("hls_secret", "").strip()

    if not new_secret:
        flash("Secret darf nicht leer sein!", "error")
        return redirect(url_for("admin_panel"))

    setting = Setting.query.first() or Setting()
    setting.hls_secret = new_secret
    db.session.add(setting)
    db.session.commit()

    clear_hls_secret_cache()
    flash("HLS-Secret gespeichert – alle alten Tokens sind jetzt ungültig.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/proxy/hls/<path:filename>")
@login_required
def proxy_hls(filename):
    if not validate_hls_token(session["username"], request.args.get("token", "")):
        abort(403)
    r = requests.get(f"{stream_base_url}/hls/{filename}", stream=True)
    return (r.iter_content(chunk_size=4096), r.status_code, {"Content-Type": r.headers.get("Content-Type", "application/vnd.apple.mpegurl")})

@app.route("/admin/user_info/<username>")
@admin_required
def user_info(username):
    user = User.query.filter_by(username=username).first_or_404()
    return jsonify(
        username=user.username,
        color=user.color,
        points=user.points,
        is_admin=user.is_admin,
        is_active=user.is_active
    )

@app.route("/admin/update_user/<username>", methods=["POST"])
@admin_required
def update_user(username):
    data = _require_json(request)
    user = User.query.filter_by(username=username).first_or_404()

    if pw := data.get("new_pw", "").strip():
        user.password = generate_password_hash(pw)
    if "color"  in data: user.color  = data["color"]
    if "points" in data:
        try:
            user.points = int(data["points"])
        except ValueError:
            return jsonify(error="points must be int"), 400

    db.session.commit()

    socketio.emit("user_data_changed", {
        "username": user.username,
        "color"   : user.color,
        "points"  : user.points
    })
    send_user_list()

    return '', 204

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if config.has_section("admin"):
            admin_user  = config["admin"].get("username", "").strip()
            admin_pass  = config["admin"].get("password", "").strip()
            admin_color = config["admin"].get("color", "#000000")

            if admin_user and admin_pass \
               and not User.query.filter_by(username=admin_user).first():

                db.session.add(User(
                    username=admin_user,
                    password=generate_password_hash(admin_pass),
                    is_admin=True,
                    is_active=True,
                    color=admin_color
                ))
                db.session.commit()

            sanitize_config()

    socketio.run(app, host="0.0.0.0", port=5015)