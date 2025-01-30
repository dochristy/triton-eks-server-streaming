FROM <account_id>.dkr.ecr.us-east-1.amazonaws.com/triton-grpc:24.11-py3

RUN apt-get -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update && \
    DEBIAN_FRONTEND=noninteractive apt-get --allow-unauthenticated install -y --no-install-recommends \
    net-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# Install additional Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt || (cat /root/.cache/pip/log/*; exit 1)
RUN pip install awscli websockets aiohttp

# Copy application code
# COPY pipeline_http_ws_server.py /app/pipeline_ws_server.py # For HTTP implementation
COPY pipeline_grpc_ws_server.py /app/pipeline_ws_server.py   # For gRPC implementation

# Set working directory
WORKDIR /app

# Environment variables for Triton
ENV CUDA_VISIBLE_DEVICES=0
ENV PATH="/usr/local/bin:${PATH}"

EXPOSE 8000 8001 8002 5000

# Default command to start both Triton server and WebSocket API
# CMD ["bash", "-c", "tritonserver --model-repository=s3://dry-bean-bucket-c/models --http-port=8000 --grpc-port=8001 --metrics-port=8002 & python3 serve_ws.py"]
# Create a startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Default command to start Triton server and WebSocket server
# Default command to use start script
ENTRYPOINT ["/app/start.sh"]
