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

## Ainda pendente antes de instalar/publicar

Registros cumulativos de espécie/modelo/nome/retratos; ampliação dos desvios e
limites do executável para admitir 502 sem quebrar 501; substituição dirigida do
Ivysaur e entrega em saves existentes; calibração das âncoras de efeito/câmera;
inspeção contínua dos ciclos de corrida e dos ossos adicionais; visualização das
transições no jogo; testes de habilidade, golpes, menu, carregamento e batalha.
A entrada/retorno à Pokébola depende também do controle e dos efeitos nativos,
não apenas de uma animação corporal exportada.

Não instalado, não publicado e nenhum teste real de Dolphin foi realizado.

## Prévia em vídeo

`sample_video.py` amostra o SDR final decodificado, sem interpolar quadros ou
adicionar suavização. `encode_video.py` usa EGL/moderngl e ffmpeg para uma prévia
com iluminação simplificada, a 30 fps. A câmera fica fixa por trecho; os olhos
recebem um enquadramento aproximado. O MP4 privado tem 773 quadros (25,77 s),
960×720, H.264, e passou na decodificação integral. Não inclui efeitos nativos
de golpes/Pokébola e não é gravação de gameplay. Ver `video-proof.json`.
