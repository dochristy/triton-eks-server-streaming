import socket
from contextlib import closing
import asyncio
import websockets
import json
import boto3
import io
from PIL import Image
import numpy as np
from tritonclient.utils import *
import tritonclient.http as httpclient

def preprocess_image(image_bytes):
    """Preprocess image for both models."""
    image = Image.open(io.BytesIO(image_bytes))
    print(f"Original image size: {image.size}")
    
    # Resize to model input size
    image = image.resize((224, 224))
    print(f"Resized image size: {image.size}")
    
    # Convert to RGB if not already
    image = image.convert('RGB')
    
    # Convert to numpy array and normalize
    image_array = np.array(image)
    
    # Transpose from HWC to CHW format
    image_array = np.transpose(image_array, (2, 0, 1))
    
    # Add batch dimension and convert to float32
    image_array = np.expand_dims(image_array, axis=0).astype(np.float32)
    print(f"Final array shape: {image_array.shape}")
    
    # Normalize to [0, 1]
    image_array = image_array / 255.0
    
    return image_array

class TritonWebSocketServer:
    def __init__(self, triton_url="localhsot:8000", websocket_port=None):
        self.triton_url = triton_url
        self.websocket_port = websocket_port if websocket_port else self._find_available_port()
        self.triton_client = httpclient.InferenceServerClient(url=triton_url)
        self.s3_client = boto3.client('s3')
        print(f"Initialized Triton client with URL: {triton_url}")

    async def run_model_inference(self, model_name, input_tensor):
        """Run inference for a single model."""
        print(f"\nRunning inference for model: {model_name}")
        try:
            response = self.triton_client.infer(
                model_name=model_name,
                inputs=[input_tensor]
            )
            print(f"Inference completed for {model_name}")
            return response
        except Exception as e:
            print(f"Error during {model_name} inference: {str(e)}")
            raise

    async def handle_inference(self, websocket):
        try:
            async for message in websocket:
                print("\n--- Starting parallel model inference request ---")
                try:
                    request_data = json.loads(message)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {str(e)}")
                    print(f"Received message: {message}")
                    raise
                
                print(f"Received request data: {request_data}")
                
                try:
                    s3_bucket = request_data['bucket']
                    s3_key = request_data['key']
                except KeyError as e:
                    print(f"Missing required field: {str(e)}")
                    raise ValueError(f"Request missing required field: {str(e)}")
                
                print(f"Loading image from s3://{s3_bucket}/{s3_key}")

                # Get image from S3
                try:
                    response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                    image_bytes = response['Body'].read()
                    print("Successfully loaded image from S3")
                except Exception as e:
                    print(f"Error loading from S3: {str(e)}")
                    raise
                
                # Preprocess image (same preprocessing for both models)
                input_data = preprocess_image(image_bytes)
                print(f"Preprocessed input shape: {input_data.shape}")
                
                try:
                    # DenseNet inference
                    densenet_metadata = self.triton_client.get_model_metadata('densenet_onnx')
                    densenet_input_name = densenet_metadata['inputs'][0]['name']
                    print(f"Using DenseNet input name: {densenet_input_name}")
                    
                    densenet_input = httpclient.InferInput(
                        densenet_input_name,
                        input_data.shape,
                        "FP32"
                    )
                    densenet_input.set_data_from_numpy(input_data)
                    densenet_response = await self.run_model_inference('densenet_onnx', densenet_input)
                    
                    # ResNet inference (using same preprocessed input)
                    resnet_metadata = self.triton_client.get_model_metadata('resnet50_onnx')
                    resnet_input_name = resnet_metadata['inputs'][0]['name']
                    print(f"Using ResNet input name: {resnet_input_name}")
                    
                    resnet_input = httpclient.InferInput(
                        resnet_input_name,
                        input_data.shape,
                        "FP32"
                    )
                    resnet_input.set_data_from_numpy(input_data)
                    resnet_response = await self.run_model_inference('resnet50_onnx', resnet_input)
                    
                except Exception as e:
                    print(f"Error during model inference: {str(e)}")
                    raise
                
                # Process outputs
                try:
                    pipeline_outputs = {
                        'densenet': {},
                        'resnet': {}
                    }
                    
                    # Process DenseNet outputs
                    for output in densenet_response.get_response()['outputs']:
                        output_name = output['name']
                        output_data = densenet_response.as_numpy(output_name)
                        pipeline_outputs['densenet'][output_name] = output_data.tolist()
                    
                    # Process ResNet outputs
                    for output in resnet_response.get_response()['outputs']:
                        output_name = output['name']
                        output_data = resnet_response.as_numpy(output_name)
                        pipeline_outputs['resnet'][output_name] = output_data.tolist()
                    
                    await websocket.send(json.dumps({
                        'status': 'success',
                        'outputs': pipeline_outputs
                    }))
                    print("Pipeline response sent to client")
                except Exception as e:
                    print(f"Error processing outputs: {str(e)}")
                    raise

        except Exception as e:
            error_msg = {'status': 'error', 'message': str(e)}
            print(f"Server error: {str(e)}")
            await websocket.send(json.dumps(error_msg))

    async def start_server(self):
        async with websockets.serve(
            self.handle_inference, 
            "0.0.0.0", 
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
