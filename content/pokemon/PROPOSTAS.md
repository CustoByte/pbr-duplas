# Bancos propostos: 20 golpes por Pokémon

Cada banco contém **14 ofensivos e 6 de status**. Um NPC recebe quatro golpes distintos;
o padrão atual rejeita conjuntos compostos apenas por status, garantindo pelo menos um ofensivo.
A opção de sorteio totalmente livre existe no gerador, caso o usuário prefira esse comportamento.

Os golpes 15–20 das tabelas são os seis de status: suporte, cura e aumento/redução de atributos também pertencem a essa categoria.
Os presets do jogador de Snivy e Mega Lucario permanecem intactos. O conjunto aprovado do Mega Charizard X continua
Flare Blitz / Dragon Claw / Earthquake / Protect, independentemente da ordem dos golpes no banco.

## Atributos e entrega

- NPCs recebem variação válida de IVs, EVs e natureza, uma vez na criação do encontro.
- O resultado não é sorteado novamente ao consultar menus ou escolher golpes; efeitos normais de combate continuam funcionando.
- Megas mantêm força comparável a lendários, sem mudar sua classificação. O orçamento proposto é 600–680 de atributos base.
- O passe de teste preserva Mega Lucario e Snivy nos slots 0 e 1 e reserva os outros quatro para os novos modelos.

## Estado dos trabalhos

Estes são bancos e contratos propostos; os novos modelos ainda não foram instalados. A rotina de geração de NPCs ainda não usa o sampler.
O código de sorteio foi testado em PowerPC e contra o cálculo original de atributos em 48 conjuntos / 288 comparações.
As animações precisam ser criadas/adaptadas e verificadas. Cada golpe tem um contrato de ação corporal e emissão de efeito;
golpes compatíveis podem compartilhar um clip, preservando o comportamento coerente de contato, projétil ou suporte.
Os valores e efeitos usados são os nativos da quarta geração. O JSON compartilhado alimenta os builds C e nativo;
isso não acrescenta um sistema de batalha ao protótipo 3D nem altera as releases já publicadas.

## Mega Charizard X

Atributos base propostos: 634 no total.

| Nº | Golpe | Categoria | Ação corporal planejada | Emissão |
|---|---|---|---|---|
| 1 | Flare Blitz | Físico | flame_rush | body |
| 2 | Dragon Claw | Físico | physical_claw | hand |
| 3 | Earthquake | Físico | ground_impact | body |
| 4 | Fire Punch | Físico | physical_strike | hand |
| 5 | Thunder Punch | Físico | physical_strike | hand |
| 6 | Brick Break | Físico | physical_strike | hand |
| 7 | Rock Slide | Físico | ranged_cast | body |
| 8 | Crunch | Físico | bite | mouth |
| 9 | Outrage | Físico | rush | body |
| 10 | Dragon Rush | Físico | rush | body |
| 11 | Fire Blast | Especial | ranged_breath | mouth |
| 12 | Air Slash | Especial | ranged_wing | wing |
| 13 | Dragon Pulse | Especial | ranged_pulse | mouth |
| 14 | Aerial Ace | Físico | aerial_strike | body |
| 15 | Protect | Status | guard | body |
| 16 | Dragon Dance | Status | focus | body |
| 17 | Roost | Status | hover_recover | body |
| 18 | Swords Dance | Status | focus | body |
| 19 | Will-O-Wisp | Status | ranged_flame | mouth |
| 20 | Substitute | Status | substitute | body |

## Ash-Greninja

Atributos base propostos: 640 no total.

| Nº | Golpe | Categoria | Ação corporal planejada | Emissão |
|---|---|---|---|---|
| 1 | Hydro Pump | Especial | ranged_water | mouth |
| 2 | Surf | Especial | ranged_wave | body |
| 3 | Dark Pulse | Especial | ranged_pulse | mouth |
| 4 | Ice Beam | Especial | ranged_beam | mouth |
| 5 | Water Pulse | Especial | ranged_water | mouth |
| 6 | Grass Knot | Especial | ranged_cast | body |
| 7 | Extrasensory | Especial | ranged_cast | head |
| 8 | U-turn | Físico | retreat_strike | body |
| 9 | Night Slash | Físico | physical_claw | hand |
| 10 | Shadow Sneak | Físico | ambush | body |
| 11 | Waterfall | Físico | rush | body |
| 12 | Low Kick | Físico | low_strike | foot |
| 13 | Aerial Ace | Físico | aerial_strike | body |
| 14 | Rock Slide | Físico | ranged_cast | body |
| 15 | Protect | Status | guard | body |
| 16 | Substitute | Status | substitute | body |
| 17 | Taunt | Status | taunt | head |
| 18 | Toxic | Status | ranged_cast | mouth |
| 19 | Double Team | Status | evasive_focus | body |
| 20 | Haze | Status | ranged_mist | body |

## Hydreigon

Atributos base propostos: 600 no total.

