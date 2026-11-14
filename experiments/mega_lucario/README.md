# Mega Lucario independente — candidato gráfico

Entrada experimental, sem ligação com o construtor de versões ou o atualizador.
Lucario normal e Snivy devem permanecer disponíveis. Nacional 448, forma Mega;
índice interno candidato 502, modelo candidato 671 e arquivo candidato 8193.
Os registros atuais foram auditados para ausência de colisão, mas esses novos
índices ainda não foram habilitados no executável.

O usuário já escolheu moveset, habilidade, ausência de item e o lugar do Ivysaur
no passe inicial. `profile.json` registra as escolhas e a proposta de treino;
`battle_set.py` calcula os atributos de nível 50. O total dos atributos base é 625.

A conversão do modelo fornecido e as primeiras animações passaram nas verificações
offline. Consulte [IMPLEMENTATION.md](IMPLEMENTATION.md) para o que foi feito,
como reproduzir as etapas e o que falta antes de uma instalação jogável.

Os relatórios são próprios; modelos, texturas, arquivos nativos e renders ficam
privados. Nada desta pasta modifica o jogo, saves ou feed de atualização.

Teste das fórmulas e da correção de rotações:

```sh
PYTHONPATH=experiments/mega_lucario python -m unittest discover -s experiments/mega_lucario -p test_candidate.py
```
