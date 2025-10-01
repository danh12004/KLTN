class ActionAgent:
    def execute_spraying(self, farmer_id: str, drug_info: dict):
        print("\n[AGENT HÀNH ĐỘNG] <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        print(f"[AGENT HÀNH ĐỘNG] Đã nhận lệnh thực thi cho nông hộ {farmer_id}.")
        print(f"[AGENT HÀNH ĐỘNG] Gửi lệnh đến hệ thống phun thuốc tự động:")
        print(f"  - Tên thuốc: {drug_info.get('sản_phẩm_tham_khảo', 'N/A')}")
        print(f"  - Liều lượng: {drug_info.get('liều_lượng', 'N/A')}")
        print(f"  - Ghi chú: {drug_info.get('cách_dùng', 'N/A')}")
        print("[AGENT HÀNH ĐỘNG] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        print("[AGENT HÀNH ĐỘNG] Thực thi hoàn tất. Hệ thống sẽ giám sát kết quả.")
        
        return {"status": "success", "message": "Lệnh đã được gửi đi."}