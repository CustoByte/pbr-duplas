"""Terminology, structural and semantic checks for the delegated large lot.

Produces private candidates and review findings, never edits approved.json.
"""
import argparse,collections,json,re
from pathlib import Path
from translation.messages import TOKEN,encoded,validate_target
from translation.compatible_text import compatible

TYPES={'Water':'Agua','Fire':'Fogo','Grass':'Planta','Electric':'Eletrico',
       'Bug':'Inseto','Ground':'Terrestre','Flying':'Voador','Psychic':'Psiquico',
       'Fighting':'Lutador','Poison':'Venenoso','Dark':'Sombrio','Ghost':'Fantasma',
       'Steel':'Aco','Rock':'Pedra','Dragon':'Dragao','Ice':'Gelo','Normal':'Normal'}
LABELS={'switch':'Trocar','bag':'Bolsa','run':'Fugir','fight':'Lutar',
        'battle moves':'Golpes','sp. def':'Def. Esp.','sp. atk':'Atq. Esp.',
        'sp.def':'Def. Esp.','sp.atk':'Atq. Esp.','call':'Chamar','no.':'N.'}
MONTHS={'Jan.':'Jan.','Feb.':'Fev.','Mar.':'Mar.','Apr.':'Abr.','May':'Maio',
        'June':'Jun.','July':'Jul.','Aug.':'Ago.','Sept.':'Set.',
        'Oct.':'Out.','Nov.':'Nov.','Dec.':'Dez.'}

def label_text(source,target):
    plain=TOKEN.sub('',source).strip()
    replacement=MONTHS.get(plain,LABELS.get(plain.lower()))
    if replacement is None or any(c in source for c in '▼▽'):return target
    if plain.isupper():replacement=replacement.upper()
    pieces=re.split('('+TOKEN.pattern+')',target);out=[];used=False
    for piece in pieces:
        if TOKEN.fullmatch(piece):out.append(piece)
        elif piece.strip() and not used:out.append(replacement);used=True
    return ''.join(out)

def terminology(source,target,technical):
    # Full proper names are protected before terminology changes; changing
    # the type Bug must never modify the move name Bug Bite.
    if technical:
        target=re.sub(r'\bmovimentos?\b',lambda m:'golpes' if m[0].endswith('s') else 'golpe',target,flags=re.I)
        target=re.sub(r'\b(?:mudança|mudanca) selecionad[ao]\b','golpe escolhido',target,flags=re.I)
        target=target.replace('alvo Pokémon','Pokémon alvo')
        target=target.replace('Um Poké Ball','Uma Poké Ball').replace('um Poké Ball','uma Poké Ball')
        target=target.replace('do Poké Ball','da Poké Ball').replace('no Poké Ball','na Poké Ball')
        target=re.sub(r'\bum único Pokémon\b','um Pokémon',target)
        target=re.sub(r'\bUm item para ser segurado por um Pokémon\b','Item para um Pokémon segurar',target)
        target=re.sub(r'\bUm item a ser segurado por um Pokémon\b','Item para um Pokémon segurar',target)
        target=re.sub(r'\b(?:[Ee]le|[Ee]la) (\w)',lambda m:m[1].upper() if m[0][0].isupper() else m[1],target)
        target=target.replace('estatísticas','atributos').replace('estatisticas','atributos')
        target=target.replace('o máximo nível de desempenho','desempenho maximo')
        target=target.replace('Um medicamento tipo spray para feridas.','Spray medicinal.')
        target=target.replace('Um medicamento tipo spray.','Spray medicinal.')
        target=target.replace('Um medicamento em spray para feridas.','Spray medicinal.')
        target=target.replace('Um medicamento em spray.','Spray medicinal.')
        target=target.replace('Defesa Especial','Sp. Def').replace('Ataque Especial','Sp. Atk')
        target=target.replace('defesa especial','Sp. Def').replace('ataque especial','Sp. Atk')
        target=target.replace('probabilidade de','chance de').replace('Isso também pode','Também pode')
        target=re.sub(r'^O usuário (\w)',lambda m:m[1].upper(),target)
        if re.search(r'\b(?:Contest|Coolness|Cuteness|Smartness|Toughness|Poffin)',source,re.I):
            target=re.sub(r'\bConcurso (?:Legal|Cool)\b','Concurso de Estilo',target,flags=re.I)
            target=re.sub(r'\bConcurso (?:Fofo|Cute)\b','Concurso de Fofura',target,flags=re.I)
            target=re.sub(r'\bConcurso (?:Inteligente|Smart)\b','Concurso de Inteligencia',target,flags=re.I)
            target=re.sub(r'\bConcurso (?:Dificil|Difícil|Tough)\b','Concurso de Valentia',target,flags=re.I)
            target=re.sub(r'\bfrieza\b','Estilo',target,flags=re.I)
        for english,portuguese in TYPES.items():
            target=re.sub(r'(?<=tipo )'+english+r'\b',portuguese,target)
            target=re.sub(r'(?<=tipos )'+english+r'\b',portuguese,target)
            if re.search(r'\b'+english+r'-type\b',source):
                target=re.sub(r'\b'+english+r'\b',portuguese,target)
        target=target.replace('Water e Bug','Agua e Inseto')
    else:
        target=target.replace('tipo Bug','tipo Inseto').replace('Bug-type','tipo Inseto')
        target=target.replace('hype','fama').replace('ímpeto','ritmo')
        target=target.replace('Yay!','Viva!').replace('See?','Viu?')
        target=re.sub(r'\bminha perda\b','minha derrota',target,flags=re.I)
        target=re.sub(r'^Minha derrota(?=[.!?]|$)','Eu perdi',target)
        if re.search(r'cool (?:judgment|decisions?)',source,re.I):
            target='Pensar com calma sempre traz vitorias!'
        if re.search(r'feel (?:gray|grey)',source,re.I):target='Perder me deixa para baixo...'
        for english,portuguese in TYPES.items():
            if re.search(r'\b'+english+r'(?:-| )type\b',source):
                target=re.sub(r'\b'+english+r'\b',portuguese,target)
    return target

