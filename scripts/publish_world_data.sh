#!/usr/bin/env bash
# Publish the locally generated world data (data/) as a versioned GitHub
# Release asset. Decouples the ~1 GB payload from git history and gives the
# CI build jobs a stable URL to `gh release download` from.
#
# Usage:
#   ./scripts/publish_world_data.sh                  # auto-picks next tag
#   ./scripts/publish_world_data.sh world-data-v3    # explicit tag
#
# Requires: `gh` CLI authenticated against the MazeWorld repo, `zip`.
# After uploading, set the repo variable WORLD_DATA_TAG to the printed tag so
# the release workflow picks it up:
#   Settings -> Secrets and variables -> Actions -> Variables -> WORLD_DATA_TAG

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f data/manifest.json ]]; then
    echo "error: data/manifest.json not found; generate a world first (python main.py --dev)" >&2
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "error: gh CLI not installed (https://cli.github.com)" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "error: gh CLI not authenticated; run 'gh auth login'" >&2
    exit 1
fi

TAG="${1:-}"
if [[ -z "$TAG" ]]; then
    LATEST_N=$(gh release list --limit 100 --json tagName --jq '.[].tagName' \
        | grep -oE '^world-data-v[0-9]+$' \
        | sed -E 's/^world-data-v//' \
        | sort -n | tail -1 || true)
    NEXT_N=$(( ${LATEST_N:-0} + 1 ))
    TAG="world-data-v${NEXT_N}"
fi

ZIP_PATH="$(mktemp -d)/world-data.zip"
echo "Zipping data/ -> $ZIP_PATH (this takes a minute for ~1 GB)..."
zip -r -q "$ZIP_PATH" data -x 'data/saves/*'

SIZE_H=$(du -h "$ZIP_PATH" | cut -f1)
echo "Zip size: $SIZE_H"

if gh release view "$TAG" >/dev/null 2>&1; then
    echo "Release $TAG exists; uploading/replacing asset..."
    gh release upload "$TAG" "$ZIP_PATH" --clobber
else
    echo "Creating release $TAG..."
    gh release create "$TAG" "$ZIP_PATH" \
        --title "World data $TAG" \
        --notes "Pre-generated MazeWorld content (data/ folder) consumed by the release CI. Not a player-facing release." \
        --prerelease
fi

rm -f "$ZIP_PATH"
rmdir "$(dirname "$ZIP_PATH")" 2>/dev/null || true

cat <<EOF

Done. Published tag: $TAG

Next step: set the repo variable so the build workflow uses this data:
  gh variable set WORLD_DATA_TAG --body "$TAG"

Or via the UI:
  Settings -> Secrets and variables -> Actions -> Variables -> WORLD_DATA_TAG = $TAG
EOF
