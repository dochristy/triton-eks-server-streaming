import numpy as np
import boto3
import io
from tritonclient.grpc import InferenceServerClient, InferInput, InferRequestedOutput
from PIL import Image
import torchvision.transforms as transforms
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from torchvision.utils import make_grid
import torch
import os
from datetime import datetime
from monitoring import pipeline_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TritonS3VisionPipeline:
    def __init__(self, s3_bucket="dry-bean-bucket-c", triton_url='a254e6b35e7374cafa61153fa01a5ae0-291966535.us-east-1.elb.amazonaws.com:8001'):
        self.client = InferenceServerClient(url=triton_url)
        self.s3 = boto3.client('s3')
        self.bucket = s3_bucket

        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        self.models = {
            "densenet": {"model_name": "densenet_onnx", "input_name": "data_0", "output_name": "fc6_1"},
            "resnet": {"model_name": "resnet50_onnx", "input_name": "data", "output_name": "resnetv24_dense0_fwd"}
        }

        # Get model configurations from Triton
        self.models = self.get_model_configurations()



        # Create output directory with timestamp
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = f"visualization_outputs_{self.timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Created output directory: {self.output_dir}")

    def get_model_configurations(self):
        """Fetch model configurations from Triton server."""
        try:
            model_configs = {}

            # Get DenseNet configuration
            densenet_metadata = self.client.get_model_metadata("densenet_onnx", "1")
            densenet_config = self.client.get_model_config("densenet_onnx", "1")

            # Get ResNet configuration
            resnet_metadata = self.client.get_model_metadata("resnet50_onnx", "1")
            resnet_config = self.client.get_model_config("resnet50_onnx", "1")

            model_configs["densenet"] = {
                "model_name": "densenet_onnx",
                "input_name": densenet_metadata.inputs[0].name,
                "output_name": densenet_metadata.outputs[0].name
            }

            model_configs["resnet"] = {
                "model_name": "resnet50_onnx",
                "input_name": resnet_metadata.inputs[0].name,
                "output_name": resnet_metadata.outputs[0].name
            }

            logger.info("Successfully fetched model configurations from Triton")
            return model_configs

        except Exception as e:
            logger.error(f"Error fetching model configurations: {str(e)}")
            logger.warning("Falling back to default configurations")

            # Fallback to default configurations
            return {
                "densenet": {
                    "model_name": "densenet_onnx",
                    "input_name": "data_0",
                    "output_name": "fc6_1"
                },
                "resnet": {
                    "model_name": "resnet50_onnx",
                    "input_name": "data",
                    "output_name": "resnetv24_dense0_fwd"
                }
            }

    def load_image_from_s3(self, s3_key):
        logger.info(f"Loading image from S3: {s3_key}")
        response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
        image_bytes = response['Body'].read()
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        return image

    def preprocess_image(self, image):
        logger.info("Preprocessing image")
        img_tensor = self.preprocess(image)
        return img_tensor.numpy()[None, ...]

    def process_model(self, input_data, model_config):
        logger.info(f"Processing with model: {model_config['model_name']}")
        inputs = [InferInput(model_config['input_name'], input_data.shape, "FP32")]
        inputs[0].set_data_from_numpy(input_data)
        outputs = [InferRequestedOutput(model_config['output_name'])]
        response = self.client.infer(model_config['model_name'], inputs, outputs=outputs)
        return response.as_numpy(model_config['output_name'])

    def transform_densenet_output(self, densenet_output):
        logger.info("Transforming DenseNet output for ResNet input")
        target_shape = (1, 3, 224, 224)
        target_elements = np.prod(target_shape)
        flattened = densenet_output.flatten()
        if flattened.size < target_elements:
            padded = np.pad(flattened, (0, target_elements - flattened.size), mode='constant')
        elif flattened.size > target_elements:
            raise ValueError(f"DenseNet output size exceeds ResNet input size: {target_elements}")
        reshaped = padded.reshape(target_shape)
        return reshaped

    def visualize_preprocessing_steps(self, original_image):
        """Visualize each step of the preprocessing pipeline."""
        plt.figure(figsize=(20, 5))

        # Original image
        plt.subplot(1, 4, 1)
        plt.imshow(original_image)
        plt.title("Original Image")
        plt.axis('off')

        # After resize
        resize_transform = transforms.Resize(256)
        resized_img = resize_transform(original_image)
        plt.subplot(1, 4, 2)
        plt.imshow(resized_img)
        plt.title("After Resize (256)")
        plt.axis('off')

        # After center crop
        crop_transform = transforms.CenterCrop(224)
        cropped_img = crop_transform(resized_img)
        plt.subplot(1, 4, 3)
        plt.imshow(cropped_img)
        plt.title("After Center Crop (224)")
        plt.axis('off')

        # After normalization
        tensor_transform = transforms.ToTensor()
        normalize_transform = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
        tensor_img = tensor_transform(cropped_img)
        normalized_img = normalize_transform(tensor_img)

        # Convert normalized tensor back to viewable image
        img_for_display = normalized_img.clone()
        for t, m, s in zip(img_for_display, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]):
            t.mul_(s).add_(m)

        plt.subplot(1, 4, 4)
        plt.imshow(img_for_display.permute(1, 2, 0).numpy())
        plt.title("After Normalization")
        plt.axis('off')

        # Save the visualization
        filename = os.path.join(self.output_dir, 'preprocessing_steps.png')
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        logger.info(f"Saved preprocessing steps visualization to {filename}")

    def visualize_feature_maps(self, tensor, title, max_features=16):
        """Visualize feature maps from the model outputs and save to file."""
        # Convert numpy array to torch tensor if needed
        if isinstance(tensor, np.ndarray):
            tensor = torch.from_numpy(tensor)

        # Reshape if necessary
        if len(tensor.shape) == 2:
            tensor = tensor.unsqueeze(0).unsqueeze(0)
        elif len(tensor.shape) == 3:
            tensor = tensor.unsqueeze(0)

        # Select a subset of features to visualize
        n_features = min(tensor.shape[1], max_features)
        features = tensor[0, :n_features]

        # Normalize features for visualization
        features = features - features.min()
        features = features / features.max()

        # Create grid
        grid = make_grid(features.unsqueeze(1), nrow=4, padding=2, normalize=True)

        # Plot and save
        plt.figure(figsize=(15, 15))
        plt.imshow(grid.numpy().transpose((1, 2, 0)), cmap='viridis')
        plt.title(f'{title} - Feature Maps')
        plt.axis('off')

        # Save the plot
        filename = os.path.join(self.output_dir, f'{title.lower()}_feature_maps.png')
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        logger.info(f"Saved feature maps to {filename}")

    def visualize_activation_heatmap(self, tensor, title):
        """Create a heatmap visualization of the activation values and save to file."""
        # If tensor is multi-dimensional, take the mean across all but the last two dimensions
        if len(tensor.shape) > 2:
            tensor = np.mean(tensor, axis=tuple(range(len(tensor.shape)-2)))

        plt.figure(figsize=(12, 8))
        sns.heatmap(tensor, cmap='viridis', center=0)
        plt.title(f'{title} - Activation Heatmap')

        # Save the plot
        filename = os.path.join(self.output_dir, f'{title.lower()}_heatmap.png')
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        logger.info(f"Saved heatmap to {filename}")

    def save_original_image(self, image, s3_key):
        """Save the original image."""
        plt.figure(figsize=(8, 8))
        plt.imshow(image)
        plt.title("Original Image")
        plt.axis('off')

        # Extract filename from S3 key
        image_name = os.path.basename(s3_key).split('.')[0]
        filename = os.path.join(self.output_dir, f'original_{image_name}.png')
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        logger.info(f"Saved original image to {filename}")

    @pipeline_monitor(timeout=300)
    def run_pipeline_with_viz(self, s3_key):
        """Run the pipeline and save visualizations."""
        logger.info("Running vision pipeline with visualizations")

        # Load original image
        original_image = self.load_image_from_s3(s3_key)

        # Save original image and preprocessing steps
        self.save_original_image(original_image, s3_key)
        self.visualize_preprocessing_steps(original_image)

        # Get model outputs
        processed_image = self.preprocess_image(original_image)

        # Process and visualize DenseNet
        densenet_output = self.process_model(processed_image, self.models['densenet'])
        self.visualize_feature_maps(densenet_output, "DenseNet")
        self.visualize_activation_heatmap(densenet_output, "DenseNet")

        # Transform DenseNet output for ResNet input
        transformed_input = self.transform_densenet_output(densenet_output)

        # Process and visualize ResNet
        resnet_output = self.process_model(transformed_input, self.models['resnet'])
        self.visualize_feature_maps(resnet_output, "ResNet")
        self.visualize_activation_heatmap(resnet_output, "ResNet")

        logger.info(f"All visualizations have been saved to directory: {self.output_dir}")
        return densenet_output, resnet_output

# Example usage
if __name__ == "__main__":
    pipeline = TritonS3VisionPipeline()
    s3_key = "images/pexels-pixabay-45201.jpg"
    densenet_output, resnet_output = pipeline.run_pipeline_with_viz(s3_key)
