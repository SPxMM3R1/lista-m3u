# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML, CSS, and JavaScript remain the frontend and GitHub Pages artifact. An optional Windows local mode serves the same frontend from loopback through a small Java helper in VibeM3U; it reuses VibeM3U resolver sources and GitHub CLI authentication without creating another hosted service or APK.

## Users

Inferred by delegation from the request: the Lista M3U / VibeM3U maintainer, working in a desktop browser to curate channels for the Android TV app.

## Product Purpose

Provide one clear place to review and curate the channel selection used with VibeM3U: choose available sources, order and number channels, hide or restore entries, review logo choices, and publish the declarative selection to Lista M3U so its runner can reconcile EPG and logos.

Success means an editor can understand exactly what will change, publish it safely to the Lista M3U repository, and see whether runner validation accepted or left any selected identities pending.

## Positioning

The editor writes editorial intent only. GitHub stores that intent, and the existing Lista M3U runner remains responsible for validating stable identities and producing public EPG, logos, and catalogue outputs. Local mode may preview a selected stream through the original VibeM3U resolvers, but playback URLs, tokens, and resolver references never become editorial identity or published data.

## Operating Context

The static GitHub Pages site loads the public catalogue and selection manifest; an authorized maintainer can publish from that page with a short-lived credential held only in browser memory. On Windows, the optional local launcher builds a temporary frontend bundle and starts the Java helper on `127.0.0.1`; GitHub CLI performs publication outside the browser, and the helper keeps resolver URLs and request headers in memory for a bounded preview session. The selection commit is processed by the existing GitHub Actions workflow. No new hosted backend is introduced.

## Capabilities and Constraints

- The editor should bring together the Lista M3U catalogue and the app-only Highfly and TvVoo selections for review and curation.
- Stable `catalogKey` is the identity for Highfly. `providerResourceId` and `resolverSlug` are mutable resolution references; HLS URLs, tokens, and signed URLs are never identities and must never be stored by the editor.
- Keep Lista M3U and VibeM3U as separate repositories with separate responsibilities.
- Respect `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md`; uncertain identities remain visibly pending instead of being guessed.
- A publish operation must target only the declared selection/editor files and let the runner validate generated outputs.
- Direct M3U outputs and app-only resolver selections remain separate unless the existing contracts explicitly bridge them.
- Local resolver preview is loopback-only and supports the TVN, Meganoticias, Highfly, and TvVoo implementations already present in VibeM3U; temporary provider URLs stay out of the browser's application data and GitHub.
- GitHub Pages keeps a token only in page memory for the active session; local mode delegates credential storage to GitHub CLI and never requests a pasted token.

## Brand Commitments

Use the existing Lista M3U and VibeM3U names. Interface copy is Spanish and direct. No new logo or brand identity was supplied.

## Evidence on Hand

- The repository's `channel-catalog.m3u`, `m3u.m3u`, `m3u-externa.m3u`, `1.m3u`, and `2.m3u`.
- The contract at `VIBEM3U_ID_CONTRACT_EPG_LOGOS.md` and the manifest at `data/vibem3u-selection.json`.
- The local launcher at `tools/Start-CatalogEditor.ps1` and the Java resolver bridge under VibeM3U's `local-catalog` module.
- Existing curated logo assets in `logos/` and the Python runner/workflows in this repository.
- No claims about stream uptime, EPG coverage, or provider availability may be invented by the interface.

## Product Principles

- Preserve identity; never infer it from order, visible name, provider slug, or playback URL.
- Make changes reversible and previewable before publication.
- Be explicit about the boundary between an editorial selection and a runner-validated public result.
- Fail closed on ambiguous identities, stale GitHub state, permission errors, or malformed data.

## Accessibility & Inclusion

No product-specific conformance target was supplied. Use semantic controls, keyboard operation, visible focus, readable contrast, and responsive layouts as implementation requirements without claiming a formal certification.
