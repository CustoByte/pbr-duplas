# Animações exigidas para a integração do Snivy

A conversão e a prévia não encerram a integração gráfica. O resultado
solicitado exige reprodução automática dentro do jogo, nos eventos corretos.
Não publicar como Snivy jogável antes dos testes abaixo.

## Referência nativa verificada

`audit_animation_contract.py` lê as tabelas GSobjectData/GSanimationData
da captura USA, sem endereços PAL nem alteração da memória. Identifica
objetos por nomes e valida ponteiros, contadores, nomes e durações:

| Pokémon de referência | Nome interno | Ações |
| --- | --- | --- |
| Monferno | moukazaru | 10 |
| Chimchar | hikozaru | 11 |
| Grotle | hayashigame | 12 |

Os nomes incluem `wait`, `run`, `damage`, `down`, `tackle`, `punch`,
`kime`, `kime_a`, `kime_phy`, `mamoru`, `tx_wink`, `tx_sleep`, `tx_wakeup`.
Essa é a união das três referências: não significa que toda espécie tenha
obrigatoriamente todas essas ações, ou que o nome sozinho determine seu uso.
Cada vínculo ainda precisa de validação dos eventos e dados próprios da espécie.

O exportador inicial usava os nomes genéricos `idle`, `faint`, `move_phys`,
`move_spec`. O adaptador `adapt_sdr_animation_names.py` prepara uma cópia
com `wait`, `down`, `tackle`, `kime`, respectivamente, preservando índices
e curvas. Confere preservação exata de todos os bytes anteriores, exceto
quatro ponteiros de nomes; as novas strings ficam no fim do arquivo.
Não substitui o registro de espécie nem os dados de despacho do jogo.
O conjunto ainda não cobre todas as ações observadas nas referências.

Resultados: `animation-contract-report.json` e
`native-animation-names-report.json`. Os SDRs derivados ficam privados.

## Cobertura necessária

| Situação | Dados disponíveis | Verificação que falta no jogo |
| --- | --- | --- |
| Espera e seleção de comandos | NorIdle0; ciclo decodificado renderizado | Loop contínuo, olhos, transições e sincronização |
| Ataque físico | Atk0_0 e outras ações Atk | Escolher ação adequada, fases de preparação/impacto/retorno e efeitos |
| Ataque especial | Atk2_0 no protótipo, outras alternativas preservadas | Rever o movimento completo; seu nome não garante a categoria |
| Golpes de status e Protect | Alternativas preservadas no BRRES | Mapear pose, evento e duração, sem reutilizar qualquer ataque arbitrariamente |
| Receber dano | DamF0 e variantes | Impacto, retorno à espera, sobreposição de status e direção |
| Derrota | Faint0 | Execução única, conclusão da ação e substituição; não usar o loop do arquivo fonte automaticamente |
| Sair da Poké Ball | Rotinas compartilhadas de batalha localizadas | Carregar Snivy, escala/posição, material, visibilidade e efeitos sincronizados |
| Retornar à Poké Ball e trocar | Rotinas compartilhadas localizadas | Recolhimento, espera de conclusão, ocultação e liberação corretas |
| Sono e despertar | Sleep0_0/1/2 e curvas de materiais | Separar os canais de corpo/olhos e preservar o estado de batalha |
| Piscar | Atlas de olhos e ações de materiais preservados | Extrair/adaptar uma piscada real; o protótipo ainda usa espera como placeholder |
| Vitória e reações adicionais | Win0_0/1, Joy0 e outras ações preservadas | Selecionar somente as que combinam com eventos reais de PBR |

Em `fight_common.fsys`, recurso `0x024d1200`, foram identificados nomes
de rotinas como `loadballin`, `actballin`, `loadballout`, `actballout`,
`scaletoball`, `setballattach`, `setballdettach` e `setballvisble`.
O inventário de nomes não comprova seus argumentos nem sua execução para
o Snivy. Os efeitos e o controle de escala não devem ser substituídos por
uma simples animação do corpo sem o restante do evento nativo.

## Próxima dependência de arquivo

Falta uma referência completa de arquivo Pokémon nativo: **pkx_388.fsys**
(Grotle), presente na raiz do sistema de arquivos da versão USA fornecida.
A captura permite auditar as tabelas carregadas, mas não substitui o pacote
original com todos os seus recursos, identificadores e metadados de carga.
Esse arquivo permitirá comparar o empacotamento e vínculos antes de montar
o pacote independente do Snivy. Não será alterado nem redistribuído.

No Dolphin para Mac: abrir as propriedades de Pokémon Battle Revolution,
ir a Sistema de Arquivos, expandir a Partição de Dados, localizar o arquivo
e usar Control+clique → Extrair arquivo. Não é necessário extrair a ROM toda.

## Critérios para concluir

- Obter/despachar a espécie independente sem substituir Grotle ou outra espécie.
- Confirmar os nomes, índices e vínculos reais de cada ação usada por Snivy.
- Testar pelo menos dois ciclos de espera durante a seleção de comandos.
- Executar os quatro golpes de teste e observar impacto/efeitos/retorno.
- Sofrer dano, condições de status, derrota e substituição sem travamentos.
- Enviar, recolher e trocar Snivy com os efeitos originais da Poké Ball.
- Verificar câmera, escala, sombras e pontos de efeitos durante movimentos.
- Testar dois atores aliados, oponentes e ações simultâneas nas duplas.
- Repetir batalhas após save/load e validar ausência de regressões.

A montagem de prévias apresenta movimentos decodificados fora do jogo;
não é evidência de que esses eventos já funcionem no Dolphin.

## Reproduzir a auditoria e a adaptação

```sh
PYTHONPATH=mod-source python experiments/snivy/audit_animation_contract.py \
  --capture /caminho/diagnostics-command \
  --fight-common /caminho/fight_common.fsys \
  --current-report experiments/snivy/graphics-report.json \
  --report /tmp/animation-contract-report.json

python experiments/snivy/adapt_sdr_animation_names.py \
  /tmp/snivy-graphics/snivy-experimental.sdr \
  /tmp/snivy-graphics/snivy-native-core.sdr \
  --report /tmp/native-animation-names-report.json
```

O renderizador de diagnóstico aceita `--preview-action damage`,
`move_phys`, `move_spec` ou `faint`, além do padrão `idle`. Enquadra os
quadros amostrados de toda a ação para não cortar saltos e deslocamentos.
