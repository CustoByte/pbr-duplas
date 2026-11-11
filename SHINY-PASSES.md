# Shinies nos passes iniciais — v0.8.0-shiny

Os seis Pokémon do passe vermelho de Cyndy e os seis do passe azul de Nate passam a ser apresentados como shiny enquanto o mod está ativo. A mudança consulta os integrantes atuais desses passes, incluindo os carregados de uma campanha existente; não exige começar um jogo novo. Também reconhece as cópias desses Pokémon usadas na seleção e na batalha.

## Atualizar e testar

1. Feche o Dolphin.
2. Abra o mesmo `INICIAR-WINDOWS.cmd` ou `INICIAR-MAC.command`, com internet.
3. Aguarde a atualização e a abertura do jogo.
4. Carregue sua campanha normalmente pelo menu do jogo e confira os dois passes e uma batalha.

Não restaure um save state antigo do Dolphin: ele repõe o código e a memória da versão antiga. Use o save normal da campanha.

O arquivo de save não é convertido nem sobrescrito pelo aplicador. Espécies, PID, natureza, habilidade, gênero, golpes, itens, níveis, atributos e progresso permanecem como estavam. Ao jogar sem o mod, a aparência segue novamente os dados originais. Se os integrantes desses passes forem trocados no próprio jogo, o efeito acompanha o time que estiver atualmente nos dois passes. Pokémon de outros passes e adversários mantêm a verificação normal, salvo cópias da mesma identidade de um integrante desses dois times.

## Implementação e evidências

Na revisão USA RPBE01 rev0, o acesso nativo aos passes usa a base em `0x80453184`, registros de `0x6EC` bytes e seis entradas Pokémon de `0x8C` bytes a partir de `+0x1FC`. No estado enviado, os registros 37 e 38 contêm exatamente as equipes iniciais de Cyndy e Nate. A consulta de shiny `0x803DF700` reconhece o par completo PID/ID de treinador dos integrantes atuais desses registros. Quando não encontra uma identidade correspondente, executa a fórmula nativa em `0x803DF75C`.

O código usa o espaço que já ficou desocupado pela substituição do despachante de pares na v7 e a própria rotina de consulta substituída. Não amplia o DOL, não altera as seções de memória, a fórmula global de shiny, os dados Pokémon, as tabelas de inicialização nem os vetores de exceção. A inicialização de esperas da v7 e a restauração do quarteto permanecem intactas. `common.fsys` é idêntico ao da v7.

Passaram 768 fixtures de identidade e 3.850 verificações com execução PowerPC, sem substituir os getters de Pokémon. Cobrem 32 variantes de organização dos blocos PK4, ambas as regiões de memória, cópias dos integrantes, PID igual com treinador diferente, treinador igual com PID diferente, PID repetido entre integrantes, outro passe, shinies naturais, base de passes ausente e preservação dos registradores, pilha e bytes Pokémon.

No replay isolado da memória privada enviada pelo usuário, os 12 integrantes e as quatro cópias selecionadas retornam shiny; os seis adversários mantêm o resultado original. Toda a área dos 159 passes permanece byte a byte igual após as consultas. O estado e a memória privados não são publicados.

Também passaram os 15 testes estruturais anteriores e as nove suítes de campanha/v7, usando o DOL novo. O relatório agregado inclui a décima suíte de shiny. Isso não é uma execução completa do Dolphin: a aparência, os efeitos visuais e a continuidade da campanha precisam de confirmação no jogo. Veja [VERIFICACAO-SHINY.json](VERIFICACAO-SHINY.json).

O canal de atualização e os iniciadores permanecem os mesmos. No Windows, o novo manifesto provoca a reconstrução automática da RVZ gerenciada; no Mac, o preset carrega os novos arquivos sobre a imagem original. Nenhum novo download manual do programa é necessário para quem já tem o aplicador.
