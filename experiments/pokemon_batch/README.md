# Preparação privada dos quatro modelos

**Revisão do usuário: os quatro rascunhos foram rejeitados por qualidade visual.**
Não usar os clips atuais como candidatos de entrega. Os testes numéricos de
interpolação não demonstram anatomia, atuação, contato com o chão ou movimento
convincente. A próxima revisão deve começar por pose e espera de uma espécie,
com referências adequadas e correções anatômicas, antes de gerar outros movimentos.

O importador prepara cenas Blender/GLB com o esqueleto e texturas fornecidos.
**Não cria animações, não instala os Pokémon e não gera FSYS/SDR para o Dolphin.**
O gerador de bancos de 20 golpes continua separado, em `content/pokemon`.

- Charizard X: quatro malhas e 119 ossos.
- Ash-Greninja: quatro malhas e 103 ossos.
- Hydreigon: uma malha e 111 ossos.
- Rillaboom: cinco malhas e 162 ossos, mantendo corpo, cabelo, baquetas e tambores.

A fonte glTF passa pelo importador do Blender. Os FBX usam o intermediário ufbx
já inspecionado e verificam as matrizes de bind, normalização/limite dos pesos e
preservação da geometria na pose de referência. O importador resolve diferenças
de maiúsculas/minúsculas nas texturas e evita escolher as variantes shiny por
acidente. A fase de trabalho usa Z-up; o GLB é exportado em Y-up.

Os quatro abriram em uma cena 3D real, com renderização por software Mesa/X11.
As imagens, GLBs, intermediários e cenas ficam privados. O relatório público
contém somente hashes e medidas de preparação, não os modelos ou texturas.
Nenhuma medição dessa fase prova desempenho em batalha ou no PC do usuário.

## Referências originais recebidas

| Modelo novo | Referência candidata do Battle Revolution | Arquivo |
|---|---|---|
| Mega Charizard Y (substitui X) | Charizard, referência de formato | `pkx_006.fsys` |
| Ash-Greninja | Sceptile | `pkx_254.fsys` |
| Hydreigon | Salamence | `pkx_373.fsys` |
| Rillaboom | Slaking | `pkx_289.fsys` |

Os quatro arquivos foram fornecidos pelo usuário e importados localmente.
Os arquivos originais permanecem privados e não são distribuídos no GitHub.

As referências são um ponto de partida para retarget, não uma promessa de
compatibilidade automática. Ainda será necessário adaptar asas, as três cabeças,
mãos e pés, entradas/saídas da Poké Ball, recuperação após dano, desmaio e os
pontos de emissão dos 20 golpes. Baquetas, tambores e shurikens precisam também
de controle de posição/visibilidade: a pose de origem não é uma pose de batalha.
O importador não disfarça a ausência desses movimentos com ações genéricas.

## Uso de desenvolvimento

Em Blender 3.3: `-- kind source textures-root output.blend output.glb`.
`kind` é `glTF` ou `ufbx`; o segundo recebe JSON do leitor ufbx do projeto.
São caminhos para arquivos privados. Não envie esses recursos para o repositório.

Esta etapa não muda os canais de atualização, os executáveis publicados ou saves.

## Rascunhos de movimento

`import_donor.py` importa o esqueleto e inventaria as ações originais usando o
SDK existente. `retarget-plan.json` registra os mapeamentos anatômicos e
`retarget_motion.py` amostra as referências a 24 fps e grava ações a 30 fps.
As cenas Blender são comprimidas para evitar duplicação de centenas de MB.

Charizard X usa Charizard; Ash-Greninja usa Sceptile. Hydreigon usa movimentos
relativos à espera aérea de Salamence, preservando sua anatomia. Rillaboom usa
movimentos relativos à espera de Slaking, com base ereta e controle das baquetas
e dos tambores. Ações de ataque/dano recebem entrada e recuperação suavizadas;
desmaios preservam seu término. Espera e corrida fecham o ciclo.

