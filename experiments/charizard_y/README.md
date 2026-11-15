# Mega Charizard Y — candidata cumulativa

Substitui somente o Wartortle de nível 50 no slot 2 do passe 37 (Cyndy).
Preserva Snivy, Mega Lucario, Little Battle e os demais slots. O Lucario e o
Charizard originais continuam disponíveis como espécies independentes.

Conjunto fixo do jogador: Flamethrower / Air Slash / Solar Beam / Protect.
Drought, Timid, sem item, IVs 20, sem EVs de treinamento competitivo.
Nível 50: HP148 / ATK107 / DEF93 / SpA150 / SpD110 / Speed115.
Base ajustada para este mod: 78/104/78/135/95/90 (total 580), sem bônus artificial de shiny.
O perfil antigo do passe é migrado pelos getters/setters nativos, sem resetar
apelido, golpes ou item; spreads de treinamento editados são preservados.
Drought usa as regras nativas de clima da geração IV.
A aleatoriedade dos NPCs está adiada e nenhum hook de geração foi instalado.

O conversor usa exclusivamente o ZIP aprovado, os arquivos originais do jogo
e o SDK local já empregado para Snivy. Não distribui modelo, textura, ROM ou save.
O nome completo usa uma String dinâmica com capacidade 24; o nickname PK4
continua limitado a 10 caracteres, com marcador interno e apelidos respeitados.

As verificações usam rotinas PPC nativas em capturas privadas: entrega idempotente,
preservação dos passes, atributos e PP, nomes e limites, seleção dos quatro,
guardas de espécie, dispatch FSYS e alocação simultânea dos três modelos.
Isso não equivale a testar GPU, efeitos ou batalha ao vivo no Dolphin.
A chama procedural aprovada no vídeo continua sem equivalência visual confirmada
no jogo; o candidato mantém o material de chama do modelo de origem.
