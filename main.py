#!/usr/bin/env python3


from typing import List, Optional

import subprocess, socket, psutil, signal
from random import randint
from fastapi import (
    FastAPI,
    HTTPException
); from fastapi.responses import (
    FileResponse
); from pydantic import BaseModel


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


proc_ids = procs = []
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
@app.get('/wsprocess')
@app.get('/ws')
@app.get('/wsprocs')
@app.get('/wproc')
@app.get('/wprocess')
def return_ws_page():
    return FileResponse('root/websocket.html')


@app.put('/proc')
@app.put('/process')
def init_proc(proc_info: Command):
    """
    TODO: Return proc info and detach from parent while spying it using its PID, instead of returning the STDOUT.
    """
    global proc_ids, proc, procs
    cmd = f'{proc_info.name} {" ".join(proc_info.args)}'
    print(cmd)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)
    pid = proc.pid
    proc_ids.append(pid)
    for _proc in psutil.process_iter():
        if _proc.pid == pid:
            procs.append(_proc)
    return {'initiated': pid}


def proc_enum(proc): 
    try:
        if proc.is_running():
            return proc.as_dict()
        return {
            'name': proc.name(), 
            'pid': proc.pid
        }
    except psutil.NoSuchProcess:
        pass


@app.get('/proc')
@app.get('/procs')
@app.get('/process')
@app.get('/procinfo')
@app.get('/processinfo')
@app.get('/process_info')
@app.get('/proc_info')
def return_proc_info(pid: Optional[int] = 0, system_wide: Optional[bool] = False):
    resp = [];
    if pid:
        if system_wide:
            for proc in psutil.process_iter():
                if proc.pid == pid:
                    return proc_enum(proc)
        else:
            for proc in procs:
                if 'pid' in dir(proc):
                    if proc.pid == pid:
                        return proc_enum(proc)
    else:
        for proc in procs:
            if 'pid' in dir(proc):
                enum = proc_enum(proc)
                if enum:
                    resp.append(enum)
    return resp


@app.get('/std')
@app.get('/stdout')
@app.get('/stderr')
def return_std_out_err():
    """
    Returns: [str(STDOUT), str(STDERR)]
    """
    if proc:
        return {'std[out, err]': proc.communicate()}
    raise HTTPException(status_code=406, detail='No running process.')


@app.delete('/proc')
@app.delete('/process')
def kill_proc():
    global proc_ids, proc, procs
    if proc:
        pid = proc.pid; proc_ids.remove(pid)
        proc.kill(); proc = None
        for _proc in procs:
            if 'pid' in dir(_proc):
                if _proc.pid == pid:
                    procs.remove(_proc)
        return {'killed': pid}
    raise HTTPException(status_code=406, detail='No running process.')


if __name__ == '__main__':
    random_port = randint(1025, 65534)
    while is_port_in_use(random_port) and is_port_in_use(random_port) + 1:
        random_port = randint(1025, 65534)
    if __import__('os').getuid():
        __import__('webbrowser').open_new_tab(f'http://localhost:{random_port}')
    ws_pid = __import__('os').system(f'python3 ./commanderX.py {random_port + 1} &')
    __import__('uvicorn').run('main:app', host='0.0.0.0', port=random_port, reload=True)
    __import__('os').kill(ws_pid, signal.SIGKILL)
    __import__('sys').exit(0)
