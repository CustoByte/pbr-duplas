# PBR Native — launcher e primeira cena 3D

Projeto separado do aplicador Dolphin e do PBR Forge (que continua pausado).
**Agora existe uma cena 3D nativa; ainda não existe o Battle Revolution completo
portado para Windows.** Consulte [o escopo e as evidências](runtime/PROGRESS.md).

## Testar a cena no Windows

A release nativa publica `PBR-Native-Runtime-Windows.zip`. Extraia tudo e execute
`INICIAR-CENA-NATIVA.cmd`. Não precisa de Dolphin, Python ou Godot instalado.
Abra um GLB convertido localmente. Se recebeu `Mega-Lucario.glb` nesta conversa,
coloque-o junto do executável para abrir automaticamente; não publique esse modelo.
Arraste com botão direito para girar, roda para zoom, lista/botões para animações.
`Medir 10 s` salva `user-data/performance.json`. 60 FPS ainda não é garantido.

## Launcher em desenvolvimento

`INICIAR-LAUNCHER.cmd` ainda requer Python 3.11+ com Tcl/Tk. Sua distribuição
independente ainda não está implementada. O botão abre a cena nativa disponível,
não a campanha completa. O atualizador pode instalar a release nativa do GitHub.

A seleção aceita ISO Wii de Battle Revolution e RVZ, inclusive imagens modificadas.
O arquivo é apenas lido para cabeçalho e SHA-256. A escolha fica em
`user-data/source.json`: **a extração e importação dessa imagem ainda não existem**.
O identificador dentro de RVZ exige um leitor posterior; seu cabeçalho sozinho
não confirma qual jogo está dentro do contêiner. Não publique imagens ou saves.

O canal `native/update.json` na branch `project/native-launcher` é independente
de `expansion/update-test.json`. As releases têm tag imutável e SHA-256; o cliente
verifica nomes/caminhos do ZIP e prepara a instalação antes de trocar a versão.
Verifica também o executável e o PCK ao iniciar. A versão anterior pode ser
restaurada. Saves/configurações ficam fora das pastas versionadas.
Neste marco os downloads são do runtime inteiro; atualização diferencial e
a atualização do próprio launcher ainda não estão implementadas.

## Desenvolvimento e testes

- `python -m unittest discover -s native/tests -v`
- `godot --headless --path native/runtime -- --model /caminho/model.glb --self-test`
- `godot --headless --path native/runtime --export-pack Windows /destino/PBRNative.pck`
- `native/tools/package_runtime.py` gera o pacote com o Godot oficial verificado.
- O CI executa o binário Windows real com um modelo de teste criado por nós.

O exportador local de GLB usa o `.blend` privado convertido anteriormente; não
é um importador universal do jogo. A decompilação disponível é parcial e PAL,
enquanto nossa base modificada é USA RPBE01. A adaptação dos sistemas de batalha
continua sendo trabalho substancial, posterior a esta cena inicial.
