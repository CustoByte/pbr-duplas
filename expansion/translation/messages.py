"""Lossless MESG reader and battle text catalogue; no originals bundled."""
import collections, re, struct
from prepare_campaign_doubles import read_archive, sha

RESOURCE = 0x27C31800
ARGUMENTS = {2: 1, 3: 1, 5: 1}
TOKEN = re.compile(r'\{[0-9A-F]{4}(?::[0-9A-F]{4})*\}')


def read_messages(data):
    if data[:4] != b'MESG':
        raise ValueError('Not a MESG resource')
    count = int.from_bytes(data[4:8], 'big')
    if not 0 < count < 65536:
        raise ValueError('Invalid message count')
    offsets = struct.unpack_from('>' + str(count) + 'I', data, 16)
    if offsets[0] != 16 + count * 4 or list(offsets) != sorted(offsets):
        raise ValueError('Unsupported MESG offset layout')
    rows = [data[start: offsets[i+1] if i+1<count else len(data)]
            for i, start in enumerate(offsets)]
    if any(len(row) % 2 or not row.endswith(b'\xff\xff\xff\xff') for row in rows):
        raise ValueError('Unterminated message')
    return data[:16], rows


def write_messages(header, rows):
    out = bytearray(header)
    at = 16 + len(rows) * 4
    for row in rows:
        out.extend(struct.pack('>I', at))
        at += len(row)
    out.extend(b''.join(rows))
    assert read_messages(bytes(out)) == (header, rows)
    return bytes(out)


def readable(row):
    words = struct.unpack('>' + str(len(row)//2) + 'H', row)
    out = []
    i = 0
    while i < len(words):
        value = words[i]
        i += 1
        if value != 65535:
            out.append(chr(value))
            continue
        command = words[i]
        i += 1
        if command == 65535:
            if i != len(words):
                raise ValueError('Unexpected words after message terminator')
            break
        if command == 65534:
            out.append('\n')
            continue
        args = words[i:i+ARGUMENTS.get(command, 0)]
        i += len(args)
        out.append('{' + ':'.join(f'{w:04X}' for w in (command, *args)) + '}')
    return ''.join(out)


def encoded(text):
    out = bytearray()
    i = 0
    while i < len(text):
        token = TOKEN.match(text, i)
        if token:
            values = [int(w, 16) for w in token[0][1:-1].split(':')]
            if len(values)-1 != ARGUMENTS.get(values[0], 0):
                raise ValueError('Control argument count mismatch')
            out.extend(struct.pack('>' + str(len(values)+1) + 'H', 65535, *values))
            i = token.end()
        elif text[i] == '\n':
            out.extend(b'\xff\xff\xff\xfe')
            i += 1
        else:
            if text[i] in '{}':
                raise ValueError('Unrecognized control token')
            out.extend(text[i].encode('utf-16-be'))
            i += 1
    out.extend(b'\xff\xff\xff\xff')
    return bytes(out)


def controls(text):
    return collections.Counter(TOKEN.findall(text))


def validate_target(original, target):
    source = readable(original)
    if controls(source) != controls(target):
        raise ValueError('Translation changed a dynamic variable or control')
    if [c for c in source if c in '▼▽'] != [c for c in target if c in '▼▽']:
        raise ValueError('Translation changed page/pause markers')
    result = encoded(target)
    if result[:8] != original[:8]:
        raise ValueError('Translation changed native font/style')
    return result


def catalogue(archive):
    entries = dict(read_archive(archive))
    header, rows = read_messages(entries[RESOURCE])
    texts = [readable(row) for row in rows]
    assert all(encoded(text) == row for text, row in zip(texts, rows))
    assert write_messages(header, rows) == entries[RESOURCE]
    return {'archive_sha256': sha(archive), 'resource_sha256': sha(entries[RESOURCE]),
            'resource': hex(RESOURCE), 'message_count': len(rows),
            'messages': [{'id': i, 'sha256': sha(row), 'text': text}
                         for i, (row, text) in enumerate(zip(rows, texts))]}
