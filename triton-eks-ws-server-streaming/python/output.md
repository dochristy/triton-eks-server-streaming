```bash
root@5cf6f491eacd:/app# python3 s3.py
```

```bash
--- Starting parallel model inference request ---
Received request data: {'bucket': 'dry-bean-bucket-c', 'key': 'images/pexels-pixabay-45201.jpg'}
Loading image from s3://dry-bean-bucket-c/images/pexels-pixabay-45201.jpg
Successfully loaded image from S3
Original image size: (2392, 2500)
Resized image size: (224, 224)
Final array shape: (1, 3, 224, 224)
Preprocessed input shape: (1, 3, 224, 224)
Using DenseNet input name: data_0

Running inference for model: densenet_onnx
Inference completed for densenet_onnx
Using ResNet input name: data

Running inference for model: resnet50_onnx
Inference completed for resnet50_onnx
Pipeline response sent to client
```

```bash
root@5cf6f491eacd:/app# python3 c3.py 

=== Starting Parallel Model Pipeline Test ===

Fetching model information...

Fetching DenseNet metadata...

DenseNet Metadata:
{
  "name": "densenet_onnx",
  "versions": [
    "1"
  ],
  "platform": "onnxruntime_onnx",
  "inputs": [
    {
      "name": "data_0",
      "datatype": "FP32",
      "shape": [
        1,
        3,
        224,
        224
      ]
    }
  ],
  "outputs": [
    {
      "name": "fc6_1",
      "datatype": "FP32",
      "shape": [
        1,
        1000,
        1,
        1
      ]
    }
  ]
}

Fetching ResNet metadata...

ResNet Metadata:
{
  "name": "resnet50_onnx",
  "versions": [
    "1"
  ],
  "platform": "onnxruntime_onnx",
  "inputs": [
    {
      "name": "data",
      "datatype": "FP32",
      "shape": [
        -1,
        3,
        224,
        224
      ]
    }
  ],
  "outputs": [
    {
      "name": "resnetv24_dense0_fwd",
      "datatype": "FP32",
      "shape": [
        -1,
        1000
      ]
    }
  ]
}

Initializing WebSocket client...
Initialized WebSocket client with URL: ws://localhost:8080

Running parallel model inference...

Starting parallel model inference request for:
Image: s3://dry-bean-bucket-c/images/pexels-pixabay-45201.jpg

Sending request to server...
Waiting for response...

Processing pipeline response...

--- Processing Pipeline Response ---

DenseNet Results:

Output name: fc6_1
Original output shape: (1, 1000, 1, 1)
Reshaped output shape: (1000,)

Top 5 DenseNet predictions:
Egyptian cat: 50.7423%
tiger cat: 14.3395%
lion: 7.9517%
tiger: 4.0478%
tabby cat: 3.3624%

ResNet Results:

Output name: resnetv24_dense0_fwd
Output shape: (1, 1000)

Top 5 ResNet predictions:
Egyptian cat: 41.0378%
tabby cat: 21.1830%
lion: 15.3351%
tiger cat: 4.6438%
tiger: 3.1139%
```
