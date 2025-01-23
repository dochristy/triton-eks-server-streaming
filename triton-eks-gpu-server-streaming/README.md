```bash
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update
```

```bash
aws ecr get-login-password --region us-east-1 | kubectl create secret docker-registry regcred \
  --docker-server=${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1) \
  --namespace=default
```

```bash
# Check nodes and GPU labels
kubectl get nodes --show-labels | grep nvidia-gpu

# Verify namespaces
kubectl get ns triton gpu-operator

# Check service account
kubectl get sa -n triton triton-service-account

# Verify ECR credentials
kubectl get secret regcred -n triton
```

```bash
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```
