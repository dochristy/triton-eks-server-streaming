import logging
from functools import wraps
import time
from typing import Optional, Tuple, Any
import numpy as np

def pipeline_monitor(timeout: int = 300):
    def decorator(func):
        @wraps(func)
        def wrapper(self, s3_key: str, *args, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
            start_time = time.time()
            status = {
                's3_load': False,
                'preprocessing': False,
                'densenet': False,
                'transformation': False,
                'resnet': False,
                'visualization': False
            }

            try:
                # 1. S3 Image Loading
                logging.info(f"Loading image from S3: {s3_key}")
                original_image = self.load_image_from_s3(s3_key)
                status['s3_load'] = True

                # 2. Preprocessing
                logging.info("Preprocessing image")
                processed_image = self.preprocess_image(original_image)
                status['preprocessing'] = True

                # 3. DenseNet Processing
                logging.info("Running DenseNet inference")
                densenet_output = self.process_model(processed_image, self.models['densenet'])
                status['densenet'] = True

                # 4. Transform DenseNet Output
                logging.info("Transforming DenseNet output")
                transformed_input = self.transform_densenet_output(densenet_output)
                status['transformation'] = True

                # 5. ResNet Processing
                logging.info("Running ResNet inference")
                resnet_output = self.process_model(transformed_input, self.models['resnet'])
                status['resnet'] = True

                # 6. Visualizations
                logging.info("Generating visualizations")
                self.save_original_image(original_image, s3_key)
                self.visualize_preprocessing_steps(original_image)
                self.visualize_feature_maps(densenet_output, "DenseNet")
                self.visualize_feature_maps(resnet_output, "ResNet")
                status['visualization'] = True

                execution_time = time.time() - start_time
                logging.info(f"Pipeline completed successfully in {execution_time:.2f} seconds")
                return densenet_output, resnet_output

            except Exception as e:
                execution_time = time.time() - start_time
                failed_step = next((step for step, completed in status.items() if not completed), "unknown")
                logging.error(f"Pipeline failed at step '{failed_step}' after {execution_time:.2f} seconds")
                logging.error(f"Error details: {str(e)}")

                if execution_time > timeout:
                    logging.error(f"Pipeline timed out after {timeout} seconds")
                    raise TimeoutError(f"Pipeline execution exceeded {timeout} seconds")

                raise RuntimeError(f"Pipeline failed at {failed_step}: {str(e)}")

        return wrapper
    return decorator
