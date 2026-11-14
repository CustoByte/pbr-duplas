"""Restore unambiguous Portuguese accents while shielding original names."""
import collections,json,re,unicodedata
from translation.messages import TOKEN

def plain(word):return ''.join(c for c in unicodedata.normalize('NFD',word) if not unicodedata.combining(c))

# Ambiguous single words (e/é, a/à, esta/está, pode/pôde) are deliberately
# excluded from global replacement and need contextual editorial overrides.
WORDS='''usuário usuários preocupação preocupações sucessão lançadas lançados lançado lançada lança instruções configurações recepção depósito começa começar excluídos excluído então tão estão mão mãos coração corações posição posições situação situações condições condição decisão decisões direção direções função funções região regiões conclusão geração gerações duração animação pressão união reunião razão razões ocasião ocasiões impressão exceção organização competição competições destruição substituição consciência consequência consequências audiência comunicação orientação localização inscrição edição medalhão missão saúde saudável parabéns aumentará diminuirá causará perderá ganhará ficará atingirá virá vencerá conseguirá ocorrerá começará deixará parará voltará enviará encontrará receberão ganharão ninguém alguém impossível óbvio ótima ótimo difíceis difícil fácil fáceis inútil útil úteis transferência técnica técnicas título títulos histórico histórias história válido válida diálogo diálogos verá conhecerá sairá revelará comparável incrível incríveis magnífico anúncio música câmera câmara memória você vocês não são ação ações descrição descrições opção opções seleção evolução evoluções Pokémon também nível níveis possível necessários necessária necessário disponíveis disponível crítico críticos acerto precisão confusão paralisia já estáticas características experiência elétrico elétricos psíquico psíquicos incêndio fará farão poderá poderão será serão terá terão receberá aparecerá usará continuará adversário adversários vitória vitórias derrota recuperação energia máxima máximo mínimos mínimo próximo próxima último última início bônus eficácia efetivo eficazes rápido rápida rapidamente três número números área áreas informações informação confirmação confirmar conexão conexões botão botões relógio acessórios aparência cópia cópias gênero importância estratégia estratégias físico físicos física físicas especialização meteorológico resistências resistência habilidade habilidades proteção alteração alterações redução reduções mudança mudanças atenção invenção diversão irmãos irmã irmão família ancestrais férias tripulação extraordinário pokétopia balcão estação recém porém além até água águas venenoso usá-lo fazê-lo derrotá-lo status negativo né açúcar atração atraído através revés conteúdo catálogo término inválido inválida período automático automática automático reinício código códigos sincronização sinalização amanhã currículo treinador'''

def lexicon(caches=()):
    variants=collections.defaultdict(set)
    for cache in caches:
        for value in cache.values():
            target=value.get('target','') if isinstance(value,dict) else value
            for word in re.findall(r'[A-Za-zÀ-ÿ]+',target):
                if len(word)>3:variants[plain(word.lower())].add(word.lower())
    table={k:next(iter(v)) for k,v in variants.items() if len(v)==1 and next(iter(v))!=k}
    for word in WORDS.split():
        if plain(word.lower())!=word.lower() and len(word)>2:table[plain(word.lower())]=word.lower()
    for word in ('esta','pratica','publico','secretaria','analise','numero','inicio','duvida','pelo','para','por','e','a'):
        table.pop(word,None)
    return table

def restore(text,table,names=()):
    saved=[]
    names=sorted(set(names),key=len,reverse=True)
    pattern=re.compile(r'(?<!\w)(?:'+'|'.join(map(re.escape,names))+r')(?!\w)') if names else None
    def mask(m):saved.append(m[0]);return '{ZXKEEP%05d}'%(len(saved)-1)
    text=TOKEN.sub(mask,text)
    if pattern:text=pattern.sub(mask,text)
    def replace(m):
        old=m[0];new=table.get(old.lower(),old)
        if old.isupper():return new.upper()
        if old.istitle():return new.capitalize()
        return new
    text=re.sub(r'[A-Za-zÀ-ÿ]+',replace,text)
    for i,word in enumerate(saved):text=text.replace('{ZXKEEP%05d}'%i,word)
    text=re.sub(r'\b([Ee])sta (?=(?:pronto|pronta|paralisad[oa]|envenenad[oa]|dormindo|congelad[oa]|queimad[oa]|confus[oa]|prestes|chei[oa]|fora|dentro|aqui|ali|com|sem|usando|caindo|lutando|mudando|esperando|conectad[oa]|sendo|ficando)\b)',lambda m:'Está ' if m[1]=='E' else 'está ',text)
    # Context-specific verb accents; do not replace the conjunction globally.
    text=re.sub(r'\b([Nn]ão)(\s+)[eE](\s+)(possível|necessári[oa])\b',lambda m:m[1]+m[2]+'é'+m[3]+m[4],text)
    text=re.sub(r'\b(semente(?:\s+que\s+causa\s+preocupação)?)(\s+)e(\s+)(plantada)\b',lambda m:m[1]+m[2]+'é'+m[3]+m[4],text,flags=re.I)
    return text
