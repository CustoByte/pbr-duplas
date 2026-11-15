#!/bin/bash
# Builds private local assets. Requires an original extracted DATA folder once.
set -Eeuo pipefail
PBR_CORE="$(cd "$(dirname "$0")/.." && pwd)"
PBR_DATA="$HOME/Library/Application Support/PBR-Duplas/Snivy"
mkdir -p "$PBR_DATA"
PBR_STATE="$PBR_DATA/config.plist"
pget() { /usr/bin/plutil -extract "$1" raw -o - "$2" 2>/dev/null || true; }
choose_file() { /usr/bin/osascript -e "POSIX path of (choose file with prompt \"$1\")"; }
choose_folder() { /usr/bin/osascript -e "POSIX path of (choose folder with prompt \"$1\")"; }
[ "$(uname -s)" = Darwin ] || { echo 'Este iniciador e para macOS.'; exit 1; }
echo 'Feche o Dolphin antes de preparar a candidata. Use o save normal, sem estados antigos.'
PBR_ORIGINALS="$(pget originals "$PBR_STATE")"
PBR_SOURCE="$(pget source "$PBR_STATE")"
PBR_IMAGE="$(pget image "$PBR_STATE")"
if [ ! -f "$PBR_ORIGINALS/sys/main.dol" ]; then
  echo 'Primeiro uso: no Dolphin, Propriedades > Sistema de Arquivos > clique direito na Particao de Dados > Extrair Tudo.'
  echo 'Selecione a pasta extraida que contem sys e files. Nao precisa extrair arquivo por arquivo.'
  PBR_ORIGINALS="$(choose_folder 'Escolha a pasta original extraida que contem sys e files')"
  PBR_ORIGINALS="${PBR_ORIGINALS%/}"
fi
[ -f "$PBR_SOURCE" ] || PBR_SOURCE="$(choose_file 'Escolha seu Tsutarja.brres')"
[ -f "$PBR_IMAGE" ] || PBR_IMAGE="$(choose_file 'Escolha sua ISO ou RVZ original USA do Battle Revolution')"
PBR_ARCH="$(uname -m)"
case "$PBR_ARCH" in arm64) PBR_ARCH=arm64;; x86_64) PBR_ARCH=x64;; *) echo 'Arquitetura nao suportada.'; exit 1;; esac
PBR_BLENDER_ROOT="$PBR_DATA/sdk/blender-$PBR_ARCH"
PBR_BLENDER="$PBR_BLENDER_ROOT/Blender.app/Contents/MacOS/Blender"
if [ ! -x "$PBR_BLENDER" ]; then
  mkdir -p "$PBR_DATA/sdk"
  PBR_FILENAME="blender-3.3.21-macos-$PBR_ARCH.dmg"
  case "$PBR_ARCH" in
    arm64) PBR_SHA=8f2306c761a8d71c9426e9dc254ed7c7db96133d5333c8233e61e0a6dd526947;;
    x64) PBR_SHA=c12a9ae93193139d0af89d04759ca0aa8c5c90f2058985c9459685c9475cff1d;;
  esac
  PBR_DMG="$PBR_DATA/sdk/$PBR_FILENAME"
  if [ ! -f "$PBR_DMG" ] || [ "$(shasum -a 256 "$PBR_DMG" | awk '{print $1}')" != "$PBR_SHA" ]; then
    echo 'Baixando Blender portatil para conversao local (apenas no primeiro uso)...'
    curl --fail --location --retry 2 "https://download.blender.org/release/Blender3.3/$PBR_FILENAME" -o "$PBR_DMG.tmp"
    [ "$(shasum -a 256 "$PBR_DMG.tmp" | awk '{print $1}')" = "$PBR_SHA" ] || { echo 'Hash do Blender invalido.'; exit 1; }
    mv -f "$PBR_DMG.tmp" "$PBR_DMG"
  fi
  PBR_MOUNT="$(mktemp -d "$PBR_DATA/sdk/mount.XXXXXX")"
  trap 'hdiutil detach "$PBR_MOUNT" >/dev/null 2>&1 || true; rmdir "$PBR_MOUNT" 2>/dev/null || true' EXIT
  hdiutil attach -readonly -nobrowse -mountpoint "$PBR_MOUNT" "$PBR_DMG" >/dev/null
  mkdir -p "$PBR_BLENDER_ROOT"
  ditto "$PBR_MOUNT/Blender.app" "$PBR_BLENDER_ROOT/Blender.app"
  hdiutil detach "$PBR_MOUNT" >/dev/null
  rmdir "$PBR_MOUNT"
  trap - EXIT
fi
export SSL_CERT_FILE=/etc/ssl/cert.pem
PBR_PYTHON="$PBR_BLENDER_ROOT/Blender.app/Contents/Resources/3.3/python/bin/python3.10"
[ -x "$PBR_PYTHON" ] || { echo 'Python interno do Blender nao encontrado.'; exit 1; }
"$PBR_PYTHON" "$PBR_CORE/experiments/snivy/prepare_local_sdk.py" --root "$PBR_DATA/sdk/dependencies"
export PYTHONPATH="$PBR_DATA/sdk/dependencies/python-deps"
PBR_OUTPUT="$PBR_DATA/install-$(date +%Y%m%d-%H%M%S)"
"$PBR_PYTHON" "$PBR_CORE/experiments/snivy/build_mac_overlay.py" --core "$PBR_CORE" --originals "$PBR_ORIGINALS" \
  --blender "$PBR_BLENDER" --source "$PBR_SOURCE" --sdk "$PBR_DATA/sdk/dependencies" --cache "$PBR_DATA/assets" \
  --output "$PBR_OUTPUT" --image "$PBR_IMAGE"
PBR_NEW_STATE="$(mktemp "$PBR_DATA/config.XXXXXX")"
plutil -create xml1 "$PBR_NEW_STATE"
plutil -insert originals -string "$PBR_ORIGINALS" "$PBR_NEW_STATE"
plutil -insert source -string "$PBR_SOURCE" "$PBR_NEW_STATE"
plutil -insert image -string "$PBR_IMAGE" "$PBR_NEW_STATE"
mv -f "$PBR_NEW_STATE" "$PBR_STATE"
echo "Pronto. No Dolphin, abra: $PBR_OUTPUT/Jogar-PBR-Duplas.json"
echo 'A imagem original e os saves foram preservados. Esta candidata ainda exige teste em jogo.'
open -R "$PBR_OUTPUT/Jogar-PBR-Duplas.json"
read -r -p 'Pressione Enter para fechar.'
