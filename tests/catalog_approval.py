"""Cuándo corren las pruebas del catálogo publicado (2026-10-12).

Esas pruebas comparan el layout, las listas y la presentación publicados con decisiones
fijadas en su momento (números, bajas, digest). Sirven para detectar cambios hechos por
otra vía (un script o un agente); no deben estorbar las decisiones del usuario.

- Runners y despliegue del editor (M3U_RUNNER_TESTS=1): se saltan; ellos regeneran después.
- Layout sellado por el editor o por la papelera de la app (campo «approval» con el SHA-256
  de su contenido, ver approveLayout en site/editor-core.mjs): se saltan; lo publicado es
  la decisión vigente del usuario y no hay que actualizar ninguna base a mano.
- Sello «chat»: un agente aplicó un cambio que el usuario pidió explícitamente en el chat
  (el commit lo cita). Mismo efecto que el editor; nunca para silenciar una prueba.
- Layout sin sello o con un sello que no coincide (alguien lo editó por fuera): corren.
"""
import hashlib
import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "data/channel-editor-layout.json"


def layout_approval_digest(layout):
    content = {
        "schemaVersion": layout.get("schemaVersion"),
        "excludedM3u": layout.get("excludedM3u", []),
        "channels": layout.get("channels", []),
    }
    # Igual que JSON.stringify en el editor: sin espacios, orden de claves tal como está.
    text = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def approved_by_user(layout):
    approval = layout.get("approval")
    return (isinstance(approval, dict)
            and approval.get("source") in {"editor", "app", "chat"}
            and approval.get("sha256") == layout_approval_digest(layout))


def _published_layout_is_approved():
    try:
        return approved_by_user(json.loads(LAYOUT_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return False


def skip_reason():
    if os.environ.get("M3U_RUNNER_TESTS") == "1":
        return "catálogo publicado: lo revisa el flujo del editor, no el runner"
    if _published_layout_is_approved():
        return "catálogo publicado por el usuario (editor o app): no se compara con fotos fijas"
    return None


_REASON = skip_reason()
live_catalog = unittest.skipIf(_REASON is not None, _REASON or "")
