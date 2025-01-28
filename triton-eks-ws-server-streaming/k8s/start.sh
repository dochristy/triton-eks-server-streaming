#!/bin/bash

# Start Triton server in the background
tritonserver --model-repository=s3://dry-bean-bucket-c/models \
            --http-port=8000 \
            --grpc-port=8001 \
            --metrics-port=8002 \
            --allow-http=1 &

# Wait for Triton server to start
sleep 10

# Start WebSocket server
python3 /app/pipeline_ws_server.py
