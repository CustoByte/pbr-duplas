# Prova de conversão gráfica de Snivy

O BRRES fornecido foi importado, convertido para SDR e reaberto por um
leitor SDR. Trata-se de uma prova fora do jogo, sem integração ao registro
de espécies, ROM ou atualizador. Os arquivos de jogo e derivados ficam
privados; o repositório guarda ferramentas e metadados de verificação.

## O que passou

- Importação das 117 animações CHR0 e dos materiais/esqueleto originais.
- Geometria exportada: 1.097 vértices e 1.936 triângulos.
- Preservação das transformações dos 48 ossos originais mediante 48
  auxiliares e uma raiz estática, totalizando 97 ossos no rig experimental.
- Conversão de nove ações candidatas para os slots do exportador PBR.
  O mapeamento é provisório; a semântica dos slots ainda requer teste real.
- Comparação do SDR decodificado com o modelo BRRES importado em 108 poses:
  todos os 84 quadros de espera e três quadros de cada uma das outras ações.
- Comparação de vértices deformados, hierarquia e três texturas difusas
  com dimensões preservadas. O erro máximo RGB foi aproximadamente 7/255,
  esperado da conversão RGB5A3 utilizada pelo exportador; alfa foi preservado.
- Prévia de espera com 28 imagens, baseada nos dados decodificados do SDR.
  Usa iluminação difusa simplificada e 30 fps como hipótese de trabalho.

Os números exatos, hashes e versões estão em `graphics-report.json`.
Essa comparação é contra a importação do BRRES pelo BerryBush, não contra
frames capturados do PokéPark 2. O leitor e o exportador SDR são do mesmo
projeto: o resultado é evidência de consistência, não prova independente
de compatibilidade com o motor original do Battle Revolution.

## Problemas encontrados e tratados

**Escala dos ossos.** A conversão direta perdia a compensação de escala
do BRRES. Foram detectados erros de matriz de aproximadamente 0,19.
Uma fatoração SVD separa cada transformação afim em duas transformações
TRS representáveis por ossos comuns. O auxiliar armazena translação,
rotação e escala; o osso original conserva a outra rotação. Não são
descartadas influências de vértices. A conversão recusa mais de quatro
influências por vértice, em vez de permitir o descarte silencioso do exportador.
São preservados também os canais da raiz original e de `Origin`, renomeado
para `SnivyMotion` para evitar a exclusão especial feita pelo exportador.

**Precisão.** A aproximação de chaves e a quantização short do exportador
acumulavam erro. O experimento usa curvas float32 e tolerância mais estrita.
Isso aumenta o tamanho do SDR. Memória e desempenho no Wii/Dolphin ainda
precisam ser medidos; o formato float não foi executado no jogo neste teste.

**Texturas vazias.** Reempacotar imagens já embutidas fazia os pixels
desaparecerem ao salvar o arquivo intermediário. A conversão preserva
imagens já empacotadas; o verificador recusa dimensões ou pixels ausentes.

**Ferramenta sem interface gráfica.** BerryBush necessita Blender 3.3/3.4
e aloca recursos GPU ao importar seus módulos. Três adaptações pequenas
desativam essas alocações somente em background. Não há substituição
dos decodificadores, transformações ou animações por resultados fixos.

## Reproduzir com recursos próprios

Requisitos: Blender 3.3.21 e clones privados dos dois projetos de ferramentas.
Não é preciso instalar essas ferramentas no computador do jogador.
O fluxo abaixo é para desenvolvimento e não altera o jogo instalado.
Prepare clones nas revisões registradas no relatório:

```sh
git clone https://github.com/hayden0729/berrybush.git /tmp/snivy-berrybush
git -C /tmp/snivy-berrybush checkout 5ff000f7362a3b18cc55e871fc3e1f645eb5e206
git clone https://github.com/bgsamm/pbr-models-import-export.git /tmp/snivy-pbr-io
git -C /tmp/snivy-pbr-io checkout ed18e4fd606bf66b670c71c2484bf9fc86ea5b7d
python experiments/snivy/prepare_graphics_tools.py \
  --berrybush /tmp/snivy-berrybush --pbr-addon /tmp/snivy-pbr-io
```

Para cada estágio, execute o Blender com estes parâmetros, trocando
`ESTAGIO` por `import`, `convert`, `verify` e `preview`, nessa ordem:

```sh
blender --background --factory-startup --threads 4 --python-exit-code 1 \
  --python experiments/snivy/graphics_ESTAGIO.py -- \
  --source /caminho/Tsutarja.brres \
  --workdir /tmp/snivy-graphics \
  --berrybush /tmp/snivy-berrybush --pbr-addon /tmp/snivy-pbr-io
```

Saídas privadas: `snivy-source.blend`, `snivy-export.blend`,
`snivy-experimental.sdr`, relatórios e imagens `idle-frames/*.png`.
Os scripts conferem o hash do BRRES fornecido; o exemplo ainda não é um
conversor genérico para qualquer Pokémon. Há geração de novas malhas,
ossos, materiais e curvas, preservando o arquivo BRRES original.

## O que falta antes da integração final

- Calibrar escala, orientação, duração, limites de câmera e pontos de efeitos
  com referências nativas de PBR e observação do jogo fonte.
- Mapear ataques, status, entrada, retorno e derrota aos eventos do motor.
  `tx_wink` usa a espera provisoriamente: ainda não implementa piscada.
  Os nomes das animações não comprovam a função de cada ataque.
- Validar curvas UV de olhos/boca no jogo; a prévia de espera não testa
  expressões de todos os ataques. O leitor SDR usado não reconstrói as
  animações de materiais, por isso elas não estão cobertas pelo roundtrip.
- Reproduzir corretamente iluminação/material, mapas de ambiente e brilho.
  As três texturas difusas foram convertidas; os outros dois mapas originais
  continuam preservados no BRRES/importação, mas não foram exportados ao SDR.
- Reduzir tamanho/custo dos auxiliares e avaliar interpolação, loops e memória.
- Registrar referências USA para nova espécie/modelo, ícone e nome, integrar
  Battle Pass, save/load e elegibilidade Little Battle.
- Executar batalhas e regressões reais no Dolphin. A prévia não comprova
  nenhum comportamento de batalha, habilidade, IA ou persistência.

Não publicar este SDR no atualizador como se fosse um Snivy jogável.

A auditoria posterior dos eventos e nomes nativos está em
[ANIMATION-LIFECYCLE.md](ANIMATION-LIFECYCLE.md), incluindo a dependência
de uma referência de pacote Pokémon original para a integração ao jogo.
Essa referência foi recebida posteriormente; o resultado está em
[NATIVE-PROFILE.md](NATIVE-PROFILE.md).
