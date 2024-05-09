import asyncio
import websockets
import cv2
import json
import base64
import time
import os

# Server data
PORT = 7890
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()
videos = list(map(lambda el: el.split(".")[0], os.listdir("../object-tracker-shared/videos")))


class VideoReader:
    isBuffering = False

    def __init__(self, websocket):
        self.websocket = websocket
        self.isBuffering = False
        self.stream_width = 640
        self.stream_height = 360
        self.cap = None
        self.position_file = None

    def start(self, video_name):
        self.isBuffering = True
        self.cap = cv2.VideoCapture(f'../object-tracker-shared/videos/{video_name}.mp4')
        self.position_file = open(f'../object-tracker-shared/outputs/{video_name}.txt', "r")

    def stop(self):
        self.isBuffering = False

    async def get_first_frame(self):
        test = self.position_file.readline().strip()
        video_summary = json.loads(test)
        await self.websocket.send(json.dumps({"type": "video_summary", "content": video_summary}))

    async def get_next_frame(self):
        success, img = self.cap.read()

        if not success:
            await self.dispose()
            return

        # Read frame information
        object_positions = json.loads(self.position_file.readline().strip())

        # Get coefficients for object position & width adjustments to stream size
        width_scale_coefficient = self.stream_width / img.shape[1]
        height_scale_coefficient = self.stream_height / img.shape[0]

        # Process frame
        resized = cv2.resize(img, (self.stream_width, self.stream_height))
        success, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 30])

        # Process & adjust object information
        for object_position in object_positions:
            object_position["x"] = object_position["x"] * width_scale_coefficient
            object_position["y"] = object_position["y"] * height_scale_coefficient
            object_position["width"] = object_position["width"] * width_scale_coefficient
            object_position["height"] = object_position["height"] * height_scale_coefficient

        await self.websocket.send(json.dumps({
            "type": "video_frame",
            "frame": base64.b64encode(buffer).decode("utf-8"),
            "positions": object_positions
        }))

    async def dispose(self):
        self.isBuffering = False
        await self.websocket.send(json.dumps({"type": "video_end"}))
        self.position_file.close()
        self.cap.release()


async def echo(websocket):
    # Store a copy of the connected client
    print("A client just connected")
    connected.add(websocket)
    await websocket.send(json.dumps({"type": "video_list", "videos": videos}))
    reader = VideoReader(websocket)

    # Handle incoming messages
    try:
        async for message in websocket:
            print("Received message from client: " + message)
            parsed_message = json.loads(message)

            if parsed_message["type"] == "stop_buffer":
                reader.stop()

            elif parsed_message["type"] == "play":
                reader.start(parsed_message["content"])
                await reader.get_first_frame()

            elif parsed_message["type"] == "get_frames":
                for i in range(int(parsed_message["content"])):
                    await reader.get_next_frame()

            else:
                await websocket.send(json.dumps({"type": "error", "description": "Unknown message!"}))

    # Handle disconnecting clients
    finally:
        print("A client just disconnected")
        connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "localhost", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
