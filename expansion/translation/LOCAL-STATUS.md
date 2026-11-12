# Preparação local — publicação suspensa

Por instrução do usuário, nenhuma nova publicação deve ocorrer antes de
concluir a tradução de todos os textos e menus exibidos durante as batalhas.
O canal público continua na versão anterior até essa conclusão.

- Textos: lotes 1–9 aprovados e aplicados; 73 textos. São 87 registros diretamente
  revisados e 75 repetições exatamente iguais reaproveitadas, além das oito
  referências de nomes: 170 mensagens alteradas no arquivo de batalha.
- Nomes: dois lotes de dez revisados. Dezenove trocas aplicadas localmente;
  Marina mantida. As oito falas que citavam Joe agora usam Pedro. Também
  atualizada a referência ao nome na classe “Joe's Groupie”.
- mes_common.fsys: 9.995 leituras verificadas com a função nativa de mensagens.
  Os IDs globais e os demais textos permanecem íntegros. As entradas de
  Sierra Leone, Crystal Colosseum, Joel e Joey foram preservadas.
- Fontes: 510 casos de métricas do arquivo de batalha passaram. Os nomes
  também foram medidos pela rotina nativa. Isso não substitui observar as
  telas e os balões no Dolphin; ainda não há validação visual desta preparação.
- Lote 5: dez falas de treinadores aprovadas e aplicadas localmente.
- Lote 6: dez novas falas aprovadas e aplicadas localmente.
- Lote 7: dez novas falas aprovadas e aplicadas localmente.
- Lote 8: dez novas falas aprovadas e aplicadas localmente.
- Lote 9: dez novas falas aprovadas e aplicadas localmente.
- Lote 10: vinte novas falas propostas e aguardando aprovação.
- Preferência atual: revisar vinte textos por lote a partir do lote 10.

Nenhum código de batalha, modelo, time de treinador ou save foi alterado nesta
etapa de nomes. Builds completos locais usam as duas opções adicionais:

```
--original-battle-text /copia/files/menu_fight_s.fsys
--original-trainer-text /copia/files/mes_common.fsys
```

As opções juntas mantêm consistentes os nomes principais e as referências
nas falas. O aplicador público ainda não inclui esta preparação local.

## Autorização mais recente e trabalho em andamento

O usuário delegou a tradução restante sem revisão de cada lote e autorizou
publicar no GitHub somente quando a tradução completa estiver pronta.
A restrição confirmada é traduzir descrições compartilhadas somente durante
as batalhas; fora delas, devem continuar no idioma original.

- Lote 10: vinte textos aprovados e aplicados; total humano de 93 textos.
- Mensagens de uso de golpes: todas as 1.401 variantes preparadas e medidas,
  preservando os 467 nomes de golpes.
- Build local atual: 1631 mensagens de batalha alteradas; 4893 casos de fonte passaram.
- Falas: 2.028 rascunhos automáticos coletados, ainda NÃO aplicados; precisam
  de revisão de contexto, terminologia e ajuste às medidas dos balões.
- A publicação ainda NÃO está pronta. O isolamento das descrições comuns
  dentro da batalha NÃO foi implementado nem testado.

Pesquisa para a separação: inicialização da UI de batalha em 0x8005EA98 e
limpeza em 0x8005F1DC; avaliar uma flag própria e redirecionamento dos IDs
comuns para cópias traduzidas anexadas ao MESG da batalha. Preservar a busca
nativa fora da batalha e a lógica de texto dos bônus shiny. Os endereços
foram inspecionados, mas nenhum novo hook foi aplicado.
