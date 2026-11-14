# Correções de interface — teste 11

A fonte original oferece os acentos agudos, graves e circunflexos e cedilha,
mas não tem ã/õ/Ã/Õ. `font_ptbr.py` adiciona esses quatro glifos nas dez
fontes usando os traços nativos do til, preservando todos os glifos antigos.
O carregador original registra os glifos; `native_text.py` verifica as quarenta
combinações de letra e fonte no código PowerPC.

`layout_text.py` mantém as âncoras de alinhamento e os limites de páginas.
A reflow anterior eliminava a quebra antes do título dos botões. Os textos
identificados nas capturas têm substituições curtas em `editorial.json`.
A referência dimensional é específica à mensagem original, não a maior
janela de outra mensagem. As medidas não comprovam a moldura real na GPU.
As candidatas que excedem essa referência não entram como novas traduções.

`reviewed-test11.json` contém sobreposições em cima dos arquivos do teste 10,
com hashes de entrada/saída. `apply_review.py` permite reproduzir os textos
sem guardar arquivos originais do jogo no repositório. Fontes em branco,
nomes de itens/golpes/espécies/natures/abilities e nomes de treinadores
não aprovados continuam protegidos.

As cópias do MESG de batalha em mes_fight_e, mes_bpass_e e menu_bpass2,
e as de nomes/formulários em menu_name2, recebem o mesmo recurso traduzido.
Essas cópias NÃO contam novamente como traduções novas.

O título usa somente a textura nítida de 514×70 no recurso 0x21320400,
cabeçalho 0x180. Nenhum vértice, animação ou código de entrada foi alterado.
A arte aprovada foi exportada para RGB5A3; o patch depende do title.fsys
original. O instante exato em relação ao aviso de botão ainda exige Dolphin.

O teste no Dolphin, inclusive renderização, salvamento e carga real de
arquivos, permanece necessário. Uma captura de RAM não substitui esse teste.

## Teste 13 — revisão dos prints

`screenshot-review-test13.json` é uma sobreposição com hashes sobre o teste 12.
`apply_screenshot_review.py` reproduz o arquivo sem mudar os comandos existentes.
As quebras antes de comandos de alinhamento são restauradas, incluindo linhas
em branco intencionais; novos títulos não são re-centralizados na mesma linha.
O aviso 8442 usa recuo com espaços medidos na fonte, dentro da extensão do texto
original. Nenhuma âncora de desenho é mudada para centralizar esse aviso.

`verify_screenshots.py` verifica as telas relatadas, proteção de nomes, natures,
campos e glifos. `help-caption-test13.json` documenta as outras mensagens similares
encurtadas e medidas. Esses testes não substituem a conferência da posição
real das caixas no Dolphin. O source builder aplica a sobreposição após o lote
anterior; o aplicador público continua distribuindo apenas patches diferenciais.


## Revisão global de diálogos — em andamento

`review_existing_layout.py` examina todos os IDs já diferentes do original nas
quatro tabelas canônicas e sincroniza as cópias de batalha/nomes nos menus.
Não traduz IDs ainda intactos. As comparações usam fontes e rotinas nativas.
A candidata é reproduzida por `apply_dialogue_review.py` usando SHA por arquivo
e por linha. Não há mudanças em DOL, modelos, regras, equipes ou saves.

`dialogue_layout.py` permite novas continuações somente para diálogos comuns
que já usam o protocolo interativo (`000D` ou `0067`), sem grades, escolhas ou
alinhamento fixo. O despacho de `000D` e `0067` chega às rotinas equivalentes
`80160a18`/`80160a10`. O replay de avanço verifica até 16 páginas; simula apenas
o botão, sem substituir o avanço ou reset do texto. Isso não é teste de GPU
nem de todos os consumidores das mensagens.

As novas páginas mantêm as palavras e a ordem dos parâmetros. O caso de NPC
com fala ativa repete somente o par de fechamento/retomada `0028/0027` em cada
novo limite, conforme o padrão original. Fontes, alinhamento e variáveis não
são duplicados. Nomes compostos são mantidos juntos. A distribuição prefere
limites de frases e evita páginas finais quase vazias.

Caixas fixas não recebem páginas automaticamente. `dialogue_editorial.py` e
`dialogue-menu-editorial.json` contêm reformulações explícitas de descrições
existentes, mantendo mecânicas, números, negações e nomes. Apenas resultados
que cabem na referência revisada entram na candidata; outros ficam pendentes.

O levantamento verificou 10.006 IDs alterados e preparou 382 correções, com
50 continuações adicionais. A revisão permanece incompleta: 2.658 alertas
conservadores ainda dependem de contexto ou da moldura real. São alertas, não
uma contagem comprovada de defeitos visuais. `dialogue-review-draft.json` não
é uma aprovação de publicação e não modifica o canal dos jogadores.


### Revisão contextual da recepcionista e dos menus

O usuário não consegue enviar prints; a revisão continua pelos dados existentes.
`dialogue-menu-editorial.json` agora inclui 89 alvos já traduzidos, revisados
contra o inglês. Foram corrigidos erros como “Treinadores” virar “tênis”, “clear”
virar “limpar”, concordância da Anna, trechos misturados e nomes de menus
inconsistentes. “Gear” passa a “Roupas”, em vez de “Engrenagem”, tanto na opção
quanto na explicação da NPC. Nomes de Pokémon/golpes/itens/natures/habilidades
não são traduzidos.

A capacidade de páginas de uma mensagem interativa pode usar a maior página
original **da mesma mensagem**, pois o avanço nativo mantém a mesma moldura e
as coordenadas. Não herda dimensões de um menu diferente. O nome do jogador
`0050` também recebe o cenário conservador de largura no medidor nativo.

Uma legenda fixa explicitamente revisada (`7076`) pode aceitar uma correção
mais curta que a tradução antiga, com controles e altura preservados, mesmo
quando a referência literal inglesa é menor. O status registra
`reviewed-no-size-increase`, sem fingir uma moldura física medida.

`package_dialogue_review.py` gera um pacote local do aplicador, reaproveitando
o núcleo Snivy test.4 e substituindo apenas deltas de mensagens. Confere o
roundtrip de todos os 13 arquivos da base; DOL, common, deck, título, catálogo,
modelo/animações/ícones e nomes da Snivy não mudam. Não publica no GitHub nem
atualiza o feed dos jogadores. A revisão geral permanece em andamento.

Atualização do canal: v0.12.1-dialogue-test.1 é preparada para o CMD autoatualizável já existente. Não pedir novo launcher ou ZIP manual. Nenhuma tradução inédita neste lote. A revisão geral continua.
