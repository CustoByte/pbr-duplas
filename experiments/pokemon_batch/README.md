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

## Referências originais recebidas

| Modelo novo | Referência candidata do Battle Revolution | Arquivo |
|---|---|---|
| Mega Charizard X | Charizard | `pkx_006.fsys` |
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
