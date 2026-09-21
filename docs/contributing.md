> **Status:** draft — do not publish until the GitHub org (`youseftrk`) is confirmed.

# Contributing — open-real2sim-capture

Thank you for helping ship honest capture bags. Read this before opening a PR.

## Do not publish yet

These docs and packaging targets use the placeholder org `youseftrk`. Do **not** treat drafts as a public release until the GitHub organization name is confirmed by the founder / CTO.

## Code license

- All code contributions are **Apache-2.0** only (`SPDX-License-Identifier: Apache-2.0`).
- No copyleft (GPL/AGPL/LGPL), no dual-license, no “source available” substitutes.
- By opening a PR you affirm you have the right to contribute the change under Apache-2.0 (DCO-style expectation: you wrote it or have permission; Signed-off-by welcome but not required until CI enforces it).

## Data / sample recordings

- Sample sessions and fixtures: **CC-BY-4.0** default; **CC0** allowed. See [`data-license.md`](data-license.md).
- Do not commit recordings that contain PII, private sites without permission, or third-party media under incompatible licenses.
- Declare license + attribution in `manifest.json` / package sidecars.

## PR bar

1. **Schema fidelity.** Bag writers and validators must match locked field names in [`schemas.md`](schemas.md) (`open-real2sim.capture.manifest/0.1`, topic paths, RDF optical, `T_parent_sensor` parent←sensor).
2. **Tests.** New writers cover at least validate-pass on a synthetic session (`or2s write-synthetic` path).
3. **No silent clocks.** Every stream declares time domain; no undocumented ROS/unix mixing.
4. **Scope.** Capture does not grow scene-export or marketplace features in this repo.
5. **Clean-room.** Describe Open Real2Sim on its own terms. Do not claim affiliation with, or “clone of,” any closed Real2Sim product. Unitree H1/G1 may appear only as demo reference robots when relevant to fixtures — Capture remains robot-agnostic.
6. Marketplace incentive programs are out of scope for v0 docs, UX copy, and issue templates.

## License checklist (maintainers)

- [ ] New dependency is Apache-2.0 / MIT / BSD (or equivalent permissive). No copyleft without an explicit project decision.
- [ ] Source files carry or inherit Apache-2.0.
- [ ] Sample data directory has an explicit CC-BY-4.0 or CC0 statement.
- [ ] PR does not vendor proprietary capture SDKs or closed binaries.

## Communication

CTO owns license + public messaging lock. Capture Lead owns bag schemas. OSS Docs owns public README/`docs` drafts.
