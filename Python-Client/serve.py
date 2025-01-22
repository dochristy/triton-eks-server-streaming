from flask import Flask, request, jsonify
from pipeline import TritonS3VisionPipeline
import os
import logging
import time
import sys
import traceback

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def wait_for_triton(timeout=60):
    start_time = time.time()
    while True:
        try:
            logger.debug("Attempting to connect to Triton server...")
            pipeline = TritonS3VisionPipeline(
                triton_url='localhost:8001',
                s3_bucket=os.getenv('S3_BUCKET', 'dry-bean-bucket-c')
            )
            logger.debug("Successfully connected to Triton server")
            return pipeline
        except Exception as e:
            if time.time() - start_time > timeout:
                logger.error(f"Timeout waiting for Triton server: {str(e)}")
                raise Exception(f"Timeout waiting for Triton server: {str(e)}")
            logger.debug(f"Waiting for Triton server... Error: {str(e)}")
            time.sleep(5)

# Initialize pipeline with retry
logger.info("Starting Triton server initialization...")
try:
    pipeline = wait_for_triton()
    logger.info("Triton server initialization complete")
except Exception as e:
    logger.error(f"Failed to initialize Triton server: {str(e)}")
    sys.exit(1)

@app.route('/predict', methods=['POST'])
def predict():
    request_start_time = time.time()
    logger.info(f"Received prediction request at {request_start_time}")

    try:
        # Log request headers
        logger.debug(f"Request headers: {dict(request.headers)}")

        # Get and validate JSON data
        try:
            data = request.get_json()
            logger.debug(f"Parsed request data: {data}")
        except Exception as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return jsonify({'error': 'Invalid JSON'}), 400

        if not data:
            logger.error("Empty request data")
            return jsonify({'error': 'Empty request'}), 400

        if 's3_key' not in data:
            logger.error("Missing s3_key in request")
            return jsonify({'error': 'Missing s3_key'}), 400

        s3_key = data['s3_key']
        logger.info(f"Starting processing for S3 key: {s3_key}")

        # Test S3 access before processing
        try:
            logger.debug("Testing S3 bucket access...")
            pipeline.s3.head_object(Bucket=pipeline.bucket, Key=s3_key)
            logger.debug("S3 bucket access successful")
        except Exception as e:
            logger.error(f"S3 access error: {str(e)}")
            return jsonify({'error': f'S3 access error: {str(e)}'}), 500

        # Run pipeline with detailed timing
        logger.info("Starting pipeline execution")
        pipeline_start = time.time()
        try:
            densenet_output, resnet_output = pipeline.run_pipeline_with_viz(s3_key)
            pipeline_duration = time.time() - pipeline_start
            logger.info(f"Pipeline execution completed in {pipeline_duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Pipeline execution failed: {str(e)}'}), 500

        # Prepare response
        try:
            result = {
                'densenet_output': densenet_output.tolist(),
                'resnet_output': resnet_output.tolist(),
                'visualization_dir': pipeline.output_dir,
                'processing_time': pipeline_duration
            }
        except Exception as e:
            logger.error(f"Error preparing response: {str(e)}")
            return jsonify({'error': 'Error preparing response'}), 500

        total_duration = time.time() - request_start_time
        logger.info(f"Request completed in {total_duration:.2f} seconds")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=5000, threaded=True)