| Nº | Golpe | Categoria | Ação corporal planejada | Emissão |
|---|---|---|---|---|
| 1 | Draco Meteor | Especial | ranged_sky | mouth |
| 2 | Dragon Pulse | Especial | ranged_pulse | mouth |
| 3 | Dark Pulse | Especial | ranged_pulse | mouth |
| 4 | Flamethrower | Especial | ranged_breath | mouth |
| 5 | Fire Blast | Especial | ranged_breath | mouth |
| 6 | Surf | Especial | ranged_wave | body |
| 7 | Earth Power | Especial | ground_cast | body |
| 8 | Focus Blast | Especial | ranged_orb | mouth |
| 9 | Flash Cannon | Especial | ranged_beam | mouth |
| 10 | U-turn | Físico | retreat_strike | body |
| 11 | Crunch | Físico | bite | mouth |
| 12 | Dragon Rush | Físico | rush | body |
| 13 | Earthquake | Físico | ground_impact | body |
| 14 | Rock Slide | Físico | ranged_cast | body |
| 15 | Protect | Status | guard | body |
| 16 | Roost | Status | hover_recover | body |
| 17 | Thunder Wave | Status | ranged_cast | body |
| 18 | Taunt | Status | taunt | head |
| 19 | Substitute | Status | substitute | body |
| 20 | Nasty Plot | Status | focus | head |

## Rillaboom

Atributos base propostos: 530 no total.

| Nº | Golpe | Categoria | Ação corporal planejada | Emissão |
|---|---|---|---|---|
| 1 | Wood Hammer | Físico | heavy_strike | hand |
| 2 | Seed Bomb | Físico | seed_cast | mouth |
| 3 | Drain Punch | Físico | physical_strike | hand |
| 4 | Superpower | Físico | heavy_strike | body |
| 5 | Brick Break | Físico | physical_strike | hand |
| 6 | Low Kick | Físico | low_strike | foot |
| 7 | Knock Off | Físico | physical_strike | hand |
| 8 | U-turn | Físico | retreat_strike | body |
| 9 | Earthquake | Físico | ground_impact | body |
| 10 | Body Slam | Físico | body_strike | body |
| 11 | Fake Out | Físico | quick_strike | hand |
| 12 | Bullet Seed | Físico | seed_cast | mouth |
| 13 | Giga Impact | Físico | rush | body |
| 14 | Double-Edge | Físico | body_strike | body |
| 15 | Protect | Status | guard | body |
| 16 | Swords Dance | Status | focus | body |
| 17 | Bulk Up | Status | focus | body |
| 18 | Taunt | Status | taunt | head |
| 19 | Substitute | Status | substitute | body |
| 20 | Rest | Status | sleep_recover | body |

## Snivy

Atributos base propostos: 308 no total.

| Nº | Golpe | Categoria | Ação corporal planejada | Emissão |
|---|---|---|---|---|
| 1 | Energy Ball | Especial | ranged_orb | mouth |
| 2 | Leaf Storm | Especial | leaf_cast | body |
| 3 | Giga Drain | Especial | drain_cast | body |
| 4 | Leaf Blade | Físico | tail_slash | tail |
| 5 | Seed Bomb | Físico | seed_cast | mouth |
| 6 | Magical Leaf | Especial | leaf_cast | body |
| 7 | Grass Knot | Especial | ranged_cast | body |
| 8 | Aqua Tail | Físico | tail_strike | tail |
| 9 | Iron Tail | Físico | tail_strike | tail |
| 10 | Aerial Ace | Físico | aerial_strike | body |
| 11 | Knock Off | Físico | tail_strike | tail |
| 12 | Wring Out | Especial | constrict | body |
| 13 | Return | Físico | body_strike | body |
| 14 | Facade | Físico | body_strike | body |
| 15 | Glare | Status | glare | head |
| 16 | Leech Seed | Status | seed_cast | mouth |
| 17 | Protect | Status | guard | body |
| 18 | Substitute | Status | substitute | body |
| 19 | Taunt | Status | taunt | head |
| 20 | Synthesis | Status | recover | body |

## Mega Lucario

Atributos base propostos: 625 no total.

| Nº | Golpe | Categoria | Ação corporal planejada | Emissão |
|---|---|---|---|---|
| 1 | Bullet Punch | Físico | physical_strike | hand |
| 2 | Close Combat | Físico | combo_strike | body |
| 3 | Aura Sphere | Especial | ranged_orb | hand |
| 4 | Extreme Speed | Físico | rush | body |
| 5 | Dragon Pulse | Especial | ranged_pulse | mouth |
| 6 | Dark Pulse | Especial | ranged_pulse | mouth |
| 7 | Crunch | Físico | bite | mouth |
| 8 | Ice Punch | Físico | physical_strike | hand |
| 9 | Thunder Punch | Físico | physical_strike | hand |
| 10 | Blaze Kick | Físico | low_strike | foot |
| 11 | Flash Cannon | Especial | ranged_beam | mouth |
| 12 | Earthquake | Físico | ground_impact | body |
| 13 | Stone Edge | Físico | ground_cast | body |
| 14 | Vacuum Wave | Especial | ranged_palm | hand |
| 15 | Protect | Status | guard | body |
| 16 | Swords Dance | Status | focus | body |
| 17 | Nasty Plot | Status | focus | head |
| 18 | Calm Mind | Status | focus | body |
| 19 | Agility | Status | evasive_focus | body |
| 20 | Substitute | Status | substitute | body |

