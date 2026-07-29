import asyncio
import websockets

async def test():
    try:
        async with websockets.connect('ws://localhost:8001/api/v1/ws') as ws:
            print('Connected!')
            await ws.send('{\"type\": \"ping\"}')
            print(await ws.recv())
    except Exception as e:
        print(type(e), e)

asyncio.run(test())
