# Preparação privada dos quatro modelos

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

## Referências originais ainda ausentes

| Modelo novo | Referência candidata do Battle Revolution | Arquivo |
|---|---|---|
| Mega Charizard X | Charizard | `pkx_006.fsys` |
| Ash-Greninja | Sceptile | `pkx_254.fsys` |
| Hydreigon | Salamence | `pkx_373.fsys` |
| Rillaboom | Slaking | `pkx_289.fsys` |

Esses arquivos não estão no ambiente. Precisam ser extraídos da cópia local do
usuário. A RVZ modificada atual pode fornecer essas referências, pois o mod
preservou esses arquivos originais. Não é necessário enviar uma imagem inteira.

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
