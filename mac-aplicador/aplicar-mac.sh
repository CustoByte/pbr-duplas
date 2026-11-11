#!/bin/bash
# macOS 12+: native tools only. No Python, DolphinTool, extraction or image writes.
set -Eeuo pipefail
trap 'printf "ERRO na linha %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR
PBR_CORE="$(cd "$(dirname "$0")" && pwd)"
PBR_DATA="${PBR_DATA_ROOT:-$HOME/Library/Application Support/PBR-Duplas}"
PBR_STATE="$PBR_DATA/config.plist"
PBR_IMAGE=""; PBR_APP=""; PBR_NO_GUI=0; PBR_NO_LAUNCH=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --image) PBR_IMAGE="$2"; shift 2;;
    --dolphin) PBR_APP="$2"; shift 2;;
    --no-gui) PBR_NO_GUI=1; shift;;
    --no-launch) PBR_NO_LAUNCH=1; shift;;
    *) echo "Parametro desconhecido: $1" >&2; exit 1;;
  esac
done
fail() { echo "ERRO: $*" >&2; exit 1; }
pget() { /usr/bin/plutil -extract "$1" raw -o - "$2" 2>/dev/null; }
hash() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
[ "$(uname -s)" = Darwin ] || fail 'Este iniciador e para macOS.'
mkdir -p "$PBR_DATA"
PBR_MANIFEST="$PBR_CORE/manifesto.json"
PBR_VERSION="$(pget mod_version "$PBR_MANIFEST")"
echo "PBR Duplas: $PBR_VERSION"
echo 'Use o save normal do jogo. Nao carregue estados antigos do Dolphin.'
# These are the exact replacement bytes used by the Windows applicator.
for PBR_I in 0 1; do
  PBR_REL="$(pget "replacements.$PBR_I.package_path" "$PBR_MANIFEST")"
  case "$PBR_REL" in mod/main.dol|mod/common.fsys) ;; *) fail 'Caminho inesperado no pacote.';; esac
  PBR_SHA="$(pget "replacements.$PBR_I.sha256" "$PBR_MANIFEST")"
  [ "$(hash "$PBR_CORE/$PBR_REL")" = "$PBR_SHA" ] || fail "Pacote corrompido: $PBR_REL"
done
if [ -f "$PBR_STATE" ]; then
  [ -n "$PBR_IMAGE" ] || PBR_IMAGE="$(pget source_image "$PBR_STATE" || true)"
  [ -n "$PBR_APP" ] || PBR_APP="$(pget dolphin_app "$PBR_STATE" || true)"
fi
if [ -z "$PBR_IMAGE" ] || [ ! -e "$PBR_IMAGE" ]; then
  [ "$PBR_NO_GUI" -eq 0 ] || fail 'Informe --image com a ISO/RVZ ou sua pasta.'
  PBR_IMAGE="$(/usr/bin/osascript -e 'POSIX path of (choose folder with prompt "Escolha a pasta da ISO ou RVZ original de Pokemon Battle Revolution")')"
