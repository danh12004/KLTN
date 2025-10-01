import os
import shutil
from src.model.retrain.config import DATASETS_DIR, STORAGE_DIR
import random

def get_latest_dataset_path():
    all_versions = [d for d in os.listdir(DATASETS_DIR) if os.path.isdir(os.path.join(DATASETS_DIR, d))]
    if not all_versions:
        return None
    latest_version = sorted(all_versions, key=lambda v: int(v.split('_v')[-1]))[-1]
    return os.path.join(DATASETS_DIR, latest_version)

def cleanup_old_datasets(keep_latest=3):
    versions = [d for d in os.listdir(DATASETS_DIR) 
                if os.path.isdir(os.path.join(DATASETS_DIR, d))]
    versions_sorted = sorted(versions, key=lambda v: int(v.split('_v')[-1]))
    for old_version in versions_sorted[:-keep_latest]:
        shutil.rmtree(os.path.join(DATASETS_DIR, old_version))
        print(f"Đã xóa dataset cũ: {old_version}")

def create_new_dataset_snapshot(train_ratio=0.8):
    latest_dataset_path = get_latest_dataset_path()
    if latest_dataset_path is None:
        print("Lỗi: Không tìm thấy dataset gốc.")
        return None

    current_version_num = int(os.path.basename(latest_dataset_path).split('_v')[-1])
    new_version_num = current_version_num + 1
    new_dataset_name = f"rice_disease_ds_v{new_version_num}"
    new_dataset_path = os.path.join(DATASETS_DIR, new_dataset_name)
    os.makedirs(new_dataset_path, exist_ok=True)

    print(f"Dataset nguồn: {latest_dataset_path}")
    print(f"Tạo dataset mới tại: {new_dataset_path}")

    all_images = {}

    for split in ["train", "test"]:
        split_path = os.path.join(latest_dataset_path, split)
        if os.path.exists(split_path):
            for class_name in os.listdir(split_path):
                class_path = os.path.join(split_path, class_name)
                if os.path.isdir(class_path):
                    all_images.setdefault(class_name, [])
                    for img in os.listdir(class_path):
                        all_images[class_name].append(os.path.join(class_path, img))

    for class_name in os.listdir(STORAGE_DIR):
        storage_class_path = os.path.join(STORAGE_DIR, class_name)
        if os.path.isdir(storage_class_path):
            all_images.setdefault(class_name, [])
            for img in os.listdir(storage_class_path):
                all_images[class_name].append(os.path.join(storage_class_path, img))

    total_new_images = 0
    for class_name, imgs in all_images.items():
        random.shuffle(imgs)
        n_train = int(len(imgs) * train_ratio)
        splits = {
            "train": imgs[:n_train],
            "test": imgs[n_train:]
        }
        for split_name, split_imgs in splits.items():
            class_dir = os.path.join(new_dataset_path, split_name, class_name)
            os.makedirs(class_dir, exist_ok=True)
            for img_path in split_imgs:
                shutil.copy(img_path, class_dir)
                if STORAGE_DIR in img_path:
                    total_new_images += 1

    for class_name in os.listdir(STORAGE_DIR):
        class_path = os.path.join(STORAGE_DIR, class_name)
        if os.path.isdir(class_path):
            for img_file in os.listdir(class_path):
                os.remove(os.path.join(class_path, img_file))

    cleanup_old_datasets(keep_latest=3)

    print(f"Đã gộp và chia lại train/test. Số ảnh mới từ 'storage' được thêm: {total_new_images}")
    return new_dataset_path
