# Golpes, atributos e animações dos novos Pokémon — proposta

As listas de 15 são propostas para revisão; o conjunto do jogador do Mega Charizard X já foi aprovado.
As habilidades, itens e conjuntos fixos dos outros três continuam pendentes.

## Regra de geração de NPC

- Escolher quatro golpes diferentes do banco de até 15, uma vez ao criar o adversário.
- Variar IVs de 24 a 31, natureza apropriada e distribuição de 508 EVs, com até 252 por atributo.
- Manter atributos base, tipos, habilidade e item da espécie/configuração; não sortear seis valores desconectados.
- Preservar o resultado durante a batalha. Dano, cura e modificadores de atributos dos golpes continuam funcionando normalmente.
- Usar o nível do encontro. O passe de teste proposto usa nível 50.
- Megas usam orçamento de atributos base comparável a lendários (600–680), sem ativar a classificação de lendário.
- As listas atuais têm três golpes de status por Pokémon; qualquer seleção de quatro inclui ao menos um ataque sem restringir o sorteio.

## Passe de teste

O passe 37 preserva Mega Lucario e Snivy nos slots 0 e 1. Os novos ocupam slots 2 a 5.
Isso é uma configuração de entrega ainda não aplicada à imagem.

## Contrato de animações

Cada golpe tem uma ação corporal e um ponto esperado de emissão de efeitos. Ações compatíveis podem compartilhar clips;
isso não dispensa aproximação/retorno, espera, reação ao dano, desmaio e entrada/saída da Poké Ball.
Os quatro arquivos recebidos não têm movimento animado. Todos os contratos estão com animation_verified=false.
Os efeitos e atributos de golpes são os da quarta geração; por exemplo, Drain Punch e Knock Off ainda têm os valores nativos antigos.

## Estado da implementação

O sampler C funciona e foi comparado com PowerPC e cálculo original de atributos em memória clonada.
O teste usa uma espécie existente como alias e substitui somente a linha de atributos no fixture; não instala os novos modelos.
A rotina de geração de NPC ainda não foi conectada ao sampler. As animações e as referências originais continuam necessárias.
O gerador produz um cabeçalho C e o mesmo JSON para o motor nativo. As próximas compilações nativas incluem esses dados;
o protótipo publicado anteriormente não ganha um sistema de batalha por receber o catálogo.

## mega-charizard-x

Total de atributos base proposto: 634.

| Nº | Golpe | Ação corporal planejada | Emissão |
|---|---|---|---|
| 1 | Flare Blitz | flame_rush | body |
| 2 | Dragon Claw | physical_claw | hand |
| 3 | Earthquake | ground_impact | body |
| 4 | Protect | guard | body |
| 5 | Dragon Dance | focus | body |
| 6 | Fire Punch | physical_strike | hand |
| 7 | Thunder Punch | physical_strike | hand |
| 8 | Roost | recover | body |
| 9 | Brick Break | physical_strike | hand |
| 10 | Rock Slide | ranged_cast | body |
| 11 | Crunch | bite | mouth |
| 12 | Outrage | rush | body |
| 13 | Dragon Rush | rush | body |
| 14 | Fire Blast | ranged_breath | mouth |
| 15 | Air Slash | ranged_wing | wing |

## ash-greninja

Total de atributos base proposto: 640.

| Nº | Golpe | Ação corporal planejada | Emissão |
|---|---|---|---|
| 1 | Hydro Pump | ranged_water | mouth |
| 2 | Surf | ranged_wave | body |
| 3 | Dark Pulse | ranged_pulse | mouth |
| 4 | Ice Beam | ranged_beam | mouth |
| 5 | Water Pulse | ranged_water | mouth |
| 6 | Grass Knot | ranged_cast | body |
| 7 | Extrasensory | ranged_cast | head |
| 8 | U-turn | retreat_strike | body |
| 9 | Night Slash | physical_claw | hand |
| 10 | Shadow Sneak | ambush | body |
| 11 | Waterfall | rush | body |
| 12 | Low Kick | low_strike | foot |
| 13 | Protect | guard | body |
| 14 | Substitute | substitute | body |
| 15 | Taunt | taunt | head |

## hydreigon

Total de atributos base proposto: 600.

| Nº | Golpe | Ação corporal planejada | Emissão |
|---|---|---|---|
| 1 | Draco Meteor | ranged_sky | mouth |
| 2 | Dragon Pulse | ranged_pulse | mouth |
| 3 | Dark Pulse | ranged_pulse | mouth |
| 4 | Flamethrower | ranged_breath | mouth |
| 5 | Fire Blast | ranged_breath | mouth |
| 6 | Surf | ranged_wave | body |
| 7 | Earth Power | ground_cast | body |
| 8 | Focus Blast | ranged_orb | mouth |
| 9 | Flash Cannon | ranged_beam | mouth |
| 10 | U-turn | retreat_strike | body |
| 11 | Crunch | bite | mouth |
| 12 | Dragon Rush | rush | body |
| 13 | Protect | guard | body |
| 14 | Roost | hover_recover | body |
| 15 | Thunder Wave | ranged_cast | body |

## rillaboom

Total de atributos base proposto: 530.

| Nº | Golpe | Ação corporal planejada | Emissão |
|---|---|---|---|
| 1 | Wood Hammer | heavy_strike | hand |
| 2 | Seed Bomb | seed_cast | mouth |
| 3 | Drain Punch | physical_strike | hand |
| 4 | Superpower | heavy_strike | body |
| 5 | Brick Break | physical_strike | hand |
| 6 | Low Kick | low_strike | foot |
| 7 | Knock Off | physical_strike | hand |
| 8 | U-turn | retreat_strike | body |
| 9 | Earthquake | ground_impact | body |
| 10 | Body Slam | body_strike | body |
| 11 | Fake Out | quick_strike | hand |
| 12 | Bullet Seed | seed_cast | mouth |
| 13 | Protect | guard | body |
| 14 | Swords Dance | focus | body |
| 15 | Bulk Up | focus | body |

