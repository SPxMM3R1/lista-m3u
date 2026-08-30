#!/usr/bin/env python3
"""Generate a human-readable, token-free maintenance report for GitHub."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "channel-status.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "health-report.md"
STATUS_LABELS = {
    "functional": "OK",
    "renewed": "RENOVADO",
    "recovered": "RECUPERADO",
    "resolver_required": "RESOLUTOR",
    "intermittent": "INTERMITENTE",
    "temporarily_unavailable": "NO DISPONIBLE",
}


def cell(value: object, limit: int = 180) -> str:
    text = str(value if value is not None else "-")
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    text = text.replace("|", "\\|")
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


def count_guides(epg: dict) -> tuple[int, int, int]:
    values = list((epg.get("guide_types") or {}).values())
    real = sum(1 for value in values if str(value).startswith("parrilla real"))
    official = sum(1 for value in values if str(value).startswith("parrilla oficial"))
    missing = sum(1 for value in values if str(value) == "sin guía")
    return real, official, missing


def render(report: dict) -> str:
    run_url = os.environ.get("RUN_URL", "")
    update_status = os.environ.get("UPDATE_STATUS", "desconocido")
    publication_status = os.environ.get("PUBLICATION_STATUS", "no ejecutada")
    raw_status = os.environ.get("RAW_STATUS", "no ejecutada")
    summary = report.get("summary") or {}
    channels = report.get("channels") or []
    epg = report.get("epg") or {}
    main_epg = report.get("main_epg") or {}
    playlists = report.get("playlists") or {}
    resolver_refresh = report.get("resolver_refresh") or {}
    logos = report.get("logos") or []
    fatal = report.get("fatal_error")
    real_guides, official_guides, missing_guides = count_guides(epg)
    failed_logos = [item for item in logos if not item.get("ok")]
    changes = [item for item in channels if item.get("status_changed")]
    removals = report.get("removed_channels") or []
    statuses = Counter(str(item.get("status", "unknown")) for item in channels)

    lines = [
        "# Estado automático de Lista M3U",
        "",
        "@SPxMM3R1",
        "",
        f"- Generado: `{cell(report.get('generated_at', 'sin fecha'))}`",
        f"- Ejecución: {f'[abrir en Actions]({run_url})' if run_url else 'local'}",
        f"- Actualizador: `{cell(update_status)}`",
        f"- Publicación: `{cell(publication_status)}`",
        f"- Verificación Raw: `{cell(raw_status)}`",
    ]
    if fatal:
        lines.extend(["", "## Error fatal", "", f"`{cell(fatal, 500)}`"])
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "",
            "## Resumen",
            "",
            f"- Canales revisados: **{summary.get('total_channels', len(channels))}**.",
            f"- Canales publicados: **{summary.get('published_channels', 0)}**.",
            f"- Retirados temporalmente tras agotar reintentos: **{summary.get('temporarily_removed', 0)}**.",
            f"- Reactivados en esta ejecución: **{summary.get('reactivated', 0)}**.",
            f"- Fuentes directas temporalmente no disponibles: **{summary.get('direct_failures', 0)}**.",
            f"- Fallos sistémicos que bloquean publicación: **{summary.get('blocking_failures', 0)}**.",
            f"- Respaldos degradados recuperables por resolutor: **{summary.get('resolver_degradations', 0)}**.",
            f"- Logos con problemas: **{len(failed_logos)}**.",
            f"- EPG: **{epg.get('channels', 0)} canales**, **{epg.get('programmes', 0)} programas**.",
            f"- Guías reales/agregadas: **{real_guides}**; oficiales con continuidad: **{official_guides}**; sin guía: **{missing_guides}**.",
            f"- Próxima renovación calculada: `{cell(epg.get('next_refresh_at', 'sin dato'))}`.",
            "",
            "Estados: "
            + ", ".join(
                f"**{STATUS_LABELS.get(name, name)}** {count}"
                for name, count in sorted(statuses.items())
            )
            + ".",
        ]
    )

    if resolver_refresh:
        lines.extend(
            [
                "",
                "### Renovación dinámica",
                "",
                f"- Intentos de renovación: **{resolver_refresh.get('attempted', 0)}**; "
                f"caché reciente reutilizada: **{resolver_refresh.get('skipped_recent', 0)}**.",
                f"- Enlaces cambiados: **{resolver_refresh.get('changed', 0)}**; "
                f"renovaciones aceptadas: **{resolver_refresh.get('accepted', 0)}**; "
                f"fallos: **{resolver_refresh.get('failed', 0)}**.",
            ]
        )
        by_engine = resolver_refresh.get("by_engine") or {}
        if by_engine:
            lines.append(
                "- Por motor: "
                + "; ".join(
                    f"`{cell(engine)}` "
                    f"(intentos {stats.get('attempted', 0)}, "
                    f"caché {stats.get('skipped_recent', 0)}, "
                    f"cambios {stats.get('changed', 0)}, "
                    f"fallos {stats.get('failed', 0)})"
                    for engine, stats in sorted(by_engine.items())
                )
                + "."
            )

    lines.extend(["", "### Salidas públicas", ""])
    for key, label in (("main", "Principal"), ("external", "Externa")):
        playlist = playlists.get(key) or {}
        epg_label = (
            f"EPG {playlist.get('epg_coverage_percent', 0)}%"
            if playlist.get("epg_required")
            else "EPG no bloqueante"
        )
        readiness = (
            "lista actualizada"
            if playlist.get("publication_ready")
            else f"retenida ({playlist.get('hold_reason') or 'validación incompleta'})"
        )
        lines.append(
            f"- **{label}** (`{cell(playlist.get('file'))}`): "
            f"{playlist.get('working_channels', 0)}/{playlist.get('candidate_channels', 0)} "
            f"canales listos; {epg_label}; {readiness}."
        )
    if main_epg.get("technical_guides"):
        lines.append(
            "- La compuerta principal incluye continuidad técnica marcada para: "
            + ", ".join(cell(item) for item in main_epg["technical_guides"])
            + "."
        )

    lines.extend(["", "## Cambios desde la revisión anterior", ""])
    if changes:
        for item in changes:
            lines.append(
                f"- **{cell(item.get('name'))}**: "
                f"`{cell(item.get('previous_status'))}` -> "
                f"`{cell(item.get('status'))}`."
            )
    else:
        lines.append("- Sin cambios de estado.")
    for item in removals:
        lines.append(
            f"- Retirado del catálogo: **{cell(item.get('name'))}** "
            f"(antes `{cell(item.get('previous_status'))}`)."
        )

    lines.extend(
        [
            "",
            "## Detalle por canal",
            "",
            "| Estado | Publicación | Lista | Canal | tvg-id | Grupo | Fuente | Fallos seguidos | Diagnóstico |",
            "|---|---|---|---|---|---|---|---:|---|",
        ]
    )
    for item in channels:
        status = str(item.get("status", "unknown"))
        lines.append(
            "| "
            + " | ".join(
                [
                    STATUS_LABELS.get(status, status.upper()),
                    cell(item.get("publication_action", "sin cambio")),
                    cell(item.get("playlist", "main")),
                    cell(item.get("name")),
                    cell(item.get("tvg_id")),
                    cell(item.get("group")),
                    cell(item.get("resolver")),
                    cell(item.get("consecutive_failures", 0)),
                    cell(item.get("detail")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Criterio de mantenimiento",
            "",
            "- Un canal que agota la validación, los reintentos y las reparaciones se retira de la M3U pública en esa ejecución.",
            "- `m3u.m3u` es la lista principal: solo se reemplaza cuando el 100% de sus candidatos tiene EPG XMLTV vigente y validada para al menos 24 horas; si la compuerta falla, se conserva la versión anterior.",
            "- `m3u-externa.m3u` contiene TvVoo/Vavoo y el resto de Highfly; Sky Sports F1 y Sky Sports Tennis son la excepción y se publican en `m3u.m3u` con sus resolutores renovables. La caída de los resolutores externos no bloquea la lista principal.",
            "- `channel-catalog.m3u` conserva todos los candidatos: cada ejecución vuelve a probar los retirados y los reactiva automáticamente cuando responden.",
            "- La EPG conserva la cobertura del catálogo completo para que una reactivación recupere inmediatamente su `tvg-id` y programación.",
            "- Una caída simultánea de al menos el 25% de las fuentes directas bloquea la publicación como posible fallo sistémico del runner o la red; los fallos de resolutores se retiran individualmente y se reintentan en la siguiente ejecución.",
            "- El informe omite URLs completas, tokens y parámetros de sesión.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        report = {"fatal_error": f"No se pudo leer el informe JSON: {error}"}
    args.output.write_text(render(report), encoding="utf-8", newline="\n")
    print(f"Informe Markdown generado en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
