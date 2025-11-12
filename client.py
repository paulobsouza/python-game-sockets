import json
import socket

host = "localhost"
port = 8788

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))
print(f"Conectado ao servidor do jogo em {host}:{port}")

try:
    buffer = b""

    while True:
        try:
            terminador_pos = buffer.index(b"\n")

            message_data = buffer[:terminador_pos]
            buffer = buffer[terminador_pos + 1 :]

            if message_data:
                comando_servidor = json.loads(message_data.decode("utf-8"))
            else:
                continue

        except ValueError:
            data = sock.recv(2048)
            if not data:
                print("O servidor encerrou a conexão.")
                break

            buffer += data
            continue

        if comando_servidor.get("tipo") == "PERGUNTA":
            print("\n" + "=" * 30)
            print(f"PERGUNTA: {comando_servidor['texto']}")
            print(f"({comando_servidor['msg_dado']})")
            print("Opções:")
            for key, value in comando_servidor["opcoes"].items():
                print(f"  {key}) {value}")

            resposta_usuario = input("Sua resposta (A, B, C ou D): ").upper()

            resposta_json = json.dumps(
                {"tipo_resposta": "RESPOSTA_JOGADOR", "resposta": resposta_usuario}
            )

            sock.sendall(resposta_json.encode("utf-8") + b"\n")

        elif comando_servidor.get("tipo") == "STATUS":
            print("\n" + "-" * 30)
            print(f"[ATUALIZAÇÃO]: {comando_servidor['msg']}")
            print(f"  > Posição Jogador 1: {comando_servidor['p1_pos']}")
            print(f"  > Posição Jogador 2: {comando_servidor['p2_pos']}")
            print(f"  > É a vez de: {comando_servidor['turno_de']}")
            print(f"  > Sua posição atual: {comando_servidor['sua_posicao']}")
            print("-" * 30)

        elif comando_servidor.get("tipo") == "AGUARDE":
            print(f"\n... {comando_servidor['msg']} ...")

        elif comando_servidor.get("tipo") == "FIM":
            print("\n" + "!" * 30)
            print(f"FIM DE JOGO! {comando_servidor.get('msg', '')}")
            print(f"{comando_servidor['vencedor']} venceu!")
            print("!" * 30)
            break

except Exception as e:
    print(f"Erro na comunicação: {e}")

finally:
    print("Desconectando do servidor.")
    sock.close()
