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

## Catálogo recebido e verificado

O **GSfsys.toc original da ROM RPBE01** foi recebido: 29.248 bytes,
1.102 registros. `catalog.py` acrescenta `pkx_501.fsys` sob o ID livre
`0x2000`, preservando os registros antigos e os bytes originais, exceto
os campos de contagem e posição da nova tabela.

A captura de memória contém uma instância GLLA desse catálogo, mas seus
campos de nomes já são ponteiros absolutos e há outros campos preenchidos
durante o carregamento. Não é uma cópia confiável do arquivo original para
gerar uma alteração distribuível com preservação byte a byte. Não foi usada
para inventar um novo arquivo original ou um hash de entrada.

`verify_catalog.py` executou a busca USA real `8024c32c`: os 1.102 IDs
anteriores e seus nomes foram preservados, o novo ID foi encontrado e
um ID inexistente continuou retornando zero. A restauração do ponteiro
original foi conferida. Isso não testa carregar/renderizar o arquivo novo.
Resultado em `catalog-proof.json`. Não é necessário reenviar esse catálogo.

## Passe solicitado e balanceamento

O usuário escolheu **receber um Passe Little Battle pronto com Snivy**.
O Little Battle original não empresta os Rental Passes iniciais de nível 50.
A entrega deve escolher uma vaga pessoal vazia, preservar passes e Pokémon
existentes e garantir seleção/uso/salvamento sem exigir uma conexão DS.
A rotina de entrega ainda não está implementada.

Os IVs 31 e 508 EVs acima são um fixture de estresse, não o balanceamento
final. Foram conferidos os oito parâmetros de dificuldade do DOL USA:

| Rank | IVs nativos | Orçamento total de EVs |
| --- | --- | --- |
| 1 | 1–6 | 1 |
| 2 | 5–10 | 100 |
| 3 | 9–14 | 200 |
| 4 | 13–18 | 300 |
| 5 | 17–22 | 400 |
| 6 | 21–25 | 500 |
| 7 | 24–28 | 510 |
| 8 | 27–30 | 510 |

`verify_sunny_park.py --rank N` verifica construção e cálculo de atributos
com cada perfil nativo. Não modifica automaticamente o Pokémon do jogador
conforme ele sobe de rank. O passe pronto precisa de um perfil fixo adequado
ao início do torneio; não deve ganhar IVs/EVs a cada leitura ou batalha.

## Segundo conjunto: Rental Pass inicial, nível 50

O outro passe inicial é o Red/Cyndy, índice 37. A vaga 1 (base zero) contém
**Charmeleon**, espécie 5, e será a vaga substituída. O Monferno modificado
do passe 38 deve permanecer intacto.

`starter_pass.py` prepara Timid, Overgrow, Lum Berry, Energy Ball, Glare,
Leech Seed e Protect; IVs 31, EVs HP4/Speed252/SpAtk252. O teste nativo
confirmou nível 50, experiência 117360, PP 10/30/10/10 e atributos sem bônus
HP121/Atk58/Def75/Speed126/SpAtk97/SpDef75. São os atributos-base oficiais,
sem inflar a espécie inteira ou afetar o Little Battle. O conjunto favorece
Speed e suporte; não garante poder equivalente ao de espécies evoluídas.

Resultado em `starter-pass-proof.json`. **Não é migração real do passe**:
a substituição persistente, aparência shiny e bônus existentes ainda precisam
ser integrados e verificados. Os retratos solicitados estão especificados em
[PORTRAITS.md](PORTRAITS.md).

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
