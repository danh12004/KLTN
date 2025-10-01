import os
import datetime
from src.model.retrain.config import MODEL_VERSIONS_DIR
from src.model.retrain.preprocess import create_new_dataset_snapshot
from src.model.retrain.training import train_model
from src.model.retrain.evaluation import evaluate_model

def retrain_run():
    print(f"--- BẮT ĐẦU QUY TRÌNH RETRAIN VÀO {datetime.datetime.now()} ---")
    
    print("\n[BƯỚC 1/3] Chuẩn bị dữ liệu...")
    new_dataset_path = create_new_dataset_snapshot()
    if new_dataset_path is None:
        print("Dừng quy trình do lỗi chuẩn bị dữ liệu.")
        return

    all_models = [m for m in os.listdir(MODEL_VERSIONS_DIR) if m.endswith('.keras')]
    latest_model_name = sorted(all_models, key=lambda m: int(m.split('_v')[-1].split('.')[0]))[-1]
    base_model_path = os.path.join(MODEL_VERSIONS_DIR, latest_model_name)
    
    print(f"\n[BƯỚC 2/3] Bắt đầu huấn luyện model từ base model: {base_model_path}...")
    train_dir = os.path.join(new_dataset_path, "train")
    new_model, history = train_model(train_dir, base_model_path)

    current_version_num = int(latest_model_name.split('_v')[-1].split('.')[0])
    new_model_name = f"efficientnet_model_v{current_version_num + 1}.keras"
    new_model_path = os.path.join(MODEL_VERSIONS_DIR, new_model_name)
    
    print(f"\n[BƯỚC 3/3] Huấn luyện hoàn tất. Lưu model mới tại: {new_model_path}")
    new_model.save(new_model_path)

    print(f"\n[BƯỚC 4/4] Đánh giá model trên test set...")
    test_dir = os.path.join(new_dataset_path, "test")
    evaluate_model(new_model_path, test_dir)

    print(f"--- KẾT THÚC QUY TRÌNH RETRAIN ---")