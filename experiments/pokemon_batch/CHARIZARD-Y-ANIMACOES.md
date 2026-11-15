# Mega Charizard Y: conjunto nativo de animações

Conjunto preparado a partir do Charizard original, mantendo a correção da
mandíbula. Candidato privado SDR; não é uma atualização jogável publicada.

| Slot original | Uso |
|---|---|
| wait | Espera no chão |
| kime | Ação especial |
| damage | Receber dano e recuperar |
| down | Desmaio |
| hikkaku | Ataque de garras/braços |
| kime_a | Ação alternativa/especial |
| kick | Ataque com pernas |
| tackle | Investida/contato |
| takeoff | Decolagem |
| kuchu_wait | Espera aérea |
| kyukoka | Mergulho aéreo |
| tx_wink | Piscar |
| tx_sleep | Olhos fechados durante sono |
| tx_wakeup | Acordar |
| run | Aproximação/corrida |

Os quinze slots preservam ordem, flags e tempos do doador. As 22 ligações de
animação e 25 ligações de nós do registro original foram verificadas contra os
novos índices. Entrada, recolhimento, troca e efeitos de golpes são composições
do controlador original; não se acrescentam clips artificiais de escala que
possam duplicar o efeito da Poké Bola.

## Verificação realizada

- Comparação das poses de origem com a cena de exportação após conversão de eixos.
- Decodificação SDR independente: matrizes em todos os frames e amostras da pele
  nas quatro malhas dos doze clips corporais.
- Texturas e canais UV de todos os estados, incluindo os três estados dos olhos.
- Alocação, realocação e prontidão do recurso por rotinas PPC originais, em uma
  cópia isolada de RAM. Isso não representa leitura do disco ou renderização.
- Reimportação e revisão visual do SDR, incluindo a mandíbula e os olhos.

A revisão glTF usa conversão Euler estável, inclui o último frame e representa
GX REPEAT com um sampler glTF repetido. Essas correções evitam que o importador
introduza distorções ou cores erradas na prévia de um arquivo SDR válido.

## Pendências para entrega no jogo

O candidato não está instalado nem deve ser copiado sobre o Charizard normal.
Faltam registro da forma, montagem do pacote e validação de batalha no Dolphin.
A chama aprovada continua como efeito do visualizador; seu equivalente nativo
não está concluído. A superfície de fogo presente no SDR é a da fonte, não a
chama procedural aprovada. O gate de pacote jogável permanece desativado.
