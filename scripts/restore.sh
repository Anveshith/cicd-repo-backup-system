#!/usr/bin/env bash
set -euo pipefail

# Usage: bash restore.sh <path-to-encrypted-backup.tar.gz.gpg> <output-dir>
ENCRYPTED_FILE="${1:?Usage: restore.sh <file.gpg> <output-dir>}"
OUTPUT_DIR="${2:?Usage: restore.sh <file.gpg> <output-dir>}"

mkdir -p "$OUTPUT_DIR"
DECRYPTED="${OUTPUT_DIR}/$(basename ${ENCRYPTED_FILE%.gpg})"

echo "▶ Decrypting $ENCRYPTED_FILE..."
echo "$GPG_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 \
  --output "$DECRYPTED" --decrypt "$ENCRYPTED_FILE"

echo "▶ Extracting to $OUTPUT_DIR..."
tar -xzf "$DECRYPTED" -C "$OUTPUT_DIR"
rm "$DECRYPTED"

echo "✅ Restore complete. Contents of $OUTPUT_DIR:"
ls "$OUTPUT_DIR"