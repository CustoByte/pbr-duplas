# Conjunto solicitado e estado da implementação

## Definição

Bullet Punch (418), Close Combat (370), Aura Sphere (396), Protect (182),
Adaptabilidade (91), nenhum item. O destino solicitado é o lugar do Ivysaur (2)
no passe inicial de nível 50, preservando Lucario normal e Snivy.

Treino proposto: natureza neutra Hardy, IVs 31, EVs HP 4 / Ataque 128 / Ataque
Especial 128 / Velocidade 248, total 508. Mantém os atributos base oficiais.
Atributos calculados: HP 146, Atk 181, Def 108, SpA 176, SpD 90, Speed 163.
Não há ainda prova de equilíbrio em gameplay. `battle_set.py` valida o conjunto.

## Conversão realizada

A falha do binding Python ufbx foi contornada com um leitor C independente,
`read_source.c`, ligado à biblioteca MIT ufbx v0.17.1. Não alteramos artificialmente
a versão do FBX. O intermediário, as imagens, os arquivos Blender e o SDR ficam
no diretório privado de trabalho, fora do repositório público.

- `import_source.py`: preserva os 4.757 vértices e 9.198 triângulos, UVs por canto,
  três materiais, 99 ossos e os pesos originais (máximo quatro por vértice).
  Compara as matrizes de bind e a deformação na pose de repouso.
- `import_native.py`: importa o Lucario fornecido como doador. Preserva as ações
  no arquivo Blender e produz o inventário do contrato nativo.
- `retarget_native.py`: adapta nove ações corporais. A cintura do Mega tem ramos
  separados para quadril e tronco; o pivô `center` do Lucario não corresponde ao
  repouso de `Waist`. As proporções do Mega são mantidas e os ossos adicionais
  herdam os movimentos dos pais. As ações de recuperação voltam à espera por
  smoothstep, reutilizando o princípio empregado na Snivy.
- `export_candidate.py`: usa o mesmo exportador PBR e armazenamento de trilhas
  compactas da Snivy. Corrige a conversão quaternion/XYZ perto de gimbal lock,
  que introduzia erro no desmaio. Quantiza as trilhas para cinco casas decimais;
  essa mudança só é aceita depois da comparação de matrizes e vértices.
  Adiciona âncoras por nome e trilhas independentes dos olhos.
- `verify_candidate.py`: decodifica o SDR e compara matrizes, vértices deformados
  e pixels das texturas, fora do jogo. Foram conferidos 138 quadros distribuídos
  pelas nove ações, incluindo todos os quadros de espera e dano.
- `verify_materials.py`: verifica ordem e flags das 12 ações, dimensões das
  texturas, recuperação completa e 7.944 amostras escalares dos UVs serializados.
- `render_portraits.py`: gera rosto e corpo normais a partir do modelo adaptado.
  O rosto foi conferido no círculo branco com `icon_textures.face_tile`, o mesmo
  método da Snivy. Não foi inventada uma variante shiny.

O candidato final tem 2.364.904 bytes, abaixo do limite de 3 MiB usado na receita
Snivy. O primeiro candidato tinha aproximadamente 3,6 MB; a redução ocorreu nas
trilhas, sem cortar geometria. Os relatórios em `*-proof.json` correspondem ao
SDR final. São provas offline, não testes de Dolphin.

## Dependências do leitor C

Compilação: `gcc -O2 -I DIRETORIO_UFBX read_source.c DIRETORIO_UFBX/ufbx.c -lm -o read_source`.
Fonte externa: https://github.com/ufbx/ufbx/tree/v0.17.1 (MIT).
SHA-256 de `ufbx.h`: `d2e3a7038f81fe8742705bff96e9c072222bd14bef85a97fa778fa858835d07e`.
SHA-256 de `ufbx.c`: `a6663d3be07e68b6b4b4fbca692e21a7449097f60b83fdc2b634f00b16d50315`.
A biblioteca não é incluída nesta pasta. Os scripts Blender documentam seus
argumentos; usar Blender 3.3.21 e o exportador já configurado para a Snivy.

## Integração cumulativa — candidata test.1

`registrations.py` acrescenta a espécie interna 502 (nacional 448, forma Mega),
modelo 671, arquivo 8193, nome global 21776 e retratos independentes. As linhas
originais e a Snivy permanecem byte a byte. A evolução fica vazia e o learnset/TMs
herdam o Lucario. Os quatro golpes solicitados são entregues pelo construtor nativo.

