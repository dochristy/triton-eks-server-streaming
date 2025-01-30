import asyncio
import websockets
import json
import boto3
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TritonTester:
    def __init__(self):
        self.base_url = "ab2c89d3704f3499e9350563e87f167b-00015305edd17ba4.elb.us-east-1.amazonaws.com"
        self.ws_uri = f"ws://{self.base_url}:8080"
        self.http_url = f"http://{self.base_url}"
        self.bucket = "dry-bean-bucket-c"
        self.s3_client = boto3.client('s3')

    async def test_websocket_connection(self):
        """Test basic WebSocket connectivity"""
        try:
            logger.info("Testing WebSocket connection...")
            async with websockets.connect(self.ws_uri) as ws:
                logger.info("✓ WebSocket connection successful!")
                return True
        except Exception as e:
            logger.error(f"✗ WebSocket connection failed: {str(e)}")
            return False

    def test_http_endpoints(self):
        """Test various HTTP endpoints"""
        endpoints = {
            "Server Health": f"{self.http_url}:8000/v2/health/ready",
            "Server Metadata": f"{self.http_url}:8000/v2",
            "Metrics": f"{self.http_url}:8002/metrics"
        }

        results = {}
        for name, url in endpoints.items():
            try:
                logger.info(f"\nTesting {name}...")
                response = requests.get(url)
                response.raise_for_status()
                results[name] = {
                    "status": "Success",
                    "status_code": response.status_code,
                    "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                }
                logger.info(f"✓ {name} check passed (Status: {response.status_code})")
            except Exception as e:
                results[name] = {
                    "status": "Failed",
                    "error": str(e)
                }
                logger.error(f"✗ {name} check failed: {str(e)}")

        return results

    def test_model_repository(self):
        """Test model repository status"""
        try:
            logger.info("\nChecking model repository...")
            url = f"{self.http_url}:8000/v2/repository/index"
            response = requests.post(url)
            response.raise_for_status()
            models = response.json()
            
            logger.info("Available models:")
            for model in models:
                logger.info(f"✓ {model['name']} (Version: {model['version']}, State: {model['state']})")
            
            return models
        except Exception as e:
            logger.error(f"✗ Model repository check failed: {str(e)}")
            return None

    def check_s3_access(self):
        """Test S3 bucket access and content"""
        try:
            logger.info(f"\nChecking S3 bucket access ({self.bucket})...")
            
            # Check models directory
            models_response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix="models/"
            )
            
            if 'Contents' in models_response:
                logger.info("✓ Found model files:")
                for obj in models_response['Contents'][:5]:  # Show first 5 files
                    logger.info(f"  - {obj['Key']}")
            else:
                logger.warning("✗ No model files found in S3")
            
            # Check images directory
            images_response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix="images/"
            )
            
            if 'Contents' in images_response:
                logger.info("\n✓ Found image files:")
                for obj in images_response['Contents']:
                    if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png')):
                        logger.info(f"  - {obj['Key']}")
            else:
                logger.warning("✗ No image files found in S3")
                
            return True
        except Exception as e:
            logger.error(f"✗ S3 access check failed: {str(e)}")
            return False

    async def test_simple_inference(self):
        """Test a simple inference request"""
        try:
            logger.info("\nTesting simple inference request...")
            
            # Get first image from S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix="images/"
            )
            
            if 'Contents' not in response:
                logger.error("✗ No images found for testing")
                return False
                
            test_image = next(
                (obj['Key'] for obj in response['Contents'] 
                 if obj['Key'].lower().endswith(('.jpg', '.jpeg', '.png'))),
                None
            )
            
            if not test_image:
                logger.error("✗ No suitable test image found")
                return False
            
            logger.info(f"Using test image: {test_image}")
            
            # Send inference request
            async with websockets.connect(self.ws_uri) as ws:
                request = {
                    "bucket": self.bucket,
                    "key": test_image
                }
                
                logger.info("Sending inference request...")
                await ws.send(json.dumps(request))
                
                logger.info("Waiting for response...")
                response = await ws.recv()
                result = json.loads(response)
                
                if result.get('status') == 'success':
                    logger.info("✓ Inference request successful!")
                    logger.info("\nModel outputs:")
                    logger.info(json.dumps(result, indent=2))
                    return True
                else:
                    logger.error(f"✗ Inference failed: {result.get('message', 'Unknown error')}")
                    return False
                
        except Exception as e:
            logger.error(f"✗ Inference test failed: {str(e)}")
            return False

async def main():
    tester = TritonTester()
    
    # Run all tests
    logger.info("=== Starting Triton Server Tests ===\n")
    
    # Test WebSocket connection
    ws_success = await tester.test_websocket_connection()
    
    # Test HTTP endpoints
    http_results = tester.test_http_endpoints()
    
    # Test model repository
    model_results = tester.test_model_repository()
    
    # Test S3 access
    s3_success = tester.check_s3_access()
    
    # Test inference
    if ws_success and s3_success:
        inference_success = await tester.test_simple_inference()
    else:
        logger.warning("Skipping inference test due to connection or S3 issues")
        inference_success = False
    
    # Print summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"WebSocket Connection: {'✓' if ws_success else '✗'}")
    logger.info(f"S3 Access: {'✓' if s3_success else '✗'}")
    logger.info(f"Inference Test: {'✓' if inference_success else '✗'}")
    logger.info("HTTP Endpoints:")
    for name, result in http_results.items():
        logger.info(f"  - {name}: {'✓' if result['status'] == 'Success' else '✗'}")
    logger.info(f"Model Repository: {'✓' if model_results else '✗'}")

if __name__ == "__main__":
    asyncio.run(main())
