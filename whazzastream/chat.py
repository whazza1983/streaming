# chat.py
from flask      import request
from markupsafe import escape
from models     import db, Message, User
import re
from smilies    import get_all_smilies

ALLOWED_EFFECTS = {"rainbow", "pulse", "neon", "updown", "glitch", "sparkle", "shake", "fire", "blur", "wave"}

def handle_chat_messages(socketio):

    @socketio.on("send_message")
    def handle_send_message(data):

        username  = data.get("username")
        raw_text  = (data.get("text") or "").strip()
        effect    = data.get("effect")

        if not username or not raw_text:
            return

        user  = User.query.filter_by(username=username).first()
        color = user.color if user else "#000000"
        font  = user.font  if user else None

        if effect in ALLOWED_EFFECTS:
            inv = user.effect_inventory or {}
            if inv.get(effect, 0) > 0:
                inv[effect] -= 1
                user.effect_inventory = inv
            else:
                effect = None
        else:
            effect = None

        all_smilies = set(get_all_smilies())
        unlocked    = set(user.unlocked_smilies) if user else set()

        tags    = re.findall(r':([\w]+):', raw_text)
        missing = [t for t in tags if t in all_smilies and t not in unlocked]

        if missing:
            socketio.emit(
                "smilie_error",
                {"message": f"Den Smilie :{missing[0]}: hast du nicht freigeschaltet."},
                to=request.sid
            )
            return

        visible = [t for t in tags if t in unlocked]

        msg = Message(username=username,
                      text=raw_text,
                      color=color,
                      font=font,
                      effect=effect)
        db.session.add(msg)
        db.session.commit()

        safe_text = str(escape(raw_text))
        socketio.emit(
            "receive_message",
            {
                "id": msg.id,
                "username": username,
                "color": color,
                "font": font,
                "effect": effect,
                "text": safe_text,
                "visible_smilies": visible
            }
        )

        socketio.emit(
            "user_data_changed",
            {
                "username": username,
                "points":   user.points,
                "color":    user.color,
                "effects":  user.effect_inventory
            }
        )

    @socketio.on("connect")
    def handle_connect():
        history = (
            Message.query
                   .order_by(Message.id.desc())
                   .limit(50)
                   .all()
        )

        payload = [
            {
                "id":       m.id,
                "username": m.username,
                "color":    m.color,
                "font":     m.font,
                "effect":   m.effect,
                "text":     str(escape(m.text))
            }
            for m in reversed(history)
        ]
        socketio.emit("chat_history", payload, to=request.sid)
