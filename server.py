import json
import queue
import random
import socket
import threading
import time

HOST = "localhost"
PORT = 8788
BUFFER_SIZE = 2048
RESPONSE_TIMEOUT_SEC = 30.0


class Player:
    def __init__(self, conn, addr, player_id):
        self.conn = conn
        self.addr = addr
        self.id = player_id
        self.pos = 0
        self.incoming_queue = queue.Queue()


def load_questions(json_file="questions.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
        print("Carregando perguntas.")
        return questions
    except Exception as e:
        print(f"Não foi possível carregar as perguntas: {e}")
        return None


def send_message(connection, message_dict):
    try:
        message_with_delimiter = json.dumps(message_dict).encode("utf-8") + b"\n"
        connection.sendall(message_with_delimiter)
        return True
    except (ConnectionResetError, BrokenPipeError):
        print("Cliente desconectado.")
        return False


def listen_for_client(player, game_is_running_event):
    print(f"[Thread - {player.id}] Iniciada.")
    while game_is_running_event.is_set():
        try:
            data = player.conn.recv(BUFFER_SIZE)
            if not data:
                print(f"[Thread - {player.id}] Cliente desconectou.")
                break

            response = json.loads(data.decode("utf-8"))
            player.incoming_queue.put(response)

        except (ConnectionResetError, BrokenPipeError):
            print(f"[Thread - {player.id}] Cliente desconectou abruptamente.")
            break
        except json.JSONDecodeError:
            print(f"[Thread - {player.id}] Recebeu dado mal formatado.")
        except OSError as e:
            if game_is_running_event.is_set():
                print(f"[Thread - {player.id}] Erro de Socket: {e}")
            break

    print(f"[Thread - {player.id}] Encerrando.")
    game_is_running_event.clear()


def game_loop(player1, player2, questions, game_is_running_event):
    print("O jogo começou!")

    players = [player1, player2]
    current_turn_index = 0

    send_message(
        players[0].conn,
        {
            "tipo": "STATUS",
            "msg": "O Jogo começou! É a sua vez.",
            "p1_pos": 0,
            "p2_pos": 0,
            "turno_de": "jogador_1",
            "sua_posicao": 0,
        },
    )
    send_message(
        players[1].conn,
        {
            "tipo": "STATUS",
            "msg": "O Jogo começou! Aguarde a vez do Jogador 1.",
            "p1_pos": 0,
            "p2_pos": 0,
            "turno_de": "jogador_1",
            "sua_posicao": 0,
        },
    )

    try:
        while game_is_running_event.is_set():
            active_player = players[current_turn_index]
            waiting_player = players[1 - current_turn_index]

            print(f"\nTurno de: {active_player.id}")

            roll = random.randint(1, 6)
            print(f"  Dado rolado: {roll}")
            temp_pos = active_player.pos + roll

            if temp_pos >= 20:
                print(f"  JOGADOR ATINGIU A CASA {temp_pos} (>= 20)")
                active_player.pos = 20
                feedback_msg = f"{active_player.id} tirou {roll} e chegou na casa {active_player.pos}!"

                send_message(
                    active_player.conn,
                    {"tipo": "FIM", "vencedor": active_player.id, "msg": feedback_msg},
                )
                send_message(
                    waiting_player.conn,
                    {"tipo": "FIM", "vencedor": active_player.id, "msg": feedback_msg},
                )
                break

            question = random.choice(questions)

            send_message(
                active_player.conn,
                {
                    "tipo": "PERGUNTA",
                    "texto": question["pergunta"],
                    "opcoes": question["opcoes"],
                    "msg_dado": f"Você tirou {roll} no dado. Sua posição atual é {active_player.pos}, indo para {temp_pos}.",
                },
            )

            send_message(
                waiting_player.conn,
                {
                    "tipo": "AGUARDE",
                    "msg": f"{active_player.id} está respondendo uma pergunta (casa {temp_pos})...",
                },
            )

            user_answer = None
            try:
                response = active_player.incoming_queue.get(
                    timeout=RESPONSE_TIMEOUT_SEC
                )

                if response and response.get("tipo_resposta") == "RESPOSTA_JOGADOR":
                    user_answer = response.get("resposta")
                else:
                    print(f"  {active_player.id} enviou resposta inválida.")

            except queue.Empty:
                print(f"  {active_player.id} demorou muito para responder (Timeout).")
                user_answer = None
                send_message(
                    active_player.conn,
                    {
                        "tipo": "AGUARDE",
                        "msg": "Tempo esgotado! Resposta considerada errada.",
                    },
                )

            final_pos = 0
            feedback_msg = ""

            if user_answer == question["resposta_correta"]:
                final_pos = temp_pos + 2
                feedback_msg = (
                    f"{active_player.id} ACERTOU! Avançou +2 casas (Total: {roll}+2)."
                )
                print(f"  Jogador acertou! Posição final: {final_pos}")
            else:
                final_pos = temp_pos - 1
                if final_pos < 0:
                    final_pos = 0
                feedback_msg = f"{active_player.id} ERROU (ou tempo esgotou)! Voltou 1 casa (Total: {roll}-1)."
                print(f"  Jogador errou! Posição final: {final_pos}")

            active_player.pos = final_pos

            if final_pos >= 20:
                print(f"  FIM DE JOGO! Vencedor: {active_player.id}")
                active_player.pos = 20

                send_message(
                    active_player.conn,
                    {"tipo": "FIM", "vencedor": active_player.id, "msg": feedback_msg},
                )
                send_message(
                    waiting_player.conn,
                    {"tipo": "FIM", "vencedor": active_player.id, "msg": feedback_msg},
                )
                break

            next_turn_id = waiting_player.id
            status_update = {
                "tipo": "STATUS",
                "msg": feedback_msg,
                "p1_pos": players[0].pos,
                "p2_pos": players[1].pos,
                "turno_de": next_turn_id,
            }

            status_p1 = status_update.copy()
            status_p1["sua_posicao"] = players[0].pos
            status_p2 = status_update.copy()
            status_p2["sua_posicao"] = players[1].pos

            if not send_message(players[0].conn, status_p1):
                break
            if not send_message(players[1].conn, status_p2):
                break

            current_turn_index = 1 - current_turn_index
            time.sleep(1)

    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        print("Jogo encerrado.")
        game_is_running_event.clear()


def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(2)

    print(f"Servidor iniciado em {HOST}:{PORT}. Aguardando jogadores...")

    questions = load_questions()
    if not questions:
        sock.close()
        return

    try:
        while True:
            player_list = []

            while len(player_list) < 2:
                try:
                    conn, addr = sock.accept()
                    player_id = len(player_list) + 1
                    print(f"Jogador {player_id} ({addr}) conectou!")

                    player = Player(conn, addr, f"jogador_{player_id}")
                    player_list.append(player)

                    send_message(
                        conn,
                        {
                            "tipo": "AGUARDE",
                            "msg": f"Você é o Jogador {player_id}. Aguardando oponente...",
                        },
                    )

                except KeyboardInterrupt:
                    print("Servidor fechando (lobby)...")
                    sock.close()
                    return

            print("Dois jogadores conectados. Iniciando o jogo...")

            game_is_running_event = threading.Event()
            game_is_running_event.set()

            player1 = player_list[0]
            player2 = player_list[1]

            t1_listen = threading.Thread(
                target=listen_for_client, args=(player1, game_is_running_event)
            )
            t2_listen = threading.Thread(
                target=listen_for_client, args=(player2, game_is_running_event)
            )

            t_game = threading.Thread(
                target=game_loop,
                args=(player1, player2, questions, game_is_running_event),
            )

            t1_listen.start()
            t2_listen.start()
            t_game.start()

            t_game.join()
            print("Loop do jogo terminou. Aguardando threads de escuta finalizarem...")

            t1_listen.join()
            t2_listen.join()

            print("Ambos os jogadores foram desconectados. Voltando ao lobby...")

            player1.conn.close()
            player2.conn.close()

    except KeyboardInterrupt:
        print("\nServidor sendo encerrado manualmente...")
    finally:
        print("Encerrando socket principal do servidor.")
        sock.close()


if __name__ == "__main__":
    start_server()
