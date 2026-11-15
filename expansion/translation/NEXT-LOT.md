# Lote adicional: manter o mesmo CMD

A test.2 acrescenta 51 correções, totalizando 433 sobre Snivy test.4. Não há
traduções inéditas. Correções de controles/títulos e acentos foram revistas
contra o inglês, com 47 testes de texto e atualização. A revisão geral continua;
não pedir prints nem fornecer outro launcher como condição para corrigir.
O pacote e seu SHA estão em packages/dialogue-test2; usar o canal existente.

---

# Canal publicado — reutilizar o CMD existente

A atualização `v0.12.1-dialogue-test.1` é entregue pelo mesmo feed
`expansion/update-test.json`, em `feat/full493-waterfall`. O usuário pediu
explicitamente evitar downloads manuais e novos CMDs. Não fornecer outro
launcher; as próximas correções devem usar esse canal.

Este lote publica 382 correções existentes e 50 continuações adicionais, com
zero traduções inéditas. Continuar a revisão antes de abrir lotes novos.
A revisão global e a validação visual completa não estão concluídas.
O Forge permanece pausado e não entra nesta publicação.

---

# Atualização do pedido: revisão sem depender de prints

O usuário informou que não consegue tirar prints. Não pedir capturas como
condição para corrigir textos. Usar os arquivos originais, contexto e fontes
nativas; manter explícitos os limites da validação visual.

A revisão contextual incluiu 89 mensagens/legendas já traduzidas da Anna e dos
menus principais. Corrigir sentido, concordância, acentos, falsos cognatos e
terminologia, mesmo quando o texto antigo já cabe pela métrica. Todos os IDs
editados já diferiam do original; nenhuma tradução inédita foi iniciada.
A candidata local tem 382 correções no total e 50 continuações extras, após
aproveitar a maior página original do mesmo diálogo (mesma moldura nativa).
Há um pacote local de teste v0.12.1-dialogue-review.1, sem publicação/feed novo.
O texto e a quantidade de caracteres da tradução não equivalem à moldura real;
não declarar que todos os 2.658 alertas conservadores são defeitos visuais.

---

# Prioridade atual — revisão do que já foi traduzido

Pedido de 14/11/2026: pausar traduções inéditas e revisar o encaixe de todos os
textos existentes. O usuário apontou os menus principais e as falas da NPC do
menu como prioridade. Não retomar lotes novos antes de encerrar essa revisão.

O levantamento atual mede 10.006 IDs já alterados em quatro tabelas MESG
canônicas, sem contar suas cópias como traduções adicionais. A candidata local
prepara 382 correções e 50 continuações novas, com zero traduções inéditas.
Os nomes de Pokémon, golpes, itens, natures, habilidades e treinadores aprovados
continuam protegidos. Não reduzir fontes para ocultar estouros.

A revisão não terminou. Há 2.658 alertas conservadores de dimensão, que não
significam 2.658 falhas visuais: o tamanho do texto original não é a moldura
física de cada caixa. Títulos curtos e nomes podem superar essa referência e
caber normalmente. Não tratar esses alertas como resolvidos sem referência de
janela ou revisão contextual. Nenhum novo pacote foi publicado.

Código e plano: `ui/review_existing_layout.py`, `ui/dialogue-review-draft.json`
e `ui/dialogue-review-proof.json`. Arquivos completos do jogo e o relatório
privado detalhado ficam somente no workspace. O plano é uma candidata local e
não foi ligado ao feed dos jogadores.

---

# Continuidade após o teste 13

O usuário autorizou finalizar e publicar todas as correções dos prints.
Essa autorização substituiu a pausa anterior. Os últimos avisos de Depósito,
Passe Pessoal e Registros foram incorporados. Ver screenshot-review-test13.json.

Verificar no Dolphin os casos de TESTAR.md quando o usuário enviar o resultado.
Não afirmar que todos os menus foram visualmente testados neste ambiente.
Fonte, título, jogabilidade e arquivos de save não mudaram neste lote.

A meta anterior de 2.500 traduções inéditas não foi concluída e não deve ser
confundida com o número de correções. Textos inteiros do jogo ainda precisam
de revisão. Preservar nomes de Pokémon, golpes, itens, natures e habilidades,
e manter somente os nomes de treinadores já aprovados.

Atualização do canal: v0.12.1-dialogue-test.1 é preparada para o CMD autoatualizável já existente. Não pedir novo launcher ou ZIP manual. Nenhuma tradução inédita neste lote. A revisão geral continua.
