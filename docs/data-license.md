> **Status:** draft — do not publish until the GitHub org (`youseftrk`) is confirmed.

# Data license — open-real2sim-capture

## Split: code vs data

| Kind | License |
|------|---------|
| **Code** (SDK, CLI, apps, schemas-as-code) | **Apache-2.0** only |
| **Sample recordings / fixture bags / published capture datasets** | **CC-BY-4.0** default; **CC0** allowed |

Code never switches to a Creative Commons license. Data never inherits “all rights reserved” by accident — declare a data license in the session package.

## Default for contributions

Unless a contributor states otherwise in the PR and in package metadata:

- Sample sessions accepted into this repository use **CC-BY-4.0**.
- Contributors may instead mark fixtures **CC0-1.0** when they waive attribution.

## What to put in the bag

- Prefer an explicit data-license statement next to the session (for example in `attribution.notes`, a `LICENSE` sidecar in the session directory, or a dataset README).
- `manifest.json` currently carries a `license` string field (locked schema). For **code-adjacent** tooling artifacts Apache-2.0 is fine; for **redistributable RGB/depth recordings** prefer documenting CC-BY-4.0 or CC0 in attribution / sidecars until the manifest enum is widened (see schema gaps tracked by Capture Lead).

## Attribution

CC-BY-4.0 requires retaining credit. Fill `attribution.contributor` / `site` / `notes` in `manifest.json` when redistributing.

## Non-goals

- No marketplace incentive framing around dataset uploads in v0.
- No claim that submitting a bag grants marketplace rights beyond the declared Creative Commons (or CC0) terms.
