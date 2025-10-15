import json
from datetime import datetime
from .base_agent import BaseAgent
from src.logging.logger import logger

class WaterAgent(BaseAgent):
    """
    Agent chuyên trách việc đưa ra các khuyến nghị về quản lý nước tưới.
    """
    def create_water_management_plan(self, farmer_id: str, iot_data: dict = None):
        if not self.client:
            logger.warning("WaterAgent không thể tạo tư vấn vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        user, farm = self._get_user_and_farm(farmer_id)
        if not farm:
            logger.warning(f"Không tìm thấy nông trại cho người dùng ID {farmer_id} khi tạo tư vấn quản lý nước.")
            return {"error": f"Không tìm thấy nông trại cho người dùng ID {farmer_id}."}

        days_after_planting = (datetime.now().date() - farm.planting_date).days if farm.planting_date else -1
        
        hourly_forecast = self.weather_service.get_forecast(farm.province)
        daily_summary = self._summarize_daily_forecast(hourly_forecast) if hourly_forecast else []

        query_for_retrieval = f"""
            Kỹ thuật điều tiết nước tưới cho lúa ở giai đoạn {days_after_planting} ngày tuổi. 
            Phương pháp tưới ngập khô xen kẽ và cách xử lý khi thời tiết nắng nóng hoặc có mưa.
        """
        retrieved_context = self.vector_store.retrieve("water_management", query_for_retrieval, k=3)

        prompt = self._build_water_prompt(retrieved_context, days_after_planting, daily_summary, iot_data)
        
        try:
            logger.info(f"Đang tạo tư vấn quản lý nước cho nông hộ {farmer_id}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.7)
            )
            plan = json.loads(response.choices[0].message.content)
            logger.info(f"Đã tạo thành công tư vấn quản lý nước cho nông hộ {farmer_id}.")
            return {"plan": plan}
        except Exception as e:
            logger.error(f"Lỗi khi tạo tư vấn quản lý nước cho nông hộ {farmer_id}: {e}")
            return {"error": "Rất tiếc, đã có lỗi khi tạo tư vấn quản lý nước."}

    def _build_water_prompt(self, retrieved_context: str, days_after_planting: int, daily_summary: list, iot_data: dict = None) -> str:
        summary_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
        iot_data_str = ""
        if iot_data:
            iot_json = json.dumps(iot_data, ensure_ascii=False, indent=2)
            iot_data_str = f"""
            4. **DỮ LIỆU CẢM BIẾN IOT (Thông tin thực tế tại ruộng):**
            ```json
            {iot_json}
            ```
            """

        prompt = f"""
            **Bối cảnh:**
            Bạn là một chuyên gia về thủy lợi và canh tác lúa. Nhiệm vụ của bạn là đưa ra lời khuyên tức thời về việc quản lý nước trên đồng ruộng cho 3 ngày tới.

            **Thông tin đầu vào:**
            1. **KIẾN THỨC NỀN:**
            ```
            {retrieved_context}
            ```
            2. **Thông tin ruộng lúa:** Lúa đã được {days_after_planting} ngày tuổi.
            3. **DỰ BÁO thời tiết 3 ngày tới (dùng để tham khảo):**
            ```json
            {summary_json}
            ```
            {iot_data_str}

            **Yêu cầu:**
            **QUY TẮC ƯU TIÊN:** Dữ liệu từ cảm biến IoT là thông tin **thực tế và chính xác nhất** về tình hình **hiện tại** trên ruộng. Hãy luôn **ƯU TIÊN** dữ liệu này hơn dữ liệu dự báo. Dữ liệu dự báo chỉ dùng để lên kế hoạch và phòng ngừa cho những ngày sắp tới.

            1.  **Phân tích tình hình thực tế:** Dựa vào **dữ liệu IoT (nếu có)** để xác định chính xác mực nước và độ ẩm đất hiện tại. Đây là cơ sở quan trọng nhất cho quyết định.
            2.  **Đối chiếu với dự báo:** So sánh tình hình thực tế với dự báo thời tiết (đặc biệt là khả năng mưa) để lường trước các kịch bản có thể xảy ra trong 1-2 ngày tới.
            3.  **Đưa ra khuyến nghị chính:** Dựa trên phân tích trên và giai đoạn sinh trưởng của lúa, quyết định hành động chính cho ngày hôm nay và ngày mai. Hành động phải là một trong ba: "TƯỚI THÊM NƯỚC", "THÁO BỚT NƯỚC", hoặc "GIỮ NGUYÊN MỰC NƯỚC".
            4.  **Giải thích lý do:** Nêu rõ tại sao bạn lại đưa ra khuyến nghị đó, nhấn mạnh vào sự kết hợp giữa điều kiện thực tế và dự báo tương lai. Ví dụ: "Nên tháo bớt nước vì **hiện tại mực nước đang cao (theo cảm biến)**, đồng thời dự báo ngày mai có mưa lớn."
            5.  **Lập kế hoạch 3 ngày:** Đưa ra lịch trình hành động ngắn gọn cho 3 ngày tới.

            **Định dạng đầu ra:**
            Hãy trả lời bằng một đối tượng JSON DUY NHẤT có cấu trúc như sau:
            ```json
            {{
                "main_recommendation": "string (TƯỚI THÊM NƯỚC / THÁO BỚT NƯỚC / GIỮ NGUYÊN MỰC NƯỚC)",
                "reason": "string (Giải thích ngắn gọn, súc tích lý do đưa ra quyết định)",
                "three_day_plan": {{
                    "today": "string (Hành động và mục tiêu cho hôm nay)",
                    "tomorrow": "string (Hành động và mục tiêu cho ngày mai)",
                    "day_after_tomorrow": "string (Hành động và mục tiêu cho ngày kia)"
                }},
                "current_assessment": "string (Đánh giá ngắn gọn về tình hình hiện tại, ví dụ: 'Lúa đang giai đoạn đẻ nhánh, cần đủ nước. Độ ẩm đất 75% là tốt.')"
            }}
            ```
        """
        return prompt
