"""Local image registration and staged native-runtime releases. Standard library only."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request
from urllib.parse import urlsplit
import zipfile

FEED_URL = 'https://raw.githubusercontent.com/CustoByte/pbr-duplas/project/native-launcher/native/update.json'
MAX_PACKAGE = 512 * 1024 * 1024


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(pending, path)


def digest(path: Path, progress=None):
    total = path.stat().st_size
    done = 0
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            result.update(block)
            done += len(block)
            if progress:
                progress(done, total)
    return result.hexdigest()


def register_image(source: Path, home: Path, progress=None):
    source = source.resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in ('.iso', '.rvz'):
        raise ValueError('Selecione uma imagem ISO ou RVZ.')
    with source.open('rb') as stream:
        header = stream.read(256)
    kind = None
    game_id = None
    if header[:4] == b'RVZ\x01':
        kind = 'RVZ'
    elif header[24:28] == bytes.fromhex('5d1c9ea3'):
        kind = 'ISO Wii'
        game_id = header[:6].decode('ascii', errors='replace')
        if not game_id.startswith('RPB'):
            raise ValueError('Esta ISO não é do Pokémon Battle Revolution.')
    if kind is None:
        raise ValueError('O cabeçalho não corresponde a uma imagem Wii ISO/RVZ válida.')
    original_stat = source.stat()
    checksum = digest(source, progress)
    final_stat = source.stat()
    if (original_stat.st_size, original_stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns):
        raise ValueError('A imagem mudou durante a leitura. Tente novamente.')
    result = dict(path=str(source), format=kind, game_id=game_id,
                  bytes=final_stat.st_size, sha256=checksum, modified_image_allowed=True,
                  assets_extracted=False)
    write_json(home / 'source.json', result)
    return result


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def validate_feed(feed):
    if feed.get('schema') != 1 or feed.get('product') != 'pbr-native':
        raise ValueError('Canal de atualização incompatível.')
    if not feed.get('runtime_available'):
        return feed
    version = feed.get('version', '')
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Versão inválida.')
    package = feed.get('windows_x64', {})
    url = urlsplit(package.get('url', ''))
    prefix = f'/CustoByte/pbr-duplas/{version}/native/packages/'
    if (url.scheme != 'https' or url.netloc != 'raw.githubusercontent.com'
            or not url.path.startswith(prefix) or not url.path.endswith('.zip')
            or url.query or url.fragment or '..' in PurePosixPath(url.path).parts):
        raise ValueError('Pacote fora do repositório e da versão autorizados.')
    if not re.fullmatch('[a-f0-9]{64}', package.get('sha256', '')):
        raise ValueError('Hash de atualização inválido.')
    return feed


def fetch_feed():
    with urllib.request.urlopen(FEED_URL, timeout=30) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('Manifesto excede o limite.')
    return validate_feed(json.loads(data))


def unpack_runtime(package: Path, destination: Path):
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        if sum(e.file_size for e in entries) > MAX_PACKAGE or len(entries) > 20000:
            raise ValueError('Pacote expandido excede o limite.')
        seen = set()
        for entry in entries:
            name = entry.orig_filename
            path = PurePosixPath(name)
            mode = (entry.external_attr >> 16) & 0o170000
            if (name != entry.filename or '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts
                    or not path.parts or mode == 0o120000
                    or any(p.endswith((' ', '.')) for p in path.parts)
                    or any(p.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                           *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
                           for p in path.parts)):
                raise ValueError('Caminho inseguro no pacote.')
            key = name.rstrip('/').casefold()
            if key in seen:
                raise ValueError('Caminho duplicado no pacote.')
            seen.add(key)
        archive.extractall(destination)
    if not (destination / 'PBRNative.exe').is_file():
        raise ValueError('O pacote não contém o executável nativo.')


def install_runtime(home: Path, feed, progress=None):
    validate_feed(feed)
    if not feed.get('runtime_available'):
        raise ValueError('Ainda não há um motor nativo publicado.')
    home.mkdir(parents=True, exist_ok=True)
    releases = home / 'releases'
    releases.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='update-', dir=home) as temporary:
        stage = Path(temporary)
        package = stage / 'runtime.zip'
        details = feed['windows_x64']
        count = 0
        with urllib.request.urlopen(details['url'], timeout=60) as response, package.open('wb') as output:
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > MAX_PACKAGE:
                    raise ValueError('Download excede o limite.')
                output.write(block)
                if progress:
                    progress(count, None)
        if digest(package) != details['sha256']:
            raise ValueError('A atualização falhou na verificação SHA-256.')
        expanded = stage / 'expanded'
        expanded.mkdir()
        unpack_runtime(package, expanded)
        receipt = dict(version=feed['version'], sha256=digest(expanded / 'PBRNative.exe'))
        target = releases / feed['version']
        if target.exists():
            raise ValueError('Essa versão já está instalada; a instalação existente foi preservada.')
        os.replace(expanded, target)
        previous = load_json(home / 'current.json')
        # Switching this small pointer happens only after download, hash and extraction.
        if previous:
            write_json(home / 'previous.json', previous)
        write_json(home / 'current.json', receipt)
    return receipt


def runtime_path(home: Path):
    receipt = load_json(home / 'current.json')
    if not receipt:
        return None
    version = receipt.get('version', '')
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Registro local inválido.')
    executable = home / 'releases' / version / 'PBRNative.exe'
    if not executable.is_file() or digest(executable) != receipt.get('sha256'):
        raise ValueError('Executável ausente ou alterado. Reinstale uma versão verificada.')
    return executable


def rollback(home: Path):
    previous = load_json(home / 'previous.json')
    if not previous:
        raise ValueError('Não há uma versão anterior instalada.')
    current = load_json(home / 'current.json')
    # Validate before changing the active pointer.
    version = previous.get('version', '')
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Registro anterior inválido.')
    executable = home / 'releases' / version / 'PBRNative.exe'
    if not executable.is_file() or digest(executable) != previous.get('sha256'):
        raise ValueError('Versão anterior ausente ou alterada.')
    write_json(home / 'current.json', previous)
    if current:
        write_json(home / 'previous.json', current)
    return previous
