#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Web Server minimale in Python
# Attenzione: ho aggiunto print di traceback e corretto il controllo path assoluto
#

import sys
import os
import threading
from socket import *

# ---------- CONFIGURAZIONE ----------

HOST = 'localhost'
PORT = 8080
WWW_DIR = 'www'       # cartella contenente i file HTML/CSS/immagini

# Mappatura delle estensioni ai MIME types
MIME_TYPES = {
    '.html': 'text/html',
    '.htm':  'text/html',
    '.css':  'text/css',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.gif':  'image/gif',
    # Se aggiungi .svg, .webp, ecc., aggiungi qui
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp'
}

# ---------- FUNZIONE DI LOGGING ----------

def log_request(client_address, request_line, response_code, resource):
    """
    Stampa a console informazioni sul client e sulla richiesta
    client_address: tupla (IP, porta)
    request_line: la prima linea della richiesta HTTP
    response_code: codice HTTP restituito (es. 200, 404)
    resource: percorso del file richiesto
    """
    ip, port = client_address
    print(f"[REQUEST] {ip}:{port} \"{request_line}\"  -->  {response_code} (file: {resource})")


# ---------- GESTIONE DEL SINGOLO CLIENT ----------

def handle_client(connectionSocket, client_address):
    """
    Funzione eseguita in un thread separato per gestire la richiesta di un client.
    Legge la richiesta HTTP, analizza il metodo e il percorso,
    prova ad aprire il file corrispondente nella cartella www/,
    e restituisce 200 OK + contenuto, oppure 404 Not Found.
    """
    try:
        # Riceviamo fino a 4096 byte (basta per request GET basilari)
        raw_request = connectionSocket.recv(4096).decode('utf-8', errors='ignore')
        if not raw_request:
            connectionSocket.close()
            return

        # Estrarre la prima riga: es. "GET /index.html HTTP/1.1"
        request_lines = raw_request.splitlines()
        request_line = request_lines[0]
        parts = request_line.split()
        if len(parts) < 2:
            # Richiesta malformata: chiudo subito
            connectionSocket.close()
            return

        method, path = parts[0], parts[1]
        # Solo GET è supportato
        if method != 'GET':
            # 501 Not Implemented: metodo non supportato
            body = "<html><body><h1>501 Not Implemented</h1></body></html>"
            header = "HTTP/1.1 501 Not Implemented\r\n"
            header += "Content-Type: text/html\r\n"
            header += f"Content-Length: {len(body.encode())}\r\n"
            header += "\r\n"
            connectionSocket.send(header.encode())
            connectionSocket.send(body.encode())
            log_request(client_address, request_line, 501, path)
            connectionSocket.close()
            return

        # Determinare quale file servire
        # Se il path è "/" o "/index.html", usiamo index.html
        if path == '/' or path == '/index.html':
            filename = 'index.html'
        else:
            # Rimuovo il "/" iniziale
            filename = path.lstrip('/')
        # Compongo il percorso file all’interno di www/
        resource_path = os.path.join(WWW_DIR, filename)

        # ------- Controllo di sicurezza correggendo con percorsi assoluti -------
        # Prendo il percorso assoluto del file richiesto
        abs_resource = os.path.abspath(resource_path)
        # Per sicurezza, prendo anche il percorso assoluto della cartella www/
        abs_www_dir  = os.path.abspath(WWW_DIR)

        # Verifico che il file richiesto sia effettivamente dentro www/ (evito directory traversal)
        # NOTA: aggiungo os.sep dopo abs_www_dir, così "/wwwfile.html" non passa per "/www/"
        if not abs_resource.startswith(abs_www_dir + os.sep):
            raise FileNotFoundError

        # Provo ad aprire il file in modalità binaria
        with open(abs_resource, 'rb') as f:
            content = f.read()

        # Determino il MIME type in base all’estensione
        _, ext = os.path.splitext(filename)
        content_type = MIME_TYPES.get(ext.lower(), 'application/octet-stream')

        # Costruisco l’header di risposta
        header = "HTTP/1.1 200 OK\r\n"
        header += f"Content-Type: {content_type}\r\n"
        header += f"Content-Length: {len(content)}\r\n"
        header += "\r\n"

        # Invio header + corpo
        connectionSocket.send(header.encode())
        connectionSocket.send(content)

        log_request(client_address, request_line, 200, filename)

        # Chiudo la connessione con questo client
        connectionSocket.close()

    except FileNotFoundError:
        # File non esiste o tentativo di directory traversal: rispondo 404 Not Found
        try:
            body = ("<html>"
                    "<head><title>404 Not Found</title></head>"
                    "<body><h1>404 Not Found</h1>"
                    f"<p>Il file '{filename}' non &egrave; stato trovato.</p>"
                    "</body></html>")
            header = "HTTP/1.1 404 Not Found\r\n"
            header += "Content-Type: text/html\r\n"
            header += f"Content-Length: {len(body.encode())}\r\n"
            header += "\r\n"
            connectionSocket.send(header.encode())
            connectionSocket.send(body.encode())
            log_request(client_address, request_line, 404, filename)
        except Exception:
            # Se qualcosa va storto nella risposta 404, vogliamo comunque chiudere il socket
            pass
        finally:
            connectionSocket.close()

    except Exception:
        # In caso di errore generico, stampo il traceback su console ed effettuo chiusura
        print(f"[ERROR] durante la gestione del client {client_address}:")
        try:
            connectionSocket.close()
        except:
            pass


# ---------- AVVIO DEL SERVER TCP ----------

def main():
    # Se passo il numero di porta come argomento, lo uso; altrimenti 8080
    global PORT
    if len(sys.argv) >= 2:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            print("Uso: python3 server.py [porta]")
            sys.exit(1)

    # Creo il socket TCP (famiglia IPv4, tipo STREAM)
    serverSocket = socket(AF_INET, SOCK_STREAM)
    # Opzione per riutilizzare rapidamente la porta anche se in TIME_WAIT
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    try:
        serverSocket.bind((HOST, PORT))
    except Exception as e:
        print(f"Impossibile fare bind su {HOST}:{PORT}: {e}")
        sys.exit(1)

    serverSocket.listen(5)
    print(f"Web Server avviato: {HOST}:{PORT}")
    print(f"Document root: ./{WWW_DIR}/")
    print("Premi CTRL-C per terminare")

    try:
        while True:
            # Accetto connessioni in arrivo
            connectionSocket, client_address = serverSocket.accept()
            # Creo un thread dedicato per gestire il client
            thread = threading.Thread(
                target=handle_client,
                args=(connectionSocket, client_address)
            )
            thread.daemon = True  # il thread si chiude se il main process termina
            thread.start()

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interruzione da tastiera (CTRL-C).")
    finally:
        serverSocket.close()
        print("[SHUTDOWN] Server chiuso.")

if __name__ == "__main__":
    main()
