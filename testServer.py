#!/usr/bin/env python3
import socket

HOST = 'localhost'
PORT = 8080

def send_request(path):
    request = f"GET {path} HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(request.encode())
        data = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    header, _, _ = data.partition(b'\r\n\r\n')
    status_line = header.decode().splitlines()[0]
    print(f"Richiesta {path:25} → {status_line}")

if __name__ == "__main__":
    percorsi = [
        "/", "/index.html", "/pagina1.html", "/pagina2.html", "/pagina3.html",
        "/styles.css", "/images/animal.jpg", "/images/dance.gif", "/images/unibo.png",
        "/nonEsiste.html"
    ]
    for p in percorsi:
        send_request(p)
