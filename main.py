import asyncio
import websockets
import cv2
import json
import base64
import os

# Server data
PORT = 7890
print("Server listening on Port " + str(PORT))

# A set of connected ws clients
connected = set()

# Tracker map to output folders
tracker_folders = {
    "SORT": "sort-outputs",
    "DEEP_SORT": "deepsort-outputs",
    "BYTE_TRACK": "bytetrack-outputs",
    "BYTE_TRACK_SEGMENTED": "bytetrack-seg-outputs",
}


class VideoReader:
    isBuffering = False
    tracker = "SORT"  # Set SORT as default tracker

    def __init__(self, websocket):
        self.websocket = websocket
        self.isBuffering = False
        self.stream_width = 640
        self.stream_height = 360
        self.cap = None
        self.position_file = None

    def start(self, video_name, tracker):
        self.tracker = tracker
        self.isBuffering = True
        self.cap = cv2.VideoCapture(f'videos/{video_name}.mp4')
        self.position_file = open(f'{tracker_folders[tracker]}/{video_name}.txt', "r")
        self.position_file.readline()  # Skip summary

    def stop(self):
        self.isBuffering = False

    async def get_next_frame(self):
        success, img = self.cap.read()

        if not success or not self.isBuffering:
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
            if self.tracker == "BYTE_TRACK_SEGMENTED":
                mask = json.loads(object_position["mask"])
                adjusted_mask = []
                for point in mask:
                    object_position["mask"] = object_position["mask"]
                    adjusted_mask.append([point[0] * width_scale_coefficient, point[1] * height_scale_coefficient])
                object_position["mask"] = adjusted_mask
            else:
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
    videos = list(map(lambda el: el.split(".")[0], os.listdir("videos")))
    await websocket.send(json.dumps({"type": "video_list", "videos": videos}))
    reader = VideoReader(websocket)

    # Handle incoming messages
    try:
        async for message in websocket:
            print("Received message from client: " + message)
            parsed_message = json.loads(message)

            if parsed_message["type"] == "stop_buffer":
                reader.stop()
                await websocket.send(json.dumps({"type": "stop_buffer_success"}))

            elif parsed_message["type"] == "get_summary":
                video_name = parsed_message["video_name"]
                position_file = open(
                    f'{tracker_folders[parsed_message["tracker"]]}/{video_name}.txt', "r"
                )
                video_summary = json.loads(position_file.readline().strip())
                await websocket.send(json.dumps({"type": "video_summary", "content": video_summary}))

            elif parsed_message["type"] == "play":
                reader.start(parsed_message["video_name"], parsed_message["tracker"])

            elif parsed_message["type"] == "get_frames":
                for i in range(int(parsed_message["count"])):
                    await reader.get_next_frame()

            else:
                await websocket.send(json.dumps({"type": "error", "description": "Unknown message!"}))

    # Handle disconnecting clients
    finally:
        print("A client just disconnected")
        connected.remove(websocket)

# Start the server
start_server = websockets.serve(echo, "0.0.0.0", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
