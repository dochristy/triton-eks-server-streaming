import websockets
import json
import asyncio
import numpy as np
import tritonclient.http as httpclient

def get_model_info():
    """Get and print detailed model information."""
    try:
        client = httpclient.InferenceServerClient(url='localhost:8000')
        
        # Get model metadata
        print("\nFetching model metadata...")
        model_metadata = client.get_model_metadata('densenet_onnx')
        print("\nModel Metadata:")
        print(json.dumps(model_metadata, indent=2))
        
        # Get model config
        print("\nFetching model config...")
        model_config = client.get_model_config('densenet_onnx')
        print("\nModel Config:")
        print(json.dumps(model_config, indent=2))
        
        return model_metadata, model_config
    except Exception as e:
        print(f"Error getting model info: {str(e)}")
        raise

class TritonWebSocketClient:
    def __init__(self, websocket_url="ws://localhost:8080"):
        self.websocket_url = websocket_url
        print(f"Initialized WebSocket client with URL: {self.websocket_url}")

    async def infer(self, model_name, s3_bucket, s3_key):
        print(f"\nStarting inference request for:")
        print(f"Model: {model_name}")
        print(f"Image: s3://{s3_bucket}/{s3_key}")
        
        async with websockets.connect(
            self.websocket_url,
            max_size=1024*1024*1024,
            max_queue=16
        ) as websocket:
            request = {
                'model_name': model_name,
                'bucket': s3_bucket,
                'key': s3_key
            }
            
            print("\nSending request to server...")
            await websocket.send(json.dumps(request))
            
            print("Waiting for response...")
            response = await websocket.recv()
            return json.loads(response)

    def run_inference(self, model_name, s3_bucket, s3_key):
        return asyncio.run(self.infer(model_name, s3_bucket, s3_key))

def process_inference_response(response):
    """Process and print the inference response."""
    print("\n--- Processing Inference Response ---")
    
    if response.get('status') == 'success':
        outputs = response['outputs']
        print("\nReceived successful response with outputs:")
        
        for output_name, output_data in outputs.items():
            print(f"\nOutput name: {output_name}")
            
            # Convert to numpy for easier processing
            output_array = np.array(output_data)
            print(f"Output shape: {output_array.shape}")
            print(f"Output dtype: {output_array.dtype}")
            
            # Get top 5 predictions
            if len(output_array.shape) == 2:  # Assuming output is [batch_size, num_classes]
                top_indices = np.argsort(output_array[0])[-5:][::-1]
                print("\nTop 5 predictions:")
                for idx in top_indices:
                    confidence = output_array[0][idx]
                    print(f"Class {idx}: {confidence:.4f}")
            else:
                print(f"Raw output data: {output_array}")
    else:
        print(f"Error in response: {response.get('message', 'Unknown error')}")

def test_inference():
    print("\n=== Starting DenseNet ONNX Inference Test ===")
    
    try:
        # First get model metadata
        print("\nFetching model information...")
        model_metadata, model_config = get_model_info()
        
        # Initialize client
        print("\nInitializing WebSocket client...")
        client = TritonWebSocketClient(websocket_url="ws://localhost:8080")
        
        # S3 details
        bucket = "dry-bean-bucket-c"
        key = "images/pexels-pixabay-45201.jpg"
        
        # Run inference
        print("\nRunning inference...")
        response = client.run_inference('densenet_onnx', bucket, key)
        
        # Process results
        print("\nProcessing response...")
        process_inference_response(response)
        
    except Exception as e:
        print(f"\nError during inference test: {str(e)}")
        raise

if __name__ == "__main__":
    test_inference()
