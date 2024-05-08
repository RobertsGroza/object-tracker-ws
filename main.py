import asyncio
import websockets
import cv2
import json
import base64
import time

# Server data
PORT = 7890
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()
video = "riteni"


async def echo(websocket):
    # Store a copy of the connected client
    print("A client just connected")
    connected.add(websocket)

    # Handle incoming messages
    try:
        async for message in websocket:
            print("Received message from client: " + message)
            await websocket.send("Message received: " + message)

            if message == "play":
                await websocket.send("Streaming started")
                cap = cv2.VideoCapture(f'../object-tracker-shared/videos/{video}.mp4')
                position_file = open(f'../object-tracker-shared/outputs/{video}.txt')

                prev_frame_time = 0
                frame_count = 0
                fps_sum = 0
                stream_width = 640
                stream_height = 360
                success, img = cap.read()

                video_summary = json.loads(position_file.readline().strip())
                await websocket.send(json.dumps({"type": "video_summary", "content": video_summary}))

                while success:
                    new_frame_time = time.time()
                    frame_count += 1

                    # Get coefficients for object position & width adjustments to stream size
                    width_scale_coefficient = stream_width / img.shape[1]
                    height_scale_coefficient = stream_height / img.shape[0]

                    # Process frame
                    resized = cv2.resize(img, (stream_width, stream_height))
                    success, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 30])

                    # Process & adjust object information
                    object_positions = json.loads(position_file.readline().strip())
                    for object_position in object_positions:
                        object_position["x"] = object_position["x"] * width_scale_coefficient
                        object_position["y"] = object_position["y"] * height_scale_coefficient
                        object_position["width"] = object_position["width"] * width_scale_coefficient
                        object_position["height"] = object_position["height"] * height_scale_coefficient

                    # Send message
                    await websocket.send(json.dumps({
                        "frame": base64.b64encode(buffer).decode("utf-8"),
                        "positions": object_positions
                    }))

                    success, img = cap.read()
                    fps = 1 / (new_frame_time - prev_frame_time)
                    prev_frame_time = new_frame_time
                    fps_sum += fps

                print("AVERAGE FPS: " + str(fps_sum / frame_count))
            else:
                await websocket.send("Unknown message!")

    # Handle disconnecting clients
    finally:
        print("A client just disconnected")
        connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "localhost", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
