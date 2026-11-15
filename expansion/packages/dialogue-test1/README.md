# Correções de diálogos — v0.12.1-dialogue-test.1

Entrega pelo CMD autoatualizável existente, no mesmo canal `full493-test`.
Não é necessário baixar outro launcher. O pacote contém código/deltas próprios;
modelos, texturas, ROMs e saves não são distribuídos.

São 382 correções em textos já traduzidos, incluindo 89 alvos revisados por
contexto e 50 continuações adicionais. Nenhuma tradução inédita. Corrige
terminologia, acentos, concordância e erros como “PIKACHU Fan” → “Ventilador”.
Os exemplos corretos são “Fã de PIKACHU” e “exausto” para “you're beat” no
comentário sobre uma sequência de vitórias.

A base Snivy test.4 é preservada: executável, dados de batalha, título, catálogo,
modelo/animações/ícones e passes não mudam. O cache gráfico existente pode ser
reutilizado. A imagem original e os saves não são modificados pelo aplicador.

Validação: 46 testes de texto/atualizador, roundtrip dos 13 deltas com originais
locais, igualdade de recursos não textuais e de cópias MESG, avanço nativo
com entrada simulada e registro dos 40 glifos de til. A revisão global continua;
não há validação visual completa desta revisão no Dolphin. Os alertas de
referência textual não equivalem a defeitos comprovados nas caixas reais.
