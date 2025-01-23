Outputs:

cluster_endpoint = "https://ABCA0FA62EAF7B6A30DEE80837C810B4.gr7.us-east-1.eks.amazonaws.com"
cluster_name = "triton-streaming-cluster"
cluster_oidc_issuer_url = "https://oidc.eks.us-east-1.amazonaws.com/id/ABCA0FA62EAF7B6A30DEE80837C810B4"
nat_public_ips = tolist([
  "98.83.237.7",
])
private_subnet_ids = [
  "subnet-07c4055f66216d1db",
  "subnet-0745a52a4e6980a3b",
]
public_subnet_ids = [
  "subnet-0d33359b813354421",
  "subnet-029207d1a19093dbb",
]
vpc_cidr = "192.168.0.0/20"
vpc_id = "vpc-00cbb6329426e1f19"
aws eks update-kubeconfig --name triton-streaming-cluster --region us-east-1
Updated context arn:aws:eks:us-east-1:<account_id>:cluster/triton-streaming-cluster in /Users/whatever/.kube/config
# Replace <account_id> with your account ID if different
kubectl create secret docker-registry regcred \
  --docker-server=<account_id>.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1)
secret/regcred created
# Check nodes
kubectl get nodes

# Check pods
kubectl get pods -A
NAME                           STATUS   ROLES    AGE     VERSION
ip-192-168-0-92.ec2.internal   Ready    <none>   8m53s   v1.27.16-eks-aeac579
NAMESPACE     NAME                             READY   STATUS    RESTARTS   AGE
default       triton-server-788555cb9d-nl6f9   1/1     Running   0          10m
kube-system   aws-node-zcgrb                   2/2     Running   0          8m55s
kube-system   coredns-d9b6d6c7d-7fpcv          1/1     Running   0          12m
kube-system   coredns-d9b6d6c7d-pl52f          1/1     Running   0          12m
kube-system   kube-proxy-zkb5n                 1/1     Running   0          8m55s
# Get the LoadBalancer endpoint
kubectl get svc triton-server
NAME            TYPE           CLUSTER-IP      EXTERNAL-IP                                                              PORT(S)                                        AGE
triton-server   LoadBalancer   10.100.167.25   a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com   8000:32547/TCP,8001:32010/TCP,8002:31001/TCP   10m
grpcurl -plaintext a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8001 inference.GRPCInferenceService/ServerReady
Error invoking method "inference.GRPCInferenceService/ServerReady": failed to query for service descriptor "inference.GRPCInferenceService": server does not support the reflection API
python3
Python 3.12.2 | packaged by conda-forge | (main, Feb 16 2024, 21:00:12) [Clang 16.0.6 ] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import tritonclient.grpc as grpcclient
>>> url = "a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com"
>>> triton_client = grpcclient.InferenceServerClient(url=url)
>>> print("Server Ready:", triton_client.is_server_ready())
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/local/Caskroom/miniconda/base/lib/python3.12/site-packages/tritonclient/grpc/_client.py", line 296, in is_server_ready
    raise_error_grpc(rpc_error)
  File "/usr/local/Caskroom/miniconda/base/lib/python3.12/site-packages/tritonclient/grpc/_utils.py", line 62, in raise_error_grpc
    raise get_error_grpc(rpc_error) from None
tritonclient.utils.InferenceServerException: [StatusCode.UNAVAILABLE] failed to connect to all addresses; last error: UNKNOWN: ipv4:3.81.197.173:443: tcp handshaker shutdown
>>> 
vi triton-test.py
                                                                                                                                                                                                                               
vi triton-test.py
%                                                                                                                                                                                                                              
python3 triton-test.py 
Server is ready: True

Available models: models {
  name: "chrisnet_onnx"
  version: "1"
  state: "READY"
}
models {
  name: "densenet_onnx"
  version: "1"
  state: "READY"
}
models {
  name: "resnet50_onnx"
  version: "1"
  state: "READY"
}


Server metadata: name: "triton"
version: "2.52.0"
extensions: "classification"
extensions: "sequence"
extensions: "model_repository"
extensions: "model_repository(unload_dependents)"
extensions: "schedule_policy"
extensions: "model_configuration"
extensions: "system_shared_memory"
extensions: "cuda_shared_memory"
extensions: "binary_tensor_data"
extensions: "parameters"
extensions: "statistics"
extensions: "trace"
extensions: "logging"

curl -v http://a2544e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8000/v2/health/ready
* Could not resolve host: a2544e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com
* Closing connection
curl: (6) Could not resolve host: a2544e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com
curl -v http://a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8000/v2/health/ready
* Host a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8000 was resolved.
* IPv6: (none)
* IPv4: 44.197.34.30, 3.81.197.173
*   Trying 44.197.34.30:8000...
* Connected to a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com (44.197.34.30) port 8000
> GET /v2/health/ready HTTP/1.1
> Host: a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8000
> User-Agent: curl/8.7.1
> Accept: */*
> 
* Request completely sent off
< HTTP/1.1 200 OK
< Content-Length: 0
< Content-Type: text/plain
< 
* Connection #0 to host a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com left intact
cat triton-test.py 
import tritonclient.grpc as grpcclient

# Create client
client = grpcclient.InferenceServerClient(
    url="a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8001"
)

# Check server status
is_ready = client.is_server_ready()
print(f"Server is ready: {is_ready}")

if is_ready:
    # Get model status
    models = client.get_model_repository_index()
    print("\nAvailable models:", models)
    
    # Get server metadata
    metadata = client.get_server_metadata()
    print("\nServer metadata:", metadata)
