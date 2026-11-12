# Pokémon Battle Revolution — campanha em duplas

[Histórico da conversa e contexto para continuar em outro computador](historico/conversa-2026-11-11.md). A exportação de 11/11/2026 é parcial: as respostas antigas que não puderam ser recuperadas estão sinalizadas no arquivo.

Aplicador experimental para Windows 10/11 e macOS 12+. Utiliza sua imagem original USA **RPBE01, revisão 0** e o DolphinTool de uma instalação recente do Dolphin. Este repositório não contém a imagem completa do jogo nem saves.

[**Baixar o aplicador para Windows**](https://github.com/CustoByte/pbr-duplas/releases/latest/download/PBR-Duplas-Aplicador-Windows.zip)

**Novidade — v0.9.1-monferno:** Monferno do passe de Nate recebe natureza Adamant, Fire Punch, Mach Punch, Blaze Kick, Close Combat e Lum Berry. Funciona também com a campanha existente; a Berry é consumida durante a luta e volta na preparação da próxima. Para atualizar, feche o Dolphin e abra o mesmo aplicador Windows/Mac com internet. [Detalhes e verificações](MONFERNO.md).

O efeito shiny nos dois passes iniciais e a campanha em duplas permanecem ativos. [Detalhes do efeito shiny da v8](SHINY-PASSES.md).

## Usar

1. Extraia todo o ZIP e abra **INICIAR-WINDOWS.cmd**.
2. Na primeira execução, escolha a pasta da sua ISO/RVZ original e, se solicitado, `Dolphin.exe`.
3. Aguarde: o aplicador monta e confere uma nova RVZ e inicia o jogo no Dolphin.

Use uma versão recente do [Dolphin oficial](https://dolphin-emu.org/download/), incluindo `DolphinTool.exe` e suas DLLs. Reserve aproximadamente **5 GB livres**. Não é necessário instalar Python, digitar comandos ou substituir arquivos manualmente.

## Atualizações e save

Nas próximas execuções, o aplicador lembra os caminhos, consulta a versão publicada neste GitHub e baixa um único pacote quando houver atualização. Refaz a cópia modificada a partir da original, confere os arquivos e substitui o destino gerenciado. Mantém um backup da imagem modificada anterior. Sem novidades, abre a cópia existente sem reconstruí-la; sem internet, utiliza o último pacote disponível localmente.

O aplicador não permanece em segundo plano: a consulta ocorre ao abrir `INICIAR-WINDOWS.cmd`. Abrir a RVZ diretamente pula a consulta. O núcleo do aplicador também é atualizado por esse canal, sem exigir outro download manual do ZIP inicial.

O original fica intacto. Caminhos e estado ficam em `%LOCALAPPDATA%\PBR-Duplas`; nenhum jogo, caminho local ou save é enviado ao GitHub. O Dolphin usa seus dados habituais e a mesma identificação RPBE01. O aplicador não escreve no save. Alterações futuras do jogo ainda precisam respeitar a compatibilidade desse save antes de serem publicadas.

## Estado da versão

A candidata v9 mantém a campanha em duplas da v7 e o efeito shiny da v8, acrescentando o conjunto de Monferno descrito acima. **Não inclui cooperativo online.** As regras especiais, batalhas e persistência real ainda exigem teste no jogo.

Passaram 23 testes dos scripts em PowerShell 7/Linux com imagens artificiais, feed local e uma ferramenta simulando o DolphinTool. Incluem atualizações sucessivas, cache/offline, caminhos com espaços/acentos, adição/remoção de arquivos, falhas, backup e abertura simulada. A interface Windows/PowerShell 5.1 e a conversão de imagens reais não foram executadas nesse ambiente. A conferência de arquivos é distinta da validação de gameplay. Veja [VERIFICACAO.json](VERIFICACAO.json).

O código está em [src](src). O pacote publicado inclui os dois arquivos de jogo modificados e seus hashes. Instruções e diagnóstico em [COMO-USAR.txt](COMO-USAR.txt).

## Canal de distribuição

O bootstrap consulta `releases/latest/download/update.json`. O manifesto publica versão, URL do núcleo e SHA-256. O pacote é baixado por HTTPS e conferido antes da extração. Somente lançamentos publicados são distribuídos; alterações de trabalho e commits isolados não chegam aos jogadores.

Para uma atualização, preparar e verificar o núcleo, atualizar o manifesto e publicar os assets do novo lançamento juntos. Manter o formato do manifesto compatível com o bootstrap e a mesma identidade do jogo para continuar usando o save.

A primeira publicação foi conferida por download público: manifesto, núcleo e ZIP inicial coincidem byte a byte com os artefatos locais. O bootstrap distribuído também consultou o canal HTTPS real, baixou e verificou o núcleo e entregou a execução ao aplicador. Esse teste parou intencionalmente na validação de uma imagem ausente; não executou o jogo. Registro em [PUBLICACAO.json](PUBLICACAO.json).

## Correção da introdução na v7

Um estado de travamento enviado pelo jogador permitiu identificar `maincallback` bloqueado antes de executar: tipo de espera 2, índice 138 (fora dos 16 índices válidos), valor esperado 357088. O reset nativo de tarefas não limpava esses campos. A v7 inicializa o objeto completo na construção e limpa a condição de espera ao reutilizar uma tarefa, preservando os buffers alocados e o comportamento de esperas válidas.

No replay isolado da memória capturada, a v6 mantém o callback bloqueado e o indicador de liberação em zero; a v7 executa o callback até o fim e coloca o indicador em um. Passaram 285 casos de reset com memória suja, dois de construção e 96 comparações de esperas ativas. A única chamada de script substituída nesse replay é a impressão de diagnóstico; a alocação é substituída apenas nos testes de construção. Duas instruções de contexto paired-single são puladas no harness de CPU escalar. Veja [CORRECAO-INTRODUCAO-v7.json](CORRECAO-INTRODUCAO-v7.json). Não é uma continuação completa no Dolphin.

A tabela modificada agora é recomprimida no slot original: common.fsys mantém o tamanho de 441.664 bytes, todos os offsets e os demais recursos comprimidos. A tabela passa de 1.179 para 1.146 bytes comprimidos. As tabelas de modelos/personagens permanecem idênticas; a aparência de Nate e dos demais personagens ainda precisa de conferência visual no jogo.

**Após atualizar, inicie normalmente e carregue o save da campanha. Não carregue um save state da v6: ele restaura o código e a memória antigos.** O arquivo enviado pelo jogador e a memória extraída permanecem privados e não estão neste repositório. Os verificadores e o compressor estão em [mod-source](mod-source); o replay exige o estado privado correspondente.

## Mac: iniciar com dois cliques

[**Baixar o iniciador para Mac**](https://github.com/CustoByte/pbr-duplas/releases/latest/download/PBR-Duplas-Aplicador-Mac.zip). Extraia tudo, feche o Dolphin e abra **INICIAR-MAC.command**. Na primeira vez, escolha a pasta da ISO/RVZ USA RPBE01 revisão 0 e Dolphin.app, se solicitado. Depois use o mesmo iniciador para consultar atualizações e jogar.

O Mac usa o suporte Riivolution do próprio Dolphin para carregar os mesmos `main.dol` e `common.fsys` da v7 sobre a imagem original. Não extrai nem regrava a ROM e não requer Python, Homebrew ou DolphinTool. Mantém a identidade RPBE01 e inicia o Dolphin com seus dados habituais, sem redirecionar o save. Os caminhos e o preset ficam em `~/Library/Application Support/PBR-Duplas`. Abrir a ROM diretamente pula o mod; utilize o iniciador ou o preset gerado.

Os oito testes nativos passaram em macOS 15.8.2 ARM64: ferramentas do sistema, atualização, cache/offline, preservação do original, cabeçalhos de ISO/RVZ, hash, bloqueio de caminhos externos e geração do descritor JSON. Os cabeçalhos de imagem e o aplicativo nos testes são fixtures. Os diálogos interativos, o lançamento real do Dolphin e uma batalha não foram executados nesses testes. Veja [VERIFICACAO-MAC.json](VERIFICACAO-MAC.json).

A versão de distribuição v0.7.1-mac acrescenta o iniciador Mac ao pacote; os arquivos de jogo permanecem exatamente os da correção v7. Os iniciadores Windows existentes continuam usando o mesmo canal e o mesmo manifesto do mod.
