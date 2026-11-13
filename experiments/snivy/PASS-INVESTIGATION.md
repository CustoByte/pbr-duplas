# Entrega dos passes: investigação ainda aberta

O pedido exige um passe Little Battle pronto em uma vaga livre e a troca
de Charmeleon no Rental Pass 37 por Snivy nível 50, preservando o passe 38.
A entrega ainda não foi implementada no jogo nem habilitada no atualizador.

## Estrutura observada na captura de batalha

- Acessor `800e8594`, ponteiro base em `80453184`, passo `6ec` bytes.
- O acessor admite índices até 158: não assumir que os 39 primeiros
  representam toda a estrutura, nem que todo registro vazio é uma vaga pessoal.
- Cabeçalho/treinador: `000..1fb`; seis caixas PK4 de `8c` bytes a partir
  de `1fc`; mais dados/flags a partir de `544` até o fim do registro.
- A rotina nativa `800e6d58` inicializa identificadores/flags dos registros
  em `544`, `545`, `1ec` e `6e6`. Não foi comprovada a semântica completa
  dos bits de disponibilidade, categoria, posse e persistência.
- Na captura, o passe 37 contém Charmeleon na vaga 1, e o passe 38 contém
  o Monferno modificado. Os registros anteriores estavam sem Pokémon.

Copiar o registro inteiro de um Rental Pass para uma vaga aparentemente
vazia copiaria também flags de categoria/identificação e dados ainda não
interpretados. Não foi feita essa escrita no save ou habilitada uma
migração desse tipo como solução pronta.

## Próxima evidência necessária

Uma captura de estado do Dolphin na tela **Escolher Passe de Batalha**,
depois de carregar o save normal do jogador, permite observar a lista
de passes, suas referências, seleção e validadores ativos. As capturas
atuais de RAM foram feitas durante batalha/escolha de golpes e não contêm
uma instância ativa desse controlador de menu.

Essa captura ajuda a fechar seleção/entrega; não substitui testes posteriores
de salvar/carregar, sequência do torneio ou renderização de Snivy no jogo.
Continuam pendentes o fluxo de obtenção, a elegibilidade completa e a
integração das demais estruturas de espécie/IA antes da publicação jogável.
