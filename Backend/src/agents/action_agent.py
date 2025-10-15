from src.logging.logger import logger

class ActionAgent:
    """
    Agent thực thi, chịu trách nhiệm gửi lệnh đến các hệ thống vật lý (mô phỏng)
    và ghi lại log chi tiết cho từng loại hành động.
    """
    def execute_spraying(self, farmer_id: str, plan_context: dict):
        """Thực thi lệnh phun thuốc và in ra log đầy đủ ngữ cảnh."""
        analysis = plan_context.get('analysis', {})
        treatment_plan = plan_context.get('treatment_plan', {})
        drug_info = treatment_plan.get('drug_info', {})
        optimal_day = treatment_plan.get('optimal_spray_day', {})

        logger.info("\n[AGENT HÀNH ĐỘNG] <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        logger.info(f"[AGENT HÀNH ĐỘNG] Đã nhận lệnh [PHUN THUỐC] cho nông hộ ID: {farmer_id}.")
        
        logger.info("\n[AGENT HÀNH ĐỘNG] ---- NGỮ CẢNH RA QUYẾT ĐỊNH ----")
        logger.info(f"  - Đánh giá rủi ro: {analysis.get('risk_assessment', 'N/A')}")
        logger.info(f"  - Lý do chọn ngày phun: {optimal_day.get('reason', 'N/A')}")
        
        logger.info("\n[AGENT HÀNH ĐỘNG] ---- CHI TIẾT LỆNH THỰC THI ----")
        logger.info(f"  - Gửi lệnh đến hệ thống Drone/Robot:")
        logger.info(f"    - Tên thuốc: {drug_info.get('sản_phẩm_tham_khảo', 'N/A')}")
        logger.info(f"    - Liều lượng: {drug_info.get('liều_lượng', 'N/A')}")
        logger.info(f"    - Hướng dẫn: {drug_info.get('cách_dùng', 'N/A')}")
        logger.info("\n[AGENT HÀNH ĐỘNG] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    def execute_fertilizing(self, farmer_id: str, plan_context: dict):
        """Thực thi lệnh bón phân và in log."""
        logger.info("\n[AGENT HÀNH ĐỘNG] <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        logger.info(f"[AGENT HÀNH ĐỘNG] Đã nhận lệnh [BÓN PHÂN] cho nông hộ ID: {farmer_id}.")
        
        logger.info("\n[AGENT HÀNH ĐỘNG] ---- TÓM TẮT KẾ HOẠCH ----")
        logger.info(f"  - Mục tiêu chính: {plan_context.get('main_summary', 'N/A')}")
        
        stages = plan_context.get('fertilization_stages', [])
        logger.info(f"\n[AGENT HÀNH ĐỘNG] ---- CHI TIẾT LỆNH THỰC THI ({len(stages)} GIAI ĐOẠN) ----")
        for i, stage in enumerate(stages):
            logger.info(f"  --- Giai đoạn {i+1}: {stage.get('stage_name', 'N/A')} ---")
            for fertilizer in stage.get('fertilizers', []):
                logger.info(f"    - Loại phân: {fertilizer.get('type')}, Số lượng: {fertilizer.get('quantity_kg')} kg")
                logger.info(f"    - Hướng dẫn thực hiện: {fertilizer.get('instructions')}")
        logger.info("\n[AGENT HÀNH ĐỘNG] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    def execute_watering(self, farmer_id: str, plan_context: dict):
        """Thực thi lệnh tưới nước và in log."""
        logger.info("\n[AGENT HÀNH ĐỘNG] <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        logger.info(f"[AGENT HÀNH ĐỘNG] Đã nhận lệnh [QUẢN LÝ NƯỚC] cho nông hộ ID: {farmer_id}.")

        logger.info("\n[AGENT HÀNH ĐỘNG] ---- NGỮ CẢNH RA QUYẾT ĐỊNH ----")
        logger.info(f"  - Đánh giá hiện tại: {plan_context.get('current_assessment', 'N/A')}")
        logger.info(f"  - Lý do đề xuất: {plan_context.get('reason', 'N/A')}")
        
        logger.info("\n[AGENT HÀNH ĐỘNG] ---- CHI TIẾT LỆNH THỰC THI ----")
        logger.info(f"  - Khuyến nghị chính: **{plan_context.get('main_recommendation', 'N/A')}**")
        plan_3_day = plan_context.get('three_day_plan', {})
        logger.info(f"  - Kế hoạch 3 ngày:")
        logger.info(f"    - Hôm nay: {plan_3_day.get('today', 'N/A')}")
        logger.info(f"    - Ngày mai: {plan_3_day.get('tomorrow', 'N/A')}")
        logger.info(f"    - Ngày kia: {plan_3_day.get('day_after_tomorrow', 'N/A')}")
        logger.info("\n[AGENT HÀNH ĐỘNG] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

