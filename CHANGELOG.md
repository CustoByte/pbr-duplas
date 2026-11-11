# Histórico

## v0.7.1-mac

- Iniciador .command nativo, com atualização/cache e preset Riivolution.
- Sem instalação de Python, Homebrew ou DolphinTool no Mac.
- Oito testes passaram em macOS ARM64; jogo/renderização não executados nesses testes.
- Mesmos arquivos de jogo da v7, sem nova mudança nas batalhas.

## v0.7.0-experimental

- Corrige campos de espera não inicializados que bloquearam maincallback na introdução do estado enviado pelo jogador.
- Inicialização e reutilização das tarefas preservam buffers e condições de espera válidas.
- Recompressão in-place preserva tamanho e offsets de common.fsys e os demais recursos.
- Passaram 15 testes estruturais e nove suítes nativas, incluindo replay isolado da memória do travamento.
- É necessário retestar a batalha e o passe de Nate; não carregar save states anteriores.

## v0.6.0-experimental

- Aplicação automática da candidata v6 da campanha em duplas.
- Consulta de atualizações pelo GitHub e núcleo atualizável.
- Seleção inicial da pasta da ROM e reutilização dos caminhos nas próximas execuções.
- Reconstrução e conferência da RVZ, destino estável e backup da imagem anterior.
- Cache, funcionamento offline e preservação dos dados habituais do Dolphin.
- Nenhuma comprovação de gameplay ou conversão real no Windows nesta versão.
