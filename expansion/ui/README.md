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
