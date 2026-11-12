# PBR Coop — candidata experimental para validação

Este pacote reúne o cooperativo implementado até aqui. **Ainda não é uma versão final validada no Dolphin ou online.** Os testes internos executam rotinas nativas isoladas; a campanha completa, as telas especiais e a sessão NetPlay precisam do teste abaixo.

## Instalar e abrir

1. Baixe o ZIP do seu sistema e extraia tudo para uma pasta.
2. Feche o Dolphin. No Windows, abra **INICIAR-COOP-WINDOWS.cmd**. No Mac, abra **INICIAR-COOP-MAC.command**.
3. Na primeira vez, escolha a pasta da sua **ROM original USA RPBE01 revisão 0** e o Dolphin. No Windows, mantenha Dolphin.exe e DolphinTool.exe na mesma pasta.
4. O iniciador prepara o mod e abre o jogo. Nas próximas vezes, use esse mesmo iniciador: ele lembra os caminhos e consulta as atualizações experimentais.
5. Comece pelo título e carregue o **save normal do jogo**. Não carregue um save state: ele restaura código/memória da versão anterior.

No Windows, a imagem de teste usa o sufixo **-Duplas-Coop-Teste.rvz**. No Mac, usa um preset Riivolution. A ROM de origem permanece intacta. As configurações do aplicador ficam em uma pasta de teste separada; o Dolphin continua usando seus dados habituais e a identidade RPBE01. O aplicador não edita saves diretamente, mas o próprio jogo pode salvar progresso durante o teste. Para preservar uma cópia anterior do progresso, exporte o save do jogo pelo Dolphin antes de testar.

O iniciador está ligado ao canal experimental deste projeto. A versão normal do aplicador continua na v0.9.1-monferno; ela não inclui este cooperativo. Para voltar a ela, use o iniciador normal.

## Primeiro teste: dois controles no mesmo PC

1. No Dolphin, configure dois **Wii Remotes emulados**, cada um com um dispositivo diferente. Os controles de PS5/Xbox funcionam como dispositivos desses Wii Remotes; portas de GameCube não substituem isso neste jogo de Wii.
2. Entre em um torneio e no passe compartilhado de seis integrantes.
3. O jogador 1 escolhe dois Pokémon; solte os botões. O jogador 2 escolhe dois dos restantes. A confirmação final volta ao jogador 1.
4. O primeiro escolhido por cada um entra em campo; o segundo fica como reserva.
5. Cada um escolhe o comando, golpe, alvo e troca do seu Pokémon. Os textos principais de escolha recebem o prefixo **P1/P2**. A exibição/atualização desse prefixo ainda precisa de conferência visual.
6. Se os dois Pokémon de um jogador caírem, o parceiro pode colocar sua reserva e controlar os dois que lhe restarem. Quem perdeu os dois aguarda.
7. Ao terminar a batalha, confira que menus e progressão voltam ao jogador 1.

Não mantenha A/B pressionado ao passar a decisão: cada nova escolha exige que o jogador solte os botões. Um controle desconectado bloqueia sua escolha; reconecte e solte os botões antes de tentar novamente. Não existe substituição por IA ou uma tela própria de reconexão.

## Teste online pelo Dolphin NetPlay

Faça primeiro o teste local. Adicionar à Steam não ativa o cooperativo online por si só.

1. Os dois jogadores usam exatamente a mesma versão do Dolphin e a mesma candidata do mod. Preparem o conteúdo pelo iniciador e confiram a identidade/hash na janela de NetPlay.
2. Mantenham o jogo fechado. No Dolphin, abram **Ferramentas → Iniciar NetPlay** (o nome pode variar com a tradução).
3. O jogador 1 hospeda a imagem modificada no Windows; o jogador 2 entra com o código da sala.
4. No mapeamento da sala, atribuam **Wii Remote 1 ao anfitrião** e **Wii Remote 2 ao convidado**. Cada um configura seu controle físico no Wii Remote emulado que lhe foi atribuído.
5. Usem o mesmo save da campanha. Se a versão do Dolphin oferecer sincronização do save de Wii pelo anfitrião, ativem-na; caso contrário, preparem uma cópia idêntica do save do jogo nos dois PCs antes de iniciar. Não usem save states.
6. Iniciem pela sala NetPlay e testem uma luta completa, as substituições e o retorno ao próximo adversário.

A conexão NetPlay, sincronização/gravação do save e equivalência entre RVZ de Windows e preset de Mac **não foram verificadas nesta sessão**. O primeiro ensaio online recomendado é entre dois PCs Windows. Se a sua versão não permitir atribuir os dois Wii Remotes, registrem essa versão e a tela da sala; não tratem isso como uma conexão funcionando.

## O que precisa passar antes de chamar a versão de final

| Verificação | Resultado esperado |
|---|---|
| Início normal com save existente | Carrega campanha sem restaurar save state |
| Seleção | Dois por jogador, sem duplicados; voltar/corrigir respeita o dono |
| Comando/golpe/alvo | Só o dono avança; mirar no aliado não transfere o controle |
| Resumos e atalhos | O outro jogador não navega, confirma nem fecha a tela |
| Troca | Reserva própria viva; não entra integrante desmaiado ou já em campo |
| Substituições | Um desmaio, desmaios simultâneos e perda dos dois de cada jogador |
| Sobrevivente | Pode assumir as duas posições com seus integrantes restantes |
| Prefixo P1/P2 | Correto e legível, inclusive ao repetir o mesmo tipo de escolha |
| Fim da luta | Vitória, derrota, empate/cancelamento; menus retornam ao P1 |
| Melhor de três/sobrevivência | Preserva donos entre rodadas; encerra no resultado final |
| Campanha | Todos os coliseus, regras especiais, próximo adversário e recompensas |
| Persistência | Fechar e reabrir com o save normal mantém o progresso |
| Online | Partida completa sem divergência entre os PCs; save do anfitrião conferido |

Se falhar, anote versão do Dolphin, candidata, coliseu/rodada, ação e jogador. Uma captura da tela e o log do Dolphin ajudam a localizar a falha. Saves, RAM e ROM não precisam ser publicados no GitHub.
