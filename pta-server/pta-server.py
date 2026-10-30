#!/usr/bin/env python3
import os
import socket

HOST = '0.0.0.0'
PORT = 11550

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, 'users.txt')
FILES_DIR = os.path.join(BASE_DIR, 'files')


def carregar_usuarios():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return {linha.strip() for linha in f if linha.strip()}


def atender_cliente(conn, addr, usuarios_validos):
    estado = "ESPERANDO"
    seq_esperado = None

    try:
        while True:
            dados = conn.recv(4096)
            if not dados:
                break

            try:
                mensagem = dados.decode('utf-8').strip('\r\n')
            except UnicodeDecodeError:
                break

            if not mensagem:
                continue

            partes = mensagem.split(' ')

            if len(partes) < 2 or not partes[0].isdigit():
                seq_str = partes[0] if partes else "0"
                conn.sendall(f"{seq_str} NOK".encode('utf-8'))
                if estado == "ESPERANDO":
                    break
                continue

            seq_num = int(partes[0])
            comando = partes[1]
            args = partes[2:]

            if seq_esperado is not None and seq_num != seq_esperado:
                conn.sendall(f"{seq_num} NOK".encode('utf-8'))
                if estado == "ESPERANDO":
                    break
                continue
            seq_esperado = seq_num + 1

            # ESTADO 1: ESPERANDO (Apresentação CUMP)
            if estado == "ESPERANDO":
                if comando == "CUMP" and len(args) == 1:
                    usuario = args[0]
                    if usuario in usuarios_validos:
                        conn.sendall(f"{seq_num} OK".encode('utf-8'))
                        estado = "PRONTO"
                    else:
                        conn.sendall(f"{seq_num} NOK".encode('utf-8'))
                        break
                else:
                    conn.sendall(f"{seq_num} NOK".encode('utf-8'))
                    break

            # ESTADO 2: PRONTO (LIST, PEGA, TERM)
            elif estado == "PRONTO":
                if comando == "LIST" and len(args) == 0:
                    try:
                        arquivos = sorted([
                            f for f in os.listdir(FILES_DIR)
                            if os.path.isfile(os.path.join(FILES_DIR, f))
                        ])
                        if not arquivos:
                            conn.sendall(f"{seq_num} NOK".encode('utf-8'))
                        else:
                            lista_str = ",".join(arquivos)
                            resposta = f"{seq_num} ARQS {len(arquivos)} {lista_str}"
                            conn.sendall(resposta.encode('utf-8'))
                    except Exception:
                        conn.sendall(f"{seq_num} NOK".encode('utf-8'))

                elif comando == "PEGA" and len(args) == 1:
                    nome_arq = args[0]
                    caminho_arq = os.path.join(FILES_DIR, nome_arq)

                    if os.path.isfile(caminho_arq) and os.path.dirname(os.path.abspath(caminho_arq)) == os.path.abspath(FILES_DIR):
                        try:
                            with open(caminho_arq, 'rb') as f:
                                conteudo_bytes = f.read()
                            tamanho = len(conteudo_bytes)
                            cabecalho = f"{seq_num} ARQ {tamanho} ".encode('utf-8')
                            conn.sendall(cabecalho + conteudo_bytes)
                        except Exception:
                            conn.sendall(f"{seq_num} NOK".encode('utf-8'))
                    else:
                        conn.sendall(f"{seq_num} NOK".encode('utf-8'))

                elif comando == "TERM" and len(args) == 0:
                    conn.sendall(f"{seq_num} OK".encode('utf-8'))
                    break

                else:
                    conn.sendall(f"{seq_num} NOK".encode('utf-8'))

    finally:
        conn.close()


def main():
    usuarios_validos = carregar_usuarios()
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(5)
    print(f"[*] Servidor PTA escutando em {HOST}:{PORT}...")

    try:
        while True:
            conn, addr = servidor.accept()
            atender_cliente(conn, addr, usuarios_validos)
    except KeyboardInterrupt:
        print("\n[*] Encerrando servidor PTA.")
    finally:
        servidor.close()


if __name__ == '__main__':
    main()
