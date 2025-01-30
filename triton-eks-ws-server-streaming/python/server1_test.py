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
    """Preprocess image for DenseNet model."""
    image = Image.open(io.BytesIO(image_bytes))
    print(f"Original image size: {image.size}")
    
    # Resize to DenseNet input size
    image = image.resize((224, 224))
    print(f"Resized image size: {image.size}")
    
    # Convert to RGB if not already
    image = image.convert('RGB')
    
    # Convert to numpy array and normalize
    image_array = np.array(image)
    print(f"Initial array shape: {image_array.shape}")
    
    # Transpose from HWC to CHW format
    image_array = np.transpose(image_array, (2, 0, 1))
    print(f"After transpose shape: {image_array.shape}")
    
    # Add batch dimension and convert to float32
    image_array = np.expand_dims(image_array, axis=0).astype(np.float32)
    print(f"Final array shape: {image_array.shape}")
    
    # Normalize to [0, 1]
    image_array = image_array / 255.0
    
    # Print statistics for debugging
    print(f"Array min: {image_array.min()}, max: {image_array.max()}, mean: {image_array.mean()}")
    
    return image_array

class TritonWebSocketServer:
    def __init__(self, triton_url="localhost:8000", websocket_port=None):
        self.triton_url = triton_url
        self.websocket_port = websocket_port if websocket_port else self._find_available_port()
        self.triton_client = httpclient.InferenceServerClient(url=triton_url)
        self.s3_client = boto3.client('s3')
        print(f"Initialized Triton client with URL: {triton_url}")

    async def handle_inference(self, websocket):
        try:
            async for message in websocket:
                print("\n--- Starting new inference request ---")
                request_data = json.loads(message)
                model_name = request_data['model_name']
                s3_bucket = request_data['bucket']
                s3_key = request_data['key']
                
                print(f"Processing request for model: {model_name}")
                print(f"Loading image from s3://{s3_bucket}/{s3_key}")

                # Get image from S3
                try:
                    response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                    image_bytes = response['Body'].read()
                    print("Successfully loaded image from S3")
                except Exception as e:
                    print(f"Error loading from S3: {str(e)}")
                    raise
                
                # Preprocess image
                input_data = preprocess_image(image_bytes)
                print(f"Preprocessed input shape: {input_data.shape}, dtype: {input_data.dtype}")

                # Get model metadata
                try:
                    model_metadata = self.triton_client.get_model_metadata(model_name)
                    print("\nModel Metadata:")
                    print(json.dumps(model_metadata, indent=2))
                    input_name = model_metadata['inputs'][0]['name']
                    print(f"Using input name: {input_name}")
                except Exception as e:
                    print(f"Error getting model metadata: {str(e)}")
                    raise
                
                # Create input tensor
                try:
                    input_tensor = httpclient.InferInput(
                        input_name,
                        input_data.shape,
                        "FP32"
                    )
                    input_tensor.set_data_from_numpy(input_data)
                    print("Successfully created input tensor")
                except Exception as e:
                    print(f"Error creating input tensor: {str(e)}")
                    raise

                # Run inference
                try:
                    print("Starting inference...")
                    response = self.triton_client.infer(
                        model_name=model_name,
                        inputs=[input_tensor]
                    )
                    print("Inference completed")
                except Exception as e:
                    print(f"Error during inference: {str(e)}")
                    raise

                # Process outputs
                try:
                    outputs = {}
                    response_dict = response.get_response()
                    print("\nRaw response:")
                    print(json.dumps(response_dict, indent=2))
                    
                    for output in response_dict['outputs']:
                        output_name = output['name']
                        output_data = response.as_numpy(output_name)
                        print(f"\nOutput {output_name}:")
                        print(f"Shape: {output_data.shape}")
                        print(f"Type: {output_data.dtype}")
                        
                        # Get top 5 predictions
                        if len(output_data.shape) == 2:  # [batch_size, num_classes]
                            top_indices = np.argsort(output_data[0])[-5:][::-1]
                            print("\nTop 5 predictions:")
                            for idx in top_indices:
                                confidence = output_data[0][idx]
                                print(f"Class {idx}: {confidence:.4f}")
                        
                        outputs[output_name] = output_data.tolist()
                except Exception as e:
                    print(f"Error processing output: {str(e)}")
                    raise

                await websocket.send(json.dumps({
                    'status': 'success',
                    'outputs': outputs
                }))
                print("Response sent to client")

        except Exception as e:
            error_msg = {'status': 'error', 'message': str(e)}
            print(f"Server error: {str(e)}")
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
