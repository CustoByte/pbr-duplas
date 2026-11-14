"""Explicit concise phrasing for existing static descriptions, never new text IDs."""
import re
from translation.messages import TOKEN, encoded

# Each replacement retains subject/condition/effect; numerical values, names,
# chance qualifiers and negation are independently checked after application.
PHRASES = (
    ('Um item a ser segurado por um Pokémon.', 'Para um Pokémon segurar.'),
    ('Um item para ser segurado por um Pokémon.', 'Para um Pokémon segurar.'),
    ('Um item que deve ser segurado por um Pokémon.', 'Para um Pokémon segurar.'),
    ('Um item a ser mantido por um Pokémon.', 'Para um Pokémon segurar.'),
    ('O efeito desaparece se o Pokémon for retirado.', 'O efeito acaba ao trocar o Pokémon.'),
    ('Uma bebida nutritiva para Pokémon.', 'Bebida nutritiva para Pokémon.'),
    ('Um fertilizante vegetal espalhado em solo macio.', 'Fertilizante para solo macio.'),
    ('Uma perola bastante grande', 'Uma pérola grande'),
    ('Eleva a base Sp. Estatistica Atk (Sp. Atk)', 'Eleva o Atq. Esp. base'),
    ('Eleva a base Sp. Estatistica de Def (Sp. Def)', 'Eleva a Def. Esp. base'),
    ('Sp. Estatistica de ataque', 'Atq. Esp.'),
    ('Sp. Estatistica de definicao', 'Def. Esp.'),
    ('estatistica de velocidade base', 'Velocidade base'),
    ('estatistica de velocidade', 'Velocidade'),
    ('estatistica de ataque', 'Ataque'),
    ('estatistica de Defesa', 'Defesa'),
    ('estatística de velocidade', 'Velocidade'),
    ('estatística de ataque', 'Ataque'),
    ('estatística de Defesa', 'Defesa'),
    ('a taxa de acerto crítico', 'a chance de acerto crítico'),
    ('No entanto,', 'Porém,'),
    ('no entanto,', 'porém,'),
)


def eligible(kind, index):
    return kind == 'common' and any(lo <= index < hi for lo,hi in
        ((1523,1991),(3114,3237),(3255,3706),(3890,4570),(8380,9150)))


def concise(text):
    # Work on exact literals after joining only whitespace, then reflow with
    # native metrics. Control/parameter tokens themselves remain byte-identical.
    target = re.sub(r'\s+', ' ', text)
    applied = []
    for source, replacement in PHRASES:
        if source in target:
            target = target.replace(source, replacement)
            applied.append(source)
    def implicit(match):
        applied.append('implicit description subject: ' + match[2])
        return match[1] + match[3].upper()
    target = re.sub(r'((?:\}|[.!?])\s*)(O usuário |Um item que )([a-záàâãéêíóôõúç])', implicit, target)
    return target, applied


def validate_editorial(before, after, names=(), allow_pages=False):
    from ui.dialogue_layout import validate_presentation
    validate_presentation(before,after,allow_pages)
    if re.findall(r'\d+(?:[.,/]\d+)*', TOKEN.sub('', before)) != re.findall(r'\d+(?:[.,/]\d+)*', TOKEN.sub('', after)):
        raise ValueError('Description revision changed numbers')
    a,b = (re.sub(r'\s+', ' ', x) for x in (before,after))
    for word in ('não', 'nunca', 'sempre', 'apenas', 'somente'):
        if len(re.findall(r'\b'+word+r'\b', a,re.I)) != len(re.findall(r'\b'+word+r'\b',b,re.I)):
            raise ValueError('Description revision changed a qualifier')
    for name in names:
        if name in a and a.count(name) != b.count(name):
            raise ValueError('Description revision changed a protected name: '+name)
    if encoded(before)[:8] != encoded(after)[:8]:
        raise ValueError('Description revision changed fonts')
    return encoded(after)
