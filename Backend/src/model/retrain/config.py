import os
import tensorflow as tf

BASE_DATA_PATH = "D:/Final_Project/KLTN/Backend/data/clean_data/image_data"
DATASETS_DIR = os.path.join(BASE_DATA_PATH, "datasets")
STORAGE_DIR = os.path.join(BASE_DATA_PATH, "storage")
MODEL_VERSIONS_DIR = "D:/Final_Project/KLTN/Backend/src/model/versions"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 64
SEED = 42
AUTOTUNE = tf.data.AUTOTUNE
LEARNING_RATE = 1e-4
EPOCHS = 50 