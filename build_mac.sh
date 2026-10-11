#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv-mac"
APP_NAME="OpenChess"
VERSION="0.9.0"
DIST_DIR="dist-$VERSION"
WORK_DIR="build-$VERSION"
SPEC_DIR="$WORK_DIR/spec"
export PYINSTALLER_CONFIG_DIR="$PWD/$WORK_DIR/pyinstaller-config"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install -r requirements.txt

mkdir -p "$DIST_DIR" "$WORK_DIR" "$SPEC_DIR"

"$VENV_DIR/bin/pyinstaller" \
    --noconfirm \
    --clean \
    --windowed \
    --name "$APP_NAME" \
    --distpath "$DIST_DIR" \
    --workpath "$WORK_DIR/work" \
    --specpath "$SPEC_DIR" \
    --osx-bundle-identifier "es.openchess.app" \
    --icon "$PWD/assets/OpenChess.icns" \
    --add-data "$PWD/assets/openchess-icon-1024.png:assets" \
    --collect-all customtkinter \
    --collect-all reportlab \
    --collect-all openpyxl \
    --collect-all xlrd \
    "$PWD/run.py"

APP_PATH="$DIST_DIR/$APP_NAME.app"
plutil -replace CFBundleShortVersionString -string "$VERSION" "$APP_PATH/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$VERSION" "$APP_PATH/Contents/Info.plist"
codesign --force --deep --sign - "$APP_PATH"
codesign --verify --deep --strict "$APP_PATH"
"$APP_PATH/Contents/MacOS/$APP_NAME" --smoke-test

PKG_PATH="$DIST_DIR/${APP_NAME}-${VERSION}-macOS-x86_64.pkg"
ZIP_PATH="$DIST_DIR/${APP_NAME}-${VERSION}-macOS-x86_64.zip"

ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

if [ -e "$PKG_PATH" ]; then
    mv "$PKG_PATH" "$PKG_PATH.previous"
fi

pkgbuild \
    --component "$DIST_DIR/$APP_NAME.app" \
    --identifier "es.openchess.app" \
    --version "$VERSION" \
    --install-location "/Applications" \
    "$PKG_PATH"

echo "Instalador creado en $PKG_PATH"
echo "Aplicación comprimida creada en $ZIP_PATH"
