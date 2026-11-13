# Associação independente do modelo Snivy

Etapa de cadastro e prova de busca nativa. **Não é carregamento ou exibição
do modelo no Dolphin e não altera a versão do atualizador.**

## Identidades e preservação

`model_registry.py` acrescenta uma linha de 72 bytes ao recurso de modelos
`common.fsys:00800200`. O índice novo é **670**. As 670 linhas anteriores
permanecem intactas. `bind_stats_row` liga a linha de atributos nova a esse
modelo, mantendo os nomes, atributos e habilidade preparados anteriormente.

| Campo | Registro |
| --- | --- |
| Espécie interna | 501 |
| Linha de modelo | 670 |
| Arquivo no catálogo | `pkx_501.fsys` |
| ID FSYS reservado | `00002000` |
| ID SDR normal reservado | `73ea0400` |
| ID SDR shiny reservado | `63ea0400` |

Os IDs SDR foram conferidos contra todas as linhas da tabela original,
sem colisões. **Reservar o ID shiny não cria a variante shiny**. Esta etapa
também não constrói nem instala um arquivo FSYS com essas duas variantes.

## Pontos e ações

Os 25 campos de ossos/pontos são resolvidos pelos nomes presentes no SDR
da Snivy, não pelos índices de Grotle. Os 22 campos de animação também são
resolvidos pelos nomes das 12 ações convertidas. Campos sem semântica
totalmente identificada seguem o perfil nativo de referência e continuam
sujeitos a teste no jogo, incluindo os fallbacks para movimentos aéreos.

Dois ajustes foram feitos no rig e o SDR foi regenerado em uma pasta privada:

- Adicionado `direct_set` sob a raiz estática, necessário à tabela nativa.
- Reposicionado o vínculo `ef_o` da cauda para `Waist`, o centro do corpo.

O SDR novo possui 119 nós, 21 pontos de efeito/controle e 12 ações.
Os controles não estão calibrados espacialmente no jogo. Os pontos dos
olhos, por exemplo, ainda usam a posição do osso Head e precisam de ajuste
individual antes de afirmar que efeitos visuais estão posicionados corretamente.

Classe pequena e velocidade de corrida 18 são parâmetros provisórios,
comparáveis ao cadastro de Treecko; não representam medição do passo,
distância percorrida ou comportamento de câmera da Snivy.

## Provas executadas

`verify_model_registry.py` executa as seguintes rotinas USA reais:

- `80396b74`: obtém o índice de modelo a partir da tabela de atributos.
- `80395cc0`: localiza uma linha de modelo.
- `80395d10` / `80395d44`: espécie e forma do modelo.
- `80395de8` / `80395e3c`: campos de pontos e de animações.
- `80395e90` / `80395ec4` / `80395ef8`: arquivo, SDR normal e SDR shiny.
- `8024c32c`: localiza o registro desse arquivo no catálogo FSYS.

O replay confirmou a cadeia **501 → 670 → 00002000 → pkx_501.fsys**,
as 25 referências de pontos e 22 de animações e o comportamento nos limites
dos dois seletores de campo. As 670 linhas de modelo e os 501 índices de
modelo de espécies anteriores foram preservados. Os ponteiros originais
foram restaurados e conferidos ao final.

`model-binding-proof.json` registra essa execução. O SDR regenerado passou
também pelo roundtrip de geometria/texturas e pela verificação de metadados
e UVs: 6.360 amostras escalares, erro máximo aproximadamente 2,98e-8.
Resultados em `model-binding-graphics-proof.json`. O SDR permanece privado.

## Reproduzir

Regenerar o SDR usando os estágios descritos em [NATIVE-PROFILE.md](NATIVE-PROFILE.md)
com os fontes atuais, preservando as provas antigas em outra pasta. Em seguida:

```sh
PYTHONPATH=experiments/snivy:expansion:mod-source:coop:/caminho/harness \
python experiments/snivy/verify_model_registry.py \
  --capture /caminho/diagnostics-command \
  --dol /caminho/test13/main.dol \
  --common /caminho/test13/common.fsys \
  --catalog /caminho/GSfsys.toc \
  --sdr /tmp/snivy-model-binding/snivy-experimental.sdr \
  --report /tmp/snivy-model-binding-proof.json
```

## Restante para uma versão jogável

Integrar estas alterações ao construtor final, criar os recursos normal/shiny,
finalizar os limites de espécie, os ícones/retratos e os passes. Continuam
necessários carregamento real, calibração de efeitos/câmera, transições,
memória/desempenho, batalhas e persistência no Dolphin.
