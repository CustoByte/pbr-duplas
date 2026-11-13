# Estado da integração Snivy — 13/11/2026

**Código experimental; não é uma atualização jogável.**

O canal usado por `INICIAR-TESTE-WINDOWS.cmd` continua em
`v0.11.0-full493-test.13`. Publicar este código em uma branch não altera
o feed nem instala Snivy pelo CMD. O mesmo CMD poderá receber a integração
quando um pacote completo for construído e o feed for atualizado.

## Verificado fora do Dolphin

- Índice interno 501, sem substituir Egg/Bad Egg, formas ou espécies 1–493.
- Atributos oficiais, construção nativa de Pokémon nos níveis 5 e 50,
  Timid, Overgrow, Lum Berry e leitura dos golpes/PP.
- Construção com os oito perfis nativos de dificuldade do Sunny Park.
- Conjunto nível 50: Energy Ball / Glare / Leech Seed / Protect;
  HP121, Atk58, Def75, Speed126, SpAtk97, SpDef75, sem bônus shiny.
- Cadastro de arquivo independente, mantendo 1.102 entradas anteriores;
  busca nativa do novo ID e restauração do catálogo original.
- Conversão experimental de geometria, 12 ações e UVs. Os relatórios
  gráficos anteriores descrevem os limites de cada prova.
- Sete testes de estrutura/identidades e validação do catálogo.

## Implementação restante antes de empacotar

- Registro completo de nome, modelo, ícones e limites de espécie no motor.
- Retratos próprios dentro da moldura branca em todas as interfaces.
- Entrega de um Passe Little Battle pronto em uma vaga vazia, sem perda
  de passes anteriores; seleção, elegibilidade e persistência.
- Migração da vaga Charmeleon do Rental Pass 37 para Snivy nível 50,
  preservando o Monferno do passe 38 e os demais dados do jogador.
- Integração das variantes visuais, bônus shiny e restauração de item.
- Calibração de pontos de efeito, deslocamento, eventos e interpolação;
  o SDR experimental de cerca de 8 MB ainda precisa de avaliação de memória.
- Conversão local a partir dos recursos próprios do jogador; os recursos
  derivados de PokéPark 2 não serão incluídos na publicação pública.

## Validação final necessária

Não há imagem completa do jogo nem Dolphin instalado neste ambiente.
As capturas de RAM permitem executar funções PPC isoladas, mas não
substituem inicialização do jogo, renderização ou gravação real do save.
Após completar a implementação, ainda é necessário testar esses caminhos
no Dolphin com a cópia local do jogador, incluindo seleção, ataques,
impactos, retorno à Poké Ball, derrota, troca e salvar/carregar.

**Não gerar uma release jogável nem avançar o feed a partir desta etapa.**
Os arquivos aqui preparados ainda não satisfazem o pedido completo.
