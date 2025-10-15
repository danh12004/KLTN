import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from src.model.retrain.config import SEED, IMAGE_SIZE, BATCH_SIZE, AUTOTUNE, LEARNING_RATE, EPOCHS
from src.logging.logger import logger

def build_model(base_model, num_classes, augmentation_layer):
    """Xây dựng model Keras với các lớp tùy chỉnh phía trên base model."""
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    inputs = tf.keras.Input(shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3))
    x = augmentation_layer(inputs)
    x = base_model(x, training=False) 
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    return models.Model(inputs, outputs)

def train_model(train_dir: str, base_model_path: str):
    """
    Huấn luyện model từ dữ liệu trong thư mục và một model cơ sở.
    """
    try:
        train_ds = tf.keras.utils.image_dataset_from_directory(
            train_dir, validation_split=0.2, subset="training",
            seed=SEED, image_size=IMAGE_SIZE, batch_size=BATCH_SIZE
        )
        val_ds = tf.keras.utils.image_dataset_from_directory(
            train_dir, validation_split=0.2, subset="validation",
            seed=SEED, image_size=IMAGE_SIZE, batch_size=BATCH_SIZE
        )
    except Exception as e:
        logger.error(f"Lỗi khi tải dataset từ {train_dir}: {e}")
        return None, None

    num_classes = len(train_ds.class_names)
    logger.info(f"Tìm thấy {num_classes} lớp: {train_ds.class_names}")

    def configure_ds(ds):
        return ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)

    train_ds = configure_ds(train_ds)
    val_ds = configure_ds(val_ds)

    efficientnet_base = EfficientNetB0(include_top=False, weights='imagenet', input_shape=(*IMAGE_SIZE, 3))
    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.1),
        layers.RandomZoom(0.1),
        layers.RandomContrast(0.1),
        layers.RandomTranslation(0.05, 0.05),
    ])

    model = build_model(efficientnet_base, num_classes, data_augmentation)
    
    try:
        model.load_weights(base_model_path)
        logger.info(f"Đã tải trọng số thành công từ model cũ: {base_model_path}")
    except Exception as e:
        logger.warning(f"Không tải được trọng số từ {base_model_path}: {e}. Bắt đầu huấn luyện từ trọng số ImageNet.")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss='sparse_categorical_crossentropy', metrics=['accuracy']
    )

    callbacks = [
        EarlyStopping(patience=7, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(factor=0.2, patience=3, verbose=1)
    ]

    try:
        logger.info(f"Bắt đầu huấn luyện model trong {EPOCHS} epochs...")
        history = model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)
        logger.info("Huấn luyện hoàn tất.")
        return model, history
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng trong quá trình huấn luyện: {e}")
        return None, None
