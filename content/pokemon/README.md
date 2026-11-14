# Catálogo compartilhado de conteúdo — entrada inicial

Este diretório registra identidade, origem verificada e decisões dos Pokémon
que deverão alimentar as versões Dolphin e nativa. **Ainda não é uma ferramenta
de sincronização ou instalação automática.** O catálogo de entrada não altera
nenhum dos dois executáveis ou canais de atualização.

O lote de 14/11/2026 contém Mega Charizard X, Ash-Greninja, Hydreigon e Rillaboom.
Os ZIPs/modelos/texturas ficam privados. O arquivo JSON contém somente metadados,
hashes e resultados de inspeção, sem atribuir IDs internos ou configurações
que o usuário ainda não escolheu. Os números nacionais são identidades oficiais;
o número `0950` nos recursos de Rillaboom não substitui seu número nacional 812.

Charizard X e Ash-Greninja trazem glTF com malhas, skin, buffers e imagens
referenciadas presentes. Não há clips de animação. Hydreigon e Rillaboom têm
uma stack FBX chamada `Take 001`, porém zero curvas e zero keyframes: o intervalo
de tempo declarado não representa animação existente. A geometria foi lida com
o ufbx 0.17.1 já utilizado no projeto. Ambos ficam dentro de quatro pesos por
vértice. Rillaboom tem corpo, cabelo, baquetas e dois tambores em cinco malhas;
essas partes não devem ser descartadas como se fossem níveis de detalhe.

A conversão precisa criar/adaptar movimentos, preservar texturas/olhos e gerar
ícones, além de verificar a integração de batalha. Movimentos e habilidades
novos não passam a existir no motor só por receberem nome ou ícone. Tough Claws
e Grassy Surge não são mecânicas nativas da quarta geração; Levitate já existe.
Battle Bond também requer definição de comportamento para uma forma Ash já
independente, sem transformação durante a batalha.

Antes de instalar um registro, será necessário confirmar o conjunto de batalha,
validar as animações e alocar os índices sem colidir com Snivy/Mega Lucario.
A futura versão nativa poderá compartilhar os recursos/configurações, mas ainda
não tem um sistema de batalha capaz de aplicar movesets ou habilidades.
