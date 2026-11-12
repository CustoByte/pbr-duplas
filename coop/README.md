# Campanha cooperativa — base de controle em desenvolvimento

**Este ramo não oferece ainda um cooperativo jogável.** O código de entrada está desativado ao iniciar e não está no canal automático de atualização. A distribuição atual continua v0.9.1-monferno.

## Regras confirmadas

- Uma campanha/save e um passe com o time compartilhado; batalhas em duplas, com quatro escolhas.
- Cada jogador escolhe dois integrantes diferentes do mesmo passe e controla os seus golpes, alvos e trocas.
- O primeiro escolhido por cada jogador começa ativo; o segundo é sua reserva.
- As reservas pertencem ao jogador que as escolheu. A troca normal não permite usar o Pokémon do parceiro.
- Se um jogador perder seus dois Pokémon, o sobrevivente continua com os seus e pode controlar os dois ativos simultaneamente. Quem ficou sem Pokémon aguarda.
- Os menus, diálogos e progressão da campanha pertencem ao jogador 1, mesmo se ele tiver perdido seus dois Pokémon naquela batalha.

O primeiro protótipo mantém a interface de escolhas sequenciais do jogo: a cada pedido de ação, o controle pertence ao dono daquele Pokémon. Ações para dois Pokémon do mesmo sobrevivente são duas decisões distintas. Interface simultânea e recuperação de uma sessão online interrompida ainda não estão definidas/implementadas.

O modelo `coop_policy.py` representa as regras e as transições. As escolhas `(P1-A, P1-B)` e `(P2-A, P2-B)` produzem a ordem lógica `(P1-A, P2-A, P1-B, P2-B)`, com donos `(P1, P2, P1, P2)`. O dono acompanha a identidade lógica do integrante, não sua posição atual em campo. **Esse modelo ainda não está conectado ao empacotamento nativo do jogo.**

## Entrada nativa já localizada e executada

A chamada de inicialização em `0x80006DC4` passa dois canais à construção do gerenciador. O gerenciador é obtido em `0x802492D8`; a contagem em `0x80249310`; cada controle em `0x802492E0`. Os objetos começam em `manager+0x38`, stride `0x928`. A atualização de botões em `0x80248A1C` mantém pressionados em `+0x20`, pressionados no quadro em `+0x1C` e quadro anterior em `+0x24`.

A rotina de consulta do jogo em `0x8005B5EC` recebe a máscara da consulta e os índices de controle. Foram identificadas 290 chamadas diretas a ela, distribuídas entre interfaces diferentes. O estado privado enviado confirma que o gerenciador tem dois canais. A execução isolada dessa rotina retorna máscaras diferentes para os dois canais quando seus caches são preparados explicitamente; a função de leitura não foi substituída.

`coop_input_router.py` contém uma transformação reproduzível, restrita ao SHA da v0.9.1, para encaminhar a leitura lógica do controle principal ao dono de uma escolha autorizada. Usa espaço vazio da seção reservada pela v9, em `0x8063C400`, e um bloco de estado em `0x8063C6C0`, sem ampliar a reserva.

O bloco tem assinatura `COOP`, habilitação, fase, dono, trava de liberação e contadores de decisão. Por padrão fica zerado/desativado. Durante menus, a consulta lógica principal mantém o controle 1; durante uma escolha autorizada, pode usar o 1 ou 2. Uma nova decisão exige soltar os botões antes de aceitar outro comando, inclusive quando o mesmo sobrevivente fará duas escolhas consecutivas. Controle ausente/desconectado bloqueia a leitura sem transferi-la ao parceiro. Isso é uma proteção da entrada; ainda não é uma tela de pausa/reconexão.

O roteador cobre consultas ao controle lógico principal. Consultas explícitas a outros controles e consultas de conexão continuam nativas e precisam ser auditadas nas interfaces reais antes da ativação. Não resolve sozinho propriedade de reservas, seleção de alvos, cancelamento ou confirmação. Não há nenhum código que atualmente detecte a fase de batalha e habilite esse bloco.

## Verificações concluídas

- 242 comparações com o protótipo desativado, preservando a leitura original.
- 121 casos em menus usando o controle principal original.
- 220 leituras por dono/fase, com os caminhos PowerPC originais e o roteador.
- Liberação de botões entre decisões, inclusive duas ações consecutivas do mesmo jogador; desconexão e falta de canal sem assumir o controle pelo parceiro.
- Oito testes do contrato de propriedade, incluindo as 360 ordens possíveis de quatro escolhas de um passe de seis, reservas, desmaios, sobrevivente com dois ativos e retorno dos menus ao jogador 1.

Os caches de botões e os campos de conexão foram preparados como entradas explícitas dos testes. Não houve leitura de hardware, renderização, partida com dois controles nem sessão online. O estado privado não está publicado. Registro: [VERIFICACAO-ENTRADAS.json](VERIFICACAO-ENTRADAS.json).

Para executar somente o contrato em Python: `python -m unittest discover -s coop -p test_coop_policy.py`. O replay PowerPC também requer as dependências em `mod-source/requirements-dev.txt`, `mod-source` e `coop` no caminho de módulos, os binários locais correspondentes e os bancos privados MEM1/MEM2.

## Transporte online

O código oficial do Dolphin contém `WiimoteMapping` e `WiimoteUpdate`, com serialização e filas separadas por Wii Remote emulado. Isso sustenta usar NetPlay como transporte, mas não comprova compatibilidade do mod numa sessão real. Referência: [NetPlayClient.cpp](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/NetPlayClient.cpp).

O primeiro teste deve usar dois PCs Windows com a mesma versão do Dolphin, o mesmo conteúdo de jogo/mod e mapeamento de um Wii Remote emulado por jogador. Formatos diferentes de aplicação — RVZ reconstruída no Windows e descritor Riivolution no Mac — ainda precisam de validação de equivalência para NetPlay. A campanha compartilhada deve partir do save do anfitrião, com preservação dos dados locais; a sincronização de save e a gravação de progresso precisam ser testadas.

Adicionar o Dolphin à Steam como jogo externo não habilita automaticamente Remote Play Together. Streaming continua sendo uma alternativa de transporte futuro; não substitui as regras de controle dentro do jogo.

## Próxima integração e dado que falta

Falta identificar os eventos reais que informam qual Pokémon está escolhendo uma ação, qual interface está ativa e quando ela encerra/cancela a escolha. Também falta integrar as quatro escolhas por dono, a ordem inicial intercalada, os limites de reserva e as substituições após desmaios.

O estado disponível foi capturado na introdução da batalha, antes da interface de comandos. Para a próxima investigação é necessário um **estado do Dolphin capturado na tela de escolha de golpes**, de preferência na v0.9.1. É diferente do save normal da campanha. Ele será analisado localmente e não será enviado ao repositório. A ROM completa não é necessária para essa captura.
