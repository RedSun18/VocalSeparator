#!/bin/bash
# create_dmg.sh — builds VocalSeparator.app then packages it into a DMG
# Run from the project root: bash create_dmg.sh

set -e
APP_NAME="VocalSeparator"
DMG_NAME="VocalSeparator-1.0.0"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${DMG_NAME}.dmg"
VOL_NAME="VocalSeparator"
ICON="assets/icon.icns"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  VocalSeparator — Build + DMG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Clean ────────────────────────────────────────────────────────────
echo ""
echo "▶ Cleaning previous build..."
rm -rf build dist

# ── Step 2: PyInstaller build ────────────────────────────────────────────────
echo ""
echo "▶ Building app with PyInstaller..."
pyinstaller VocalSeparator.spec

if [ ! -d "$APP_PATH" ]; then
    echo "✗ Build failed — $APP_PATH not found"
    exit 1
fi
echo "✓ App built: $APP_PATH"

# ── Step 3: Force icon refresh ───────────────────────────────────────────────
# macOS caches app icons — touch the app bundle to bust the cache
echo ""
echo "▶ Refreshing icon cache..."
touch "$APP_PATH"
# Copy icon explicitly into the bundle Resources folder
if [ -f "$ICON" ]; then
    cp "$ICON" "$APP_PATH/Contents/Resources/icon.icns"
    echo "✓ Icon copied to bundle"
fi

# ── Step 4: Ad-hoc code sign ─────────────────────────────────────────────────
echo ""
echo "▶ Code signing (ad-hoc)..."
codesign --deep --force --sign - "$APP_PATH"
echo "✓ Signed"

# ── Step 5: Create DMG ───────────────────────────────────────────────────────
echo ""
echo "▶ Creating DMG..."

STAGING="dist/dmg_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"

cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# Create writable DMG first so we can set its icon
TMP_DMG="dist/tmp_rw.dmg"
hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDRW \
    "$TMP_DMG"

# Mount it and set volume icon
MOUNT_DIR=$(hdiutil attach "$TMP_DMG" -readwrite -noverify -noautoopen | \
    grep "$VOL_NAME" | awk '{print $NF}')

if [ -n "$MOUNT_DIR" ] && [ -f "$ICON" ]; then
    # Copy icon as volume icon
    cp "$ICON" "$MOUNT_DIR/.VolumeIcon.icns"
    # Set custom icon bit on the volume
    SetFile -a C "$MOUNT_DIR" 2>/dev/null || true
    echo "✓ DMG volume icon set"
fi

# Unmount
hdiutil detach "$MOUNT_DIR" -quiet 2>/dev/null || true

# Convert to compressed read-only DMG
hdiutil convert "$TMP_DMG" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$DMG_PATH"

rm -f "$TMP_DMG"
rm -rf "$STAGING"

if [ -f "$DMG_PATH" ]; then
    SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ✓ Done!"
    echo "  DMG: $DMG_PATH"
    echo "  Size: $SIZE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    open dist/
else
    echo "✗ DMG creation failed"
    exit 1
fi
