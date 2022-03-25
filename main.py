#!/usr/bin/env python3

from typing import List

import subprocess, socket
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response,
    HTTPException
); from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    RedirectResponse
); from pydantic import BaseModel
from random import randint


USE_NL_DELIMETER = True


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def unbuffered(proc, stream='stdout'):
    stream = getattr(proc, stream)
    with __import__('contextlib').closing(stream):
        while True:
            last = stream.read(22528) # read up to 22528(:80)chars
            # Stop when end of stream reached
            if not last:
                if proc.poll() is not None:
                    break
            else:
                yield last


async def stream_std(cmd):
    if cmd.endswith('!'):
        cmd = cmd[:-1]
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True, shell=True) as prox:
            for line in unbuffered(prox):
                yield line
            for line in unbuffered(prox, 'stderr'):
                yield line
    else:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True, shell=True) as prox:
            for line in prox.stdout:
                yield line
            for line in prox.stderr:
                yield line


class Command(BaseModel):
    name: str
    args: List[str]


proc_ids = []
app = FastAPI()
proc = None


@app.get('/')
def root():
    return FileResponse('root/index.html')


@app.get('/yokto.js')
def yokto():
    return FileResponse('root/yokto.js')


@app.get('/style.css')
def style():
    return FileResponse('root/style.css')

@app.get('/wsproc')
@app.get('/ws')
@app.get('/wsprocs')
@app.get('/wproc')
def return_ws_page():
    return FileResponse('root/websocket.html')


@app.put('/proc')
def init_proc(proc_info: Command):
    """
    TODO: Return proc info and detach from parent while spying it using its PID, instead of returning the STDOUT.
    """
    global proc_ids, proc
    cmd = f'{proc_info.name} {" ".join(proc_info.args)}'
    print(cmd)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)
    proc_ids.append(proc.pid)
    return {'initiated': proc.pid}


@app.get('/std')
def return_std_out_err():
    """
    Returns: [str(STDOUT), str(STDERR)]
    """
    if proc:
        return {'std[out, err]': proc.communicate()}
    raise HTTPException(status_code=406, detail='No running process.')


@app.delete('/proc')
def kill_proc():
    global proc_ids, proc
    if proc:
        pid = proc.pid; proc_ids.remove(pid)
        proc.kill(); proc = None
        return {'killed': pid}
    raise HTTPException(status_code=406, detail='No running process.')


@app.websocket("/procopn")
async def websocket_endpoint(ws: WebSocket):
    print(ws)
    await ws.accept()
    try:
        while 1:
            cmd = await ws.receive_text()
            print(cmd)
            if cmd.endswith('!'):
                cmd = cmd[:-1]
                use_lines = False
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True, shell=True) as prox:
                if use_lines:
                    for line in prox.stdout:
                        line = line.rstrip()
                        await ws.send_text(line)
                    for line in prox.stderr:
                        line = line.rstrip()
                        await ws.send_text(line)
                else:
                    for line in unbuffered(prox):
                        await ws.send_text(line)
                    for line in unbuffered(prox, 'stderr'):
                        await ws.send_text(line)
    except WebSocketDisconnect:
        print(ws)


if __name__ == '__main__':
    random_port = randint(1025, 65534)
    while is_port_in_use(random_port):
        random_port = randint(1025, 65534)
    __import__('webbrowser').open_new_tab(f'http://localhost:{random_port}')
    __import__('os').system('python3 ./commanderX.py &')
    __import__('uvicorn').run('main:app', host='0.0.0.0', port=random_port, reload=True)
