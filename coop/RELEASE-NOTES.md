Candidata de teste do cooperativo para RPBE01 USA revisão 0. **Não é uma versão final: ainda falta validar uma partida completa no Dolphin, a campanha e NetPlay.**

O código reúne seleção de dois Pokémon por jogador, comandos/golpes/alvos pelo dono do atacante, reservas próprias, sobrevivente com duas posições, entrada nos atalhos/resumos, retorno dos menus ao P1 e prefixos P1/P2 nos prompts de batalha.

Baixe o ZIP do seu sistema, extraia tudo e abra INICIAR-COOP-WINDOWS.cmd ou INICIAR-COOP-MAC.command. Escolha a pasta da ROM original e o Dolphin na primeira vez. Use o mesmo iniciador para futuras atualizações experimentais. Inicie pelo título e carregue o save normal do jogo; não restaure save states anteriores.

Os aplicadores preservam a ROM de origem e usam a identidade RPBE01. No Windows a candidata usa outra imagem, com sufixo -Duplas-Coop-Teste.rvz; os caminhos do aplicador ficam em uma pasta de teste própria. O jogo pode salvar progresso normalmente durante os testes. Este pré-lançamento não muda o canal latest da v0.9.1-monferno.

Verificação interna: 720 seleções, 9.216 casos de legalidade de troca, 288 comparações de comando/golpe/alvo por dono, 384 entradas auxiliares, resultados nativos e prefixos. São execuções PPC isoladas com fixtures explícitas; não equivalem à inicialização/renderização do jogo ou a uma conexão online.

O projeto não está marcado como concluído. Navegação completa dos resumos, visualização/atualização dos prefixos, telas especiais, persistência, dois controles físicos e NetPlay precisam do teste manual.

Instruções completas e critérios: https://github.com/CustoByte/pbr-duplas/blob/feat/coop-input-foundation/coop/TESTAR-COOP.md

Código e relatórios: https://github.com/CustoByte/pbr-duplas/pull/1
