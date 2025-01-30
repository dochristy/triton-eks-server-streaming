import asyncio
import websockets
import json
import cv2
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
import csv
import boto3
from PIL import Image
import io
from typing import Dict, List, Any
from tqdm import tqdm
import concurrent.futures

class ParallelVideoProcessor:
    def __init__(self, uri: str, bucket: str, max_concurrent_videos: int = 2, max_concurrent_frames: int = 3):
        self.uri = uri
        self.bucket = bucket
        self.s3_client = boto3.client('s3')
        self.results_dir = Path('video_inference_results')
        self.results_dir.mkdir(exist_ok=True)
        self.max_concurrent_videos = max_concurrent_videos
        self.max_concurrent_frames = max_concurrent_frames

    def list_s3_videos(self, prefix: str = "videos/") -> List[str]:
        """List all videos in the S3 bucket with given prefix."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', []) 
                    if obj['Key'].lower().endswith(('.mp4', '.avi', '.mov'))]
        except Exception as e:
            print(f"Error listing S3 videos: {e}")
            return []

    def download_video_from_s3(self, video_key: str) -> str:
        """Download video from S3 to local temp file."""
        local_path = self.results_dir / Path(video_key).name
        try:
            self.s3_client.download_file(self.bucket, video_key, str(local_path))
            print(f"Downloaded video to: {local_path}")
            return str(local_path)
        except Exception as e:
            print(f"Error downloading video: {e}")
            raise

    async def process_frame(self, websocket, frame, frame_number: int):
        """Process a single frame through the models."""
        try:
            frame_path = self.results_dir / f"temp_frame_{frame_number}.jpg"
            cv2.imwrite(str(frame_path), frame)
            
            frame_s3_key = f"temp_frames/frame_{frame_number}.jpg"
            self.s3_client.upload_file(str(frame_path), self.bucket, frame_s3_key)
            
            request = {
                "bucket": self.bucket,
                "key": frame_s3_key
            }
            
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            result = json.loads(response)
            
            frame_path.unlink()
            self.s3_client.delete_object(Bucket=self.bucket, Key=frame_s3_key)
            
            return result
            
        except Exception as e:
            print(f"Error processing frame {frame_number}: {e}")
            return {"status": "error", "message": str(e)}

    def process_model_outputs(self, outputs: Dict, model_name: str) -> Dict[str, Dict]:
        """Process model outputs and return predictions."""
        model_outputs = outputs[model_name]
        results = {}
        
        for output_name, output_data in model_outputs.items():
            output_array = np.array(output_data)
            
            if len(output_array.shape) > 2:
                output_array = output_array.reshape(output_array.shape[0], -1)
            
            if output_array.size > 0:
                predictions = output_array[0]
                exp_preds = np.exp(predictions - np.max(predictions))
                probabilities = exp_preds / exp_preds.sum()
                
                top_indices = np.argsort(probabilities)[-5:][::-1]
                top_predictions = [{
                    'class_id': int(idx),
                    'confidence': float(probabilities[idx]),
                    'score': float(predictions[idx])
                } for idx in top_indices]
                
                results[output_name] = {
                    'top_predictions': top_predictions
                }
                
        return results

    async def process_video(self, video_key: str, frame_interval: int = 30):
        """Process video with parallel frame processing."""
        results = []
        start_time = datetime.now()
        
        try:
            video_path = self.download_video_from_s3(video_key)
            cap = cv2.VideoCapture(video_path)
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"\nProcessing video: {video_key}")
            print(f"FPS: {fps}")
            print(f"Total frames: {frame_count}")
            
            frame_number = 0
            pbar = tqdm(total=frame_count, desc="Processing frames")
            
            while cap.isOpened():
                frame_batch = []
                frame_numbers = []
                
                # Read a batch of frames
                for _ in range(self.max_concurrent_frames):
                    if frame_number >= frame_count:
                        break
                        
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    if frame_number % frame_interval == 0:
                        frame_batch.append(frame)
                        frame_numbers.append(frame_number)
                    
                    frame_number += 1
                    pbar.update(1)
                
                if not frame_batch:
                    break
                
                # Process frames in parallel
                async with websockets.connect(self.uri) as websocket:
                    tasks = [self.process_frame(websocket, frame, num) 
                            for frame, num in zip(frame_batch, frame_numbers)]
                    batch_results = await asyncio.gather(*tasks)
                    
                    for num, result in zip(frame_numbers, batch_results):
                        frame_result = {
                            'frame_number': num,
                            'timestamp': num / fps,
                            'status': result.get('status', 'error')
                        }
                        
                        if result.get('status') == 'success':
                            outputs = result['outputs']
                            frame_result['predictions'] = {
                                'densenet': self.process_model_outputs(outputs, 'densenet'),
                                'resnet': self.process_model_outputs(outputs, 'resnet')
                            }
                        
                        results.append(frame_result)
            
            pbar.close()
            cap.release()
            Path(video_path).unlink()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            return results, processing_time
            
        except Exception as e:
            print(f"Error processing video {video_key}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return results, processing_time

    async def process_videos_batch(self, video_keys: List[str], frame_interval: int = 30):
        """Process multiple videos in parallel."""
        batch_start_time = datetime.now()
        batch_results = []
        
        print(f"\nStarting parallel processing of {len(video_keys)} videos")
        print(f"Maximum concurrent videos: {self.max_concurrent_videos}")
        print(f"Maximum concurrent frames per video: {self.max_concurrent_frames}")
        print("=" * 50)

        for i in range(0, len(video_keys), self.max_concurrent_videos):
            chunk = video_keys[i:i + self.max_concurrent_videos]
            tasks = [self.process_video(video_key, frame_interval) for video_key in chunk]
            
            print(f"\nProcessing batch {i//self.max_concurrent_videos + 1}, "
                  f"videos {i+1}-{min(i+self.max_concurrent_videos, len(video_keys))}")
            
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for video_key, result in zip(chunk, chunk_results):
                if isinstance(result, Exception):
                    print(f"Error processing video {video_key}: {result}")
                    batch_results.append({
                        'video_key': video_key,
                        'status': 'failed',
                        'frames_processed': 0,
                        'successful_frames': 0,
                        'failed_frames': 0,
                        'processing_time': 0,
                        'error_message': str(result)
                    })
                else:
                    results, processing_time = result
                    success = any(r['status'] == 'success' for r in results)
                    batch_results.append({
                        'video_key': video_key,
                        'status': 'success' if success else 'failed',
                        'frames_processed': len(results),
                        'successful_frames': sum(1 for r in results if r['status'] == 'success'),
                        'failed_frames': sum(1 for r in results if r['status'] == 'error'),
                        'processing_time': processing_time
                    })

        total_time = (datetime.now() - batch_start_time).total_seconds()
        successful = sum(1 for r in batch_results if r['status'] == 'success')
        failed = sum(1 for r in batch_results if r['status'] == 'failed')

        print("\n" + "=" * 50)
        print("Batch Processing Summary:")
        print(f"Total videos processed: {len(video_keys)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average time per video: {(total_time/len(video_keys)):.2f} seconds")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = self.results_dir / f'batch_summary_{timestamp}.csv'
        
        with open(summary_path, 'w', newline='') as csvfile:
            fieldnames = ['video_key', 'status', 'frames_processed', 'successful_frames', 
                         'failed_frames', 'processing_time', 'error_message']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in batch_results:
                writer.writerow(result)

        print(f"\nBatch summary saved to: {summary_path}")
        return batch_results

async def main():
    uri = "ws://ab2c89d3704f3499e9350563e87f167b-00015305edd17ba4.elb.us-east-1.amazonaws.com:8080"
    bucket = "dry-bean-bucket-c"
    frame_interval = 30  # Process every 30th frame
    
    # Adjust these based on your system resources
    max_concurrent_videos = 2
    max_concurrent_frames = 3

    processor = ParallelVideoProcessor(
        uri=uri, 
        bucket=bucket,
        max_concurrent_videos=max_concurrent_videos,
        max_concurrent_frames=max_concurrent_frames
    )
    
    video_keys = processor.list_s3_videos()
    
    if not video_keys:
        print("No videos found in S3 bucket")
        sys.exit(1)
    
    print(f"Found {len(video_keys)} videos in bucket:")
    for key in video_keys:
        print(f"- {key}")
    
    await processor.process_videos_batch(video_keys, frame_interval)

if __name__ == "__main__":
    asyncio.run(main())

