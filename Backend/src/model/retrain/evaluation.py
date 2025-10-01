import tensorflow as tf
from tensorflow.keras.applications.efficientnet import preprocess_input as efficientnet_preprocess
from src.model.retrain.config import SEED, IMAGE_SIZE, BATCH_SIZE, AUTOTUNE

def evaluate_model(model_path: str, test_dir: str):
    test_ds = tf.keras.utils.image_dataset_from_directory(
        test_dir, seed=SEED,
        image_size=IMAGE_SIZE, batch_size=BATCH_SIZE
    )

    def preprocess(image, label):
        image = efficientnet_preprocess(image)
        return image, label

    test_ds = test_ds.map(preprocess)
    test_ds = test_ds.cache().prefetch(buffer_size=AUTOTUNE)

    model = tf.keras.models.load_model(model_path)
    loss, acc = model.evaluate(test_ds)
    print(f"Đánh giá trên test set: Loss={loss:.4f}, Accuracy={acc:.4f}")
    return loss, acc
