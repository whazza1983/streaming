from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from flask import current_app, flash, redirect, request, url_for
from werkzeug.utils import secure_filename

def _json_path() -> Path:
    return Path(current_app.static_folder, "smilies.json")

def _smilie_dir() -> Path:
    return Path(current_app.static_folder, "smilie")

def get_all_smilies() -> Dict[str, int]:
    p = _json_path()
    if not p.exists():
        return {}

    try:
        data = json.loads(p.read_text(encoding="utf-8")) or {}
        smilies = data.get("smilies", {})

        if isinstance(smilies, list):
            default_price = 50
            try:
                from models import Setting

                setting = Setting.query.first()
                if setting and getattr(setting, "smilie_cost", None) is not None:
                    default_price = int(setting.smilie_cost)
            except Exception:
                pass

            smilies = {n: default_price for n in smilies}
            data["smilies"] = smilies
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        return {str(k): int(v) for k, v in smilies.items()}

    except Exception:
        return {}

def handle_smilie_upload():
    file = request.files.get("smilie_file")
    name = request.form.get("smilie_name", "").strip().lower()
    price_str = request.form.get("smilie_price", "0").strip()

    if not file or not name:
        flash("Name und Datei sind erforderlich!", "error")
        return redirect(url_for("admin_panel"))

    if not file.filename.lower().endswith(".webp"):
        flash("Nur .webp‑Dateien erlaubt!", "error")
        return redirect(url_for("admin_panel"))

    try:
        price = max(0, int(price_str))
    except ValueError:
        flash("Ungültiger Preis!", "error")
        return redirect(url_for("admin_panel"))

    smilie_dir = _smilie_dir()
    smilie_dir.mkdir(exist_ok=True)

    filename = secure_filename(f"{name}.webp")
    save_path = smilie_dir / filename

    try:
        file.save(save_path)
    except Exception as e:
        flash(f"Fehler beim Speichern: {e}", "error")
        return redirect(url_for("admin_panel"))

    p = _json_path()
    try:
        data: dict = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        smilies = data.get("smilies", {})
        if isinstance(smilies, list):
            smilies = {n: price for n in smilies}
        smilies[name] = price
        data["smilies"] = smilies
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        flash(f"Fehler beim Schreiben der JSON‑Datei: {e}", "error")
        return redirect(url_for("admin_panel"))

    flash("Smilie erfolgreich hinzugefügt ✔", "success")
    return redirect(url_for("admin_panel"))

def update_smilie_prices():
    try:
        updates = {
            k: max(0, int(v))
            for k, v in request.form.items()
            if v and v.isdigit()
        }
        if not updates:
            flash("Keine Preis‑Änderungen erkannt!", "info")
            return redirect(url_for("admin_panel"))

        p = _json_path()
        data: dict = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        smilies = data.get("smilies", {})
        if isinstance(smilies, list):
            smilies = {n: 50 for n in smilies}
        smilies.update(updates)
        data["smilies"] = smilies
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        flash("Smilie‑Preise aktualisiert ✔", "success")
        return redirect(url_for("admin_panel"))

    except Exception as e:
        flash(f"Fehler beim Aktualisieren der Preise: {e}", "error")
        return redirect(url_for("admin_panel"))

def delete_smilie(name: str):
    """Entfernt das Bild UND den Eintrag aus der JSON."""
    name = name.strip().lower()
    if not name:
        flash("Kein Smilie‑Name angegeben!", "error")
        return redirect(url_for("admin_panel"))

    file_path = _smilie_dir() / secure_filename(f"{name}.webp")
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            flash(f"Fehler beim Löschen der Datei: {e}", "error")
            return redirect(url_for("admin_panel"))

    p = _json_path()
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            smilies = data.get("smilies", {})
            if isinstance(smilies, list):
                smilies = {n: 50 for n in smilies}
            if name in smilies:
                smilies.pop(name, None)
                data["smilies"] = smilies
                p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        flash(f"Fehler beim Aktualisieren der JSON‑Datei: {e}", "error")
        return redirect(url_for("admin_panel"))

    flash(f"Smilie „{name}“ gelöscht ✔", "success")
    return redirect(url_for("admin_panel"))
