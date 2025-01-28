```bash


```

## First, Prepare Your AWS Environment:

### Configure AWS CLI
aws configure

### Create ECR repository for Triton server (if not exists)
aws ecr create-repository --repository-name websocket-pipeline



### Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

### Build using your Dockerfile
docker build -t triton-ws-pipeline .

### Tag and push
docker tag triton-ws-pipeline ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/websocket-pipeline:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/websocket-pipeline:latest


### Create S3 bucket if not exists
aws s3 mb s3://dry-bean-bucket-c

### Upload your models to S3
aws s3 cp models/ s3://dry-bean-bucket-c/models/ --recursive

