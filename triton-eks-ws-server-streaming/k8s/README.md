```bash
docker build -t triton-ws-pipeline .
docker tag triton-ws-pipeline ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/websocket-pipeline:latest
```
