import websockets
import json
import asyncio
import numpy as np
import tritonclient.http as httpclient

def get_model_info():
    # Create a client to get model metadata
    client = httpclient.InferenceServerClient(url='localhost:8000')
    
    # Get model metadata
    model_metadata = client.get_model_metadata('densenet_onnx')
    print("\nModel Metadata:")
    print(json.dumps(model_metadata, indent=2))
    
    # Get model config
    model_config = client.get_model_config('densenet_onnx')
    print("\nModel Config:")
    print(json.dumps(model_config, indent=2))
    
    return model_metadata, model_config

class TritonWebSocketClient:
    def __init__(self, websocket_url="ws://localhost:8080"):
        self.websocket_url = websocket_url

    async def infer(self, model_name, inputs):
        async with websockets.connect(
            self.websocket_url,
            max_size=1024*1024*1024,
            max_queue=16
        ) as websocket:
            request = {
                'model_name': model_name,
                'inputs': inputs
            }
            
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            return json.loads(response)

    def run_inference(self, model_name, inputs):
        return asyncio.run(self.infer(model_name, inputs))

def test_inference():
    # First get model metadata
    model_metadata, model_config = get_model_info()
    
    # Get the input name from metadata
    input_name = model_metadata['inputs'][0]['name']
    print(f"\nUsing input name: {input_name}")
    
    client = TritonWebSocketClient(websocket_url="ws://localhost:8080")
    
    # Create input data with explicit float32
    sample_input = np.zeros((1, 3, 224, 224), dtype=np.float32)
    print(f"Input array dtype: {sample_input.dtype}")
    
    inputs = [
        {
            'name': input_name,  # Use the correct input name from metadata
            'shape': [1, 3, 224, 224],
            'datatype': 'FP32',
            'data': sample_input.tolist()
        }
    ]
    
    try:
        response = client.run_inference('densenet_onnx', inputs)
        print("Inference response:", response)
    except Exception as e:
        print(f"Error during inference: {str(e)}")

if __name__ == "__main__":
    test_inference()

