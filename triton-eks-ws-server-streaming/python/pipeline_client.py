import websockets
import json
import asyncio
import numpy as np
import tritonclient.http as httpclient

def softmax(x):
    """Apply softmax to numpy array."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

def get_imagenet_labels():
    """Return mapping of ImageNet class indices to labels."""
    # This is a simplified version - you might want to load actual labels from a file
    labels = {
        285: "Egyptian cat",
        281: "tabby cat",
        287: "lion",
        283: "tiger cat",
        282: "tiger",
        # Add more labels as needed
    }
    return labels

def get_models_info():
    """Get and print detailed model information for both models."""
    try:
        client = httpclient.InferenceServerClient(url='localhost:8000')
        
        print("\nFetching DenseNet metadata...")
        densenet_metadata = client.get_model_metadata('densenet_onnx')
        print("\nDenseNet Metadata:")
        print(json.dumps(densenet_metadata, indent=2))
        
        print("\nFetching ResNet metadata...")
        resnet_metadata = client.get_model_metadata('resnet50_onnx')
        print("\nResNet Metadata:")
        print(json.dumps(resnet_metadata, indent=2))
        
        return densenet_metadata, resnet_metadata
    except Exception as e:
        print(f"Error getting model info: {str(e)}")
        raise

class TritonWebSocketClient:
    def __init__(self, websocket_url="ws://localhost:8080"):
        self.websocket_url = websocket_url
        print(f"Initialized WebSocket client with URL: {self.websocket_url}")

    async def infer(self, s3_bucket, s3_key):
        print(f"\nStarting parallel model inference request for:")
        print(f"Image: s3://{s3_bucket}/{s3_key}")
        
        async with websockets.connect(
            self.websocket_url,
            max_size=1024*1024*1024,
            max_queue=16
        ) as websocket:
            request = {
                'bucket': s3_bucket,
                'key': s3_key
            }
            
            print("\nSending request to server...")
            await websocket.send(json.dumps(request))
            
            print("Waiting for response...")
            response = await websocket.recv()
            return json.loads(response)

    def run_inference(self, s3_bucket, s3_key):
        return asyncio.run(self.infer(s3_bucket, s3_key))

def process_pipeline_response(response):
    """Process and print the parallel model inference response."""
    print("\n--- Processing Pipeline Response ---")
    
    if response.get('status') == 'success':
        outputs = response['outputs']
        labels = get_imagenet_labels()
        
        # Process DenseNet outputs
        print("\nDenseNet Results:")
        densenet_outputs = outputs['densenet']
        for output_name, output_data in densenet_outputs.items():
            print(f"\nOutput name: {output_name}")
            output_array = np.array(output_data)
            print(f"Original output shape: {output_array.shape}")
            
            # Reshape to remove extra dimensions (1,1000,1,1) -> (1000,)
            output_array = output_array.squeeze()
            print(f"Reshaped output shape: {output_array.shape}")
            
            # Apply softmax
            probabilities = softmax(output_array)
            
            # Get top 5 predictions
            top_indices = np.argsort(probabilities)[-5:][::-1]
            print("\nTop 5 DenseNet predictions:")
            for idx in top_indices:
                prob = probabilities[idx]
                label = labels.get(idx, f"Class {idx}")
                print(f"{label}: {prob:.4%}")
        
        # Process ResNet outputs
        print("\nResNet Results:")
        resnet_outputs = outputs['resnet']
        for output_name, output_data in resnet_outputs.items():
            print(f"\nOutput name: {output_name}")
            output_array = np.array(output_data)
            print(f"Output shape: {output_array.shape}")
            
            # Apply softmax
            probabilities = softmax(output_array[0])
            
            # Get top 5 predictions
            top_indices = np.argsort(probabilities)[-5:][::-1]
            print("\nTop 5 ResNet predictions:")
            for idx in top_indices:
                prob = probabilities[idx]
                label = labels.get(idx, f"Class {idx}")
                print(f"{label}: {prob:.4%}")
    else:
        print(f"Error in response: {response.get('message', 'Unknown error')}")

def test_pipeline():
    print("\n=== Starting Parallel Model Pipeline Test ===")
    
    try:
        # First get model metadata
        print("\nFetching model information...")
        densenet_metadata, resnet_metadata = get_models_info()
        
        # Initialize client
        print("\nInitializing WebSocket client...")
        client = TritonWebSocketClient(websocket_url="ws://localhost:8080")
        
        # S3 details
        bucket = "dry-bean-bucket-c"
        key = "images/pexels-pixabay-45201.jpg"
        
        # Run pipeline inference
        print("\nRunning parallel model inference...")
        response = client.run_inference(bucket, key)
        
        # Process results
        print("\nProcessing pipeline response...")
        process_pipeline_response(response)
        
    except Exception as e:
        print(f"\nError during pipeline test: {str(e)}")
        raise

if __name__ == "__main__":
    test_pipeline()
