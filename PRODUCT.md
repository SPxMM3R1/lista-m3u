# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: static HTML, CSS, and JavaScript, because this project is published from its existing GitHub repository and needs to run on GitHub Pages without a server.

## Users

Inferred by delegation from the request: the Lista M3U / VibeM3U maintainer, working in a desktop browser to curate channels for the Android TV app.

## Product Purpose

Provide one clear place to review and curate the channel selection used with VibeM3U: choose available sources, order and number channels, hide or restore entries, review logo choices, and publish the declarative selection to Lista M3U so its runner can reconcile EPG and logos.

Success means an editor can understand exactly what will change, publish it safely to the Lista M3U repository, and see whether runner validation accepted or left any selected identities pending.

## Positioning

The editor writes editorial intent only. GitHub stores that intent, and the existing Lista M3U runner remains responsible for validating stable identities and producing public EPG, logos, and catalogue outputs. The editor is not a stream resolver and never treats a resolver reference as a channel identity.

## Operating Context

Inferred by delegation: a static GitHub Pages site loads the public catalogue and selection manifest, while an authorized repository maintainer supplies a short-lived GitHub credential in the browser to publish a commit. The selection commit is processed by the existing GitHub Actions workflow. No server-side session or credential store is assumed.

## Capabilities and Constraints

- The editor should bring together the Lista M3U catalogue and the app-only Highfly and TvVoo selections for review and curation.
- Stable `catalogKey` is the identity for Highfly. `providerResourceId` and `resolverSlug` are mutable resolution references; HLS URLs, tokens, and signed URLs are never identities and must never be stored by the editor.
- Keep Lista M3U and VibeM3U as separate repositories with separate responsibilities.
- Respect `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md`; uncertain identities remain visibly pending instead of being guessed.
- A publish operation must target only the declared selection/editor files and let the runner validate generated outputs.
- Direct M3U outputs and app-only resolver selections remain separate unless the existing contracts explicitly bridge them.
- Inferred by delegation: prefer a token held only in page memory for the active session; do not persist it in local or session storage.

## Brand Commitments

Use the existing Lista M3U and VibeM3U names. Interface copy is Spanish and direct. No new logo or brand identity was supplied.

## Evidence on Hand

- The repository's `channel-catalog.m3u`, `m3u.m3u`, `m3u-externa.m3u`, `1.m3u`, and `2.m3u`.
- The contract at `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md` and the manifest at `data/vibem3u-selection.json`.
- Existing curated logo assets in `logos/` and the Python runner/workflows in this repository.
- No claims about stream uptime, EPG coverage, or provider availability may be invented by the interface.

## Product Principles

- Preserve identity; never infer it from order, visible name, provider slug, or playback URL.
- Make changes reversible and previewable before publication.
- Be explicit about the boundary between an editorial selection and a runner-validated public result.
- Fail closed on ambiguous identities, stale GitHub state, permission errors, or malformed data.

## Accessibility & Inclusion

No product-specific conformance target was supplied. Use semantic controls, keyboard operation, visible focus, readable contrast, and responsive layouts as implementation requirements without claiming a formal certification.
