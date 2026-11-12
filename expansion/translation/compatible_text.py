"""Conservative fallback for Portuguese glyphs missing in the USA font."""
import unicodedata

def compatible(text, protected=()):
    names = sorted(set(protected) | {'Pokémon', 'Pokétopia', 'POKéMON'}, key=len, reverse=True)
    markers = {}
    for i, name in enumerate(names):
        marker = f'ZXPROTECTED{i}ZX'
        if name in text:
            text = text.replace(name, marker)
            markers[marker] = name
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if not unicodedata.combining(c))
    for marker, name in markers.items():
        text = text.replace(marker, name)
    return text
