import asyncio
import websockets
import cv2
import json
import base64

# Server data
PORT = 7890
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()

async def echo(websocket):
    # Store a copy of the connected client
    print("A client just connected")
    connected.add(websocket)

    # TODO: Probably we will need some variable here, that says if video is playing
    # TODO: And if the variable is true, it just loops through frames

    # Handle incoming messages
    try:
        async for message in websocket:
            print("Received message from client: " + message)
            await websocket.send("Message received: " + message)

            if message == "play":
                # TODO: Send video frame by frame with object
                # TODO: At first send just first frame
                print("PLAY")
                await websocket.send("Message received: " + message)
                cap = cv2.VideoCapture("./riteni.mp4")
                success, img = cap.read()
                # TODO: Pamēģināt dabūt normālu performanci - pagaidām ir diezgan shitty PFS
                # await websocket.send(json.dumps({"frame": img.tolist()}))
                # await websocket.send(json.dumps({"frame": "".join(map(str, img.tolist()))}))
                while success:
                    success, buffer = cv2.imencode('.png', img)  # TODO: Maybe redundant step?
                    await websocket.send(json.dumps({"frame": base64.b64encode(buffer).decode("utf-8")}))
                    success, img = cap.read()
            elif message == "stop":
                # TODO: Stop sending video frames
                print("STOP")
                await websocket.send("Message received: " + message)
            elif message == "setVideo":
                # TODO: Change video
                # TODO: Maybe add video in message payload. Create message { type: string, payload: object }
                print("SET_VIDEO")
                await websocket.send("Message received: " + message)
            else:
                await websocket.send("Unknown message!")

            # # Send a response to sender
            # for conn in connected:
            #     await conn.send("Someone said: " + message)
    # Handle disconnecting clients
    finally:
        print("A client just disconnected")
        connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "localhost", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
