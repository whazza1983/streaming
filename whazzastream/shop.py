# shop.py
from __future__ import annotations

from flask import Blueprint, jsonify, request, session, current_app
from auth   import login_required
from models import db, User, Setting
from smilies import get_all_smilies

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")

def _all_items(kind: str) -> dict[str, int] | list[str]:

    if kind == "smilie":
        return get_all_smilies()

    if kind == "color":
        return {
            "#ff4444": 200,
            "#44ff44": 200,
            "#4488ff": 250,
            "#ff44ff": 200,
            "#ffa500": 150,

            "#E51A4C": 180,  # Crimson
            "#FF5A4D": 170,  # Flamingo
            "#FF8A00": 160,  # Orange Peel
            "#C0FF00": 150,  # Lime Punch
            "#17E8B2": 150,  # Aqua Mint
            "#1899FF": 160,  # Dodger Blue
            "#3B3BFF": 170,  # Ultramarine
            "#8C00FF": 180,  # Electric Violet

            "#F4C0CB": 120,  # Powder Pink
            "#FFC9A3": 120,  # Peach Fuzz
            "#FAD97A": 110,  # Sunray
            "#CFFAE4": 110,  # Mint Cream
            "#B9DBFF": 120,  # Baby Blue
            "#D7C9FF": 120,  # Lavender Fog
            "#D8F5C8": 110,  # Tea Green
            "#E9D7F4": 110,  # Misty Lilac

            "#FF0090": 200,  # Neon Pink
            "#E8FF00": 190,  # Laser Lemon
            "#39FF14": 190,  # Toxic Green
            "#00F6FF": 190,  # Cyber Aqua
            "#B000FF": 200,  # Shock Purple
            "#FF5400": 190,  # Acid Orange

            "#E07A5F": 140,  # Terracotta
            "#C6AD8F": 130,  # Sand Dune
            "#6E8B3D": 130,  # Olive Drab
            "#2C5E3B": 140,  # Pine Forest
            "#3D5A80": 140,  # Denim
            "#708090": 130,  # Slate Grey

        }

    if kind == "font":
        return {
            "Press Start 2P": 300,
            "Roboto Slab"    : 250,
            "Comic Neue"     : 200,
            "VT323"          : 220,
            "Luckiest Guy"   : 260,
            "Lobster"        : 240,
            "Poppins"        : 230,
            "Source Code Pro": 210,
            "Dancing Script": 500,
            "Codystar": 400,
        }

    if kind == "effect":
        return {"rainbow":25, "pulse":25, "neon":30, "glitch":100, "sparkle":30, "shake":20, "fire":30, "blur":20, "wave": 30}
    return []


def _cost(kind: str, item: str | None = None) -> int:

    items = _all_items(kind)
    if isinstance(items, dict) and item in items:
        return items[item]

    setting  = Setting.query.first()
    defaults = {"smilie": 50, "color": 200, "font": 300, "effect": 25}
    if not setting:
        return defaults[kind]

    return {
        "smilie": getattr(setting, "smilie_cost", defaults["smilie"]),
        "color" : getattr(setting, "color_cost" , defaults["color"]),
        "font"  : getattr(setting, "font_cost"  , defaults["font"]),
        "effect": getattr(setting, "effect_cost", defaults["effect"]),
    }[kind]

@shop_bp.route("/catalog/<kind>")
@login_required
def catalog(kind: str):
    if kind not in ("smilie", "color", "font", "effect"):
        return jsonify([])

    user   = User.query.filter_by(username=session["username"]).first()
    items  = _all_items(kind)

    if kind in ("color", "font"):
        active = user.color if kind == "color" else (user.font or "")
        names  = items.keys() if isinstance(items, dict) else items
        return jsonify([
            {
                "name" : n,
                "cost" : (items[n] if isinstance(items, dict) else _cost(kind, n)),
                "active": (n == active),
            }
            for n in names
        ])

    unlocked = [] if kind == "effect" else getattr(user, f"unlocked_{kind}s", [])
    names    = items.keys() if isinstance(items, dict) else items
    return jsonify([
        {
            "name"    : n,
            "cost"    : (items[n] if isinstance(items, dict) else _cost(kind, n)),
            "unlocked": n in unlocked,
        }
        for n in names
    ])

@shop_bp.route("/inventory/effect")
@login_required
def inventory_effect():
    user = User.query.filter_by(username=session["username"]).first()
    return jsonify(user.effect_inventory or {})

@shop_bp.route("/buy/color", methods=["POST"])
@login_required
def buy_color():
    user  = User.query.filter_by(username=session["username"]).first()
    color = (request.get_json(force=True) or {}).get("item")

    if color not in _all_items("color"):
        return jsonify(success=False, message="Ungültige Farbe"), 400
    if color == user.color:
        return jsonify(success=False, message="Farbe bereits aktiv"), 400

    price = _cost("color", color)
    if user.points < price:
        return jsonify(success=False, message="Zu wenig Münzen!"), 400

    user.points -= price
    user.color   = color
    db.session.commit()

    current_app.extensions["socketio"].emit("user_data_changed", {
        "username": user.username, "color": user.color, "points": user.points
    })

    return jsonify(success=True, new_points=user.points, new_color=user.color)

@shop_bp.route("/buy/font", methods=["POST"])
@login_required
def buy_font():
    user = User.query.filter_by(username=session["username"]).first()
    font = (request.get_json(force=True) or {}).get("item")

    if font not in _all_items("font"):
        return jsonify(success=False, message="Ungültige Schrift"), 400
    if font == user.font:
        return jsonify(success=False, message="Schrift bereits aktiv"), 400

    price = _cost("font", font)
    if user.points < price:
        return jsonify(success=False, message="Zu wenig Münzen!"), 400

    user.points -= price
    user.font    = font
    db.session.commit()

    current_app.extensions["socketio"].emit("user_data_changed", {
        "username": user.username, "font": user.font, "points": user.points
    })

    return jsonify(success=True, new_points=user.points, new_font=user.font)

@shop_bp.route("/buy/<kind>", methods=["POST"])
@login_required
def buy(kind: str):
    if kind not in ("smilie", "effect"):
        return jsonify(success=False, message="Ungültige Kategorie"), 400

    user = User.query.filter_by(username=session["username"]).first()
    item = (request.get_json(force=True) or {}).get("item")
    if not item:
        return jsonify(success=False, message="Item fehlt"), 400

    if kind != "effect" and item in getattr(user, f"unlocked_{kind}s"):
        return jsonify(success=False, message="Schon freigeschaltet!"), 400

    price = _cost(kind, item)
    if user.points < price:
        return jsonify(success=False, message="Nicht genug Punkte!"), 400

    user.points -= price
    if kind == "effect":
        inv = user.effect_inventory
        inv[item] = inv.get(item, 0) + 1
    else:
        getattr(user, f"unlocked_{kind}s").append(item)

    db.session.commit()
    return jsonify(success=True, new_points=user.points)

@shop_bp.route("/unlocked_smilies")
@login_required
def unlocked_smilies():
    user = User.query.filter_by(username=session["username"]).first()
    return jsonify(user.unlocked_smilies if user else [])

@shop_bp.route("/smilies")
@login_required
def smilie_catalogue():
    user     = User.query.filter_by(username=session["username"]).first()
    unlocked = set(user.unlocked_smilies) if user else set()
    names    = _all_items("smilie")
    return jsonify([
        {"name": s, "cost": _cost("smilie", s), "unlocked": s in unlocked}
        for s in names
    ])

@shop_bp.route("/unlock", methods=["POST"])
@login_required
def unlock_smilie():
    return buy("smilie")
