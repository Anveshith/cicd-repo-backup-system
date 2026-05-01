#!/usr/bin/env bash
set -euo pipefail

echo "============================="
echo " Repository Backup System"
echo "============================="

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPO_NAME=$(basename "$REPO_URL" .git)
CLONE_DIR="/tmp/${REPO_NAME}_${TIMESTAMP}.git"
ARCHIVE="${BACKUP_DIR}/${REPO_NAME}_${TIMESTAMP}.tar.gz"
ENCRYPTED="${ARCHIVE}.gpg"

echo "▶ [1/4] Cloning: $REPO_URL"
git clone --mirror "$REPO_URL" "$CLONE_DIR"

echo "▶ [2/4] Compressing to $ARCHIVE"
tar -czf "$ARCHIVE" -C /tmp "${REPO_NAME}_${TIMESTAMP}.git"
rm -rf "$CLONE_DIR"

echo "▶ [3/4] Encrypting..."
echo "$GPG_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 \
  --symmetric --cipher-algo AES256 "$ARCHIVE"
rm "$ARCHIVE"

echo "▶ [4/4] Writing manifest..."
MANIFEST="${BACKUP_DIR}/manifest.json"
SIZE=$(stat -c%s "$ENCRYPTED")
ENTRY="{\"file\":\"$(basename $ENCRYPTED)\",\"repo\":\"$REPO_URL\",\"timestamp\":\"$TIMESTAMP\",\"size_bytes\":$SIZE}"

if [ -f "$MANIFEST" ]; then
  # Append to existing manifest array
  python3 -c "
import json, sys
with open('$MANIFEST') as f: data = json.load(f)
data.append($ENTRY)
with open('$MANIFEST', 'w') as f: json.dump(data, f, indent=2)
"
else
  echo "[$ENTRY]" > "$MANIFEST"
fi

echo "✅ Backup complete: $(basename $ENCRYPTED)"
echo "   Size: $SIZE bytes"