## First, Prepare Your AWS Environment:

### Configure AWS CLI
aws configure

### Create ECR repository for Triton server (if not exists)
aws ecr create-repository --repository-name websocket-pipeline

### Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

### Build using your Dockerfile
docker build -t websocket-pipeline .

### Tag and push
```bash
docker tag triton-ws-pipeline ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/websocket-pipeline:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/websocket-pipeline:latest
```

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

## Connect to the EKS cluster
```bash
aws eks update-kubeconfig --name triton-streaming-cluster --region us-east-1
```

```bash
kubectl get nodes
NAME                           STATUS   ROLES    AGE    VERSION
ip-192-168-1-65.ec2.internal   Ready    <none>   125m   v1.27.16-eks-aeac579
```

### Make sure port 8080 which is the web-socket port ( in this implementation ) is exposed

```bash
kubectl get svc
NAME            TYPE           CLUSTER-IP       EXTERNAL-IP                                                                     PORT(S)                                                       AGE
kubernetes      ClusterIP      10.100.0.1       <none>                                                                          443/TCP                                                       154m
triton-server   LoadBalancer   10.100.206.244   ab2c89d3704f3499e9350563e87f167b-00015305edd17b67.elb.us-east-1.amazonaws.com   8000:32604/TCP,8001:31757/TCP,8002:31379/TCP,8080:30896/TCP   146m
```

How to Test:
## Server Side
```bash
kubectl get pods
NAME                             READY   STATUS    RESTARTS   AGE
triton-server-5cd9dffd89-527mr   1/1     Running   0          59m
```

### Inside the container
```bash
kubectl exec -it triton-server-5cd9dffd89-527mr -- /bin/bash
root@triton-server-5cd9dffd89-527mr:/app# ps -ef
UID          PID    PPID  C STIME TTY          TIME CMD
root           1       0  0 01:07 ?        00:00:00 /bin/bash /app/start.sh tritonserver --model-repository=s3://dry-bean-bucket-c/models --http-port=8000 --grpc-port=8001 --metrics-port=8002
root          20       1  0 01:07 ?        00:00:12 tritonserver --model-repository=s3://dry-bean-bucket-c/models --http-port=8000 --grpc-port=8001 --metrics-port=8002 --allow-http=1
root          80       1  0 01:07 ?        00:00:06 python3 /app/pipeline_ws_server.py
root         140       0  0 02:07 pts/0    00:00:00 /bin/bash
root         178     140  0 02:07 pts/0    00:00:00 ps -ef

root@triton-server-5cd9dffd89-527mr:/app# netstat -tuln
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State      
tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN     
tcp        0      0 0.0.0.0:8000            0.0.0.0:*               LISTEN     
tcp        0      0 0.0.0.0:8002            0.0.0.0:*               LISTEN     
tcp6       0      0 :::8001                 :::*                    LISTEN     
```

## Client Side

```bash
python3 simple_test.py ( this file is in python/client directory )

Connection successful!
```

```bash
python3 extended_test.py

=== Test Summary ===
2025-01-29 21:01:08,255 - INFO - WebSocket Connection: ✓
2025-01-29 21:01:08,255 - INFO - S3 Access: ✓
2025-01-29 21:01:08,255 - INFO - Inference Test: ✓
2025-01-29 21:01:08,256 - INFO - HTTP Endpoints:
2025-01-29 21:01:08,256 - INFO -   - Server Health: ✓
2025-01-29 21:01:08,256 - INFO -   - Server Metadata: ✓
2025-01-29 21:01:08,256 - INFO -   - Metrics: ✓
2025-01-29 21:01:08,256 - INFO - Model Repository: ✓
```

```bash
python3 inference_test.py

2025-01-29 21:01:53,124 - INFO - === Starting Inference Test ===
2025-01-29 21:01:53,125 - INFO - Testing inference with image: images/pexels-pixabay-45201.jpg
2025-01-29 21:01:53,217 - INFO - WebSocket connected. Sending request...
2025-01-29 21:01:53,217 - INFO - Request data: {
  "bucket": "dry-bean-bucket-c",
  "key": "images/pexels-pixabay-45201.jpg"
}
2025-01-29 21:01:53,218 - INFO - Request sent successfully
2025-01-29 21:01:53,218 - INFO - Waiting for response...
2025-01-29 21:01:53,878 - INFO - Response received!
2025-01-29 21:01:53,880 - INFO - Response status: success
2025-01-29 21:01:53,880 - INFO - Inference successful!
2025-01-29 21:01:53,880 - INFO - 
densenet predictions:
2025-01-29 21:01:53,882 - INFO - - fc6_1: [[[[-3.0129332542419434]], [[0.46903765201568604]], [[-0.265620619058609]], [[-1.6208163499832153]], [[-0.4089038670063019]], [[2.012303352355957]], [[-0.46711796522140503]], [[-2.303323984146118]], [...
2025-01-29 21:01:53,882 - INFO - 
resnet predictions:
2025-01-29 21:01:53,883 - INFO - - resnetv24_dense0_fwd: [[-3.003066062927246, -0.5051834583282471, -2.0540456771850586, -0.12822139263153076, 0.47703659534454346, 1.8847764730453491, 0.598005473613739, -1.3736971616744995, -0.2111804187297821, 0.0984265208...
```

