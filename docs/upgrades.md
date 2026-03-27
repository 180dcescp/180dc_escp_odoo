# Upgrades

## Policy

- install-only initialization belongs in install data or narrowly scoped hooks
- repeatable default synchronization belongs in release-to-release upgrade code
- product releases must support upgrade from the previous tagged version

## Current baseline

This repository now carries the final community-first module split:

- `core`
- `contacts`
- `cycles`
- `hr`
- `recruitment`
- `projects`
- `reviews`
- `website`
- `meta`
- thin distribution overlays

Versioned upgrade scripts should preserve those boundaries and keep distribution addons free of reusable business logic.