`runtime_layer.py` reserva 0x8064c000..0x80652000 por meio do arena clamp existente.
Acrescenta caminhos seletivos para 502 nos limites de menu, nomes, previsão,
narrador e câmera. A câmera inicial usa a linha do Lucario normal. Os três
caminhos de áudio mapeiam apenas o novo índice para o banco de grito 448;
o narrador mantém a proteção de tabela, sem inventar um nome falado.

`pass_delivery.c` encadeia o accessor existente da Snivy. Troca apenas o Ivysaur
nível 50 do passe 37, slot 0, por Mega. Mantém o slot 1 da Snivy e o passe Little.
A entrega é idempotente e só ocorre com todas as tabelas e catálogo registrados.
O construtor do mod anterior força aparência shiny nas identidades dos passes
iniciais e adiciona 10% ao maior atributo. Somente a nova espécie usa o predicado
PID/OT nativo e nasce normal, para respeitar os atributos combinados. Todas as
espécies antigas mantêm sua política de aparência/bônus. Shiny natural do Mega
continua podendo receber o bônus, mas reutiliza a arte normal nesta candidata.

`native-proof.json`: construção, quatro golpes/PP, habilidade, item, natureza,
IVs, EVs, atributos, presença/validade e segunda chamada sem reset. Confirma também
as duas Snivy. Trabalha sobre cópia privada da memória, sem escrever saves.
`runtime-proof.json`: 90 casos de limites de menu, 21 casos de banco de grito,
504 nomes legados, previsão segura e lookup nativo dos quatro recursos gráficos.
`loading-proof.json`: os modelos Snivy e Mega foram alocados e relocados juntos
pelas rotinas nativas, sem sobreposição, e o Mega retornou pronto. A fixture
reaponta um descritor FSYS capturado; não prova DVD I/O ou upload na GPU.
`selection-proof.json`: seleção e empacotamento nativos dos quatro Pokémon em
uma fixture reconstruída de UI solo, incluindo Mega e Snivy. Não é UI real.

O instalador Windows mantém o mesmo atualizador. Faz Snivy primeiro e Mega depois,
acrescentando os retratos sem perder os anteriores. Pede o ZIP aprovado uma vez,
lembra seu caminho, usa cache validado e reutiliza o SDK Blender da Snivy.
`convert_local.py` foi executado integralmente no Linux com os arquivos privados.
O leitor Windows x64 foi compilado a partir do mesmo C e ufbx MIT; não foi
executado no Windows neste ambiente. Os testes reais de PowerShell usaram
fixtures para imagens/conversão, verificando ordem, falhas e preservação de save.

Ainda é necessário testar a batalha real no Dolphin Windows, efeitos/câmera,
entrada/retorno à Pokébola, transições e save/load pelo próprio jogo. Isso não
impede disponibilizar a candidata experimental, mas não equivale a gameplay
completo validado. Nenhum save ou imagem original é alterado pelo instalador.

## Prévia em vídeo

`sample_video.py` amostra o SDR final decodificado, sem interpolar quadros ou
adicionar suavização. `encode_video.py` usa EGL/moderngl e ffmpeg para uma prévia
com iluminação simplificada, a 30 fps. A câmera fica fixa por trecho; os olhos
recebem um enquadramento aproximado. O MP4 privado tem 773 quadros (25,77 s),
960×720, H.264, e passou na decodificação integral. Não inclui efeitos nativos
de golpes/Pokébola e não é gravação de gameplay. Ver `video-proof.json`.

## Correção do pacote test.2

O pacote test.1 omitia `expansion/translation/messages.py`, importado na montagem
final dos assets. A reprodução a partir do ZIP publicado, com PYTHONPATH limpo,
confirmou `ModuleNotFoundError: No module named translation`. O empacotador agora
inclui esse módulo. A checagem de publicação importa os registros dentro de uma
extração isolada do pacote, impedindo que arquivos da checkout ocultem dependências
ausentes. Um teste de regressão confirma a falha do ZIP antigo e o sucesso do novo.
Falhas fora das etapas Blender também são gravadas em `conversion-failure.log`
e o instalador apresenta o detalhe e o caminho do log. Localizar o modelo em
Downloads não causa essa falha. As configurações do personagem não mudaram.
