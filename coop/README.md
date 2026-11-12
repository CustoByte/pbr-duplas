# Campanha cooperativa em desenvolvimento

**Este ramo ainda não oferece um cooperativo jogável.** O protótipo fica desativado ao iniciar e não está no canal automático de atualização. A versão distribuída continua v0.9.1-monferno. Saves e bancos de memória privados não são publicados.

## Regras confirmadas

- Uma campanha/save e um passe compartilhado, com quatro Pokémon por batalha.
- Cada jogador escolhe dois integrantes diferentes do mesmo passe e controla seus golpes, alvos e trocas.
- O primeiro escolhido por cada jogador começa ativo; o segundo é sua reserva.
- A troca normal só permite a reserva do próprio jogador.
- Se um jogador perder seus dois Pokémon, o sobrevivente pode controlar seus dois ativos restantes. Quem ficou sem Pokémon aguarda.
- Menus, diálogos e progressão da campanha pertencem ao jogador 1, mesmo se ele tiver perdido seus dois Pokémon naquela batalha.

O protótipo mantém escolhas sequenciais na interface original. Duas ações do mesmo sobrevivente são decisões diferentes e exigem liberação dos botões entre elas. Interface simultânea e recuperação de sessão online interrompida continuam indefinidas.

`coop_policy.py` representa essas regras. As escolhas `(P1-A, P1-B)` e `(P2-A, P2-B)` geram a ordem `(P1-A, P2-A, P1-B, P2-B)`, com donos `(P1, P2, P1, P2)`. **A seleção nativa ainda não preenche essa tabela automaticamente.**

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

As capturas privadas do Dolphin 2609b permitem executar duas famílias de interface efetivamente registradas:

| Captura | Modo nativo | Posição ativa | Rotina registrada | Retorno da consulta de entrada |
|---|---|---|---|---|
| Primeira | 2 | 0 | `0x80061C98` | `0x80062180` |
| Segunda | 6 | 1 | `0x80061598` | `0x8006180C` |

O registro de callbacks está em `0x804E60F0`, o identificador da interface em SDA `-0x7E1C` e o objeto de comandos em `0x8044DF88`. Os campos `+0x64` e `+0x6E` indicam posição ativa e lado/controle lógico. Encontrar uma função no executável, sozinho, não é tratado como prova de que ela controla a tela capturada.

`coop_actor_bridge.py` cruza chamada de entrada, registro ativo, modo e posição. A rotina original `0x803CC838` fornece o índice de equipe correspondente à posição ativa; a ponte consulta então o dono daquele integrante. A propriedade não é calculada somente pela posição em campo. A tabela tem seis entradas: donos 0/1 ou 255 para integrantes sem atribuição.

A habilitação automática exige tabela explicitamente instalada pelo teste, marca de validade e identificação da sessão correspondente. Sessão diferente, tabela ausente, posição inválida ou integrante sem dono bloqueiam a leitura nas interfaces reconhecidas. Chamadas de outras interfaces continuam nativas: a ponte ainda não cobre todos os menus de batalha.

O gancho em `0x8005F364` incrementa o contador de decisão em cada abertura nativa de interface. Isso rearma a exigência de soltar os botões até para outro pedido igual do mesmo jogador. O estado fica zerado/desativado na imagem produzida.

A geração usa apenas lacunas verificadas da seção reservada pela v0.9.1: restauração em `0x8063C200`, roteador em `0x8063C400`, ponte em `0x8063C540`, estado em `0x8063C6C0` e gancho de abertura em `0x8063C720`. Não amplia o DOL ou a reserva de memória. Rejeita base diferente e sobreposição com código existente.

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

Para o contrato sem binários: `python -m unittest discover -s coop -p test_coop_policy.py`.

Para o replay privado, instale `mod-source/requirements-dev.txt` e coloque `mod-source` e `coop` no caminho de módulos. Extraia as capturas localmente com `mod-source/read_dolphin_state.py`, sem copiá-las para o repositório. Execute `coop/verify_coop_actor.py --source <main.dol-v0.9.1> --captures <primeira-pasta-privada> <segunda-pasta-privada> --output <relatorio.json>`. Isso gera um relatório, não um lançamento jogável.

## Próximas integrações

Faltam escolha de dois integrantes por pessoa, criação automática da tabela e ordenação inicial intercalada; cobertura das demais interfaces de comandos/alvos; restrição de reservas; substituições após desmaios; descarte da tabela ao terminar a batalha; retorno completo aos menus do jogador 1. Depois será possível testar uma partida completa com dois controles e NetPlay. Não é necessário outro estado para repetir esta etapa.

## Transporte online

O código oficial do Dolphin contém `WiimoteMapping` e `WiimoteUpdate`, com filas por Wii Remote emulado. Isso sustenta investigar NetPlay, mas não comprova compatibilidade do mod numa sessão real. Referência: [NetPlayClient.cpp](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/NetPlayClient.cpp).

O primeiro teste deve usar dois PCs Windows com a mesma versão do Dolphin, o mesmo conteúdo e um Wii Remote emulado por jogador. Equivalência entre RVZ reconstruída e aplicação Riivolution no Mac, sincronização do save do anfitrião e gravação do progresso ainda precisam de validação. Adicionar o Dolphin à Steam como jogo externo não habilita automaticamente Remote Play Together.
