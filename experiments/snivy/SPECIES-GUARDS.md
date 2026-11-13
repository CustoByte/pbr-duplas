# Verificações seletivas da espécie 501

`species_guards.py` trata 31 comparações USA auditadas: 30 limites 493 e
o limite 495 do predicado de presença usado pelos menus. Não substitui
literalmente 493 por 501, não desloca Egg/Bad Egg/formas e não admite
automaticamente os índices intermediários.

Cada ponte preserva a comparação original para qualquer valor diferente
de 501. Para 501, produz EQ, aceito pelo `bgt`/`ble` nativo imediatamente
seguinte. Mantém os registradores gerais, LR, CTR, XER e CR1..7 intactos;
CR0 contém o resultado da comparação, como na instrução substituída.

O módulo exige o DOL exato da etapa de nomes e acrescenta código ao último
slot livre, reservando a área até `80647200` nos dois setters de arena MEM1.
O crescimento posterior desse código precisará estender a reserva antes
de ultrapassar esse endereço, sem sobrescrever seções ou heaps.

`verify_species_guards.py` executou 1.116 casos de comparação no emulador
PPC, incluindo sentinelas, formas, IDs inválidos, extremos assinados e
overflow. Para os valores antigos, o estado resultante é o nativo anterior.
O predicado real `80058c34`, com uma caixa construída por alteração de
espécie pelo setter nativo, rejeitava 501 e passou a aceitá-lo.

Esse fixture não migra o Pokémon do jogador: sua única finalidade é testar
presença. O resultado não prova a validação do Little Battle, salvamento,
IA, carregamento de modelos ou cobertura de todos os limites do executável.
O DOL experimental não deve ser usado isoladamente: as tabelas, recursos,
passes e demais caminhos também precisam estar integrados.

Resultado: `species-guards-proof.json`. O atualizador continua inalterado.
