import json
import os
import socket
import threading
import logging
from datetime import datetime

import uvicorn
from jinja2 import Template
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Ініціалізація логера
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

storage_dir = "/app/storage"
data_file = os.path.join(storage_dir, "data.json")

if not os.path.exists(storage_dir):
    os.makedirs(storage_dir)
if not os.path.exists(data_file):
    with open(data_file, "w") as f:
        json.dump([], f)


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html") as f:
        template = Template(f.read())
    return template.render()


@app.get("/message", response_class=HTMLResponse)
async def message():
    with open("templates/message.html") as f:
        template = Template(f.read())
    return template.render()


@app.post("/submit")
async def submit_form(request: Request):
    form_data = await request.form()
    username = form_data["username"]
    message = form_data["message"]

    udp_client(username, message)

    return RedirectResponse(url="/message", status_code=303)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    with open("templates/error.html") as f:
        template = Template(f.read())
    return HTMLResponse(content=template.render(), status_code=404)


def udp_client(username, message):
    data = json.dumps(
        {"date": str(datetime.now()), "username": username, "message": message}
    )
    logger.info("send")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data.encode(), ("127.0.0.1", 8080))


def socket_server():
    logger.info("Socket server starting")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("127.0.0.1", 8080))
    logger.info("Socket server bound to port 8080")

    while True:
        message, _ = server_socket.recvfrom(4096)
        logger.info(f"Received message: {message.decode()}")

        with open(data_file, "r+", encoding="utf-8") as f:
            logger.info("Opening file for reading")
            try:
                file_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("JSONDecodeError encountered, initializing empty list")
                file_data = []

            new_message = json.loads(message.decode())
            file_data.append(new_message)
            logger.info(f"Appending message: {new_message}")

            f.seek(0)
            json.dump(file_data, f, ensure_ascii=False, indent=4)
            f.truncate()
            logger.info("File updated")


def start_socket_server():
    logger.info("Starting socket server thread")
    thread = threading.Thread(target=socket_server)
    thread.daemon = True
    thread.start()
    logger.info("Socket server thread started")


if __name__ == "__main__":
    start_socket_server()
    uvicorn.run(app, host="0.0.0.0", port=3000)
