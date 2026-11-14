# PBR Native — primeira base do launcher

Projeto separado do aplicador Dolphin e do PBR Forge, que permanece pausado.
**Ainda não há motor nativo, cena 3D ou batalha jogável.** O launcher não converte
PowerPC/GX em código Windows, nem representa uma otimização medida do jogo.

## Executar a base no Windows

Requer Python 3.11+ com Tcl/Tk. Execute `INICIAR-LAUNCHER.cmd`.
A distribuição independente do Python ainda não está implementada.

A seleção aceita ISO Wii de Battle Revolution e RVZ, inclusive imagens modificadas.
O arquivo é apenas lido para verificar cabeçalho e calcular SHA-256. A escolha fica
registrada em `user-data/source.json`, com caminho e hash: **nenhum recurso é extraído
nesta etapa**. O identificador de jogo dentro de RVZ exige um leitor posterior;
o cabeçalho RVZ sozinho ainda não confirma qual jogo está dentro do contêiner.
Não distribua imagens, recursos ou saves no GitHub.

O canal nativo usa `native/update.json` na branch `project/native-launcher`.
É independente de `expansion/update-test.json`: não altera a versão Dolphin atual.
Nesta primeira etapa o manifesto declara explicitamente que não há runtime.
Quando existir, um pacote Windows será publicado em uma tag imutável deste mesmo
repositório com SHA-256. O cliente verifica o hash, valida os caminhos do ZIP,
prepara uma pasta de versão e só então troca o ponteiro da versão ativa.
A versão anterior pode ser restaurada. Saves/configurações ficam fora das releases.
O formato inicial instala um runtime inteiro; downloads diferenciais e atualização
do próprio launcher ainda não estão implementados.

## Próximo marco: cena nativa mensurável

- Definir e implementar a leitura local dos recursos da imagem selecionada,
  preservando as alterações presentes nela e registrando incompatibilidades.
- Renderizar uma cena com modelo e animação em Windows sem Dolphin; não substituir
  isso por vídeo pré-renderizado ou por abrir o emulador de forma oculta.
- Medir tempo de quadro, carregamento e memória, com simulação e apresentação
  desacopladas. 60 FPS é uma meta ainda não verificada.
- Depois incorporar regras de batalha, efeitos, interface e áudio. A decompilação
  disponível é parcial e mira PAL; nossa base modificada é USA RPBE01. Isso exige
  adaptação e não oferece hoje um port Windows pronto.

## Testes

`python -m unittest discover -s native/tests -v`

Os testes verificam registro somente para leitura, recusa de caminhos inseguros,
falha de hash sem trocar a versão ativa e recuperação da versão anterior.
A interface precisa de validação visual no Windows.