## Image processing in parallel

```bash
python3 parallel_image_processing.py
Found 3 images
Processing with max 5 concurrent connections

Processing image: images/densenet_heatmap.png

Processing image: images/pexels-pixabay-45201.jpg

Processing image: images/preprocessing_steps (2).png

Results for image: images/densenet_heatmap.png

DENSENET Top 5 Predictions:

fc6_1:
Class 916: 0.5518 (55.18%)
Class 549: 0.2204 (22.04%)
Class 921: 0.0589 (5.89%)
Class 769: 0.0301 (3.01%)
Class 446: 0.0213 (2.13%)

RESNET Top 5 Predictions:

resnetv24_dense0_fwd:
Class 916: 0.9371 (93.71%)
Class 549: 0.0487 (4.87%)
Class 769: 0.0032 (0.32%)
Class 922: 0.0011 (0.11%)
Class 111: 0.0007 (0.07%)

Results for image: images/pexels-pixabay-45201.jpg

DENSENET Top 5 Predictions:

fc6_1:
Class 285: 0.5074 (50.74%)
Class 283: 0.1434 (14.34%)
Class 287: 0.0795 (7.95%)
Class 282: 0.0405 (4.05%)
Class 281: 0.0336 (3.36%)

RESNET Top 5 Predictions:

resnetv24_dense0_fwd:
Class 285: 0.4104 (41.04%)
Class 281: 0.2118 (21.18%)
Class 287: 0.1534 (15.34%)
Class 283: 0.0464 (4.64%)
Class 282: 0.0311 (3.11%)

Results for image: images/preprocessing_steps (2).png

DENSENET Top 5 Predictions:

fc6_1:
Class 716: 0.2988 (29.88%)
Class 991: 0.0922 (9.22%)
Class 112: 0.0878 (8.78%)
Class 684: 0.0528 (5.28%)
Class 700: 0.0346 (3.46%)

RESNET Top 5 Predictions:

resnetv24_dense0_fwd:
Class 285: 0.5263 (52.63%)
Class 203: 0.1262 (12.62%)
Class 250: 0.1018 (10.18%)
Class 248: 0.0584 (5.84%)
Class 281: 0.0531 (5.31%)

Results saved to: inference_results/inference_results_20250129_210250.csv

Batch Processing Summary:
Total images processed: 3
Successful: 3
Failed: 0
Total time: 1.48 seconds
Average time per image: 0.49 seconds
```

## Video processing in parallel

```bash
python3 parallel_video_processing.py

Found 3 videos in bucket:
- videos/Loop 1 - Bloodstream.mp4
- videos/Loop 2 - Blue motion.mp4
- videos/VID-20210905-WA0008.mp4

Starting parallel processing of 3 videos
Maximum concurrent videos: 2
Maximum concurrent frames per video: 3
==================================================

Processing batch 1, videos 1-2
Downloaded video to: video_inference_results/Loop 1 - Bloodstream.mp4

Processing video: videos/Loop 1 - Bloodstream.mp4
FPS: 30.0
Total frames: 300
Processing frames:   0%|                                                                                                                                                                           | 0/300 [00:00<?, ?it/s]Downloaded video to: video_inference_results/Loop 2 - Blue motion.mp4

Processing video: videos/Loop 2 - Blue motion.mp4
FPS: 30.0
Total frames: 270
Processing frames:   2%|███▎                                                                                                                                                               | 6/300 [00:01<00:56,  5.19it/s]
Error processing frame 0: [Errno 2] No such file or directory: 'video_inference_results/temp_frame_0.jpg'                                                                                          | 0/270 [00:00<?, ?it/s]
Processing frames:   2%|███▌                                                                                                                                                               | 6/270 [00:00<00:40,  6.56it/s]
Processing frames:   1%|██▍                                                                                                                                                                | 4/270 [00:00<01:00,  4.39it/s]
Processing batch 2, videos 3-3
Downloaded video to: video_inference_results/VID-20210905-WA0008.mp4

Processing video: videos/VID-20210905-WA0008.mp4
FPS: 30.80880903725065
Total frames: 66
Processing frames:   9%|██████████████▉                                                                                                                                                     | 6/66 [00:00<00:06,  9.66it/s]

==================================================
Batch Processing Summary:
Total videos processed: 3
Successful: 2
Failed: 1
Total time: 2.68 seconds
Average time per video: 0.89 seconds

Batch summary saved to: video_inference_results/batch_summary_20250129_210336.csv

cat video_inference_results/batch_summary_20250129_210336.csv

video_key,status,frames_processed,successful_frames,failed_frames,processing_time,error_message
videos/Loop 1 - Bloodstream.mp4,success,1,1,0,1.792485,
videos/Loop 2 - Blue motion.mp4,failed,1,0,1,1.16032,
videos/VID-20210905-WA0008.mp4,success,1,1,0,0.833841,
```
