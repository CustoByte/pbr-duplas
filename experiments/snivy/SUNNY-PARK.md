# Entrega solicitada: Snivy no Sunny Park / Little Battle

O usuário confirmou Sunny Park, Little Battle, até nível 5, e autorizou
substituir uma opção utilizável pelo jogador e publicar quando a integração
estiver pronta. A autorização não significa que o protótipo já seja jogável.
Não substituir a espécie de um Pokémon original na Pokédex ou no registro
global; a troca solicitada é de uma vaga disponibilizada ao jogador.

## Conjunto preparado e verificado

| Campo | Valor |
| --- | --- |
| Espécie nacional | Snivy, 495 |
| Índice interno provisório | 501, preservando Egg/Bad Egg e formas |
| Nível | 5 |
| Nature | Timid |
| Habilidade | Overgrow |
| Item | Lum Berry |
| Golpes | Tackle, Leer, Magical Leaf, Protect |
| IVs | 31 em todos os atributos |
| EVs | HP 4 / Speed 252 / Sp. Atk 252 |

Legalidade confirmada nos dados da quinta geração: Tackle por nível 1,
Leer por nível 4, Magical Leaf por reprodução e Protect por TM.
O funcionamento dos golpes continua sendo o nativo da quarta geração.
Contrary, habilidade oculta posterior, não foi implementada.
Fontes e hashes em `sunny-park-legality.json`.

`sunny_park.py` prepara os dados de construção. Os campos de nome, modelo
e catálogo continuam sem registro final: esses dados não devem ser usados
diretamente em uma versão pública do jogo.

`verify_sunny_park.py` executa as rotinas nativas USA:

- `8017d750`: construtor DCKP/PK4.
- `803de52c`: leitura PK4.
- `803dfd78`: conversão da caixa para Pokémon de equipe.
- `803e100c`: leitura dos dados de equipe.
- `803df14c`: experiência por espécie/nível.

A prova confirmou espécie interna 501 sem virar Egg, PID de natureza Timid,
habilidade 65, item 157, quatro golpes corretos, PP 35/30/20/10, IVs/EVs e
experiência 135. Os atributos calculados no nível 5 foram HP21, Atk9,
Def12, Speed17, SpAtk14, SpDef12. Uma cópia dos bytes preservou espécie,
item e nível ao reler pelas rotinas nativas; isso não é teste de save real.

Foi identificado que a seleção de item no DCKP depende dos bits 12..14
dos flags, além dos quatro campos de item. O fixture usa modo 1, item fixo,
e sua leitura nativa comprovou Lum Berry. Não há stub de item, golpe,
habilidade, natureza ou experiência. Apenas memória de tabela e alocação
temporária são fixtures. Os 501 registros de atributos anteriores são
preservados pelo anexador.

Resultados: `sunny-park-proof.json`. O conjunto **não foi inserido num
pool de adversários como substituto de uma opção do jogador**. A seleção
e migração da vaga efetiva do jogador ainda precisam ser implementadas.

## Arquivo necessário para avançar com o pacote independente

É necessário o **GSfsys.toc original da ROM RPBE01**, encontrado na raiz
do sistema de arquivos. O FST fornecido indica tamanho de 29.248 bytes.
Esse catálogo associa identificadores globais a nomes de arquivos FSYS.
O registro novo deve acrescentar o pacote Snivy e preservar os existentes.

A captura de memória contém uma instância GLLA desse catálogo, mas seus
campos de nomes já são ponteiros absolutos e há outros campos preenchidos
durante o carregamento. Não é uma cópia confiável do arquivo original para
gerar uma alteração distribuível com preservação byte a byte. Não foi usada
para inventar um novo arquivo original ou um hash de entrada.

No Mac: Dolphin → Propriedades de Pokémon Battle Revolution → Sistema
de Arquivos → Partição de Dados → GSfsys.toc → Control+clique → Extrair.

## Bloqueios de publicação

- Registrar pacote, IDs, modelos, nomes e ícones independentes; conferir
  limites de espécies sem admitir os sentinelas como espécies normais.
- Disponibilizar a vaga do jogador no Sunny Park e verificar a elegibilidade
  real do Little Battle, preservando suas regras e o save atual.
- Testar obtenção, seleção, troca, consumo da Lum Berry e restauração entre
  batalhas conforme as regras existentes, sem restaurá-la a cada leitura.
- Verificar ataques, impactos, deslocamento, Poké Ball, conclusão de eventos,
  desempenho e gravação/carregamento no jogo.
- Definir a aplicação local dos recursos do usuário sem publicar os assets
  protegidos de PokéPark 2. O pedido original proíbe distribuí-los no projeto.

O atualizador e a versão pública continuam sem Snivy. Não foi criada uma
release nem alterado o feed: publicar agora não entregaria o comportamento
solicitado. A autorização de publicação continua válida após a conclusão.

## Reproduzir a prova

```sh
PYTHONPATH=experiments/snivy:expansion:mod-source:coop:/caminho/harness \
python experiments/snivy/verify_sunny_park.py \
  --capture /caminho/diagnostics-command \
  --dol /caminho/test13/main.dol --common /caminho/test13/common.fsys \
  --report /tmp/sunny-park-proof.json
```
