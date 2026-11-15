# Mega Lucario independente — candidato gráfico

Integração experimental com conversão privada e entrega pelo atualizador Windows.
Lucario normal e Snivy devem permanecer disponíveis. Nacional 448, forma Mega;
índice interno candidato 502, modelo candidato 671 e arquivo candidato 8193.
Os registros e caminhos seletivos do executável foram integrados e passaram nos
replays nativos offline; o teste real no Dolphin Windows ainda está pendente.

O usuário já escolheu moveset, habilidade, ausência de item e o lugar do Ivysaur
no passe inicial. `profile.json` registra as escolhas e a proposta de treino;
`battle_set.py` calcula os atributos de nível 50. O total dos atributos base é 625.

A conversão do modelo fornecido e as primeiras animações passaram nas verificações
offline. Consulte [IMPLEMENTATION.md](IMPLEMENTATION.md) para o que foi feito,
como reproduzir as etapas e o que falta antes de uma instalação jogável.

Os relatórios são próprios; modelos, texturas, arquivos nativos e renders ficam
privados. Os construtores geram cópias privadas e o pacote contém código/deltas. O instalador
preserva a imagem original e não escreve em saves.

Teste das fórmulas e da correção de rotações:

```sh
PYTHONPATH=experiments/mega_lucario python -m unittest discover -s experiments/mega_lucario -p test_candidate.py
```
