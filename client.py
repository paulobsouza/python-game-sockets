import json
import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

HOST = "localhost"
PORT = 8788
BUFFER_SIZE = 2048

# --- CONFIGURAÇÕES DE ESTILO ---
BACKGROUND_COLOR = "#FBEAEB"  # Rosa pálido
PRIMARY_COLOR = "#FF69B4"  # Rosa Choque (para destaque)
SECONDARY_COLOR = "#D8BFD8" # Lavanda (para botões)
FONT_DEFAULT = ("Helvetica", 12)
FONT_TITLE = ("Helvetica", 14, "bold")
# --- FIM CONFIGURAÇÕES DE ESTILO ---


class GameClient(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Jogo de Tabuleiro - Quiz de TI")
        self.geometry("600x650")
        self.configure(bg=BACKGROUND_COLOR) # Cor de fundo da janela

        self.incoming_queue = queue.Queue()

        self.status_label = tk.Label(
            self, text="Conectando...", font=FONT_TITLE, pady=10, bg=BACKGROUND_COLOR, fg=PRIMARY_COLOR
        )
        self.status_label.pack()

        # Área de Log
        self.log_area = scrolledtext.ScrolledText(
            self, 
            state="disabled", 
            height=15, 
            width=70, 
            font=("Consolas", 10), 
            bg="#FFFFFF", # Fundo branco para o log
            fg="#333333",
            relief=tk.FLAT,
            bd=5
        )
        self.log_area.pack(pady=5, padx=10)

        # Frame da Pergunta
        self.question_frame = tk.LabelFrame(
            self, 
            text="Pergunta", 
            font=FONT_DEFAULT, 
            padx=10, 
            pady=10,
            bg=BACKGROUND_COLOR, 
            fg="#6A5ACD", # Roxo sutil para o título do frame
            relief=tk.GROOVE 
        )
        self.question_frame.pack(pady=10, padx=10, fill="x")

        self.question_label = tk.Label(
            self.question_frame,
            text="Aguardando sua vez...",
            font=("Helvetica", 12, "italic"),
            wraplength=550,
            bg=BACKGROUND_COLOR,
            fg="#555555"
        )
        self.question_label.pack()

        self.dado_label = tk.Label(self.question_frame, text="", font=("Helvetica", 10), bg=BACKGROUND_COLOR)
        self.dado_label.pack()

        # Frame dos Botões de Resposta
        self.button_frame = tk.Frame(self, bg=BACKGROUND_COLOR)
        self.button_frame.pack(pady=15)

        self.buttons = {}
        options = [
            ("A", SECONDARY_COLOR), 
            ("B", SECONDARY_COLOR), 
            ("C", PRIMARY_COLOR), 
            ("D", PRIMARY_COLOR)
        ]
        
        for i, (option, color) in enumerate(options):
            button = tk.Button(
                self.button_frame,
                text=option,
                font=("Helvetica", 12, "bold"),
                wraplength=280,
                height=3,
                justify="center",
                bg=color, # Cor de fundo dos botões
                fg="#FFFFFF", # Texto branco
                activebackground=PRIMARY_COLOR, # Cor ao clicar
                activeforeground="#FFFFFF",
                relief=tk.RAISED, # Simula bordas arredondadas (Raised/Sunken são os melhores no Tkinter)
                bd=3, # Espessura da borda
                command=lambda opt=option: self.send_answer(opt),
            )

            # Posicionamento dos botões (2x2)
            button.grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="nsew")
            self.button_frame.grid_columnconfigure(i % 2, weight=1)
            self.buttons[option] = button
            
        self.set_buttons_state(False)

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.add_log(f"Conectado ao servidor do jogo em {HOST}:{PORT}")

            self.buffer = b""

            self.network_thread = threading.Thread(
                target=self.listen_for_messages, daemon=True
            )
            self.network_thread.start()

            # Inicia o loop para processar mensagens da fila (necessário para Tkinter)
            self.process_incoming_messages()

        except Exception as e:
            messagebox.showerror(
                "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}"
            )
            self.destroy()

    def add_log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.config(state="disabled")
        self.log_area.see(tk.END)

    def set_buttons_state(self, enabled):
        state = "normal" if enabled else "disabled"
        for button in self.buttons.values():
            button.config(state=state)

    def send_answer(self, answer):
        self.add_log(f"-> Você respondeu: {answer}")

        self.set_buttons_state(False)

        resposta_json = json.dumps(
            {"tipo_resposta": "RESPOSTA_JOGADOR", "resposta": answer}
        )

        try:
            self.sock.sendall(resposta_json.encode("utf-8") + b"\n")
        except Exception as e:
            self.add_log(f"[ERRO] Falha ao enviar resposta: {e}")
            messagebox.showerror("Erro de Rede", "Não foi possível enviar a resposta.")
            self.destroy()

    def listen_for_messages(self):
        while True:
            try:
                # 1. Tenta encontrar o delimitador '\n' no buffer (Solução de Delimitação TCP)
                try:
                    terminador_pos = self.buffer.index(b"\n")
                    message_data = self.buffer[:terminador_pos]
                    self.buffer = self.buffer[terminador_pos + 1 :]

                    if message_data:
                        comando_servidor = json.loads(message_data.decode("utf-8"))
                        self.incoming_queue.put(comando_servidor)
                    else:
                        continue

                # 2. Se não encontrou '\n', lê mais dados do socket (Chamada bloqueante)
                except ValueError:
                    data = self.sock.recv(BUFFER_SIZE)
                    if not data:
                        self.incoming_queue.put({"tipo": "DESCONECTADO"})
                        break
                    self.buffer += data

            except (ConnectionResetError, BrokenPipeError):
                self.incoming_queue.put({"tipo": "DESCONECTADO"})
                break
            except Exception as e:
                print(f"Erro na thread de rede: {e}")
                self.incoming_queue.put({"tipo": "DESCONECTADO"})
                break

    def process_incoming_messages(self):
        """Processa mensagens da fila de forma segura no loop principal do Tkinter."""
        try:
            while not self.incoming_queue.empty():
                msg = self.incoming_queue.get_nowait()

                tipo = msg.get("tipo")

                if tipo == "PERGUNTA":
                    self.add_log(f"\n[PERGUNTA] {msg['texto']}")
                    self.question_label.config(
                        text=msg["texto"], font=("Helvetica", 12, "bold"), bg=BACKGROUND_COLOR
                    )
                    self.dado_label.config(text=f"({msg['msg_dado']})", bg=BACKGROUND_COLOR)

                    # Atualiza o texto das opções nos botões
                    for opt in ["A", "B", "C", "D"]:
                        self.buttons[opt].config(
                            text=f"{opt}) {msg['opcoes'].get(opt, 'N/A')}"
                        )

                    self.set_buttons_state(True)

                elif tipo == "STATUS":
                    self.add_log(f"[ATUALIZAÇÃO] {msg['msg']}")
                    self.add_log(
                        f"  > P1: {msg['p1_pos']} | P2: {msg['p2_pos']} | Turno: {msg['turno_de']}"
                    )
                    self.status_label.config(text=f"Sua Posição: {msg['sua_posicao']}")

                    self.question_label.config(
                        text="Aguardando oponente...", font=("Helvetica", 12, "italic"), bg=BACKGROUND_COLOR
                    )
                    self.dado_label.config(text="", bg=BACKGROUND_COLOR)

                elif tipo == "AGUARDE":
                    self.add_log(f"... {msg['msg']} ...")
                    self.question_label.config(
                        text="Aguardando oponente...", font=("Helvetica", 12, "italic"), bg=BACKGROUND_COLOR
                    )
                    self.dado_label.config(text="", bg=BACKGROUND_COLOR)
                    self.set_buttons_state(False)

                elif tipo == "FIM":
                    self.add_log("\n" + "!" * 30)
                    self.add_log(f"FIM DE JOGO! {msg.get('msg', '')}")
                    self.add_log(f"{msg['vencedor']} venceu!")
                    self.add_log("!" * 30)
                    self.set_buttons_state(False)
                    self.question_label.config(
                        text=f"FIM DE JOGO! {msg['vencedor']} venceu!", bg=BACKGROUND_COLOR
                    )
                    messagebox.showinfo("Fim de Jogo", f"{msg['vencedor']} venceu!")

                elif tipo == "DESCONECTADO":
                    self.add_log("[ERRO] O servidor desconectou.")
                    messagebox.showerror(
                        "Erro de Rede", "A conexão com o servidor foi perdida."
                    )
                    self.destroy()
                    return

        except queue.Empty:
            pass

        # Garante que esta função seja chamada novamente em 100ms
        self.after(100, self.process_incoming_messages)


if __name__ == "__main__":
    app = GameClient()
    app.mainloop()
