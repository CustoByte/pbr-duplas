# Correções de nome e leitura de Pokémon em batalha

O nome global já existia, mas o construtor nativo deixava o apelido vazio ao
receber MEGA LUCARIO: são 12 caracteres para um campo serializado de 10.
O registro PK4 continua com 140 bytes. Um marcador interno curto identifica o
nome padrão; os leitores de String dinâmica exibem o nome completo. O construtor
aloca capacidade real de 16 para Strings antes solicitadas com capacidade 11.
Apelidos personalizados permanecem intactos. O acesso ao passe também repara
nomes vazios de Megas já entregues, sem recriar os atributos ou golpes.

`verify_names.py` executa construtor, leitores e setter nativos. Confere comprimento,
conteúdo, sentinela após a alocação, preservação dos registros e apelido personalizado.
O nome global mede 120 × 25 pixels no medidor da fonte nativa; a renderização de
cada tela e do anúncio de golpe ainda exige teste visual no Dolphin.
Também foi verificado o nome com as tabelas reais do estado recebido, em cópia
privada da memória, sem substituir essas tabelas nem modificar o arquivo enviado.

O hook de aparência usava o leitor de Pokémon em caixa para uma estrutura de
Pokémon em batalha. Com bloqueio de party ativo e checksum adiado, isso acrescentava
a marca de Pokémon inválido. O leitor de party nativo respeita esse bloqueio.
O teste confirma que a versão anterior muda flags 8000 para A000 e a corrigida
mantém o registro inteiro idêntico.

O aviso relatado em 801A58B0 lê um alvo inválido, E6AEE6AE + 794. A ligação entre
essa referência e a falha do checksum não foi reproduzida. O estado recebido é
anterior à criação do contexto de batalha; a consulta direta a atores não pode
ser executada nele como se a batalha já estivesse inicializada. Não foi adicionado
um desvio para esconder a leitura inválida. A candidata teste 3 deve ser iniciada
pelo começo normal, sem carregar estado antigo, e ainda precisa validar esse aviso.

A geometria, as texturas e a receita de conversão não mudam. O cache gráfico
existente pode ser reutilizado. Snivy, Lucario normal, atributos e moveset passaram
novamente nos replays nativos. Os relatórios não representam uma batalha completa
executada no Dolphin do Windows.
