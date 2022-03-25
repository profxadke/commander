#!/usr/bin/env python

import asyncio as aio
import websockets as wss
import subprocess as sp

USE_NL_DELIMETER = True

async def commander_x(ws):
    try:
        async for cmd in ws:
            print(cmd)
            if cmd.endswith('!'):
                cmd = cmd[:-1]
                with sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, bufsize=1, universal_newlines=True, shell=True) as prox:
                    for line in unbuffered(prox):
                        line = line
                        await ws.send(line)
                    for line in unbuffered(prox, 'stderr'):
                        line = line
                        await ws.send(line)
            else:
                with sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=True) as prox:
                    for line in prox.stdout:
                        line = line.rstrip() + b"\n"
                        await ws.send(line)
                    for line in prox.stderr:
                        line = line.rstrip() + b"\n"
                        await ws.send(line)
            prox.kill()
            await ws.send(cmd)
    except wss.ConnectionClosedError:
        pass


async def main():
    async with wss.serve(commander_x, "localhost", 8888):
        await aio.Future()  # run forever


if __name__ == '__main__':
    aio.run(main())
