import asyncio
import websockets
import json
import boto3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_inference():
    base_url = "ab2c89d3704f3499e9350563e87f167b-00015305edd17ba4.elb.us-east-1.amazonaws.com"
    ws_uri = f"ws://{base_url}:8080"
    bucket = "dry-bean-bucket-c"
    test_image = "images/pexels-pixabay-45201.jpg"  # Using a specific test image
    
    logger.info(f"Testing inference with image: {test_image}")
    
    try:
        async with websockets.connect(
            ws_uri,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=20,
            max_size=None
        ) as ws:
            # Prepare request
            request = {
                "bucket": bucket,
                "key": test_image
            }
            
            logger.info("WebSocket connected. Sending request...")
            logger.info(f"Request data: {json.dumps(request, indent=2)}")
            
            # Send request with timeout
            try:
                await asyncio.wait_for(
                    ws.send(json.dumps(request)),
                    timeout=10
                )
                logger.info("Request sent successfully")
            except asyncio.TimeoutError:
                logger.error("Timeout while sending request")
                return
            
            # Wait for response with timeout
            try:
                logger.info("Waiting for response...")
                response = await asyncio.wait_for(
                    ws.recv(),
                    timeout=30
                )
                logger.info("Response received!")
                
                # Parse and log response
                result = json.loads(response)
                logger.info(f"Response status: {result.get('status')}")
                if result.get('status') == 'success':
                    logger.info("Inference successful!")
                    # Log first part of the outputs to avoid too much data
                    outputs = result.get('outputs', {})
                    for model, preds in outputs.items():
                        logger.info(f"\n{model} predictions:")
                        for output_name, values in preds.items():
                            logger.info(f"- {output_name}: {str(values)[:200]}...")
                else:
                    logger.error(f"Inference failed: {result.get('message', 'Unknown error')}")
                
            except asyncio.TimeoutError:
                logger.error("Timeout while waiting for response")
            except Exception as e:
                logger.error(f"Error processing response: {str(e)}")
                
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")

if __name__ == "__main__":
    logger.info("=== Starting Inference Test ===")
    asyncio.run(test_inference())
