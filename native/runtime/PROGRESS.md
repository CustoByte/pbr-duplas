# Primeira cena nativa — escopo e evidências

A cena usa Godot 4.6.3, executado diretamente no sistema operacional. Não chama
Dolphin nem executa código PowerPC. Isto é uma reimplementação inicial da
apresentação 3D; não é um port completo do Battle Revolution.

## Implementado

- Leitura de GLB externo com texturas, esqueleto e animações via GLTFDocument.
- Skinning em GPU durante a renderização; ajuste inicial da câmera calcula a
  geometria da pose de espera uma única vez, pois o AABB de bind não a enquadra.
- Palco, iluminação, câmera orbital, zoom e seleção de animações.
- Transição de 0,18 segundo; corrida/espera em ciclo, ataques/dano retornam à espera.
- Indicador FPS/ms e medição de 10 segundos, com 2 segundos iniciais excluídos.
- Pacote Windows x64 independente de Python e Dolphin, com motor MIT e avisos
  de terceiros. Usa o binário oficial com editor como runtime do protótipo;
  é maior que uma futura distribuição feita com template de exportação.
- Integração do launcher com o pacote PCK e verificação de integridade de ambos.

## Verificado

O modelo privado convertido do Mega gerou GLB com três texturas, nove ações
corporais e 116 ossos. O runtime confirmou 5.976 vértices (incluindo duplicação
por materiais/UVs) e mudança real de pose dos ossos. A mesma verificação passou
com o PCK compilado que será distribuído, não apenas com os scripts soltos.

Houve renderização OpenGL real em Linux/X11 com Mesa llvmpipe, sem GPU física.
Esse teste por software serve para verificar a cena; não prova melhora de FPS
no PC do usuário. Seus resultados ficam identificados como software no relatório.
O CI de Windows usa um triângulo animado criado por nós para executar o binário
real, importador, skin e animações sem publicar o modelo privado do Pokémon.
Teste headless não comprova renderização gráfica/performance no Windows.

## Ainda não implementado

Importação automática dos recursos da ISO/RVZ, regras/IA da batalha, cenários do
jogo, menus do jogo, áudio, efeitos de golpes, Poké Balls, animações UV dos olhos,
compatibilidade com saves do Wii e atualização diferencial. O registro da imagem
modificada do launcher não equivale a importar esses sistemas.

60 FPS continua sendo uma meta a medir no PC do usuário. Uma cena de um Pokémon
não permite garantir desempenho de uma batalha completa futura.

Nenhum modelo/textura/ISO/save é publicado com o runtime. O GLB privado é
fornecido separadamente para o teste local autorizado pelo usuário.