O relatório `motion-draft-proof.json` registra os testes locais do visualizador.
Ele prova carregamento e movimento de ossos, **não compatibilidade com Dolphin**.
As poses e os acessórios ainda exigem revisão quadro a quadro. Olhos/UVs,
entrada/saída da Poké Ball, pontos de emissão, os 20 golpes e o empacotamento
SDR/FSYS ainda não estão validados. Os aliases são propostas, não efeitos
implementados. Não foi alterado nenhum feed ou pacote jogável.

Uso privado (Blender, após `--`):

- Importação: `original.fsys caminho-do-pbr-addon pasta-do-doador`
- Retarget: `chave modelo.blend pasta-do-doador retarget-plan.json pasta-de-saida`

O visualizador aceita `--initial-action damage --pose-frame 15` para inspeção
estática da pose e reconhece ações com prefixo `Body_`.

## Revisão numérica e vídeos

`verify_motion.py` verifica valores finitos, normalização e continuidade de sinal
dos quaternions, fechamento dos ciclos e retorno das ações à espera. Encontrou
inversões de sinal em Rillaboom e Hydreigon; as chaves foram corrigidas antes dos
vídeos. O baker mantém o mesmo hemisfério entre chaves consecutivas. Isso evita
que a interpolação linear siga uma rotação longa apesar de poses equivalentes.

Ash-Greninja tem controle secundário da língua com influência parcial do pescoço,
para não herdar a inclinação inteira da referência de Sceptile. A geometria não
é removida. Os acessórios alternativos continuam ocultos nos rascunhos.

`render_motion_review.py` gera uma prévia privada por espécie, usando a cena
`native/runtime/preview.tscn`. Os vídeos mostram todos os clips corporais gerados,
as transições e uma indicação final do que falta. A captura usa relógio fixo de
30 Hz e **não comprova FPS em tempo real**, desempenho no Windows ou gameplay.
As legendas distinguem o voo estacionário provisório de Hydreigon do deslocamento.
Não há efeitos de golpes nem simulação de entrada/saída da Poké Bola nesses vídeos.
Ações de status ainda usam propostas de compartilhamento de poses, sem validação.
Os MP4 e modelos permanecem fora do repositório público.

A câmera da prévia acompanha o deslocamento do osso Waist, para não cortar o
corpo nas sequências aéreas. Esse acompanhamento é exclusivo do vídeo de revisão
e não altera as câmeras do Battle Revolution. O gerador verifica a sintaxe do
script antes de iniciar a captura para evitar gravações vazias.

## Substituição por Mega Charizard Y e espera própria

O usuário substituiu o X pelo Y. O banco anterior de 20 golpes fica provisoriamente
associado ao Y; os presets de Snivy/Mega Lucario e os outros três slots não mudam.
Atributos base passam ao perfil canônico do Y (78/104/78/159/115/100), ainda em
configuração e sem instalação. O cálculo isolado de atributos foi verificado
novamente no sampler PPC e nas rotinas originais; isso não instala a espécie.

`author_charizard_y_idle.py` cria pose e espera próprias sem ler qualquer doador.
Conserva pernas/quadril na postura de origem e anima apenas peito, pescoço,
braços, asas, cauda e chama. A espera tem seis segundos, movimento periódico e
controle de sinal de quaternion. Asas ficam parcialmente abertas e a cauda recebe
curvatura própria. Verifica a posição efetiva dos pés durante o ciclo.

A nova espera ainda não foi aprovada pelo usuário e não está pronta para Dolphin.
Os mapeamentos automáticos rejeitados foram desabilitados no baker; o X fica
somente como histórico, apontando para a substituição pelo Y. Ataques e outros
estados deverão ser trabalhados depois da revisão desta base.

## Estados próprios de batalha e chama em revisão

`author_charizard_y_battle.py` cria quatorze clips próprios sem importar ações
nativas: espera aérea, aproximação, decolagem, pouso, ataque de braço, ataque
especial com abertura da boca, investida, defesa, impacto no solo, recuperação,
dano, desmaio, saída e recolhimento corporais. As poses de contato usam solução
analítica de duas articulações para manter os tornozelos no solo. O retorno de
ataques à espera e os ciclos têm contratos numéricos distintos; desmaio e
recolhimento preservam seus estados terminais. `verify_charizard_y_battle.py`
verifica esses contratos, quaternions e os pontos de contato.

