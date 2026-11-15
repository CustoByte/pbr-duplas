# Catálogo compartilhado de conteúdo — entrada inicial

Este diretório registra identidade, origem verificada e decisões dos Pokémon
que deverão alimentar as versões Dolphin e nativa. **Ainda não é uma ferramenta
de sincronização ou instalação automática.** O catálogo de entrada não altera
nenhum dos dois executáveis ou canais de atualização.

O lote de 14/11/2026 contém Mega Charizard X, Ash-Greninja, Hydreigon e Rillaboom.
Os ZIPs/modelos/texturas ficam privados. O arquivo JSON contém somente metadados,
hashes e resultados de inspeção, sem atribuir IDs internos ou configurações
que o usuário ainda não escolheu. Os números nacionais são identidades oficiais;
o número `0950` nos recursos de Rillaboom não substitui seu número nacional 812.

Charizard X e Ash-Greninja trazem glTF com malhas, skin, buffers e imagens
referenciadas presentes. Não há clips de animação. Hydreigon e Rillaboom têm
uma stack FBX chamada `Take 001`, porém zero curvas e zero keyframes: o intervalo
de tempo declarado não representa animação existente. A geometria foi lida com
o ufbx 0.17.1 já utilizado no projeto. Ambos ficam dentro de quatro pesos por
vértice. Rillaboom tem corpo, cabelo, baquetas e dois tambores em cinco malhas;
essas partes não devem ser descartadas como se fossem níveis de detalhe.

A conversão precisa criar/adaptar movimentos, preservar texturas/olhos e gerar
ícones, além de verificar a integração de batalha. Movimentos e habilidades
novos não passam a existir no motor só por receberem nome ou ícone. Tough Claws
e Grassy Surge não são mecânicas nativas da quarta geração; Levitate já existe.
Battle Bond também requer definição de comportamento para uma forma Ash já
independente, sem transformação durante a batalha.

Antes de instalar um registro, será necessário confirmar o conjunto de batalha,
validar as animações e alocar os índices sem colidir com Snivy/Mega Lucario.
A futura versão nativa poderá compartilhar os recursos/configurações, mas ainda
não tem um sistema de batalha capaz de aplicar movesets ou habilidades.

## Regras solicitadas após a inspeção

`battle-rules.json` é a fonte das propostas de bancos de 20 golpes (14 ofensivos e 6 de status) e dos
atributos base. `PROPOSTAS.md` permite revisar as listas e seus contratos de
animação. O moveset fixo de quatro golpes do jogador foi confirmado para Mega Charizard X;
os conjuntos já entregues de Snivy e Mega Lucario também são preservados.
Os outros três continuam em configuração.

`content/tools/random_sets.c` sorteia quatro golpes distintos e IVs/EVs/natureza
coerentes com o papel ofensivo do conjunto. Não altera atributos base a cada
adversário e respeita o limite de treino. O sampler não tem acesso a saves,
menus ou estado da batalha. Sua chamada na criação de cada NPC ainda precisa
ser integrada ao jogo, junto com os novos registros e modelos.

`generate_rules.py` gera um cabeçalho C e o mesmo JSON para compilações nativas.
O empacotador nativo agora prepara esses dados automaticamente antes de gerar o
PCK. O motor nativo lê os metadados; isso não implementa combate. A release
nativa anteriormente publicada permanece intacta e não é substituída por estes
arquivos de desenvolvimento. Novos binários exigem uma nova versão publicada.

O relatório `native-randomizer-proof.json` cobre execução PPC e 288 comparações
de atributos com cálculo original. A linha de atributos de uma espécie existente
foi substituída apenas no fixture privado. Nenhum dos quatro novos Pokémon foi
instalado por esse teste. As animações continuam sem clips criados/aprovados.