def prepare(inventory,cache,protected):
    editorial=json.loads(Path(__file__).with_name('lot5000-editorial.json').read_text())
    names=sorted(set(protected),key=len,reverse=True)
    pattern=re.compile(r'(?<!\w)(?:'+'|'.join(map(re.escape,names))+r')(?!\w)')
    entries=[];issues=[];skipped=[]
    for e in inventory['entries']:
        source=e['source'];prefix=re.match(r'^(?:\{F[0-9A-F]{3}\})+',source)[0]
        body=re.sub(r'\s+',' ',source[len(prefix):]).strip();draft=cache.get(body,{})
        if 'target' not in draft:
            issues.append({'archive':e['archive'],'id':e['id'],'reason':'missing-draft'});continue
        if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',TOKEN.sub('',body)):
            skipped.append({'archive':e['archive'],'id':e['id'],'reason':'non-English-source'});continue
        if re.fullmatch(r'[A-Z0-9-]+',body) and re.search('[A-Z]',body) and re.search('[0-9]',body):
            skipped.append({'archive':e['archive'],'id':e['id'],'reason':'identifier-code'});continue
        if re.search(r'\bPremium \d+ \(tent\)',body):continue
        target=editorial.get(e['archive'],{}).get(str(e['id']),draft['target']);saved=[]
        def protect(m):
            saved.append(m[0]);return 'ZXPROPER%04dZX'%(len(saved)-1)
        masked=pattern.sub(protect,target)
        # Gender of Poké Ball can be corrected without changing its name.
        target=terminology(body,masked,not source.startswith('{F006}'))
        for i,name in enumerate(saved):target=target.replace('ZXPROPER%04dZX'%i,name)
        target=label_text(body,target)
        # The USA font can show the original proper-name glyphs, but new
        # typographic punctuation may otherwise become replacement boxes.
        target=target.translate(str.maketrans({'\u2018':"'",'\u2019':"'",'\u201c':'"','\u201d':'"',
                                              '\u2013':'-','\u2014':'-','\u2212':'-',
                                              '\u2026':'...','\u00a0':' ','\u200b':'','\uff0d':'-'}))
        target=re.sub(r'\b[Nn][º°]','N.',target)
        target=target.replace('º','o').replace('ª','a')
        target=target.replace('Um Poké Ball','Uma Poké Ball').replace('um Poké Ball','uma Poké Ball')
        target=target.replace('Um item para um Pokémon segurar.','Item para segurar.')
        target=target.replace('Um item para ser segurado por um Pokémon.','Item para segurar.')
        target=target.replace('Um item a ser segurado por um Pokémon.','Item para segurar.')
        target=target.replace('um único Pokémon','um Pokémon')
        if not source.startswith('{F006}'):
            target=re.sub(r'\bSelecione\b','Escolha',target)
            target=re.sub(r'\bselecione\b','escolha',target)
            target=target.replace('passe personalizado','Passe Pessoal').replace('passes personalizados','Passes Pessoais')
            target=target.replace('Passe Personalizado','Passe Pessoal')
            target=target.replace('cupons Poke','Poké Coupons')
        target=compatible(target,names)
        # Formatting controls preceding the first word retain their position.
        leading=re.match(r'^(?:\{000[235]:[0-9A-F]{4}\})+',body)
        if leading and not target.startswith(leading[0]):
            for token in TOKEN.findall(leading[0]):target=target.replace(token,'',1)
            target=leading[0]+target
        full=prefix+target
        try:validate_target(encoded(source),full)
        except ValueError:
            issues.append({'archive':e['archive'],'id':e['id'],'reason':'changed-control-fields'});continue
        def numbers(s):
            values=re.findall(r'(?<!\w)\d+(?:[.,]\d+)*',TOKEN.sub('',s))
            def normalize(value):
                if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+',value):return re.sub('[.,]','',value)
                return value.replace(',','.')
            return collections.Counter(map(normalize,values))
        if numbers(body)!=numbers(target):
            issues.append({'archive':e['archive'],'id':e['id'],'reason':'changed-numeric-values','source':body,'target':target});continue
        visible=lambda s:re.sub(r'\s+',' ',TOKEN.sub('',s)).strip()
        if encoded(full)==encoded(source) or visible(full)==visible(source):continue
        entries.append({**e,'target':full,'status':'terminology-and-structural-check-passed-awaiting-layout'})
    return {'requested_new_messages':5000,'entries':entries,'issues':issues,'skipped':skipped,'publication_allowed':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('inventory','cache','protected','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();result=prepare(json.loads(a.inventory.read_text()),json.loads(a.cache.read_text()),json.loads(a.protected.read_text()))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Candidates',len(result['entries']),'review findings',len(result['issues']))
