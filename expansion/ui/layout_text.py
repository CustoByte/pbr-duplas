"""Preserve native anchors and page boundaries; wrap to source-specific bounds."""
import re
from translation.messages import TOKEN,validate_target,encoded

LEAD=re.compile(r'^(?:(?:'+TOKEN.pattern+r')|\s)*')
FONT=re.compile(r'^(?:\{F[0-9A-F]{3}\})+')

COMPACT=(('Você pode ','Pode '),('você pode ','pode '),('Você deve ','Deve '),('você deve ','deve '),
         ('Por favor, ','Por favor, '),('Gostaria de ','Quer '),('gostaria de ','quer '),
         ('habilidades de batalha','técnica'),('habilidades na batalha','técnica'),('em uma batalha','na batalha'),
         ('Pokémon funcionou perfeitamente','Pokémon lutou muito bem'),('um pouco de maravilha','algo de especial'),
         ('novamente','de novo'),('perfeitamente','muito bem'),('Você gostaria de fazer parte','Quer entrar'),
         ('Pontos de Perfeição','Pontos Perfeitos'),('battle','batalha'),('game','jogo'))

def compact(text):
    for a,b in COMPACT:text=text.replace(a,b)
    return text

def wrap(source,target,metrics):
    prefix=FONT.match(source)[0]
    src_pages=source.split('{000D}');dst_pages=target.split('{000D}')
    if len(src_pages)!=len(dst_pages):raise ValueError('Page count changed')
    result=[];cases=[]
    for src,dst in zip(src_pages,dst_pages):
        if not TOKEN.sub('',src).strip():result.append(dst);continue
        # Keep each leading control once, including the newline before a
        # centered/icon caption. Old family-wide reflow erased this anchor.
        lead=LEAD.match(src)[0];oldlead=LEAD.match(dst)[0]
        lead_tokens=TOKEN.findall(lead);old_tokens=TOKEN.findall(oldlead)
        if lead_tokens==old_tokens:body=dst[len(oldlead):]
        else:lead=FONT.match(dst)[0] if FONT.match(dst) else '';body=dst[len(lead):]
        source_width,source_height=metrics(prefix+src)
        width=max(source_width,120)
        if len(TOKEN.sub('',src).split())<4:width=max(source_width,160)
        def flow(body):
            lines=['']
            # Existing explicit alignment changes must retain their own line.
            for word in body.split():
                value=(lines[-1]+' '+word).strip()
                if metrics(prefix+value)[0]>width and lines[-1]:lines.append(word)
                else:lines[-1]=value
            return lead+'\n'.join(lines)
        formatted=flow(body);mw,mh=metrics(prefix+formatted)
        # Native vertical controls can add an empty row. Compare to source
        # with the same exact leading anchor, rather than to another message.
        allowed_height=max(source_height,metrics(prefix+'M')[1])
        if mh>allowed_height:
            shortened=flow(compact(body));sw,sh=metrics(prefix+shortened)
            if sh<mh:formatted,mw,mh=shortened,sw,sh
        result.append(formatted)
        cases.append({'source_width':source_width,'source_height':source_height,'allowed_width':width,
                      'target_width':mw,'target_height':mh,'within_source_bounds':mw<=width and mh<=allowed_height})
    output='{000D}'.join(x.rstrip() for x in result)
    if source.endswith('\n'):output=output.rstrip()+'\n'
    validate_target(encoded(source),output)
    return output,cases
