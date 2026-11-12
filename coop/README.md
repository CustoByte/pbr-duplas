# Campanha cooperativa em desenvolvimento

**Candidata experimental para teste, ainda sem validação de uma partida completa no Dolphin ou online.** A compilação de desenvolvimento continua desativada por padrão; o pacote experimental ativa a seleção cooperativa explicitamente. A versão do canal normal continua v0.9.1-monferno. Saves, ROM completa e bancos de memória privados não são publicados.

[**Instruções de instalação e validação**](TESTAR-COOP.md) · [Windows](https://github.com/CustoByte/pbr-duplas/releases/download/v0.10.0-coop-test.1/PBR-Coop-Teste-Windows.zip) · [Mac](https://github.com/CustoByte/pbr-duplas/releases/download/v0.10.0-coop-test.1/PBR-Coop-Teste-Mac.zip)

O projeto permanece com `project_complete: false` em [STATUS-COOP.json](STATUS-COOP.json): os testes isolados não demonstram inicialização completa, navegação de todas as telas especiais, persistência ou sincronização NetPlay.

## Regras confirmadas

- Uma campanha/save e um passe compartilhado, com quatro Pokémon por batalha.
- Cada jogador escolhe dois integrantes diferentes do mesmo passe e controla seus golpes, alvos e trocas.
- O primeiro escolhido por cada jogador começa ativo; o segundo é sua reserva.
- A troca normal só permite a reserva do próprio jogador.
- Se um jogador perder seus dois Pokémon, o sobrevivente pode controlar seus dois ativos restantes. Quem ficou sem Pokémon aguarda.
- Menus, diálogos e progressão da campanha pertencem ao jogador 1, mesmo se ele tiver perdido seus dois Pokémon naquela batalha.

O protótipo mantém escolhas sequenciais na interface original. Duas ações do mesmo sobrevivente são decisões diferentes e exigem liberação dos botões entre elas. Interface simultânea e recuperação de sessão online interrompida continuam indefinidas.

`coop_policy.py` representa essas regras. As escolhas `(P1-A, P1-B)` e `(P2-A, P2-B)` geram a ordem `(P1-A, P2-A, P1-B, P2-B)`, com donos `(P1, P2, P1, P2)`. O novo protótipo de seleção já preenche essa tabela ao confirmar as quatro escolhas. A indicação visual de quem deve escolher ainda está pendente.

## Fechamento da implementação e candidata de teste

A camada adicional cobre as 12 leituras dos atalhos `0x8006B468` e do visualizador de detalhes `0x800FC1B4`. Ela cruza callback registrado, contexto de batalha, posição e propriedade, inclusive se o visualizador reteve um índice físico de controle. Detalhes durante a seleção usam o dono da escolha atual; consultas de menus fora desses contextos preservam o caminho nativo. As seis páginas de detalhes têm seus pontos de entrada cobertos, mas a navegação visual completa ainda precisa ser executada no emulador.

A entrada nativa de resultados `0x800754C8` devolve a fase de menus ao P1; o código de cancelamento `0x80` invalida a tabela. A consulta final `0x80075394` mantém os donos enquanto retorna resultado pendente `0x80` e os descarta nos resultados finais 0/1/2. A operação é idempotente e não escreve no save. Isso preserva a atribuição entre rodadas de uma série, sem transferir os menus ao sobrevivente.

O accessor de textos `0x8024FB34` acrescenta `P1: ` ou `P2: ` aos prompts nativos `0x2ECB`, `0x2ECC`, `0x3123` e `0x3124`, preservando cabeçalhos, placeholders e terminadores. Os textos originais e os apelidos dos Pokémon não são modificados. A integridade dos bytes foi verificada; **posição, tamanho e atualização visual do prefixo ainda não foram verificados**. A seleção inicial segue a ordem documentada de dois por pessoa; não há um novo painel visual específico para ela.

[VERIFICACAO-ENCERRAMENTO-COOP.json](VERIFICACAO-ENCERRAMENTO-COOP.json) contém 384 casos de entrada auxiliar por dono, 96 comparações desativadas, dez guardas, 16 execuções do callback secundário nativo, quatro detalhes durante a seleção, oito entradas de resultado, 32 consultas de resultado e 32 repetições idempotentes, oito verificações de menu P1, 64 prefixos e 48 mensagens preservadas. Registro de callbacks, campos de animação, estados de resultado, controles e alguns objetos são fixtures explícitas. Não houve renderização nem resultado produzido por uma batalha real.

A reserva atual termina em `0x80641000`. O código próprio continua em `0x8063D400` e ocupa 8.116 bytes. Adaptadores ficam a partir de `0x80640000`, estado de seleção em `0x80640100`, entradas auxiliares em `0x80640200` e buffers de texto em `0x80640400..0x80640BFF`. Os dois setters de ArenaLo reservam esse novo limite; a lacuna do EXPHeap em `0x8063C800` permanece fora da seção carregada.

`prepare_coop_draft.py --activate-experimental` altera somente cinco bytes do estado próprio (`DRFT` e habilitação) em relação à compilação padrão. Duas execuções do reset nativo verificaram a ativação; [VERIFICACAO-ATIVACAO-COOP.json](VERIFICACAO-ATIVACAO-COOP.json) distingue os hashes das duas imagens. Sempre iniciar normalmente; restaurar um save state antigo não testa esse arranjo de memória.

`package_coop_candidate.py` usa o núcleo da v0.9.1, mantém common.fsys, as conferências da ROM e os aplicadores e substitui a imagem interna pelo candidato ativado. O Windows usa outro sufixo para a RVZ e ambos os iniciadores guardam seus caminhos em uma pasta de teste separada. O canal experimental consulta [update-test.json](update-test.json) neste ramo e valida o SHA-256 do núcleo baixado. Esse ramo precisa permanecer disponível para as atualizações experimentais. O canal normal `releases/latest` permanece inalterado. Os ZIPs passaram pelas conferências estruturais/roundtrip; os novos iniciadores ainda precisam ser executados nos sistemas dos jogadores.

## Consulta de entrada e cursor

O jogo inicializa dois canais na chamada em `0x80006DC4`. O gerenciador está acessível em `0x802492D8`, a contagem em `0x80249310` e cada controle em `0x802492E0`. Os objetos começam em `manager+0x38`, stride `0x928`. Pressionados ficam em `+0x20`; pressionados no quadro, em `+0x1C`.

A função `0x8005B5EC` tem 290 chamadas diretas. Seus parâmetros mudam de significado conforme a máscara:

| Consulta | r4 | r5 |
|---|---|---|
| Botões brutos/consultas com os bits altos correspondentes | Controle físico consultado | Controle usado pela validação |
| API normal do cursor | Identificador do botão selecionado na interface | Controle que fornece a entrada |

Essa distinção foi confirmada nas capturas e nas instruções nativas. O roteador agora preserva `r4` nas consultas de cursor, alterando somente `r5`. Nas consultas brutas aplicáveis, encaminha os dois índices. Consultas explícitas a outros controles e consultas de conexão preservam o caminho nativo.

`coop_input_router.py` aceita somente a base de SHA-256 `10913e96306bd0f8ef85f07c1d95d73ca90cbe923added8b513809640163fe96`. Usa `0x8063C400` e estado de 32 bytes em `0x8063C6C0`. Nova decisão bloqueia entrada até o dono soltar os botões, inclusive se ele continuar sendo o mesmo. Controle ausente/desconectado bloqueia sem transferir a escolha ao parceiro. Ainda não há tela de reconexão.

## Ponte experimental para o ator

As seções seguintes registram as etapas anteriores; os endereços e pendências atuais estão no fechamento acima.

As capturas privadas do Dolphin 2609b permitem executar duas famílias de interface efetivamente registradas:

| Captura | Modo nativo | Posição ativa | Rotina registrada | Retorno da consulta de entrada |
|---|---|---|---|---|
| Primeira | 2 | 0 | `0x80061C98` | `0x80062180` |
| Segunda | 6 | 1 | `0x80061598` | `0x8006180C` |

O registro de callbacks está em `0x804E60F0`, o identificador da interface em SDA `-0x7E1C` e o objeto de comandos em `0x8044DF88`. Os campos `+0x64` e `+0x6E` indicam posição ativa e lado/controle lógico. Encontrar uma função no executável, sozinho, não é tratado como prova de que ela controla a tela capturada.

`coop_actor_bridge.py` cruza chamada de entrada, registro ativo, modo e posição. A rotina original `0x803CC838` fornece o índice de equipe correspondente à posição ativa; a ponte consulta então o dono daquele integrante. A propriedade não é calculada somente pela posição em campo. A tabela tem seis entradas: donos 0/1 ou 255 para integrantes sem atribuição.

A habilitação automática exige tabela, marca de validade e identificação da sessão correspondente. O teste isolado da ponte instala uma tabela explícita; o novo protótipo de seleção a produz pela escolha nativa. Sessão diferente, tabela ausente, posição inválida ou integrante sem dono bloqueiam a leitura nas interfaces reconhecidas. Chamadas de outras interfaces continuam nativas: a ponte ainda não cobre todos os menus de batalha.

O gancho em `0x8005F364` incrementa o contador de decisão em cada abertura nativa de interface. Isso rearma a exigência de soltar os botões até para outro pedido igual do mesmo jogador. O estado fica zerado/desativado na imagem produzida.

A geração usa apenas lacunas verificadas da seção reservada pela v0.9.1: restauração em `0x8063C200`, roteador em `0x8063C400`, ponte em `0x8063C540`, estado em `0x8063C6C0` e gancho de abertura em `0x8063C720`. Não amplia o DOL ou a reserva de memória. Rejeita base diferente e sobreposição com código existente.

## Seleção de dois Pokémon por jogador

`coop_draft.c` conecta a seleção à tabela da ponte. O jogador 1 escolhe dois; em seguida o jogador 2 escolhe dois dentre os restantes. A confirmação final pertence ao jogador 1. Clicar num integrante já escolhido pelo outro jogador não o remove. Cada mudança de escolha rearma a exigência de soltar os botões. Chamadas de seleção em lote e confirmação também respeitam essa barreira; não podem continuar escolhendo pelo jogador que acaba de receber o controle sem uma nova consulta de entrada.

O botão nativo de voltar/recusar desfaz a escolha mais recente e devolve o controle ao dono dela: voltar antes da primeira escolha do jogador 2 retorna ao jogador 1; recusar depois das quatro retorna ao jogador 2. Também é possível remover uma escolha própria e refazê-la. A montagem preserva a ordem relativa das escolhas de cada jogador, inclusive após essas correções, e intercala os integrantes para produzir um ativo e uma reserva por dono.

As rotinas originais continuam responsáveis pelos filtros de elegibilidade/presença (`0x80154E0C`, `0x80058C34`), marcação e desmarcação (`0x80159DB8`) e cópia dos Pokémon selecionados (`0x8015A1C4`). A nova camada limita as cotas, impede remoção pelo parceiro e reorganiza os números de seleção antes da cópia. Confirmação incompleta também é bloqueada nos dois pontos nativos de confirmação: o código retorna à seleção em vez de deixar o chamador encerrar a tela.

O reset nativo (`0x80159B6C`) inicia a atribuição e invalida a tabela anterior. A limpeza (`0x80156364`) cancela uma seleção incompleta e devolve os menus ao jogador 1; após confirmação, preserva a tabela necessária à batalha. Ao confirmar, o próprio código preenche os donos e vincula a sessão. Nos testes, essa tabela foi consumida pela ponte das duas telas de comandos sem preenchimento manual.

As consultas de entrada são limitadas à rotina de seleção registrada `0x80156414`, às chamadas conhecidas e ao lado principal do passe compartilhado. Regras que não correspondem à seleção de quatro da campanha mantêm o comportamento nativo. O protótipo continua desativado na imagem gerada e depende de habilitação explícita de desenvolvimento.

### Memória e compilação

O código é compilado para PowerPC 750 com GCC 14.2.0, sem bibliotecas de execução, e usa uma quarta seção de texto em `0x8063D400..0x8063EFFF`. O código e os dados anteriores em `0x8063C000..0x8063C7FF` permanecem em sua seção original. Ambos os setters de ArenaLo passam a reservar memória até `0x8063F000` antes da criação dos heaps. O prefixo nativo de criação do heap foi executado separadamente e recebeu esse endereço como base.

Essa separação é necessária: nas capturas antigas existe um cabeçalho SDK EXPHeap em `0x8063C800`, com metadados de alocação nas proximidades. Ele não pode ser sobrescrito por uma extensão contígua do código anterior. Os testes preservam esse cabeçalho e vigiam escritas sobre o código adicional. A reserva muda a disposição do heap ao iniciar o protótipo; o replay isolado não equivale a restaurar um estado antigo dentro do Dolphin com essa nova disposição. A validação de uma inicialização completa no emulador ainda está pendente.

Para desenvolvimento, disponibilize `powerpc-linux-gnu-gcc-14` (14.2.0) e os binutils correspondentes. A compilação usada nesta etapa empregou os pacotes Debian oficiais listados em [toolchain-debian-lock.json](toolchain-debian-lock.json), extraídos num diretório local; não há compilador no aplicador do jogador.

Com `mod-source` e `coop` no caminho de módulos:

1. `python coop/build_coop_draft.py --output <pasta-de-build>` produz apenas o código próprio e seu manifesto. `--toolchain <raiz-extraida>` aceita um conjunto Debian extraído localmente.
2. `python coop/prepare_coop_draft.py --source <main.dol-v0.9.1> --payload <build>/draft.bin --manifest <build>/draft-symbols.json --output <copia-interna.dol>` gera uma cópia interna desativada.
3. `python coop/verify_coop_draft.py --source <main.dol-v0.9.1> --changed <copia-interna.dol> --payload <build>/draft.bin --manifest <build>/draft-symbols.json --captures <primeira-pasta-privada> <segunda-pasta-privada> --output <relatorio.json>` repete a verificação privada.

O estado próprio da seleção fica em `0x8063EB00`. O código gerado não inclui dados de Pokémon, saves, RAM ou arquivos do jogo.

### Evidência desta etapa

[VERIFICACAO-SELECAO-COOP.json](VERIFICACAO-SELECAO-COOP.json) registra 720 sequências (360 por captura), 720 bloqueios de remoção de uma escolha do parceiro, oito confirmações incompletas bloqueadas, seis casos de voltar/corrigir escolhas, oito consultas de entrada por dono, duas escolhas de comando após atribuição automática, 20 comparações com o protótipo desativado, 28 verificações dos setters de ArenaLo, quatro limpezas de tela e oito bloqueios de chamadas sem liberação da entrada.

Os testes usam os seis integrantes reais de um passe obtido pelo accessor nativo, preservam os filtros e comparam os dados copiados com os integrantes de origem. **Não substituem predicados de elegibilidade, getters de Pokémon, marcação ou empacotamento.** Como as capturas são da batalha, o objeto da tela de seleção e seu registro são reconstruídos; botões/conexão são preparados como entradas explícitas. Os testes de entrada executam os pontos de chamada nativos isoladamente. Os sons de feedback e quatro instruções de contexto paired-single são tratados como nos replays anteriores.

Não houve renderização da seleção, navegação completa por dois controles físicos, inicialização completa da batalha a partir dessa tela nem NetPlay. O cabeçalho de heap capturado é preservado, mas as alocações do heap antigo não são reproduzidas durante a seleção isolada. O indicador visual de turno e a cobertura dos torneios com telas especiais ainda precisam ser integrados e testados.

## Comando, golpe e alvo pelo dono do atacante

A integração atual diferencia três famílias da interface principal:

| Etapa | Callback nativo | Modos para posições 0 / 1 | Retornos de entrada reconhecidos |
|---|---|---|---|
| Comando principal e confirmação auxiliar | `0x80060EEC` | 0 / 4 | `0x80061118`, `0x8006113C`, `0x80061154`, `0x8006143C` |
| Escolha de golpe | `0x80061598` | 1 / 6 | `0x8006180C` |
| Escolha de alvo | `0x80061C98` | 2 / 7 | `0x80062180` |

A análise das rotinas de inicialização, dos getters de golpes e dos resultados de alvo identifica a primeira captura como a família de alvos e a segunda como a de golpes. Os replays anteriores tratavam ambas genericamente como interfaces de comando; a nova etapa registra essa distinção e usa fase 3 para alvos e fase 2 para comandos/golpes. O comando principal da segunda posição usa modo **4**, não 5; isso foi conferido na tabela de abertura nativa.

`coop_input_scope` cruza ponto da chamada, registro ativo, lado, modo, posição, sessão e tabela de donos. A propriedade vem do integrante lógico ativo, cujo HP é consultado no contexto real da batalha. Contexto reconhecido com vínculo inválido ou atacante sem HP bloqueia entrada. A nova camada cobre também o comando principal e sua confirmação de duas opções; as duas famílias verificadas anteriormente passam pela mesma verificação de contexto. Entrada fora desses pontos reconhecidos continua pelos caminhos anteriores/nativos.

Quem escolhe o alvo é o dono do **atacante**. Mirar no Pokémon do parceiro, quando o golpe permite, não transfere o controle a ele. A camada não muda a elegibilidade dos alvos nem as máscaras de resultado: continuam calculadas pelas funções e getters originais. Os dois ativos do sobrevivente usam o controle dele após a reordenação nativa. Novos pedidos e mudanças de fase/dono exigem liberação dos botões.

[VERIFICACAO-ALVOS-COOP.json](VERIFICACAO-ALVOS-COOP.json) registra 84 comparações de callbacks com coop desativado; 288 comparações encaminhadas ao dono, 288 bloqueios do outro jogador e 288 barreiras de entrada; 48 inicializações de perfis numéricos de alvo e 240 comparações do resultado final; 144 casos com reordenação nativa para o sobrevivente; 36 vínculos inválidos bloqueados; oito chamadas dos ramos de comando/confirmação; quatro escolhas explícitas do aliado mantendo o dono do atacante; e 64 casos de máscaras com alvos sem HP. As regressões de seleção e troca usam a mesma imagem interna.

O teste executa a abertura e o registro de callback originais, a configuração nativa de botões, o cursor e o resultado final da escolha. Para avançar as animações sem renderizar, prepara explicitamente o campo de conclusão que o getter nativo `0x802585F4` consulta. Donos, caches dos controles e alguns mapeamentos são fixtures; HP é preparado pelo setter nativo. Sons e contexto PSQ têm as mesmas exceções estreitas dos testes anteriores. Não são testes de todos os golpes/habilidades, de animações renderizadas, de controles físicos nem de uma batalha completa.

Para repetir: `python coop/verify_coop_target.py --source <main.dol-v0.9.1> --changed <copia-interna.dol> --captures <primeira-pasta-privada> <segunda-pasta-privada> --output <relatorio.json>`. Ainda falta integrar a rotina secundária de resumo/atalhos `0x8006B468`, telas especiais, indicação de dono e encerramento da batalha. O protótipo segue desativado e fora do aplicador distribuído.

## Trocas e substituições por dono

A nova camada em `coop_draft.c` atende a tela nativa de equipe `0x80062B50`, nos modos 3 e 8, e a validação original de troca `0x801722BC`. As posições ativas e as linhas da tela são convertidas para o índice lógico pela função original `0x803CC838`; a propriedade continua ligada ao integrante, mesmo depois de uma reordenação.

A leitura de HP usa o getter nativo `0x803E100C`, campo `0xA2`, nos quatro integrantes reais do contexto de batalha. Trocas voluntárias só aceitam uma reserva viva do próprio dono. Após um desmaio, esse dono escolhe sua reserva; se ambos os integrantes dele estiverem sem HP, a posição passa ao parceiro, que pode colocar sua reserva em campo. Após a reordenação nativa, a ponte de comandos já identifica os dois ativos como pertencentes ao sobrevivente. Quando não há reserva válida, a camada não inventa um integrante para preencher a posição.

A entrada da tela é encaminhada ao dono correspondente, com nova barreira de liberação ao mudar o jogador ou a fase. Confirmações de integrante indisponível são suprimidas, mantendo o foco. Cancelamento segue o processamento nativo, pelo controle correto. O gancho de validação também cobre consultas fora desse ponto de entrada: primeiro executa os bloqueios originais de HP, ativo, escolha pendente e aprisionamento; depois acrescenta a verificação de dono. Contextos inimigos continuam nativos. Tabela/sessão/contexto incompatíveis impedem uma nova escolha cooperativa válida. Ainda não há indicação visual explicando esse bloqueio.

O adaptador de entrada fica em `0x8063EB40` e o retorno à validação original em `0x8063EB50`, separados do estado em `0x8063EB00`. O código compilado atual, incluindo comando/golpe/alvo, ocupa 5.428 bytes e cabe na reserva anterior; o limite de ArenaLo permanece `0x8063F000`. A imagem gerada continua desativada ao iniciar.

[VERIFICACAO-TROCAS-COOP.json](VERIFICACAO-TROCAS-COOP.json) registra 9.216 comparações com o contrato de propriedade, cobrindo todos os 16 padrões de HP, pares ordenados de ativos, duas atribuições de dono, ambas as posições e as seis linhas, nas duas capturas. Inclui 7.684 rejeições nativas preservadas, 72 verificações de entrada, 72 transições da rotina real da tela, 144 comparações da validação desativada, 84 comparações da entrada desativada, oito casos com reordenação nativa para o sobrevivente, 34 guardas e 12 casos de cada: cancelamento, controle desconectado e barreira de liberação.

**Esses são testes nativos isolados, não uma batalha completa no Dolphin.** HP é alterado pelo setter original `0x803DEB54`, sem executar dano/animações de desmaio. A estrutura de validação e a equipe na ordem de exibição são reconstruídas; não foram capturadas numa substituição real. Os padrões de reordenação exaustivos, botões e donos são entradas preparadas. A rotina real da tela parte da fase pronta para entrada, com foco preparado; não percorre toda a animação de abertura. Entrada, validação, getters, setter de HP e reordenação não são substituídos; mantêm-se as exceções estreitas de áudio/contexto PSQ do replay anterior. O texto do erro nativo `0x505A` ainda não foi conferido visualmente.

Para repetir com os arquivos privados e a imagem interna: `python coop/verify_coop_switch.py --source <main.dol-v0.9.1> --changed <copia-interna.dol> --captures <primeira-pasta-privada> <segunda-pasta-privada> --output <relatorio.json>`. A regressão das 720 seleções foi repetida com essa mesma imagem; o relatório atualizado está em [VERIFICACAO-SELECAO-COOP.json](VERIFICACAO-SELECAO-COOP.json).

## Verificações e limites

As três seções executáveis completas de cada captura, incluindo a seção do mod, têm 4.069.376 bytes idênticos à base v0.9.1. Dados de execução não são comparados com seus valores iniciais no disco. `verify_coop_capture.py` rejeita divergência no código e exporta somente resultados.

O roteador isolado passou em 242 comparações desativado, 121 casos de menu, 220 leituras por dono/fase e 20 casos de confirmação/cancelamento preservando o cursor. As consultas de cursor desse teste usam os flags nativos de supressão de sons. Os oito testes do contrato incluem as 360 ordens de quatro escolhas de um passe de seis.

O replay das interfaces em `verify_coop_actor.py` cobre:

- Comportamento nativo preservado com o protótipo desativado, incluindo direções, confirmação e cancelamento.
- Confirmação/cancelamento pelo dono correto; comandos do outro jogador não avançam a decisão.
- Identificador do botão, pilha e registradores não voláteis preservados.
- Consulta de propriedade pelo índice de equipe, com tabelas invertidas e reservas colocadas no mapeamento ativo.
- Reordenação pela função original `0x803C96D4`, colocando dois integrantes do mesmo dono como ativos e encaminhando ambas as interfaces ao sobrevivente correspondente.
- Bloqueio com tabela/sessão/posição/modo/índice inválidos; novos pedidos do mesmo dono; contador de decisão chegando ao limite de 32 bits.

Botões, conexão e tabela de donos são entradas preparadas. Parte dos mapeamentos é preparada diretamente; os casos de sobrevivente usam a reordenação nativa. **Não há simulação de perda de HP/desmaios ou troca completa pela interface.** O replay das interfaces substitui apenas os sons de feedback 1/2/3 em `0x8005C04C`; pula quatro instruções de contexto paired-single em `0x8000AD80`, `0x8000AD88`, `0x8000AE88` e `0x8000AE90`. Entrada, obtenção do integrante, cursor, reordenação e transições da interface executam instruções originais.

Não houve renderização cooperativa, teste com dois controles físicos ou sessão NetPlay. Os relatórios contêm os números exatos, sem saves, RAM ou equipes:

- [VERIFICACAO-ENTRADAS.json](VERIFICACAO-ENTRADAS.json)
- [VERIFICACAO-TELA-GOLPES.json](VERIFICACAO-TELA-GOLPES.json)
- [VERIFICACAO-SEGUNDA-TELA.json](VERIFICACAO-SEGUNDA-TELA.json)
- [VERIFICACAO-ATORES.json](VERIFICACAO-ATORES.json)
- [VERIFICACAO-SELECAO-COOP.json](VERIFICACAO-SELECAO-COOP.json)
- [VERIFICACAO-TROCAS-COOP.json](VERIFICACAO-TROCAS-COOP.json)
- [VERIFICACAO-ALVOS-COOP.json](VERIFICACAO-ALVOS-COOP.json)

Para o contrato sem binários: `python -m unittest discover -s coop -p test_coop_policy.py`.

Para o replay privado, instale `mod-source/requirements-dev.txt` e coloque `mod-source` e `coop` no caminho de módulos. Extraia as capturas localmente com `mod-source/read_dolphin_state.py`, sem copiá-las para o repositório. Execute `coop/verify_coop_actor.py --source <main.dol-v0.9.1> --captures <primeira-pasta-privada> <segunda-pasta-privada> --output <relatorio.json>`. Isso gera um relatório, não um lançamento jogável.

## Validação restante para finalizar

A implementação nativa reunida está empacotada para teste manual. Ainda faltam a validação visual dos resumos/atalhos e do prefixo, inicialização completa, todos os coliseus/regras especiais, persistência com o save real, dois controles físicos e NetPlay. O roteiro e os critérios de aprovação estão em [TESTAR-COOP.md](TESTAR-COOP.md). O projeto não é marcado como concluído enquanto esses itens estiverem sem evidência.

## Transporte online

O código oficial do Dolphin contém `WiimoteMapping` e `WiimoteUpdate`, com filas por Wii Remote emulado. Isso sustenta investigar NetPlay, mas não comprova compatibilidade do mod numa sessão real. Referência: [NetPlayClient.cpp](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/NetPlayClient.cpp).

O primeiro teste deve usar dois PCs Windows com a mesma versão do Dolphin, o mesmo conteúdo e um Wii Remote emulado por jogador. Equivalência entre RVZ reconstruída e aplicação Riivolution no Mac, sincronização do save do anfitrião e gravação do progresso ainda precisam de validação. Adicionar o Dolphin à Steam como jogo externo não habilita automaticamente Remote Play Together.
