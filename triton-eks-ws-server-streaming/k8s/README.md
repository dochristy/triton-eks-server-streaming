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


### Terraform init, plan, apply
```bash
cluster_endpoint = "https://15DF156C8781098F09C4B799AD43D8.gr7.us-east-1.eks.amazonaws.com"
cluster_name = "triton-streaming-cluster"
cluster_oidc_issuer_url = "https://oidc.eks.us-east-1.amazonaws.com/id/15DF156C8781098F09C4B799AD43D8"
nat_public_ips = tolist([
  "34.224.171.15",
])
private_subnet_ids = [
  "subnet-0d0b7c6cd9f6f437",
  "subnet-074348f3c450bb87",
]
public_subnet_ids = [
  "subnet-0f2b7965fea6f433",
  "subnet-0429df4f58aecd25",
]
vpc_cidr = "192.168.0.0/20"
vpc_id = "vpc-00af56b44d3c27ef"
```

## Connect to the cluster
```bash
aws eks update-kubeconfig --name triton-streaming-cluster --region us-east-1
```

```bash
kubectl get nodes
NAME                           STATUS   ROLES    AGE    VERSION
ip-192-168-1-65.ec2.internal   Ready    <none>   125m   v1.27.16-eks-aeac579
```



