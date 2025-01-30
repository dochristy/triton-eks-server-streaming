import asyncio
import websockets
import json
import boto3
from typing import List, Dict, Any
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
import csv
from asyncio import Semaphore
from contextlib import asynccontextmanager

class BatchInferenceClient:
    def __init__(self, uri: str, bucket: str, max_concurrent: int = 5):
        self.uri = uri
        self.bucket = bucket
        self.s3_client = boto3.client('s3')
        self.results_dir = Path('inference_results')
        self.results_dir.mkdir(exist_ok=True)
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        
    def list_s3_images(self, prefix: str = "images/") -> List[str]:
        """List all images in the S3 bucket with given prefix."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', []) 
                    if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png'))]
        except Exception as e:
            print(f"Error listing S3 objects: {e}")
            return []

    @asynccontextmanager
    async def get_websocket(self):
        """Context manager for websocket connections with semaphore control."""
        async with self.semaphore:
            async with websockets.connect(self.uri) as websocket:
                yield websocket

    async def process_single_image(self, image_key: str) -> Dict[str, Any]:
        """Process a single image and return results."""
        start_time = datetime.now()
        try:
            async with self.get_websocket() as websocket:
                request = {
                    "bucket": self.bucket,
                    "key": image_key
                }
                
                print(f"\nProcessing image: {image_key}")
                await websocket.send(json.dumps(request))
                response = await websocket.recv()
                result = json.loads(response)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                image_result = {
                    'image_key': image_key,
                    'status': result.get('status', 'error'),
                    'processing_time': processing_time
                }
                
                if result.get('status') == 'success':
                    outputs = result['outputs']
                    image_result['predictions'] = {
                        'densenet': self.process_model_outputs(outputs, 'densenet'),
                        'resnet': self.process_model_outputs(outputs, 'resnet')
                    }
                    self._print_predictions(image_result['predictions'], image_key)
                else:
                    print(f"Error processing {image_key}: {result.get('message', 'Unknown error')}")
                
                return image_result
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            print(f"Error processing {image_key}: {e}")
            return {
                'image_key': image_key,
                'status': 'error',
                'message': str(e),
                'processing_time': processing_time
            }

    def _print_predictions(self, predictions: Dict, image_key: str):
        """Helper method to print predictions."""
        print(f"\nResults for image: {image_key}")
        for model in ['densenet', 'resnet']:
            print(f"\n{model.upper()} Top 5 Predictions:")
            for output_name, output_results in predictions[model].items():
                print(f"\n{output_name}:")
                for pred in output_results['top_predictions']:
                    print(f"Class {pred['class_id']}: {pred['confidence']:.4f} ({pred['confidence']*100:.2f}%)")

    def process_model_outputs(self, outputs: Dict, model_name: str) -> Dict[str, Dict]:
        """Process model outputs and return predictions with statistics."""
        model_outputs = outputs[model_name]
        results = {}
        
        for output_name, output_data in model_outputs.items():
            output_array = np.array(output_data)
            
            # Reshape if needed (for DenseNet)
            if len(output_array.shape) > 2:
                output_array = output_array.reshape(output_array.shape[0], -1)
            
            if output_array.size > 0:
                predictions = output_array[0]
                
                # Apply softmax for probability scores
                exp_preds = np.exp(predictions - np.max(predictions))
                probabilities = exp_preds / exp_preds.sum()
                
                # Get top 5 predictions
                top_indices = np.argsort(probabilities)[-5:][::-1]
                top_predictions = [{
                    'class_id': int(idx),
                    'confidence': float(probabilities[idx]),
                    'score': float(predictions[idx])
                } for idx in top_indices]
                
                # Calculate statistics
                stats = {
                    'min_score': float(predictions.min()),
                    'max_score': float(predictions.max()),
                    'mean_score': float(predictions.mean()),
                    'unique_values': len(np.unique(predictions)),
                    'min_prob': float(probabilities.min()),
                    'max_prob': float(probabilities.max()),
                }
                
                results[output_name] = {
                    'top_predictions': top_predictions,
                    'statistics': stats
                }
                
        return results

    def save_results_csv(self, results: List[Dict], timestamp: str):
        """Save batch processing results to CSV file."""
        csv_path = self.results_dir / f'inference_results_{timestamp}.csv'
        fieldnames = ['image_key', 'status', 'densenet_top1_class', 'densenet_top1_confidence', 
                     'resnet_top1_class', 'resnet_top1_confidence', 'processing_time']
        
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {
                    'image_key': result['image_key'],
                    'status': result['status']
                }
                
                if result['status'] == 'success':
                    if 'densenet' in result['predictions']:
                        top_densenet = result['predictions']['densenet'].get('fc6_1', {}).get('top_predictions', [{}])[0]
                        row['densenet_top1_class'] = top_densenet.get('class_id', '')
                        row['densenet_top1_confidence'] = top_densenet.get('confidence', '')
                    
                    if 'resnet' in result['predictions']:
                        top_resnet = result['predictions']['resnet'].get('resnetv24_dense0_fwd', {}).get('top_predictions', [{}])[0]
                        row['resnet_top1_class'] = top_resnet.get('class_id', '')
                        row['resnet_top1_confidence'] = top_resnet.get('confidence', '')
                
                row['processing_time'] = result.get('processing_time', '')
                writer.writerow(row)
        
        print(f"\nResults saved to: {csv_path}")

    async def process_batch(self, image_keys: List[str]):
        """Process a batch of images in parallel."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_start_time = datetime.now()
        
        try:
            # Create tasks for all images
            tasks = [self.process_single_image(image_key) for image_key in image_keys]
            
            # Process all tasks concurrently and gather results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out any exceptions and create final results list
            final_results = []
            for result in results:
                if isinstance(result, Exception):
                    print(f"Task failed with error: {result}")
                else:
                    final_results.append(result)
            
            total_time = (datetime.now() - total_start_time).total_seconds()
            
            # Save results
            self.save_results_csv(final_results, timestamp)
            
            # Print summary
            print(f"\nBatch Processing Summary:")
            print(f"Total images processed: {len(final_results)}")
            print(f"Successful: {sum(1 for r in final_results if r['status'] == 'success')}")
            print(f"Failed: {sum(1 for r in final_results if r['status'] == 'error')}")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Average time per image: {total_time/len(final_results):.2f} seconds")
            
            return final_results
            
        except Exception as e:
            print(f"Batch processing error: {e}")
            return []

async def main():
    uri = "ws://ab2c89d3704f3499e9350563e87f167b-00015305edd17ba4.elb.us-east-1.amazonaws.com:8080"
    bucket = "dry-bean-bucket-c"
    max_concurrent = 5  # Maximum number of concurrent connections
    
    client = BatchInferenceClient(uri, bucket, max_concurrent)
    image_keys = client.list_s3_images()
    
    if not image_keys:
        print("No images found in S3 bucket")
        sys.exit(1)
    
    print(f"Found {len(image_keys)} images")
    print(f"Processing with max {max_concurrent} concurrent connections")
    await client.process_batch(image_keys)

if __name__ == "__main__":
    asyncio.run(main())

