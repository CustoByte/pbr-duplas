# Perfil gráfico derivado da referência nativa recebida

O arquivo `pkx_388.fsys` solicitado foi recebido e permanece intacto.
SHA-256: `ce02a053b41bc806391bf3bb4606faffcae3edc7b974120959d25f488f75afb8`.
Esta etapa produz um **SDR experimental do Snivy**, não um pacote jogável.

## Diagnóstico da referência

`pkx_reference.py` valida a versão auditada, descomprime os dois recursos,
confere o tamanho das estruturas, percorre os nós e lê ações e texturas.
Os recursos `1b7b0400` e `1fdd0400` contêm o objeto `hayashigame`, 76 nós
e as mesmas 12 ações, em ordem. A ordem, os nomes, durações e flags também
coincidiram com a referência Grotle já auditada na captura de memória USA.

As variantes diferem em dados de textura e em outros 734 bytes. Não foi
assumido que todos os bytes diferentes sejam apenas uma mudança de cor.
Esses IDs continuam pertencendo ao conteúdo original: não foram atribuídos
ao Snivy nem inseridos em tabelas globais.

## Implementação no protótipo

`--native-reference` habilita um perfil separado; o fluxo inicial de nove
ações continua disponível sem essa opção.

- São exportadas 12 ações na ordem nativa da referência: wait, run, damage,
  down, tackle, kime, kime_a, tx_wink, tx_sleep, tx_wakeup, mamoru e kime_phy.
- Os movimentos continuam vindo do BRRES do Snivy. Não são usados movimentos
  do Grotle. As escolhas Atk/Charge/Faint ainda são candidatas à função final.
- Os flags de corpo/material e as frações dos marcadores temporais vêm da
  referência. As durações vêm das ações do Snivy. Isso não prova que o instante
  de impacto esteja ajustado: a sincronização precisa de observação em batalha.
- Nenhum ponteiro, máscara com índices nativos ou curva do Grotle é copiado.
- São criados 20 pontos/controles com nomes nativos, ligados a ossos do Snivy.
  Atualmente usam as origens desses ossos, inclusive os olhos: ainda precisam
  de deslocamentos/calibração anatômica e validação no jogo.
- O perfil contém 118 nós: 48 ossos originais, 48 auxiliares de compensação,
  uma raiz estática, 20 pontos/controles e um nó de malha.
- Os canais de olhos/boca são separados das ações do corpo, conforme os
  flags nativos. No perfil novo, `tx_wink` possui cinco quadros com UVs de
  olhos abertos, fechados e abertos novamente. Fechamento e abertura usam o
  atlas do próprio Snivy. Sleep e wakeup têm estados próprios de materiais.
- O conversor não reempacota desnecessariamente texturas já embutidas.

## Verificações executadas

Resultados completos em `native-profile-report.json`:

- 12 ações, nomes/ordem e flags iguais à referência; marcadores proporcionais.
- 20 nomes de pontos/controles presentes na hierarquia serializada.
- 108 poses comparadas ao BRRES importado: espera inteira e amostras das
  outras oito ações do corpo. Os três canais exclusivamente de materiais
  não são anunciados como testes de pose corporal.
- Erro máximo de distância dos vértices: aproximadamente 0,0001242 nas
  unidades do modelo. Dimensões/pixels das três texturas difusas conferidos.
- 6.360 valores escalares UV conferidos após decodificar as curvas do SDR;
  erro máximo de aproximadamente 0,00000003. O teste exige fechamento e
  reabertura diferentes para a piscada, não apenas um nome de ação presente.
- Fluxo de verificação do protótipo anterior preservado.

Esses são testes de dados e geometria fora do jogo. Não comprovam execução
do formato float no motor, fluidez em tempo real, desempenho, efeitos,
deslocamento até o alvo ou conclusão dos eventos da Poké Ball.

## Reproduzir

Preparar as ferramentas nas revisões descritas em `GRAPHICS.md`:

```sh
python experiments/snivy/prepare_graphics_tools.py \
  --berrybush /caminho/berrybush --pbr-addon /caminho/pbr-models-import-export
```

Executar os estágios `graphics_import.py`, `graphics_convert.py` e
`graphics_verify.py` com os parâmetros habituais e a opção adicional:

```sh
--native-reference /caminho/pkx_388.fsys
```

O diretório de saída deve ser próprio para o perfil novo, preservando os
experimentos anteriores. Em seguida:

```sh
PYTHONPATH=mod-source python experiments/snivy/verify_native_asset.py \
  --sdr /tmp/snivy-native-profile/snivy-experimental.sdr \
  --reference /caminho/pkx_388.fsys \
  --uv /tmp/snivy-native-profile/expected-uv.json \
  --report /tmp/snivy-native-profile/native-asset-report.json
```

## Pendências para entrar no jogo

1. Reservar IDs de recursos independentes, expandir o mapeamento de modelos
   e construir o pacote Snivy, sem usar os IDs de Grotle ou sentinelas Egg.
2. Resolver limites de espécie, aquisição, menus e save/load para o ID novo.
3. Calibrar escala, pontos de efeito, câmera e colisão/proxies. O exportador
   base possui um valor fixo no campo de controle `ct_all`; sua interpretação
   e ajuste também precisam ser verificados antes de usar em batalha.
4. Confirmar seleção de movimentos, fases de ataques e transições de estado;
   ligar os eventos nativos de aproximação, impacto, Poké Ball e substituição.
5. Medir interpolação/fluidez, RAM e desempenho no Dolphin. O SDR deste
   experimento tem aproximadamente 8 MB; o empacotamento e o carregamento
   simultâneo de atores ainda não foram testados.
6. Preparar e validar as variantes visuais próprias de Snivy, sem clonar
   texturas de Grotle. Só então testar a integração com regras de shiny.

Nenhuma ISO, arquivo original ou conteúdo do atualizador foi alterado.
Não há publicação de arquivos derivados dos jogos nesta etapa.
