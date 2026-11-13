# Snivy — candidata experimental integrada

Esta etapa reúne os protótipos anteriores. Não comprova uma partida completa
no Dolphin. O instalador cria uma imagem/overlay local com os arquivos originais
do jogador; a distribuição pública contém ferramentas e deltas, sem modelos,
texturas, ROM, save ou arquivos FSYS/DOL completos.

## Entrega ao jogador

- Espécie interna independente **501**, nacional 495. Espécies originais,
  Egg/Bad Egg e formas mantêm seus índices.
- Primeiro espaço pessoal vazio, disponível e sem personalização recebe um
  passe **Little**, com Snivy, Charmander, Squirtle, Turtwig, Chimchar e Piplup,
  todos no nível 5. Nenhum passe ocupado/personalizado é substituído.
- A rotina nativa de elegibilidade do Little Battle aceitou esse passe na
  execução offline da captura fornecida. Se todos os espaços estiverem ocupados
  ou personalizados, é preciso disponibilizar um espaço pessoal vazio.
- Apenas o Charmeleon original (espécie 5, vaga 1) do Rental Pass vermelho,
  índice 37, recebe Snivy nível 50. Outro Pokémon nessa vaga é preservado.
  O Rental Pass do Monferno, índice 38, permanece intacto.
- A entrega é idempotente: não recria um passe já entregue nem redefine uma
  Snivy que o jogador alterou.

| Perfil | Nature / habilidade / item | Golpes | IVs / EVs |
|---|---|---|---|
| Little, nível 5 | Timid / Overgrow / Lum Berry | Tackle, Leer, Magical Leaf, Protect | IV15 todos / EV0 |
| Rental, nível 50 | Timid / Overgrow / Lum Berry | Energy Ball, Glare, Leech Seed, Protect | IV31 todos / HP4, Speed252, SpAtk252 |

O perfil Little antigo de IV31/EV508 em SUNNY-PARK.md era uma prova de
construção. A entrega integrada usa o perfil equilibrado IV15/EV0 acima.

A Lum Berry continua consumida pelo restante da batalha. O gancho existente
entre batalhas restaura o item apenas quando o passe original ainda contém
Lum Berry e a identidade do Pokémon corresponde. Remover o item no passe é
respeitado. O comportamento anterior do Monferno continua no mesmo caminho.

## Recursos e segurança dos índices

O cadastro acrescenta dados de espécie, modelo, nome, ícones, evolução e
aprendizado. Apenas golpes presentes no motor de quarta geração são usados;
Leaf Tornado e Coil não são inventados nem associados a outros números.
Não se adicionam Servine/Serperior fictícios.

A conversão local gera 12 ações, 119 nós e 21 pontos de associação de efeitos,
mais retratos normal/shiny. Os 645 recursos anteriores de cada arquivo de
retratos são preservados. A cor shiny usa uma variante de tonalidade do modelo
local; não foi confirmada como reprodução exata da arte shiny oficial.

Somente duas verificações de presença de interface admitiram o novo índice.
Os outros limites pesquisados em species_guards.py não são todos ativados:
limites de bancos de áudio originais permanecem protegidos. Tabelas fixas de
previsão e narração recebem caminhos específicos para 501, sem ler além dos
registros antigos. Os 499 registros de previsão e 494 de narração mantêm as
mesmas consultas nativas. A câmera de resumo usa uma entrada própria provisória
para Snivy, preservando a tabela original.

**Limitação de áudio:** grito e nome falado da Snivy ficam silenciosos, pois
não foram fornecidas gravações. Sons de golpes/impactos continuam no motor
nativo. Não se atribui o grito ou a identidade de outro Pokémon a ela.

## Instalação

Windows: o mesmo INICIAR-TESTE-WINDOWS.cmd baixa o núcleo novo quando o feed
for publicado. No primeiro uso desta candidata, selecione **Tsutarja.brres**
extraído do seu PokéPark 2 USA. O aplicador baixa Blender 3.3.21 portátil e
ferramentas com hashes fixos, converte localmente e reutiliza o cache nas
próximas execuções quando a receita não muda. A imagem original é somente lida;
a RVZ anterior é preservada ao atualizar. O primeiro download é de cerca de
300 MB, além das dependências. Não requer instalar Python, Git ou Blender.

Mac: extraia o núcleo ZIP e abra
`mac-aplicador/INICIAR-SNIVY-MAC.command`. No primeiro uso, extraia **a partição
de dados inteira** do Battle Revolution pelo Dolphin e selecione a pasta que
contém `sys` e `files`; não precisa extrair arquivo por arquivo. Selecione
Tsutarja.brres e a ISO/RVZ original. O iniciador prepara um overlay privado e
mostra `Jogar-PBR-Duplas.json`, para abrir no Dolphin. Usa o mecanismo nativo
Riivolution, inclusive criação de pkx_501.fsys. Não modifica a imagem original.
Este lançador não foi executado em macOS neste ambiente Linux.

A conversão usa processos separados do Blender em segundo plano, com dois
threads. Não inicia um modelo de linguagem local. Os recursos convertidos são
privados e ficam no computador do jogador. As dependências têm revisões/SHA256
em sdk-downloads.json; adaptações em prepare_graphics_tools.py. BerryBush usa
GPL-3.0-or-later; Blender GPL; Pillow HPND. Não se redistribui o exportador PBR:
a ferramenta obtém a revisão pública fixada para uso local.

## Evidências e limites

- `pass-delivery-proof.json`: código nativo da captura, registradores ampliados,
  construtores PK4, flags de posse, leitura dos seis Pokémon, elegibilidade
  Little, idempotência, preservação dos espaços personalizados, consumo e
  restauração da Lum Berry e regressão de 993 consultas legadas.
- `build_integration.py`: confere hashes test13 e preserva byte a byte os
  recursos descompactados fora do conjunto declarado.
- `convert_local.py`: importação, conversão, roundtrip e renderização local;
  validação do cache por hash, sem instalar recursos de uma conversão falha.
- Testes do aplicador com ferramenta de imagem simulada validam inclusão dos
  novos arquivos, caminhos lembrados, conservação da imagem original e save.
  Isso não equivale a executar DolphinTool ou validar uma ROM real.

Antes de anunciar a integração como concluída, é necessário testar no Dolphin:
seleção dos dois passes; retratos; câmera; entrada/retorno da Poké Ball;
movimento até o alvo; golpes físicos/especiais; dano/derrota; sono e despertar;
Overgrow; consumo da Berry; segunda batalha; salvar normalmente, fechar o jogo
e carregar novamente. Não use save states de outra versão. Caso uma etapa
falhe, preserve o diagnóstico e volte à imagem/descritor anterior.
