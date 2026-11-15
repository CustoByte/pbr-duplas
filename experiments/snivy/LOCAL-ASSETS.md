# Recursos locais: retratos e variante shiny

Os recursos gráficos derivados dos jogos continuam privados. O repositório
contém ferramentas e relatórios, sem os modelos, texturas ou arquivos FSYS
originais/derivados. Esta etapa **não é uma versão instalável pelo CMD**.

## Retratos

O formato nativo não usa um PNG isolado por Pokémon:

- Face: atlas 96×96, quatro células 48×48. Normal em cima, shiny embaixo;
  as duas colunas mostram direções espelhadas. A borda circular faz parte
  da própria imagem, e não deve ser omitida ou desenhada duas vezes.
- Corpo: atlas 54×108, duas células 54×54, normal em cima e shiny embaixo.
- Os dois atlases usam C8 com paleta RGB5A3. O corpo exige padding horizontal
  nos blocos de 8×4; ignorar esse padding deslocaria pixels/linhas.

`render_portraits.py` renderiza face e corpo a partir do rig convertido,
com transparência. `icon_textures.py` monta os atlases, cria uma borda branca
procedural e codifica/decodifica o formato nativo. Não copia pixels de outro
Pokémon. O enquadramento foi revisto visualmente fora do jogo.

`icon_registry.py` acrescenta o índice 562 de ícones, com IDs próprios
`7bea0c00` (face) e `6bea0c00` (corpo). Os dois sexos apontam para esses
recursos, pois não há dimorfismo visual de Snivy. As tabelas de face/corpo
ganham a linha 501, mantendo as linhas originais e deixando 495..500 vazias.
A face informa uma forma e o bit nativo de espécie capaz de evoluir.
Isso ainda não prova a elegibilidade completa do Little Battle.

`verify_icons.py` executou getters nativos USA e conferiu os quatro IDs
de gênero, a contagem de formas e o bit evolutivo. Foram preservadas
495 linhas de face, 495 de corpo e 562 de ícones. O teste não renderiza
a interface real, não carrega FSYS pelo sistema de arquivos e não cria passes.

## Variante shiny

`shiny_variant.py` cria uma variante própria alterando apenas pixels verdes
das texturas RGB5A3 do SDR, deslocando o matiz para azul-esverdeado. Outros
matizes e bits de alfa são preservados. Os bytes de geometria, esqueleto,
ações, curvas e metadados permanecem idênticos ao modelo normal.

A mesma política de cor é usada no render dos retratos. A prévia foi
inspecionada, mas **não há comprovação de correspondência exata com a arte
shiny oficial nem teste de iluminação no Dolphin**. Não apresentar esta etapa
como validação visual final dentro do jogo.

## Empacotamento privado e reprodução

`resource_packages.py` acrescenta recursos sem substituir os antigos. Novos
cabeçalhos, nomes e tabelas ficam antes do primeiro payload: o carregador
nativo lê apenas esse prefixo como metadados. Os 645 payloads antigos de
cada arquivo de ícones são preservados, incluindo seus dados comprimidos.
O pacote `pkx_501.fsys` contém somente os SDRs próprios normal/shiny, sob
os IDs `73ea0400` e `63ea0400`; nenhum SDR de Grotle permanece nele.

Depois dos estágios atuais de conversão/verificação e do render dos retratos:

```sh
PYTHONPATH=experiments/snivy:expansion:mod-source \
python experiments/snivy/build_local_assets.py \
  --workdir /tmp/snivy-model-binding \
  --reference /caminho/pkx_388.fsys \
  --face-archive /caminho/menu_face.fsys \
  --body-archive /caminho/menu_pokemon.fsys \
  --output /tmp/snivy-private-assets
```

Requer Python com Pillow, os arquivos locais auditados e Blender 3.3 para
os estágios gráficos anteriores. O construtor rejeita arquivos de ícones
de outra versão, verifica o roundtrip de geometria/texturas e os UVs,
comprime com CRC verificado e produz um relatório de hashes. Não abre saves,
não modifica a ROM e não atualiza o canal público. Os arquivos resultantes
**não devem ser adicionados ao repositório nem anexados à release pública**.

Restam integrar esses recursos ao construtor final e ao fluxo de conversão
local do atualizador, além dos passes, estruturas de IA e testes reais.
