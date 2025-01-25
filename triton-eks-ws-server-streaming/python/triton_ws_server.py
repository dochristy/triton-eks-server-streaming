import socket
from contextlib import closing
import asyncio
import websockets
import json
from tritonclient.utils import *
import tritonclient.http as httpclient
import numpy as np

class TritonWebSocketServer:
    def __init__(self, triton_url="localhost:8000", websocket_port=None):
        self.triton_url = triton_url
        self.websocket_port = websocket_port if websocket_port else self._find_available_port()
        self.triton_client = httpclient.InferenceServerClient(url=triton_url)

    async def handle_inference(self, websocket):
        try:
            async for message in websocket:
                request_data = json.loads(message)
                model_name = request_data['model_name']
                input_data = request_data['inputs']

                inputs = []
                for inp in input_data:
                    # Convert input data to numpy array with explicit float32
                    np_array = np.array(inp['data'], dtype=np.float32)
                    print(f"Server: Input array dtype: {np_array.dtype}")
                    print(f"Server: Input array shape: {np_array.shape}")
                    
                    input_tensor = httpclient.InferInput(
                        inp['name'], 
                        inp['shape'], 
                        inp['datatype']
                    )
                    input_tensor.set_data_from_numpy(np_array)
                    inputs.append(input_tensor)

                response = self.triton_client.infer(
                    model_name=model_name,
                    inputs=inputs
                )

                outputs = {}
                for output in response.get_response()['outputs']:
                    output_name = output['name']
                    outputs[output_name] = response.as_numpy(output_name).tolist()

                await websocket.send(json.dumps({
                    'status': 'success',
                    'outputs': outputs
                }))

        except Exception as e:
            error_msg = {'status': 'error', 'message': str(e)}
            print(f"Server error: {str(e)}")  # Add server-side error printing
            await websocket.send(json.dumps(error_msg))

    async def start_server(self):
        async with websockets.serve(
            self.handle_inference, 
            "localhost", 
            self.websocket_port,
            max_size=1024*1024*1024,
            max_queue=16
        ):
            print(f"WebSocket server started on ws://localhost:{self.websocket_port}")
            await asyncio.Future()

    def _find_available_port(self):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
            return port

    def run(self):
        asyncio.run(self.start_server())

if __name__ == "__main__":
    server = TritonWebSocketServer(
        triton_url="localhost:8000",
        websocket_port=8080
    )
    print("Starting WebSocket server...")
    server.run()

