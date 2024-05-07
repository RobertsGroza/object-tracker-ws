import asyncio
import websockets

# Server data
PORT = 7890
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()


async def echo(websocket):
    # Store a copy of the connected client
    print("A client just connected")
    connected.add(websocket)

    # Handle incoming messages
    try:
        async for message in websocket:
            print("Received message from client: " + message)
            await websocket.send("Message received: " + message)

            # # Send a response to sender
            # for conn in connected:
            #     await conn.send("Someone said: " + message)
    # Handle disconnecting clients
    finally:
        print("REMOVE!")
        connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "localhost", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
