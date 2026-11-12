# Preparação local — publicação suspensa

Por instrução do usuário, nenhuma nova publicação deve ocorrer antes de
concluir a tradução de todos os textos e menus exibidos durante as batalhas.
O canal público continua na versão anterior até essa conclusão.

- Textos: lotes 1–4 aprovados e aplicados; 23 textos com 37 registros no MESG.
- Nomes: dois lotes de dez revisados. Dezenove trocas aplicadas localmente;
  Marina mantida. As oito falas que citavam Joe agora usam Pedro. Também
  atualizada a referência ao nome na classe “Joe's Groupie”.
- mes_common.fsys: 9.995 leituras verificadas com a função nativa de mensagens.
  Os IDs globais e os demais textos permanecem íntegros. As entradas de
  Sierra Leone, Crystal Colosseum, Joel e Joey foram preservadas.
- Fontes: 135 casos de métricas do arquivo de batalha passaram. Os nomes
  também foram medidos pela rotina nativa. Isso não substitui observar as
  telas e os balões no Dolphin; ainda não há validação visual desta preparação.
- Lote 5: dez falas de treinadores propostas e aguardando aprovação.

Nenhum código de batalha, modelo, time de treinador ou save foi alterado nesta
etapa de nomes. Builds completos locais usam as duas opções adicionais:

```
--original-battle-text /copia/files/menu_fight_s.fsys
--original-trainer-text /copia/files/mes_common.fsys
```

As opções juntas mantêm consistentes os nomes principais e as referências
nas falas. O aplicador público ainda não inclui esta preparação local.
