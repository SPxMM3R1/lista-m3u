"""Probe random TvVoo aliases with Resolver Forge without persisting stream URLs."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from forge_core import ForgePolicy, discover_recipe, execute_recipe


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_ROOT.parent.parent
FORGE_PATH = EXPERIMENT_ROOT / "forge_core.py"
CATALOG_PATH = REPOSITORY_ROOT / "resolver-catalog.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alias_label(alias: str) -> str:
    decoded = unquote(alias).removeprefix("vavoo_")
    return decoded.split("|", 1)[0].strip()


def public_result(result) -> dict[str, object]:  # noqa: ANN001
    stream_host = ""
    if result.resolved_url:
        stream_host = (urlsplit(result.resolved_url).hostname or "").lower()
    return {
        "accepted": result.accepted,
        "reason": result.reason,
        "streamHost": stream_host,
        "requests": result.requests,
        "bytesRead": result.bytes_read,
        "identityEvidence": list(result.identity_evidence),
        "securityEvents": list(result.security_events),
        "recipeDigest": result.recipe.digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument(
        "--channel",
        action="append",
        default=[],
        help="nombre exacto del canal del catalogo; se puede repetir",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EXPERIMENT_ROOT / "results" / "tvvoo-live-results.json",
    )
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples debe ser positivo")

    # Freeze the forge before choosing the live holdout aliases.
    forge_hash = sha256_file(FORGE_PATH)
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    provider = next(item for item in catalog["providers"] if item["id"] == "tvvoo")
    endpoint = provider["config"]["endpointBase"].rstrip("/")
    aliases = provider["compatibilityAliases"]
    population = [
        (channel_name, alias)
        for channel_name, values in aliases.items()
        for alias in values[:1]
    ]
    if not population:
        raise RuntimeError("catalogo TvVoo sin aliases")
    if args.channel:
        requested = set(args.channel)
        selected = [item for item in population if item[0] in requested]
        missing = requested.difference(channel for channel, _ in selected)
        if missing:
            parser.error("canales ausentes del catalogo: " + ", ".join(sorted(missing)))
    else:
        rng = secrets.SystemRandom()
        selected = rng.sample(population, min(args.samples, len(population)))

    policy = ForgePolicy(
        allowed_control_origins=frozenset({"https://tvvoo.hayd.uk"}),
        max_requests=16,
        max_response_bytes=256 * 1024,
        max_redirects=3,
        max_depth=3,
        max_candidates=64,
        max_strings=256,
        timeout_seconds=12.0,
        segments_to_probe=1,
        test_mode=False,
        allow_http_stream_fallback=bool(
            provider["config"].get("allowHttpFallback", False)
        ),
    )
    records: list[dict[str, object]] = []
    for channel_name, alias in selected:
        label = alias_label(alias)
        entry_url = f"{endpoint}/{alias}.json"
        discovery = discover_recipe(entry_url, label, channel_name, policy)
        replay = execute_recipe(discovery.recipe, policy) if discovery.accepted else None
        records.append(
            {
                "channel": channel_name,
                "aliasLabel": label,
                "aliasDigest": hashlib.sha256(alias.encode("utf-8")).hexdigest(),
                "discovery": public_result(discovery),
                "replay": public_result(replay) if replay else None,
                "acceptedTwice": bool(discovery.accepted and replay and replay.accepted),
            }
        )

    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "forgeSha256": forge_hash,
        "samples": len(records),
        "acceptedTwice": sum(bool(record["acceptedTwice"]) for record in records),
        "records": records,
        "note": "No stream URLs, query strings or session tokens are persisted.",
    }
    serialized = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    # The result schema intentionally contains no URL-valued fields except no URLs at all.
    if "access_token" in serialized.lower() or "/sunshine/" in serialized.lower():
        raise RuntimeError("el informe intentaba persistir datos de sesion")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(f"forge_sha256={forge_hash}")
    print(f"samples={len(records)}")
    print(f"accepted_twice={report['acceptedTwice']}")
    for record in records:
        discovery = record["discovery"]
        print(
            f"{record['channel']}: accepted_twice={record['acceptedTwice']} "
            f"reason={discovery['reason']} requests={discovery['requests']}"
        )
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
