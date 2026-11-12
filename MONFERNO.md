# Monferno de Nate — v0.9.1-monferno

Ao acessar o passe azul de Nate ou seu Monferno original, o mod aplica também a uma campanha existente:

- Natureza **Adamant**: +10% de Ataque, −10% de Ataque Especial.
- **Fire Punch**, **Mach Punch**, **Blaze Kick**, **Close Combat**.
- **Lum Berry**, substituindo Meadow Plate. Cura uma condição de status ou confusão ao ativar e é consumida. Outra fica disponível ao iniciar a próxima batalha; o mod não repõe o item durante uma luta.
- A habilidade permanece **Blaze**; o efeito shiny e a campanha em duplas permanecem ativos.

Feche o Dolphin e abra o mesmo `INICIAR-WINDOWS.cmd` ou `INICIAR-MAC.command` com internet. Carregue o save normal pelo menu e acesse o passe de Nate. Não restaure um save state antigo do Dolphin, que repõe código e dados anteriores. O aplicador lembra a ROM original e baixa esta atualização sem exigir outro download manual do programa.

O aplicador não edita arquivos de save. A mudança ocorre nos dados do passe carregados pelo jogo e poderá ser gravada pelo salvamento normal da campanha. Não requer iniciar outra campanha. Os demais Pokémon, IVs, EVs, nível, identidade do treinador e habilidade são preservados. A natureza exige mudar parte do PID; os 20 bits inferiores são mantidos, preservando a ordem dos blocos PK4, o critério de gênero e a paridade usada pela habilidade.

O alvo é o Monferno original do passe azul: registro 38, slot 1, em índices iniciados em zero, espécie 391. Se esse slot tiver sido trocado por outra espécie, ela não é alterada. As duas substituições de golpes reinicializam apenas seus próprios PP e PP Ups na primeira aplicação. Consultas posteriores não repõem os PP gastos. O efeito shiny acompanha a nova identidade.

## Lum Berry entre batalhas

Nas partidas normais e nas séries, o time começa com o item do passe. O caminho de sobrevivência também restaurava o item consumido da partida anterior; a versão v9 substitui somente essa restauração de item para a identidade completa desse Monferno por Lum Berry. HP, PP, status e os demais Pokémon mantêm o comportamento anterior do torneio. Ler os atributos, trocar o Pokémon ou consultar sua aparência durante a luta não restitui a Berry.

## Implementação e verificações

As saídas nativas de `0x800E8594` e `0x800E88B0` recebem uma migração idempotente, que usa os getters e setters PK4 reais, incluindo a atualização de checksum. Os dados do passe são ajustados antes da montagem das cópias para batalha. O caminho de restauração de item em `0x80155AE4` reconhece o PID e ID de treinador do Monferno atual do passe; os demais usam o valor nativo. Não há mudança na fórmula de Blaze nem na implementação de Lum Berry.

Uma seção de texto de 2.048 bytes é acrescentada ao DOL em `0x8063C000`. Fica acima do topo original da pilha principal (`0x8063B2B0`) e abaixo do limite inferior padrão do heap (`0x8063D2C0`). Ambos os setters nativos de MEM1 ArenaLo limitam valores alternativos a pelo menos `0x8063C800`, protegendo o código em inicializações alternativas. As seções originais, o BSS, o topo da pilha e os vetores de exceção não são deslocados. `common.fsys` permanece idêntico ao da v7/v8.

A revisão v0.9.1 usa o getter de Pokémon de batalha na identificação da cópia que recebe a Berry. Isso respeita o estado de decodificação e o checksum diferido da estrutura de batalha; o passe continua usando seu getter próprio. Há regressão específica para esse estado.

Passaram 800 fixtures com 32 arranjos PK4 e todas as 25 classes de natureza, preservação de registradores/pilha, consultas repetidas, PP já gastos, cópias de batalha, limites de passe/slot/espécie e 14 casos de reserva de memória. A busca de natureza também foi verificada para todas as 4.096 combinações dos bits superiores do PID, incluindo estouro de 32 bits. Foram testados três ciclos consecutivos de consumo e reposição de Berry na preparação seguinte, usando setters reais, sem restaurar o item na leitura durante a batalha.

No replay isolado do estado privado enviado, o Monferno passa para Adamant, golpes 7/183/299/370 e item 157. Todos os demais Pokémon e os demais dados dos passes permanecem iguais; os IVs, EVs, a habilidade e o treinador são preservados. O estado e a memória privados não são distribuídos.

Essas verificações executam rotinas PowerPC isoladas. Não houve inicialização/renderização completa desta versão no Dolphin nem teste de persistência de um save real. A seleção, a batalha e o salvamento precisam ser confirmados no jogo. Relatórios: [VERIFICACAO-MONFERNO.json](VERIFICACAO-MONFERNO.json) e [VERIFICACAO-v9.json](VERIFICACAO-v9.json).
