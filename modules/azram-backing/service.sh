#!/system/bin/sh
# ZRAM Backing module — guarded hybridswap backing setup.
#
# This module is intentionally device-specific. It runs before Scene's swap
# controller, attaches the vendor hybridswap partition, and then stops. Scene
# remains responsible for zram size, compressor selection, rebuild and swapon.
# Unknown devices, partition conflicts and failed preconditions are refused
# before any swapoff/reset operation.

EXPECTED_MODEL=PLQ110
EXPECTED_DEVICE=OP6113L1
EXPECTED_ANDROID_MAJOR=16
BACKING_DEV=/dev/block/by-name/hybridswap
ZRAM_DEV=/dev/block/zram0
ZRAM_SYS=/sys/block/zram0
SCENE_MOD=/data/adb/modules/scene_swap_controller
SCENE_CONFIG=/data/swap_config.conf

log() { echo "zram-backing: $*"; }
refuse() { log "REFUSE: $*"; exit 1; }

# ---- identity gate ----
[ "$(getprop ro.product.model)" = "$EXPECTED_MODEL" ] \
    || refuse "unsupported model $(getprop ro.product.model)"
[ "$(getprop ro.product.device)" = "$EXPECTED_DEVICE" ] \
    || refuse "unsupported device $(getprop ro.product.device)"
[ "$(getprop ro.build.version.release)" = "$EXPECTED_ANDROID_MAJOR" ] \
    || refuse "unsupported Android release $(getprop ro.build.version.release)"

# ---- userspace ownership gate ----
# Scene owns zram rebuild/sizing/swapon. This module is only allowed to set a
# backing before Scene observes it. If Scene is configured to rebuild zram or
# manage writeback itself, there is no safe hand-off contract, so refuse.
[ -d "$SCENE_MOD" ] || refuse "scene_swap_controller is not installed"
[ -f "$SCENE_CONFIG" ] || refuse "Scene config is missing"
SCENE_ZRAM=$(sed -n 's/^zram=//p' "$SCENE_CONFIG" | head -n 1)
SCENE_WRITEBACK=$(sed -n 's/^zram_writeback=//p' "$SCENE_CONFIG" | head -n 1)
[ "$SCENE_ZRAM" = false ] \
    || refuse "Scene zram manager is enabled; it owns reset/rebuild"
[ "$SCENE_WRITEBACK" = default ] \
    || refuse "Scene writeback mode is $SCENE_WRITEBACK; it owns backing"

# ---- wait for zram and validate the backing partition before reset ----
i=0
while [ ! -e "$ZRAM_SYS/disksize" ] && [ "$i" -lt 60 ]; do
    sleep 1
    i=$((i + 1))
done
[ -e "$ZRAM_SYS/disksize" ] || refuse "zram0 never appeared"
[ -e "$ZRAM_SYS/backing_dev" ] \
    || refuse "zram backing_dev interface is unavailable (writeback is not enabled)"
[ -w "$ZRAM_SYS/backing_dev" ] \
    || refuse "zram backing_dev interface is not writable"
[ -e "$ZRAM_SYS/reset" ] && [ -w "$ZRAM_SYS/reset" ] \
    || refuse "zram reset interface is unavailable or not writable"
[ -e "$ZRAM_SYS/comp_algorithm" ] && [ -w "$ZRAM_SYS/comp_algorithm" ] \
    || refuse "zram compressor interface is unavailable or not writable"
[ -w "$ZRAM_SYS/disksize" ] \
    || refuse "zram disksize interface is not writable"
[ -b "$BACKING_DEV" ] || refuse "$BACKING_DEV is not a block device"

BACKING_REAL=$(readlink -f "$BACKING_DEV" 2>/dev/null)
[ -n "$BACKING_REAL" ] || refuse "cannot resolve $BACKING_DEV"
grep -F -q "$BACKING_REAL" /proc/mounts 2>/dev/null \
    && refuse "$BACKING_REAL is mounted"
grep -F -q "$BACKING_REAL" /proc/swaps 2>/dev/null \
    && refuse "$BACKING_REAL is already used as swap"

