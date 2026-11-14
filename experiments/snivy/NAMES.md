# Nome independente da Snivy

Esta etapa implementa o cadastro e prova as buscas nativas. Não instala uma
Snivy jogável nem muda o atualizador.

## Cadastro

- Mensagem adicionada: `SNIVY`, com os controles de fonte nativos.
- Recurso MESG: `mes_common.fsys`, `0x27c10000`.
- Índice local, base um: **9996**.
- ID global: **21775**, acrescentado ao mapa `common.fsys`, `0x008b0000`.
- Os 9.995 textos e 21.774 registros globais antigos permanecem intactos.
- Os dois campos de nome da nova linha de atributos podem receber esse ID
  por `sunny_park.stats_row(global_name_id=21775)`.

O ID global não é o índice local. Também não é `501 + 10`, fórmula que o
jogo usava para os nomes originais. `names.patch_dol` desvia a instrução
USA `803e3478` para uma rotina que trata somente a espécie interna 501.
Para todos os outros valores, executa o cálculo anterior.

O seletor de categoria da busca `803e3458` é **2** para espécies. As outras
categorias, inclusive nomes de itens e golpes, não são alteradas. A busca
do nome na tabela de atributos usa `80396b0c`, recebendo o endereço do
ponteiro da tabela e o índice da espécie como dois argumentos separados.

## Reserva de memória

O código é acrescentado ao slot de texto 3, em `80646000`, reservando
`0x200` bytes. O limite mínimo das duas entradas do setter de arena MEM1
é estendido de `80646000` para `80646200`, sem remover as modificações
anteriores. Fontes diferentes do DOL test13 auditado são rejeitadas.

A rotina preserva r0, CR, SP, LR e CTR, além dos registradores não usados.
O teste inclui nove entradas com r0/CR/CTR não zerados para detectar uma
alteração de estado que o harness convencional, sozinho, não perceberia.

## Resultado e limite

`names-proof.json` registra:

- 501 resultados anteriores iguais, tanto na busca de categoria quanto na
  busca pelo registro de atributos; sentinelas e formas não são deslocados.
- 90 resultados iguais nas demais categorias de mensagens.
- 9.996 consultas nativas ao MESG comum, incluindo a nova mensagem.
- Nome da Snivy medido pela fonte nativa: **51 × 25** unidades.
- Verificação dos dois aliases do setter de arena.

As tabelas são registradas em RAM temporária no replay. Não há carregamento
real dos arquivos FSYS, teste visual da interface ou gravação de save.
O modelo e os retratos continuam pendentes. O tamanho medido do nome não
comprova o enquadramento de nenhuma tela específica.

## Reproduzir

```sh
PYTHONPATH=experiments/snivy:expansion:mod-source:coop:/caminho/harness \
python experiments/snivy/verify_names.py \
  --capture /caminho/diagnostics-command \
  --dol /caminho/test13/main.dol \
  --common /caminho/test13/common.fsys \
  --messages /caminho/test13/mes_common.fsys \
  --report /tmp/snivy-names-proof.json
```

Os arquivos originais e os recursos alterados continuam privados. Somente
código, metadados e resultados de teste fazem parte da branch pública.
