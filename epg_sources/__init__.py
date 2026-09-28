"""Fuentes EPG, una por archivo. update_m3u las reexporta para compatibilidad."""

# Cada fuente usa utilidades de update_m3u; cargarlo primero garantiza que
# importar epg_sources.<fuente> directamente también funcione.
import update_m3u  # noqa: F401
