# Retratos e identificação da Snivy

Requisito do jogador: mostrar um retrato próprio da Snivy em todas as
interfaces que pedem um ícone de Pokémon, enquadrado no círculo branco
nativo, como os seis retratos do Battle Pass enviado como referência.

## Critérios de integração

- Usar a cabeça da Snivy, reconhecível em tamanho pequeno, com margem para
  não cortar olhos ou focinho; preservar a proporção da imagem.
- Preservar a moldura circular nativa e sua máscara. Não desenhar outra
  borda no retrato se a interface já fornece a borda branca.
- Conferir alfa, filtragem e bordas em fundo claro e escuro.
- Associar face e miniatura corporal próprias à espécie interna 501 nas
  tabelas de faces, corpos e ícones, sem reutilizar a identidade de Grotle
  ou Charmeleon e sem alterar retratos das espécies existentes.
- Conferir as referências masculina/feminina, mesmo sem diferença visual,
  e investigar se a interface seleciona variante shiny do retrato.
- Usar os recursos locais do jogador para produzir as imagens; não
  distribuir os recursos extraídos de PokéPark 2 no repositório público.

## Telas a conferir no Dolphin

- Passe Little Battle pronto: visualização, seleção e confirmação do passe.
- Rental Pass inicial: vaga que substitui Charmeleon, nível 50.
- Escolha da equipe, ordem de entrada e substituição durante a batalha.
- Resumo, atributos, golpes e demais telas de informações do Pokémon.
- Armazenamento e edição de passes, quando acessíveis para essa espécie.

O checklist exige capturas reais e conferência de todas as referências.
A existência deste requisito não comprova retratos instalados ou testados.
Nenhum resultado de renderização no Dolphin foi verificado nesta etapa.