CURRENT_BACKING=$(cat "$ZRAM_SYS/backing_dev" 2>/dev/null)
if [ -n "$CURRENT_BACKING" ]; then
    CURRENT_REAL=$(readlink -f "$CURRENT_BACKING" 2>/dev/null)
    [ "$CURRENT_REAL" = "$BACKING_REAL" ] \
        && { log "backing already set: $CURRENT_BACKING"; exit 0; }
    refuse "zram already has a different backing: $CURRENT_BACKING"
fi

OLD_SIZE=$(cat "$ZRAM_SYS/disksize" 2>/dev/null)
case "$OLD_SIZE" in
    ''|*[!0-9]*) refuse "invalid zram disksize: $OLD_SIZE" ;;
esac

# The uninitialized case needs no destructive transition.
if [ "$OLD_SIZE" = 0 ]; then
    echo "$BACKING_DEV" > "$ZRAM_SYS/backing_dev" 2>/dev/null \
        || refuse "cannot attach backing to uninitialized zram"
    CURRENT_BACKING=$(cat "$ZRAM_SYS/backing_dev" 2>/dev/null)
    CURRENT_REAL=$(readlink -f "$CURRENT_BACKING" 2>/dev/null)
    [ "$CURRENT_REAL" = "$BACKING_REAL" ] \
        || refuse "backing verification failed after attach"
    log "backing attached without reset: $CURRENT_BACKING"
    exit 0
fi

# ---- capture enough state for a failed-attach recovery ----
command -v swapoff >/dev/null 2>&1 || refuse "swapoff is unavailable"
command -v swapon >/dev/null 2>&1 || refuse "swapon is unavailable"
command -v mkswap >/dev/null 2>&1 || refuse "mkswap is unavailable for recovery"
OLD_ALGO=$(sed -n 's/.*\[\([^]]*\)\].*/\1/p' "$ZRAM_SYS/comp_algorithm" 2>/dev/null)
[ -n "$OLD_ALGO" ] || refuse "cannot determine current zram compressor"
SWAP_LINE=$(awk '$1 == "/dev/block/zram0" { print; exit }' /proc/swaps 2>/dev/null)
OLD_PRIORITY=$(printf '%s\n' "$SWAP_LINE" | awk '{print $5}')

restore_zram() {
    log "attempting zram recovery"
    echo "$OLD_ALGO" > "$ZRAM_SYS/comp_algorithm" 2>/dev/null || return 1
    echo "$OLD_SIZE" > "$ZRAM_SYS/disksize" 2>/dev/null || return 1
    mkswap "$ZRAM_DEV" >/dev/null 2>&1 || return 1
    if [ -n "$OLD_PRIORITY" ]; then
        swapon -p "$OLD_PRIORITY" "$ZRAM_DEV" >/dev/null 2>&1 || return 1
    else
        swapon "$ZRAM_DEV" >/dev/null 2>&1 || return 1
    fi
    return 0
}

# Only deactivate zram after all identity, partition, conflict and recovery
# preconditions have passed.
if [ -n "$SWAP_LINE" ]; then
    swapoff "$ZRAM_DEV" >/dev/null 2>&1 \
        || refuse "swapoff failed; zram was not reset"
fi

if ! echo 1 > "$ZRAM_SYS/reset" 2>/dev/null; then
    restore_zram || log "ERROR: reset failed and recovery also failed"
    exit 1
fi
if [ "$(cat "$ZRAM_SYS/disksize" 2>/dev/null)" != 0 ]; then
    restore_zram || log "ERROR: reset was incomplete and recovery also failed"
    exit 1
fi

if ! echo "$BACKING_DEV" > "$ZRAM_SYS/backing_dev" 2>/dev/null; then
    restore_zram || log "ERROR: backing attach failed and recovery also failed"
    exit 1
fi
CURRENT_BACKING=$(cat "$ZRAM_SYS/backing_dev" 2>/dev/null)
CURRENT_REAL=$(readlink -f "$CURRENT_BACKING" 2>/dev/null)
[ "$CURRENT_REAL" = "$BACKING_REAL" ] \
    || { restore_zram || log "ERROR: backing verification failed and recovery also failed"; exit 1; }

log "backing attached: $CURRENT_BACKING"
exit 0
