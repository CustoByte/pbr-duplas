# Full493, Waterfall, shinies e chefes — candidata para teste

Implementação local compilada e verificada em rotinas nativas PowerPC de RPBE01
USA revisão 0. **Ainda precisa de testes reais no Dolphin**, incluindo finalizar
Waterfall, trocar no Gateway, salvar/carregar e conferir a apresentação visual.

Esta entrega é da campanha single-player em duplas. O protótipo cooperativo tem
seu canal separado; a seleção cooperativa 2+2 ainda não cobre o Waterfall de seis.

## Alterações incluídas

- Tradução **parcial** pt-BR: lotes 1–10 aprovados e todas as 1.401 mensagens
  de uso de golpes, preservando os 467 nomes de golpes. São 1.631 registros
  alterados no arquivo de batalha, contando repetições e referências de nomes.
  Dezenove nomes de treinadores escolhidos foram aplicados; Marina fica igual.
  As buscas nativas e medições de fonte passaram; a aparência real no Dolphin
  ainda precisa de teste. As falas em rascunho e a tradução das descrições
  compartilhadas apenas durante a batalha **não estão incluídas**.
- Poké Coupons ilimitados: saldo de 999.999, disponível mesmo em saves
  existentes e mantido após compras. Estoque, desbloqueios e inventário usam
  as regras originais. Testadas 72 compras pela rotina nativa; a loja real e
  salvar/carregar ainda precisam ser conferidos no Dolphin.
- 493 espécies alcançáveis nos pools variáveis compatíveis, inclusive no rank
  final repetível. Registros originais, treinadores, IA e regras de nível
  preservados; seis pools ampliados e listas internas aumentadas para 2048.
- Little Battle mantém os pools e suas restrições originais.
- Waterfall: seis escolhidos em ordem; duplas 1–2, 3–4 e 5–6, melhor de três.
  Só dois Pokémon são enviados à batalha por rodada. Rotação, resultados e
  desempates reaproveitam a rotina original. Outros coliseus continuam com quatro.
- Trade Battle mantém desbloqueio, elegibilidade, uma troca e armazenamento
  originais. As transferências em memória foram testadas; a persistência em
  save ainda precisa de confirmação em jogo.
- Shinies por Pokémon adversário gerado: **3 / 3,28 / 3,57 / 3,85 / 4,14 /
  4,42 / 4,71 / 5%** nos ranks 1 a 8. Masters usam o conjunto escolhido;
  Survival acompanha suas faixas nativas de dificuldade, chegando a 5% no topo.
- Shiny recebe `floor(atributo × 1,10)` no maior atributo calculado, incluindo
  HP. Empates: HP, Attack, Defense, Sp. Attack, Sp. Defense, Speed. O bônus
  não acumula ao recalcular e não ressuscita Pokémon desmaiado.
- O estado shiny dos novos adversários usa o identificador secreto do Pokémon,
  preservando PID, natureza, gênero, letra do Unown, manchas do Spinda, nome
  e identificador público do treinador. O setter e checksum continuam nativos.
- Tela de atributos: `100 (+10)`, ou `100(+10)` quando o espaço pede. Mantém
  fonte, cor, altura e limites originais, medindo com as fontes do jogo.
  Se o campo for pequeno demais, mantém o valor efetivo original para evitar
  sobreposição. No HP, a anotação mostra `atual/base (+bônus)`.

## Chefes e Mewtwo

- Ranks 6 e 7: substituir o integrante mais fraco pela soma dos atributos-base
  por um lendário distinto, preferindo tipos compatíveis com o treinador.
- Rank 8: Mewtwo shiny garantido. Se o chefe já possui Mewtwo, melhorá-lo e
  substituir o mais fraco restante por outro lendário, sem duplicar espécies.
- Little Battle é a exceção aprovada: não recebe lendários.
- Mewtwo dos chefes: Timid, Pressure, IVs 31, EVs 4 HP / 252 SpA / 252 Speed,
  Life Orb; Psychic, Aura Sphere, Ice Beam e Protect. Todos são da geração 4.
- Gateway: Mewtwo normal ou shiny **somente no rank 8**, inclusive em equipes
  fixas. Psychic e Protect com dois golpes sorteados entre Aura Sphere,
  Ice Beam, Thunderbolt, Flamethrower, Shadow Ball e Grass Knot. São 15
  combinações legais; evita repetição imediata durante a sessão. O chefe
  continua recebendo o Mewtwo shiny garantido, com essa variação de cobertura.
- Sunset mantém a seleção compartilhada; um Mewtwo já na reserva é movido
  para o time em vez de duplicado na lista de seleção.

## Uso no Windows

O pacote utiliza o aplicador existente e apenas patches. Não inclui ROM,
main.dol/FSYS completos, save ou RAM. A ISO/RVZ original é lida; uma nova RVZ
é montada e reaberta para conferir todos os arquivos. O save normal do jogo
continua no diretório habitual do Dolphin.

A candidata possui um CMD de teste que escolhe seu canal de atualização.
Coloque-o ao lado de `Atualizar-Iniciar.ps1` do aplicador já instalado. Não é
preciso baixar o aplicador novamente. A ROM e os caminhos já salvos são reutilizados.
As próximas atualizações desse canal são baixadas pelo mesmo CMD.

O canal estável anterior, inclusive o aplicador Mac, permanece disponível.
Esta candidata empacotada é para Windows. O builder abaixo também pode ser
executado em outros sistemas com Python, usando arquivos originais extraídos.

## Reprodução e limites

Na raiz do repositório, com Python 3:

```sh
PYTHONPATH=expansion:mod-source python3 expansion/build_full493.py \
  --original-dol /copia/sys/main.dol \
  --original-common /copia/files/common.fsys \
  --original-deck /copia/files/deck.fsys \
  --output /nova/pasta-de-saida
```

Os arquivos de entrada têm hashes exatos; os originais nunca são sobrescritos.
Para reproduzir esta candidata com traduções e nomes, acrescentar
`--original-battle-text /copia/files/menu_fight_s.fsys` e
`--original-trainer-text /copia/files/mes_common.fsys` ao comando acima.
Para recompilar o pequeno payload próprio, usar GCC PowerPC 14.2.0 e
`build_shiny_payload.py`. O compilador não é necessário no aplicador do jogador.
O manifesto do payload confere os hashes do C, dos conjuntos e do cabeçalho.

Os testes de desenvolvimento precisam de Unicorn/Capstone e capturas privadas
compatíveis. As capturas e arquivos do jogo não estão no repositório. Os relatórios
identificam os stubs, contextos e limites: testes nativos não equivalem a jogar
no Dolphin, executar turnos, renderizar modelos, gravar NAND ou salvar/carregar.
A auditoria de golpes verifica fontes individuais das gerações 3/4; não substitui
um validador completo de combinações de eventos/egg moves.
