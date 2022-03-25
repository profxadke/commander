#!/usr/bin/env python

import os 
from signal import (
    SIGKILL,
    SIGINT
); from subprocess import (
    Popen,
    PIPE
); from websock import WebSocketServer as WS


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


def invoke_commanderX(client, cmd):
    if cmd.startswith('SIG'):
        if cmd.startswith('SIGINT:'):
            cmd, pid = cmd.split(':')
            ws.send(client, f'!MSG:Interrupting({pid})')
            os.kill(int(pid), SIGINT)
        elif cmd.startswith('SIGKILL:'):
            cmd, pid = cmd.split(':')
            os.kill(int(pid), SIGKILL)
            ws.send(client, f'!MSG:KILLED({pid})')
        else:
            ws.send(client, f'!MSG:UNSUPPORTED_SIGNAL({pid})')
    elif cmd.startswith('!'):
        cmd = cmd[1:];
        with Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True) as prox:
            ws.send(client, f'!PID:{prox.pid}\n')
            for line in unbuffered(prox):
                ws.send(client, line.decode())
            for line in unbuffered(prox, 'stderr'):
                ws.send(client, line.decode())
            prox.kill()
    else:
        with Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True) as prox:
            ws.send(client, f'!PID:{prox.pid}\n')
            for line in prox.stdout:
                line = line.rstrip().decode() + "\n"
                ws.send(client, line)
            for line in prox.stderr:
                line = line.rstrip().decode() + "\n"
                ws.send(client, line)
            prox.kill()


def on_data_receive(client, data):
    invoke_commanderX(client, data)


def on_connection_open(client): pass
    
def on_error(exception): pass
    
def on_connection_close(client): pass

def on_server_destruct(): pass

print(__import__('sys').argv[1])
ws = WS(
    "0.0.0.0",
    int(__import__("sys").argv[1]),
    on_data_receive=on_data_receive,
    on_connection_open=on_connection_open,
    on_error=on_error,
    on_connection_close=on_connection_close,
    on_server_destruct=on_server_destruct
);


if __name__ == '__main__':
    ws.serve_forever()
