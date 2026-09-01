"""Run randomized holdout trials without exposing fixture truth to the forge.

The judge hashes the system under test before it generates any holdout seed.
Only PublicCase values cross into forge_core. Full URLs and issued tokens remain
in memory and are deliberately omitted from result artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from blind_lab import BlindFixtureLab
from forge_core import (
    ForgePolicy,
    discover_recipe,
    execute_recipe,
    fixed_schema_baseline,
)


ROOT = Path(__file__).resolve().parent
FORGE_PATH = ROOT / "forge_core.py"
DEFAULT_RESULTS = ROOT / "results"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def session_token(url: str | None) -> str:
    if not url:
        return ""
    values = parse_qs(urlsplit(url).query).get("access_token", [])
    return values[0] if values else ""


def public_resolution(result) -> dict[str, object]:  # noqa: ANN001
    return {
        "accepted": result.accepted,
        "reason": result.reason,
        "redactedUrl": result.redacted_url,
        "identityEvidence": list(result.identity_evidence),
        "streamIdentity": result.stream_identity,
        "requests": result.requests,
        "bytesRead": result.bytes_read,
        "securityEvents": list(result.security_events),
        "recipeDigest": result.recipe.digest,
        "strategy": result.recipe.strategy,
    }


def outcome(expectation: str, accepted: bool) -> str:
    if expectation == "resolve":
        return "TP" if accepted else "FN"
    return "FP" if accepted else "TN"


def run_seed(seed: int, repetitions: int) -> tuple[list[dict[str, object]], list[str]]:
    lab = BlindFixtureLab(seed, repetitions=repetitions)
    lab.start()
    records: list[dict[str, object]] = []
    hygiene_failures: list[str] = []
    try:
        policy = ForgePolicy(
            allowed_control_origins=frozenset({lab.origin}),
            max_requests=16,
            max_response_bytes=256 * 1024,
            max_redirects=3,
            max_depth=3,
            max_candidates=128,
            max_strings=512,
            timeout_seconds=2.0,
            segments_to_probe=2,
            test_mode=True,
        )
        for public in lab.public_cases():
            hidden = lab.hidden(public.case_id)
            baseline = fixed_schema_baseline(
                public.entry_url,
                public.expected_id,
                public.expected_name,
                policy,
            )
            discovery = discover_recipe(
                public.entry_url,
                public.expected_id,
                public.expected_name,
                policy,
            )
            replay = execute_recipe(discovery.recipe, policy) if discovery.accepted else None
            first_token = session_token(discovery.resolved_url)
            second_token = session_token(replay.resolved_url if replay else None)
            renewable = bool(
                discovery.accepted
                and replay
                and replay.accepted
                and first_token
                and second_token
                and first_token != second_token
            )
            accepted = bool(discovery.accepted and replay and replay.accepted and renewable)
            classification = outcome(hidden.expectation, accepted)
            record: dict[str, object] = {
                "seed": seed,
                "caseId": public.case_id,
                "family": hidden.family,
                "expectation": hidden.expectation,
                "classification": classification,
                "acceptedTwiceWithFreshToken": accepted,
                "baselineAccepted": baseline,
                "discovery": public_resolution(discovery),
                "replay": public_resolution(replay) if replay else None,
            }

            serialized = json.dumps(record, ensure_ascii=True, sort_keys=True)
            leaked = [token for token in hidden.issued_tokens if token and token in serialized]
            if leaked:
                hygiene_failures.append(f"{public.case_id}: token persistido")
            if discovery.requests > policy.max_requests:
                hygiene_failures.append(f"{public.case_id}: presupuesto de peticiones excedido")
            if discovery.bytes_read > policy.max_response_bytes:
                hygiene_failures.append(f"{public.case_id}: presupuesto de bytes excedido")
            if replay and replay.requests > policy.max_requests:
                hygiene_failures.append(f"{public.case_id}: replay excedio peticiones")
            if replay and replay.bytes_read > policy.max_response_bytes:
                hygiene_failures.append(f"{public.case_id}: replay excedio bytes")
            records.append(record)
    finally:
        lab.close()
    return records, hygiene_failures


def summarize(records: list[dict[str, object]], hygiene_failures: list[str]) -> dict[str, object]:
    classifications = Counter(str(record["classification"]) for record in records)
    baseline_by_expected = Counter()
    family_stats: dict[str, Counter[str]] = defaultdict(Counter)
    max_requests = 0
    max_bytes = 0
    for record in records:
        expected = str(record["expectation"])
        if record["baselineAccepted"]:
            baseline_by_expected[expected] += 1
        family_stats[str(record["family"])][str(record["classification"])] += 1
        for phase in (record.get("discovery"), record.get("replay")):
            if isinstance(phase, dict):
                max_requests = max(max_requests, int(phase["requests"]))
                max_bytes = max(max_bytes, int(phase["bytesRead"]))

    video_only_safe = bool(
        classifications["FN"] == 0
        and classifications["FP"] == 0
        and not hygiene_failures
    )
    return {
        "cases": len(records),
        "classifications": dict(sorted(classifications.items())),
        "baselineAccepted": dict(sorted(baseline_by_expected.items())),
        "maxRequestsPerPhase": max_requests,
        "maxBytesPerPhase": max_bytes,
        "hygieneFailures": hygiene_failures,
        "videoOnlyCoreValid": video_only_safe,
        "safeForAutomaticPromotionBasedOnVideo": video_only_safe,
        "familyStats": {
            family: dict(sorted(values.items()))
            for family, values in sorted(family_stats.items())
        },
    }


def markdown_report(report: dict[str, object]) -> str:
    summary = report["summary"]
    assert isinstance(summary, dict)
    lines = [
        "# Resolver Forge: resultado de pruebas ciegas",
        "",
        f"- Fecha UTC: `{report['generatedAt']}`",
        f"- SHA-256 congelado: `{report['forgeSha256']}`",
        f"- Semillas generadas despues del hash: `{', '.join(map(str, report['seeds']))}`",
        f"- Casos: **{summary['cases']}**",
        f"- Clasificacion: `{json.dumps(summary['classifications'], sort_keys=True)}`",
        f"- Maximo por fase: **{summary['maxRequestsPerPhase']} peticiones**, **{summary['maxBytesPerPhase']} bytes**",
        "",
        "## Veredicto",
        "",
        f"- Nucleo de disponibilidad de video valido: **{summary['videoOnlyCoreValid']}**.",
        "- Promocion automatica basada en video reproducible: "
        f"**{summary['safeForAutomaticPromotionBasedOnVideo']}**.",
        "- Fallos de higiene o presupuesto: "
        f"**{len(summary['hygieneFailures'])}**.",
        "",
        "## Resultado por familia",
        "",
        "| Familia | TP | FN | TN | FP |",
        "|---|---:|---:|---:|---:|",
    ]
    family_stats = summary["familyStats"]
    assert isinstance(family_stats, dict)
    for family, values in family_stats.items():
        lines.append(
            f"| `{family}` | {values.get('TP', 0)} | {values.get('FN', 0)} | "
            f"{values.get('TN', 0)} | {values.get('FP', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretacion",
            "",
            "La forja puede reparar cambios de envoltorio declarativos dentro de su DSL "
            "sin ejecutar codigo remoto y puede renovar tokens al repetir la receta. La "
            "identidad del canal proviene del alias estable y autorizado del catalogo; "
            "no se inspeccionan logos, publicidad, moscas ni el contenido editorial. La "
            "aceptacion exige que el HLS entregue una muestra multimedia reconocible.",
            "",
            "El JSON conserva solamente URLs redactadas, digests y metricas; no almacena "
            "tokens ni URLs de sesion completas.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    if args.trials < 1 or args.repetitions < 1:
        parser.error("trials y repetitions deben ser positivos")

    # Freeze first; only then create holdout seeds.
    forge_hash = sha256_file(FORGE_PATH)
    seeds = [secrets.randbits(63) for _ in range(args.trials)]

    records: list[dict[str, object]] = []
    hygiene_failures: list[str] = []
    for seed in seeds:
        seed_records, seed_failures = run_seed(seed, args.repetitions)
        records.extend(seed_records)
        hygiene_failures.extend(seed_failures)

    report: dict[str, object] = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "forgeSha256": forge_hash,
        "seeds": seeds,
        "trialCount": args.trials,
        "repetitionsPerFamily": args.repetitions,
        "summary": summarize(records, hygiene_failures),
        "cases": records,
    }

    output_dir = args.results_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "blind-results.json"
    markdown_path = output_dir / "blind-results.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(markdown_report(report), encoding="utf-8")

    summary = report["summary"]
    print(f"forge_sha256={forge_hash}")
    print(f"seeds={','.join(map(str, seeds))}")
    print("summary=" + json.dumps(summary, ensure_ascii=True, sort_keys=True))
    print(f"json={json_path}")
    print(f"markdown={markdown_path}")
    return 0 if not hygiene_failures else 2


if __name__ == "__main__":
    sys.exit(main())