fi
if [ -d "$PBR_IMAGE" ]; then
  PBR_CHOICES=()
  shopt -s nullglob
  for PBR_FILE in "$PBR_IMAGE"/*; do
    [ -f "$PBR_FILE" ] || continue
    case "$PBR_FILE" in *-Duplas*) continue;; esac
    case "$PBR_FILE" in *.[rR][vV][zZ]|*.[iI][sS][oO]) PBR_CHOICES+=("$PBR_FILE");; esac
  done
  [ "${#PBR_CHOICES[@]}" -gt 0 ] || fail 'Nao encontrei ISO/RVZ nessa pasta.'
  if [ "${#PBR_CHOICES[@]}" -eq 1 ]; then PBR_IMAGE="${PBR_CHOICES[0]}"
  else
    [ "$PBR_NO_GUI" -eq 0 ] || fail 'Ha varias imagens. Informe --image com um arquivo.'
    PBR_IMAGE="$(/usr/bin/osascript -e 'POSIX path of (choose file with prompt "Escolha a ISO ou RVZ original do Pokemon Battle Revolution")')"
  fi
fi
[ -f "$PBR_IMAGE" ] || fail "Imagem nao encontrada: $PBR_IMAGE"
PBR_IMAGE="$(cd "$(dirname "$PBR_IMAGE")" && pwd)/$(basename "$PBR_IMAGE")"
# RVZ Header1 is 0x48 bytes; Header2's 0x10-byte prefix precedes disc_header.
PBR_MAGIC="$(/usr/bin/od -An -tx1 -N4 "$PBR_IMAGE" | tr -d ' \n')"
PBR_OFFSET=0
case "$PBR_MAGIC" in 52565a01) PBR_OFFSET=88;; 52504245) PBR_OFFSET=0;; *) fail 'Formato nao suportado. Escolha uma ISO ou RVZ Wii original.';; esac
PBR_ID="$(/bin/dd if="$PBR_IMAGE" bs=1 skip="$PBR_OFFSET" count=8 2>/dev/null | /usr/bin/od -An -tx1 | tr -d ' \n')"
PBR_WII="$(/bin/dd if="$PBR_IMAGE" bs=1 skip="$((PBR_OFFSET+24))" count=4 2>/dev/null | /usr/bin/od -An -tx1 | tr -d ' \n')"
[ "$PBR_ID" = 5250424530310000 ] && [ "$PBR_WII" = 5d1c9ea3 ] || fail 'Necessario USA RPBE01, disco 1, revisao 0.'
if [ -z "$PBR_APP" ] || [ ! -x "$PBR_APP/Contents/MacOS/Dolphin" ]; then
  PBR_APP=''
  for PBR_CANDIDATE in /Applications/Dolphin.app "$HOME/Applications/Dolphin.app"; do
    if [ -x "$PBR_CANDIDATE/Contents/MacOS/Dolphin" ]; then PBR_APP="$PBR_CANDIDATE"; break; fi
  done
fi
if [ -z "$PBR_APP" ]; then
  [ "$PBR_NO_GUI" -eq 0 ] || fail 'Informe --dolphin com o Dolphin.app.'
  PBR_APP="$(/usr/bin/osascript -e 'POSIX path of (choose file of type {"com.apple.application-bundle"} with prompt "Escolha Dolphin.app")')"
  PBR_APP="${PBR_APP%/}"
fi
[ -x "$PBR_APP/Contents/MacOS/Dolphin" ] || fail 'O aplicativo escolhido nao e um Dolphin.app valido.'
if [ "$PBR_NO_LAUNCH" -eq 0 ] && /usr/bin/pgrep -x Dolphin >/dev/null; then
  fail 'Feche o Dolphin e abra este iniciador novamente. Seu progresso nao sera encerrado a forca.'
fi
PBR_DESCRIPTOR="$PBR_DATA/Jogar-PBR-Duplas.json"
PBR_TEMP="$(/usr/bin/mktemp "$PBR_DATA/descritor.XXXXXX")"
trap 'rm -f "${PBR_TEMP:-}" "${PBR_CONFIG_TEMP:-}"' EXIT
/usr/bin/osascript -l JavaScript "$PBR_CORE/descriptor.jxa" "$PBR_IMAGE" "$PBR_CORE/riivolution.xml" "$PBR_VERSION" > "$PBR_TEMP"
/usr/bin/plutil -lint "$PBR_TEMP" >/dev/null
/bin/mv -f "$PBR_TEMP" "$PBR_DESCRIPTOR"
PBR_TEMP=''
PBR_CONFIG_TEMP="$(/usr/bin/mktemp "$PBR_DATA/config.XXXXXX")"
/usr/bin/plutil -create xml1 "$PBR_CONFIG_TEMP"
/usr/bin/plutil -insert source_image -string "$PBR_IMAGE" "$PBR_CONFIG_TEMP"
/usr/bin/plutil -insert dolphin_app -string "$PBR_APP" "$PBR_CONFIG_TEMP"
/usr/bin/plutil -insert mod_version -string "$PBR_VERSION" "$PBR_CONFIG_TEMP"
/bin/mv -f "$PBR_CONFIG_TEMP" "$PBR_STATE"
PBR_CONFIG_TEMP=''
echo 'Mod preparado. A ISO/RVZ original e os saves nao foram alterados.'
echo "Descritor: $PBR_DESCRIPTOR"
if [ "$PBR_NO_LAUNCH" -eq 0 ]; then
  # No -u: keep the user's ordinary Dolphin configuration and campaign saves.
  /usr/bin/open -a "$PBR_APP" --args -e "$PBR_DESCRIPTOR"
fi
