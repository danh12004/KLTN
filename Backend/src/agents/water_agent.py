import json
from datetime import datetime, timezone
from .base_agent import BaseAgent
from src.logging.logger import logger

class WaterAgent(BaseAgent):
    """
    Agent chuyên trách việc đưa ra các khuyến nghị về quản lý nước tưới.
    """
    def create_water_management_plan(self, farmer_id: str, context_data_from_ema=None, iot_data: dict = None):
        if not self.client:
            logger.warning("WaterAgent không thể tạo tư vấn vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        user, farm = self._get_user_and_farm(farmer_id)
        if not farm:
            logger.warning(f"Không tìm thấy nông trại cho người dùng ID {farmer_id} khi tạo tư vấn quản lý nước.")
            return {"error": f"Không tìm thấy nông trại cho người dùng ID {farmer_id}."}
        
        if context_data_from_ema:
            logger.info("[Water] Sử dụng Context Data từ Orchestrator (EMA).")
            days_after_planting = context_data_from_ema.get('days_after_planting', -1)
            daily_summary = context_data_from_ema.get('daily_weather_summary')
            
        else:
            days_after_planting = (datetime.now().date() - farm.planting_date).days if farm.planting_date else -1
            hourly_forecast = self.weather_service.get_forecast(farm.province)
            daily_summary = self._summarize_daily_forecast(hourly_forecast) if hourly_forecast else []

        query_for_retrieval = f"""
            Kỹ thuật điều tiết nước tưới cho lúa ở giai đoạn {days_after_planting} ngày tuổi. 
            Phương pháp tưới ngập khô xen kẽ và cách xử lý khi thời tiết nắng nóng hoặc có mưa.
        """
        retrieved_context = self.vector_store.retrieve("water_management", query_for_retrieval, k=3)

        prompt = self._build_water_prompt(farmer_id, retrieved_context, days_after_planting, daily_summary, iot_data)
        
        try:
            logger.info(f"Đang tạo tư vấn quản lý nước cho nông hộ {farmer_id}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.7)
            )
            plan = json.loads(response.choices[0].message.content)
            
            new_session = self.analysis_repo.create_session(
                farm_id=farm.id,
                initial_detection="Quản lý Nước",
                plan_type="water",
                image_path=None,
            )
            self.analysis_repo.update_session_plan(new_session, plan)
            self.analysis_repo.commit()
            
            logger.info(f"Đã tạo và lưu thành công kế hoạch nước cho session {new_session.id}.")
            return {"session_id": new_session.id, "plan": plan}
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo tư vấn quản lý nước cho nông hộ {farmer_id}: {e}")
            self.analysis_repo.rollback()
            return {"error": "Rất tiếc, đã có lỗi khi tạo tư vấn quản lý nước."}
            
    def _build_update_prompt(self, current_plan: dict, user_message: str) -> str:
        current_plan_json = json.dumps(current_plan, ensure_ascii=False, indent=2)

        prompt = f"""
            **Bối cảnh & Vai trò:**
            Bạn là một trợ lý nông nghiệp AI chuyên gia về thủy lợi. Nhiệm vụ của bạn là điều chỉnh kế hoạch quản lý nước hiện tại (JSON) dựa trên yêu cầu cụ thể của nông dân.

            **QUY TẮC RÀNG BUỘC CỐT LÕI:**
            1. **Chỉ Cập nhật Dữ liệu:** Nhiệm vụ của bạn chỉ là cập nhật dữ liệu liên quan đến nước (mực nước, lệnh, lý do) trong JSON.
            2. **KHÔNG** được thêm thông tin ngoài lề, kiến thức chung, hay nội dung không liên quan đến VIỆC QUẢN LÝ NƯỚC này vào bất kỳ trường nào.
            3. Nếu yêu cầu của nông dân **mơ hồ** (ví dụ: "làm tốt hơn") hoặc **không thể xác định** thay đổi cụ thể, BẮT BUỘC bạn phải giữ nguyên kế hoạch cũ và giải thích trong `reason` hoặc `current_assessment` rằng thông tin chưa rõ ràng.
            4. **Cảnh báo BẮT BUỘC:** Nếu yêu cầu của nông dân có thể gây hại cho cây trồng (ví dụ: tháo cạn nước ở giai đoạn đẻ nhánh/làm đòng), BẮT BUỘC phải ghi rõ cảnh báo trong `reason` và `current_assessment`.

            **Kế hoạch ban đầu của bạn:**
            ```json
            {current_plan_json}
            ```

            **Phản hồi/Yêu cầu của nông dân:**
            "{user_message}"

            **QUY TRÌNH RA QUYẾT ĐỊNH (Bắt buộc tuân thủ):**
            1. **Trích xuất ý định:** Xác định chính xác nông dân muốn thay đổi gì về **định lượng nước (mực nước/lượng nước) hoặc lịch trình hành động**.
            2. **Đánh giá và Cảnh báo (Nếu cần):**
            a. So sánh ý định của nông dân với các nguyên tắc nông học.
            b. Nếu ý định đó **KHÔNG tối ưu** hoặc **CÓ HẠI**, bạn **phải** giải thích cảnh báo chi tiết trong trường `reason` và `current_assessment`.
            3. **Cập nhật Kế hoạch (Bắt buộc):** Bất kể có cảnh báo hay không, **BẠN PHẢI CẬP NHẬT TRƯỜNG `water_amount_detail`, `three_day_plan` và `immediate_command`** ĐỂ PHẢN ÁNH CHÍNH XÁC VÀ CỤ THỂ SỐ LƯỢNG MÀ NÔNG DÂN ĐƯA RA (ví dụ: 'nâng mực nước lên 4 cm').
            4. **Tạo thông điệp mới:** Cập nhật lại `reason` và `current_assessment` để bao gồm cả việc xác nhận/cảnh báo và giải thích cho việc thay đổi.

            **Định dạng đầu ra:**
            Chỉ trả về đối tượng JSON của kế hoạch đã được cập nhật, giữ nguyên cấu trúc như kế hoạch ban đầu.
        """
        return prompt

    def _build_water_prompt(self, farmer_id, retrieved_context: str, days_after_planting: int, daily_summary: list, iot_data: dict = None) -> str:
        current_time_utc = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        summary_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
        iot_data_str = ""
        if iot_data:
            iot_json = json.dumps(iot_data, ensure_ascii=False, indent=2)
            iot_data_str = f"""
            4. **DỮ LIỆU CẢM BIẾN IOT & GPS (Thông tin thực tế tại ruộng):**
            ```json
            {iot_json}
            ```
            """

        prompt = f"""
            **Bối cảnh:**
            Bạn là một chuyên gia về thủy lợi và canh tác lúa. Nhiệm vụ của bạn là đưa ra lời khuyên tức thời về việc quản lý nước trên đồng ruộng cho 3 ngày tới.
            
            **THỜI GIAN HIỆN TẠI (Để tham chiếu thời gian thực):** {current_time_utc} (ISO 8601 UTC)

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

            1. **Phân tích tình hình thực tế:** Dựa vào **dữ liệu IoT (nếu có)** để xác định chính xác mực nước và độ ẩm đất hiện tại. Đây là cơ sở quan trọng nhất cho quyết định.
            2. **Đối chiếu với dự báo:** So sánh tình hình thực tế với dự báo thời tiết (đặc biệt là khả năng mưa) để lường trước các kịch bản có thể xảy ra trong 1-2 ngày tới.
            3. **Đưa ra khuyến nghị chính:** Dựa trên phân tích trên và giai đoạn sinh trưởng của lúa, quyết định hành động chính cho ngày hôm nay và ngày mai. Hành động phải là một trong ba: "TƯỚI THÊM NƯỚC", "THÁO BỚT NƯỚC", hoặc "GIỮ NGUYÊN MỰC NƯỚC".
            4. **Đưa ra định lượng nước (BẮT BUỘC):** Nếu khuyến nghị là "TƯỚI THÊM NƯỚC" hoặc "THÁO BỚT NƯỚC", hãy đưa ra một **định lượng** cụ thể (ví dụ: mực nước mục tiêu là **3-5 cm** hoặc **tháo cạn để khô nứt chân chim**) dựa trên kiến thức nền và giai đoạn sinh trưởng của lúa.
            5. **Giải thích lý do:** Nêu rõ tại sao bạn lại đưa ra khuyến nghị đó, nhấn mạnh vào sự kết hợp giữa điều kiện thực tế và dự báo tương lai. Ví dụ: "Nên tháo bớt nước vì **hiện tại mực nước đang cao (theo cảm biến)**, đồng thời dự báo ngày mai có mưa lớn."
            6. **Lập kế hoạch 3 ngày:** Đưa ra lịch trình hành động ngắn gọn cho 3 ngày tới.
            7. **Lệnh Thực thi Tức thời (BẮT BUỘC):** Tạo một câu lệnh cụ thể, dứt khoát kết hợp khuyến nghị chính và định lượng (dùng `main_recommendation` và `water_amount_detail`) để thực thi ngay hôm nay. Ví dụ: "THỰC HIỆN BƠM NƯỚC để đạt mực 5 cm" hoặc "THỰC HIỆN THÁO NƯỚC để đất nứt nhẹ".

            **Định dạng đầu ra:**
            Hãy trả lời bằng một đối tượng JSON DUY NHẤT có cấu trúc như sau:
            ```json
            {{
                "main_recommendation": "string (TƯỚI THÊM NƯỚC / THÁO BỚT NƯỚC / GIỮ NGUYÊN MỰC NƯỚC)",
                "execution_time": "{current_time_utc}",
                "immediate_command": "string (Lệnh dứt khoát cho hôm nay, ví dụ: 'THỰC HIỆN BƠM NƯỚC để đạt mực 5 cm')", 
                "reason": "string (Giải thích ngắn gọn, súc tích lý do đưa ra quyết định)",
                "water_amount_detail": "string (Chi tiết về lượng nước/mực nước mục tiêu. Ví dụ: 'Nâng mực nước lên 3-5cm' hoặc 'Tháo cạn để đất nứt nhẹ.')", 
                "three_day_plan": {{
                    "today": "string (Hành động và mục tiêu cho hôm nay)",
                    "tomorrow": "string (Hành động và mục tiêu cho ngày mai)",
                    "day_after_tomorrow": "string (Hành động và mục tiêu cho ngày kia)"
                }},
                "current_assessment": "string (Đánh giá ngắn gọn về tình hình hiện tại, ví dụ: 'Lúa đang giai đoạn đẻ nhánh, cần đủ nước. Độ ẩm đất 75% là tốt.')",
                "action_details_for_system": {{ 
                    "farmer_id": "{farmer_id}",
                    "gps_data": {{
                        "lat": "float/string", 
                        "lon": "float/string" 
                    }},
                    "water_command": "string (Tổng hợp Action và Target Level)"
                }}
            }}
            ```
        """
        return prompt

    def update_plan_from_feedback(self, current_plan: dict, user_message: str):
        """Cập nhật kế hoạch quản lý nước dựa trên phản hồi của người dùng."""
        if not self.client:
            logger.warning("Không thể cập nhật kế hoạch vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        logger.info(f"Đang xử lý phản hồi về kế hoạch nước: '{user_message}'")
        prompt = self._build_update_prompt(current_plan, user_message)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.6),
                top_p=self.generation_config.get("top_p", 0.9)
            )
            response_content = response.choices[0].message.content
            updated_plan = json.loads(response_content)
            logger.info("Đã cập nhật kế hoạch nước từ phản hồi của người dùng thành công.")
            return updated_plan
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật kế hoạch nước từ phản hồi: {e}")
            return {"error": "Rất tiếc, đã có lỗi khi xử lý yêu cầu của bác. Vui lòng thử lại."}