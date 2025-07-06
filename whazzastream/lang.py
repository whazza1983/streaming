# lang.py
import json
from pathlib import Path
from urllib.parse import urlencode

from flask import request, g, session, redirect

_LANG_DIR = Path("static/lang")
_CACHE: dict[str, dict[str, str]] = {}        

def _(key: str, lang: str | None = None) -> str:
    lang = lang or getattr(g, "lang", "de")
    data = _CACHE.get(lang)
    if data is None:
        try:
            with (_LANG_DIR / f"{lang}.json").open(encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        _CACHE[lang] = data
    return data.get(key, key)

def init_i18n(app):
    @app.before_request
    def detect_language():
        qlang = request.args.get("lang")

        if qlang in {"de", "en"}:
            g.lang = qlang
            session["lang"] = qlang

            args = request.args.to_dict(flat=True)
            args.pop("lang", None)                
            target = request.path                 
            if args:                              
                target += "?" + urlencode(args)
            return redirect(target, code=302)

        if "lang" in session:
            g.lang = session["lang"]

        else:
            g.lang = request.accept_languages.best_match(["de", "en"]) or "de"

    app.jinja_env.globals["_"]    = _
    app.jinja_env.globals["lang"] = lambda: g.get("lang", "de")
