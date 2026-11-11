# Pokémon Battle Revolution — campanha em duplas

Aplicador experimental para Windows 10/11. Utiliza sua imagem original USA **RPBE01, revisão 0** e o DolphinTool de uma instalação recente do Dolphin. Este repositório não contém a imagem completa do jogo nem saves.

[**Baixar o aplicador para Windows**](https://github.com/CustoByte/pbr-duplas/releases/latest/download/PBR-Duplas-Aplicador-Windows.zip)

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

A candidata v6 modifica seleção/formato de campanha e limites de equipes/séries para duplas com quatro Pokémon. **Não inclui cooperativo online.** As regras especiais, batalhas e persistência real ainda exigem teste no jogo.

Passaram 23 testes dos scripts em PowerShell 7/Linux com imagens artificiais, feed local e uma ferramenta simulando o DolphinTool. Incluem atualizações sucessivas, cache/offline, caminhos com espaços/acentos, adição/remoção de arquivos, falhas, backup e abertura simulada. A interface Windows/PowerShell 5.1 e a conversão de imagens reais não foram executadas nesse ambiente. A conferência de arquivos é distinta da validação de gameplay. Veja [VERIFICACAO.json](VERIFICACAO.json).

O código está em [src](src). O pacote publicado inclui os dois arquivos de jogo modificados e seus hashes. Instruções e diagnóstico em [COMO-USAR.txt](COMO-USAR.txt).

## Canal de distribuição

O bootstrap consulta `releases/latest/download/update.json`. O manifesto publica versão, URL do núcleo e SHA-256. O pacote é baixado por HTTPS e conferido antes da extração. Somente lançamentos publicados são distribuídos; alterações de trabalho e commits isolados não chegam aos jogadores.

Para uma atualização, preparar e verificar o núcleo, atualizar o manifesto e publicar os assets do novo lançamento juntos. Manter o formato do manifesto compatível com o bootstrap e a mesma identidade do jogo para continuar usando o save.
