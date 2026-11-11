#!/bin/bash
# Stable native macOS bootstrap; download/update only from the user's repository.
set -Eeuo pipefail
trap 'printf "ERRO na linha %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR
PBR_HERE="$(cd "$(dirname "$0")" && pwd)"
PBR_DATA="${PBR_DATA_ROOT:-$HOME/Library/Application Support/PBR-Duplas}"
PBR_FEED="${PBR_FEED_URL:-https://github.com/CustoByte/pbr-duplas/releases/latest/download/update.json}"
PBR_CACHE="$PBR_DATA/cache"
PBR_LOCK="$PBR_DATA/aplicador.lock"
PBR_LOCKED=0
cleanup() {
  [ -z "${PBR_FEED_TEMP:-}" ] || rm -f "$PBR_FEED_TEMP"
  [ -z "${PBR_PARTIAL:-}" ] || rm -f "$PBR_PARTIAL"
  if [ -n "${PBR_STAGING:-}" ] && [ -d "$PBR_STAGING" ]; then rm -rf -- "$PBR_STAGING"; fi
  if [ "$PBR_LOCKED" -eq 1 ]; then rm -f "$PBR_LOCK/pid"; rmdir "$PBR_LOCK" 2>/dev/null || true; fi
}
trap cleanup EXIT
pget() { /usr/bin/plutil -extract "$1" raw -o - "$2" 2>/dev/null; }
hash() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
download() {
  case "$1" in https://*) /usr/bin/curl --fail --location --silent --show-error --connect-timeout 20 --max-time 180 "$1" -o "$2";;
    file://*) [ "${PBR_TEST_MODE:-0}" = 1 ] && /bin/cp "${1#file://}" "$2";;
    *) return 1;;
  esac
}
PBR_STATUS=0
main() {
  [ "$(uname -s)" = Darwin ] || { echo 'Este arquivo e para macOS.'; return 1; }
  mkdir -p "$PBR_CACHE"
  if ! mkdir "$PBR_LOCK" 2>/dev/null; then
    PBR_PID="$(cat "$PBR_LOCK/pid" 2>/dev/null || true)"
    if [[ "$PBR_PID" =~ ^[0-9]+$ ]] && kill -0 "$PBR_PID" 2>/dev/null; then echo 'Outro aplicador ja esta aberto.'; return 1; fi
    rm -f "$PBR_LOCK/pid"; rmdir "$PBR_LOCK" || return 1; mkdir "$PBR_LOCK" || return 1
  fi
  PBR_LOCKED=1; echo "$$" > "$PBR_LOCK/pid"
  PBR_FEED_TEMP="$(/usr/bin/mktemp "$PBR_CACHE/feed.XXXXXX")"
  PBR_PACKAGE=''
  echo 'Consultando atualizacoes do PBR Duplas...'
  if download "$PBR_FEED" "$PBR_FEED_TEMP"; then
    PBR_SCHEMA="$(pget schema "$PBR_FEED_TEMP" || true)"
    PBR_SHA="$(pget package_sha256 "$PBR_FEED_TEMP" || true)"
    PBR_URL="$(pget package_url "$PBR_FEED_TEMP" || true)"
    PBR_VERSION="$(pget version "$PBR_FEED_TEMP" || true)"
    if [ "$PBR_SCHEMA" = 1 ] && [[ "$PBR_SHA" =~ ^[a-f0-9]{64}$ ]]; then
      case "$PBR_URL" in
        https://github.com/CustoByte/pbr-duplas/releases/download/*/aplicador-core.zip) ;;
        file://*) [ "${PBR_TEST_MODE:-0}" = 1 ] || PBR_URL='';;
        *) PBR_URL='';;
      esac
      if [ -n "$PBR_URL" ]; then
        PBR_CANDIDATE="$PBR_CACHE/$PBR_SHA.zip"
        if [ -f "$PBR_CANDIDATE" ] && [ "$(hash "$PBR_CANDIDATE")" = "$PBR_SHA" ]; then
          PBR_PACKAGE="$PBR_CANDIDATE"
        else
          PBR_PARTIAL="$(/usr/bin/mktemp "$PBR_CACHE/download.XXXXXX")"
          echo "Baixando $PBR_VERSION..."
          if download "$PBR_URL" "$PBR_PARTIAL" && [ "$(hash "$PBR_PARTIAL")" = "$PBR_SHA" ]; then
            mv -f "$PBR_PARTIAL" "$PBR_CANDIDATE"; PBR_PARTIAL=''; PBR_PACKAGE="$PBR_CANDIDATE"
          else echo 'Falha no download/hash. A versao anterior sera mantida.'; fi
        fi
        if [ -n "$PBR_PACKAGE" ]; then cp "$PBR_FEED_TEMP" "$PBR_DATA/ultima-versao.json"; fi
      fi
    fi
  fi
  if [ -z "$PBR_PACKAGE" ] && [ -f "$PBR_DATA/ultima-versao.json" ]; then
    PBR_SHA="$(pget package_sha256 "$PBR_DATA/ultima-versao.json" || true)"
    if [[ "$PBR_SHA" =~ ^[a-f0-9]{64}$ ]] && [ -f "$PBR_CACHE/$PBR_SHA.zip" ] && [ "$(hash "$PBR_CACHE/$PBR_SHA.zip")" = "$PBR_SHA" ]; then PBR_PACKAGE="$PBR_CACHE/$PBR_SHA.zip"; fi
  fi
  if [ -z "$PBR_PACKAGE" ]; then
    echo 'Usando o pacote inicial incluido.'
    PBR_PACKAGE="$PBR_HERE/base.zip"
    PBR_SHA="$(tr -d ' \r\n' < "$PBR_HERE/base.sha256")"
    [ "$(hash "$PBR_PACKAGE")" = "$PBR_SHA" ] || { echo 'Pacote inicial corrompido.'; return 1; }
  fi
  # Reject archive paths that can escape the versioned cache directory.
  PBR_LIST="$(/usr/bin/unzip -Z1 "$PBR_PACKAGE")" || return 1
  while IFS= read -r PBR_ENTRY; do
    case "$PBR_ENTRY" in /*|*\\*|../*|*/../*|*/..|*:*) echo 'Caminho inseguro no pacote.'; return 1;; esac
  done <<< "$PBR_LIST"
  PBR_RUN="$PBR_CACHE/mac-$PBR_SHA"
  if [ ! -d "$PBR_RUN" ]; then
    PBR_STAGING="$(/usr/bin/mktemp -d "$PBR_CACHE/montagem.XXXXXX")"
    /usr/bin/ditto -x -k "$PBR_PACKAGE" "$PBR_STAGING" || return 1
    [ -f "$PBR_STAGING/aplicar-mac.sh" ] && [ -f "$PBR_STAGING/descriptor.jxa" ] && [ -f "$PBR_STAGING/riivolution.xml" ] || { echo 'Pacote sem suporte Mac.'; return 1; }
    mv "$PBR_STAGING" "$PBR_RUN"; PBR_STAGING=""
  fi
  for PBR_FILE in aplicar-mac.sh descriptor.jxa riivolution.xml manifesto.json mod/main.dol mod/common.fsys; do
    PBR_EXPECTED="$(/usr/bin/unzip -p "$PBR_PACKAGE" "$PBR_FILE" | /usr/bin/shasum -a 256 | /usr/bin/awk '{print $1}')"
    [ -f "$PBR_RUN/$PBR_FILE" ] && [ "$(hash "$PBR_RUN/$PBR_FILE")" = "$PBR_EXPECTED" ] || { echo 'Cache alterado ou corrompido. Nenhum jogo foi modificado.'; return 1; }
  done
  /bin/bash "$PBR_RUN/aplicar-mac.sh" "$@"
}
# Do not wrap main in a conditional: retain errexit on unexpected core failures.
main "$@"
