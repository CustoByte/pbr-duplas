# Snivy: experimento isolado de registro

Base: RPBE01 USA revisão 0, publicação test13, commit
`93d318a052b3f3b7d026d1bebab6783a04a1a195`.
Este módulo não é importado pelo construtor das versões públicas.
Não modifica a ISO, o atualizador, saves ou os arquivos publicados.

## Resultado comprovado

`verify_native.py` executa a rotina USA `0x803E052C` em Unicorn PPC,
usando memória capturada e o DOL modificado original do test13.
Uma cópia da tabela é registrada temporariamente no ponteiro `0x80625184`.
O registro adicional retorna HP45, Atk45, Def55, Speed63, SpAtk45,
SpDef55, Grass/Grass e Overgrow. Todos os 501 registros anteriores
produzem saídas idênticas; a restauração do ponteiro também é verificada.
Os getters de atributos não são substituídos por resultados simulados.
O harness existente tem adaptações de áudio/PSQ para execução isolada;
isso não é um teste do jogo completo no Dolphin.

## Identidade e estrutura

O número nacional 495 não pode ser usado diretamente como índice:
494/495 são reservados para Egg/Bad Egg; 496..500 contêm dados
das formas de Deoxys e Wormadam. O índice **provisório** escolhido é 501.
Ainda falta provar sua disponibilidade em todos os demais registros.
O mapeamento nacional 495 → interno 501 existe apenas neste módulo;
não foi integrado às interfaces ou ao motor completo.
Victini nacional 494 continua não implementado.

`common.fsys`, recurso `0x00810200`: cabeçalho 48 bytes, 501 linhas de
52 bytes; contador em +0, stride em +4, offset em +16, tamanho dos dados
em +20 e tamanho total em +24. A linha nova é anexada antes do padding,
preservando integralmente as linhas antigas e atualizando os comprimentos.
Campos não investigados da nova linha permanecem zerados, de propósito:
**não é um registro pronto para uso em jogo**.

Outros recursos a investigar: evolução `0x00820200` (501 × 42),
possível aprendizado `0x12a90200` (501 × 80), associações
`0x16410200` (495 × 12) e `0x007d0200` (495 × 8).
A função USA de formas `0x803E0F0C` mantém os índices 496..500.
A busca de linha `0x803963D0` não valida o limite superior;
aumentar apenas um contador não torna as demais rotinas seguras.

## Reproduzir

Com Python e os módulos já usados pelo projeto:

```sh
PYTHONPATH=experiments/snivy python -m unittest discover -s experiments/snivy -p 'test_*.py'
PYTHONPATH=experiments/snivy:expansion:mod-source:coop:/caminho/harness \
python experiments/snivy/verify_native.py \
  --capture /caminho/diagnostics-command \
  --dol /caminho/test13/main.dol \
  --common /caminho/test13/common.fsys \
  --report /tmp/snivy-native-report.json
```

Os hashes exigidos estão no verificador. Capturas e arquivos de jogo não
são distribuídos. O relatório registra os hashes e a saída observada.

## Próximas verificações obrigatórias

- Mapear limites, nomes, ícones, modelos, IA e serialização; resolver todos
  os índices sem substituir Egg, Bad Egg, formas ou espécies originais.
- Completar os metadados oficiais e confirmar o aprendizado de quinta geração
  para Tackle, Leer, Magical Leaf e Protect antes de atribuí-los.
- Demonstrar construção PK4, atributos no nível 5 e save/load sem perdas.
- Representar elegibilidade evolutiva de Snivy sem cadastrar evoluções
  inexistentes nem alterar as regras de Little Battle.
- Importar os recursos próprios de Snivy e testar menus e batalhas reais.

Na investigação inicial faltavam os recursos de Snivy de PokéPark 2;
eles foram recebidos posteriormente, conforme o registro abaixo.
O exportador PBR suporta SDR e ações como idle, damage,
faint, move_phys e move_spec, mas não comprova conversão direta do formato
de PokéPark 2. Precisam ser validados esqueleto, materiais, root motion,
eventos, entrada/retorno e loops. Nenhum modelo foi importado nesta prova.

Referências auditadas (não se aplicaram endereços PAL ao DOL USA):

- pbr-ret/pbr-decomp: `bc8ac653c98eb146d793b7a024bfa48045194592`.
- bgsamm/pbr-models-import-export: `ed18e4fd606bf66b670c71c2484bf9fc86ea5b7d`.

O experimento não demonstra renderização, batalhas, ativação de Overgrow,
elegibilidade, obtenção em Battle Pass ou persistência. Nenhuma dessas
etapas deve ser anunciada como funcional antes de testes próprios.

## Recurso gráfico recebido

Foi recebido `Tsutarja.brres` de PokéPark 2 USA, SHA-256
`42ee39d351dc05e4f509267a2ce540286b134f6e8d024b776175a4c75c5a9308`.
O arquivo original permanece privado e não faz parte do repositório.
`inspect_brres.py` percorre os dicionários BRRES, valida limites e conta
seções; `brres-inventory.json` contém apenas metadados, sem os recursos.

Inventário: 1 MDL0 v11, 5 TEX0 v3, 117 CHR0 v5 e 105 SRT0 v5.
A ação `NorIdle0` declara 84 frames e repetição; `Atk0_0`, 36 frames;
`DamF0`, 31 frames. As três têm 48 trilhas de transformação.
`Faint0` declara repetição no arquivo fonte: é necessário verificar o
comportamento esperado antes de mapear essa ação para derrota no PBR.
Os nomes permitem selecionar candidatos, mas não comprovam seu conteúdo
visual. Ao concluir esse inventário, ainda não havia conversão ou reprodução.
Os resultados da etapa gráfica posterior estão em `GRAPHICS.md`; a importação
no motor do jogo continua pendente.

```sh
python experiments/snivy/inspect_brres.py /caminho/Tsutarja.brres \
  --report /tmp/snivy-brres.json
```

O pedido anterior de recursos gráficos está atendido. A etapa seguinte já
produziu uma prova de conversão SDR e uma prévia animada fora do jogo.
Consulte [GRAPHICS.md](GRAPHICS.md) para resultados, reprodução e limitações.
A associação do modelo à nova espécie na versão USA continua pendente.