`tail_flame_review.gd` substitui a malha rígida de fogo SOMENTE no visualizador
por chama procedural emissiva e brasas, ancoradas ao osso da ponta da cauda.
O tempo do efeito é explícito para a gravação a 30 Hz. A câmera e o efeito são
recursos de revisão, não código executável no Wii. O chão usa uma referência
de pouso para não normalizar a pose voando como se estivesse no solo.

**Não há exportação SDR, hooks de batalha, efeitos dos golpes ou efeitos de
Poké Bola validados nesta etapa.** Saída/recolhimento incluem encenação de escala
na prévia; não devem receber escala duplicada pelo motor durante integração.
O fogo precisará de implementação compatível com os materiais/animações do jogo.
Os vídeos anteriores rejeitados não são promovidos e esta revisão também exige
avaliação visual. Nenhum feed de atualização ou save é alterado.

A fixação da chama procura o vértice terminal da cauda rigidamente influenciado
por Tail8 e transforma esse ponto para o espaço do osso. Isso evita usar EndTail8
como se fosse a superfície: no modelo fornecido, esse marcador fica além da malha.
A busca ocorre uma vez; durante os clips, o emissor acompanha o mesmo ponto da
pele. A gravação aproximada serve para conferir a ligação e o movimento do fogo.

`render_charizard_y_battle.py` produz o vídeo completo e o detalhe da chama com
relógio fixo de 30 Hz, verifica a sintaxe GDScript e decodifica os MP4 ao terminar.
A fonte da chama é calculada pelo shader; nenhuma imagem ou vídeo foi usado para
simular uma captura do jogo. Os vídeos são privados e não demonstram integração
com o motor de batalha original.

## Direção atual: Charizard original como base do Y

O usuário aprovou a chama e rejeitou os movimentos corporais autorais. O Y passa
a usar as doze ações corporais importadas de `pkx_006.fsys`: espera, corrida,
dano, desmaio, ações especiais/físicas, decolagem, espera aérea e mergulho. Os
mapeamentos consideram as asas de seis segmentos e a cauda de oito segmentos do
Y. A escala de deslocamento usa quadril/tornozelo, evitando ossos auxiliares na
medição. Nenhum mapeamento dos outros três modelos rejeitados é reativado.

`retarget-plan.json` registra a autorização de usar Charizard como doador,
**não aprovação visual do resultado nem validação de gameplay**. Os scripts de
animação autoral ficam como histórico rejeitado. A implementação da chama aprovada
permanece igual à revisão anterior; sua versão compatível com Wii ainda falta.

`render_motion_review.py --keys mega-charizard-y --tail-flame` produz a revisão
com as ações do doador e o efeito aprovado. A sequência de decolagem/espera aérea
não recebe uma volta artificial à espera no chão entre esses dois clips. As
prévia e os modelos ficam privados. A integração SDR/FSYS e os testes no Dolphin
continuam pendentes e nenhum canal de atualização jogável é alterado.

## Correção dos dentes atravessando o focinho

A mandíbula de bind do Charizard original fica aberta; a espera fecha cerca de
30 graus em relação a esse bind. Copiar esse delta para o bind já fechado do Y
fecha além da superfície do focinho. A correção usa a posição fechada da espera
como referência e transfere a rotação relativa entre cabeça e mandíbula como
uma dobradiça local. O ganho é 0,75, com limites 0–65 graus. A língua acompanha a
mandíbula do Y, evitando compensação global indevida. Texturas e dentes são
preservados; não se pinta nem remove a geometria branca.

`verify_jaw_hinge.py` amostra frames inteiros e intermediários dos doze clips e
verifica os limites e o eixo da articulação. A revisão compara a pose-fonte,
a adaptação anterior e a correção no mesmo quadro, e confere abertura em ataque.
Isso é uma correção do modelo adaptado; não valida instalação no Dolphin.
