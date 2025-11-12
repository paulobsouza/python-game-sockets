# python-game-sockets

# Jogo de Tabuleiro em Rede com Sockets Python

Este projeto é uma aplicação acadêmica dos conceitos de programação de rede, implementando um jogo de tabuleiro multiplayer (2 jogadores) em tempo real usando sockets TCP em Python.

O jogo é um "Quiz de TI", onde os jogadores avançam em um tabuleiro de 20 casas. A cada rodada, o servidor "rola um dado" e faz uma pergunta sobre conceitos de tecnologia. Acertos concedem casas bônus, e erros penalizam o jogador. Vence quem chegar à casa 20 primeiro.

## Conceitos Aplicados

Este projeto foi desenvolvido para aplicar e demonstrar os seguintes conceitos:

* **Programação de Rede (Sockets):** Utilização da biblioteca `socket` do Python para estabelecer comunicação TCP persistente entre um servidor e múltiplos clientes.
* **Arquitetura Cliente-Servidor:** Separação clara de responsabilidades, onde o Servidor (Mestre do Jogo) centraliza toda a lógica e estado, e os Clientes (Jogadores) atuam apenas como interfaces de entrada e saída.
* **Multithreading:** Uso da biblioteca `threading` no servidor para gerenciar múltiplos clientes concorrentemente. O servidor possui:
    * Uma *thread principal* para aceitar novas conexões (Lobby).
    * Uma *thread de lógica de jogo* para gerenciar os turnos e regras.
    * Uma *thread de escuta* dedicada para cada cliente, permitindo E/S (I/O) não-bloqueante.
* **Sincronização de Threads:** Uso de `queue.Queue` para comunicação segura entre a thread de escuta e a thread de jogo, e `threading.Event` para sinalizar o encerramento do jogo para todas as threads ativas.
* **Protocolo de Comunicação:** Definição de um protocolo simples baseado em **JSON** para serializar e desserializar mensagens entre cliente e servidor.

## Tecnologias Utilizadas

* **Python**
* Bibliotecas Nativas do Python:
    * `socket` (para a comunicação de rede)
    * `threading` (para concorrência no servidor)
    * `json` (para serialização do protocolo)
    * `queue` (para sincronização entre threads)
    * `random` (para rolar dados e selecionar perguntas)
    * `time` (para pausas entre os turnos)

## Estrutura dos Arquivos

```
.
├── server.py       # O servidor (Mestre do Jogo)
├── client.py       # O cliente (Interface do Jogador)
├── questions.json  # O banco de dados de perguntas e respostas
└── README.md       # Este arquivo
```

## Como Executar

Para rodar este projeto, você precisará de três janelas de terminal.

### 1. Iniciar o Servidor

Primeiro, inicie o servidor. Ele ficará aguardando no "lobby" por dois jogadores.

```bash
python server.py
```
*Saída esperada:*
`Servidor iniciado em localhost:8788. Aguardando jogadores...`

### 2. Iniciar o Cliente 1 (Jogador 1)

Em uma **segunda** janela de terminal, inicie o primeiro cliente.

```bash
python client.py
```
*Saída esperada:*
`Conectado ao servidor do jogo em localhost:8788`
`... Você é o Jogador 1. Aguardando oponente... ...`

### 3. Iniciar o Cliente 2 (Jogador 2)

Em uma **terceira** janela de terminal, inicie o segundo cliente.

```bash
python client.py
```
*Saída esperada:*
`Conectado ao servidor do jogo em localhost:8788`
`... Você é o Jogador 2. Aguardando oponente... ...`

Assim que o Jogador 2 se conectar, o jogo começará automaticamente em todas as três janelas.

## Arquitetura Detalhada

### Servidor (`server.py`)

O servidor é o "cérebro" do jogo e a fonte da verdade. Ele gerencia o estado do jogo (posição de cada jogador, de quem é o turno) e lida com toda a lógica.

1.  **Lobby:** A thread principal espera por conexões `sock.accept()`.
2.  **Início do Jogo:** Quando 2 jogadores estão conectados, a thread principal lança 3 novas threads:
    * `t_game` (Thread de Lógica do Jogo): Controla o loop principal (`while game_is_running`).
    * `t1_listen` (Thread de Escuta P1): Fica em um loop `conn.recv()` para o Jogador 1.
    * `t2_listen` (Thread de Escuta P2): Fica em um loop `conn.recv()` para o Jogador 2.
3.  **Fluxo de Turno:**
    1.  A `t_game` rola o dado.
    2.  Verifica a vitória (>= 20).
    3.  Se não venceu, seleciona uma pergunta de `questions.json`.
    4.  Envia a pergunta (`{'tipo': 'PERGUNTA', ...}`) ao jogador ativo.
    5.  Espera por uma resposta da `player.incoming_queue` (com um timeout de 30s).
    6.  As threads de escuta (`t_listen`) recebem os dados, os decodificam e os colocam na `incoming_queue` do jogador correspondente.
    7.  A `t_game` calcula a nova posição (baseado no acerto/erro).
    8.  Verifica a vitória novamente (com bônus).
    9.  Envia a atualização (`{'tipo': 'STATUS', ...}`) para *ambos* os jogadores.
    10. Troca o turno e repete.

### Cliente (`client.py`)

1.  **Conexão:** Conecta-se ao servidor.
2.  **Loop Principal:** Entra em um `while True`.
3.  **Buffer de Leitura:** O cliente mantém um `buffer` de bytes. Ele lê do socket (`sock.recv()`) e adiciona ao buffer.
4.  **Processamento de Mensagens:** Ele continuamente verifica se o buffer contém o delimitador `\n`.
    * Se sim, ele extrai a mensagem, a decodifica de JSON e a processa (exibe na tela).
    * Se a mensagem for do tipo `PERGUNTA`, ele pausa, solicita um `input()` do usuário e envia a resposta de volta ao servidor (também com um `\n`).
    * Se for `STATUS` ou `AGUARDE`, apenas exibe a mensagem.
    * Se for `FIM`, exibe o vencedor e enc
