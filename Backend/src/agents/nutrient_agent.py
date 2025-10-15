import json
from datetime import datetime
from .base_agent import BaseAgent
from src.logging.logger import logger 

class NutrientAgent(BaseAgent):
    """
    Agent chuyên trách việc lập kế hoạch bón phân cho toàn bộ vụ mùa.
    """
    def create_fertilization_plan(self, farmer_id: str):
        if not self.client:
            logger.warning("NutrientAgent không thể tạo kế hoạch vì Trợ lý AI (OpenAI client) chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        user, farm = self._get_user_and_farm(farmer_id)
        if not farm:
            logger.warning(f"Không tìm thấy nông trại cho người dùng ID {farmer_id} khi tạo kế hoạch bón phân.")
            return {"error": f"Không tìm thấy nông trại cho người dùng ID {farmer_id}."}

        days_after_planting = (datetime.now().date() - farm.planting_date).days if farm.planting_date else -1
        rice_variety = getattr(farm, 'rice_variety', 'chưa rõ giống')
        soil_type = getattr(farm, 'soil_type', 'chưa rõ loại đất')

        farmer_info_for_llm = {
            "farmer_id": user.id, "farm_name": farm.name, "area_ha": farm.area_ha,
            "planting_date": str(farm.planting_date), "days_after_planting": days_after_planting,
            "rice_variety": rice_variety, "soil_type": soil_type,
        }

        query_for_retrieval = f"""
            Quy trình bón phân đầy đủ cho giống lúa {rice_variety} trên loại đất {soil_type}. 
            Thông tin về các giai đoạn sinh trưởng quan trọng như đẻ nhánh, làm đòng, trổ bông. 
            Liều lượng NPK, Urê, Kali cho từng giai đoạn.
        """
        retrieved_context = self.vector_store.retrieve("fertilizer_management", query_for_retrieval, k=10)

        prompt = self._build_fertilization_prompt(retrieved_context, farmer_info_for_llm)
        
        try:
            logger.info(f"Đang tạo kế hoạch bón phân cho nông hộ {farmer_id}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.2) 
            )
            plan = json.loads(response.choices[0].message.content)
            logger.info(f"Đã tạo thành công kế hoạch bón phân cho nông hộ {farmer_id}.")
            return {"plan": plan}
        except Exception as e:
            logger.error(f"Lỗi khi gọi API OpenAI để tạo kế hoạch bón phân cho {farmer_id}: {e}")
            return {"error": "Rất tiếc, đã có lỗi khi tạo kế hoạch bón phân."}

    def _build_fertilization_prompt(self, retrieved_context: str, farmer_info: dict) -> str:
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        
        prompt = f"""
            **Bối cảnh:**
            Bạn là một chuyên gia nông học hàng đầu về dinh dưỡng cây lúa. Nhiệm vụ của bạn là tạo ra một lịch trình bón phân cực kỳ chi tiết, khoa học và dễ áp dụng cho nông dân.

            **Thông tin đầu vào:**
            1. **KIẾN THỨC NỀN (Từ tài liệu nông nghiệp):**
            ```
            {retrieved_context}
            ```
            2. **Thông tin nông hộ:**
            ```json
            {farmer_json}
            ```

            **Yêu cầu:**
            1.  **Phân tích:** Dựa vào kiến thức nền, xác định các giai đoạn bón phân chính.
            2.  **Lập Kế hoạch Chi tiết:** Tạo ra một kế hoạch bón phân theo từng giai đoạn. Với MỖI giai đoạn, hãy nêu thật rõ ràng các điểm sau:
                -   **Mục tiêu (objective):** Nêu rõ mục đích nông học của đợt bón phân.
                -   **Dấu hiệu nhận biết (key_indicators):** Mô tả các dấu hiệu hình thái của cây lúa để nông dân xác định đúng thời điểm bón.
                -   **Tính toán liều lượng:** **BẮT BUỘC thực hiện theo 3 bước sau:**
                    1.  **Trích xuất:** Từ KIẾN THỨC NỀN, tìm liều lượng khuyến nghị (thường là một khoảng, ví dụ: '20–30 kg/công'). Ghi giá trị này vào trường `recommended_dosage_per_cong`.
                    2.  **Tính toán:** Chọn một giá trị trung bình từ khoảng đó. Áp dụng công thức: `Tổng Lượng (kg) = area_ha * 10 * (giá trị trung bình kg/công)`. Ghi lại toàn bộ phép tính của bạn vào trường `calculation_details` (ví dụ: '1.3 ha * 10 công/ha * 25 kg/công = 325 kg').
                    3.  **Ghi kết quả:** Ghi kết quả cuối cùng vào trường `quantity_kg`.
                -   **Hướng dẫn kỹ thuật bón (fertilizers.instructions):** **CỰC KỲ QUAN TRỌNG.** Bạn PHẢI trích xuất và tổng hợp thông tin chi tiết từ KIẾN THỨC NỀN. **KHÔNG ĐƯỢC PHÉP** chỉ viết "Rải đều". Hướng dẫn phải bao gồm:
                    -   Phương pháp bón (rải đều, vùi vào đất, etc.).
                    -   Quản lý nước (mực nước lý tưởng trước và sau khi bón).
                    -   Thời điểm trong ngày (sáng sớm/chiều mát).
                    -   Điều kiện cần tránh (nắng gắt, mưa to, ruộng ngập/khô).
                -   **Lưu ý quan trọng (important_notes):** Đưa ra những cảnh báo hoặc sai lầm phổ biến cần tránh.
            3.  **Tư vấn bổ sung (additional_advice):** Đưa ra các lời khuyên chung cho cả vụ.

            **Định dạng đầu ra:**
            Hãy trả lời bằng một đối tượng JSON DUY NHẤT, tuân thủ nghiêm ngặt cấu trúc chi tiết như sau:

            ```json
            {{
                "main_summary": "string",
                "fertilization_stages": [
                    {{
                        "stage_name": "string",
                        "timing": "string",
                        "objective": "string",
                        "key_indicators": "string",
                        "fertilizers": [
                            {{
                                "type": "string (ví dụ: 'Supe lân')",
                                "recommended_dosage_per_cong": "string (Trích xuất nguyên văn từ tài liệu, ví dụ: '20-30 kg/công')",
                                "calculation_details": "string (Hiển thị rõ phép tính, ví dụ: '1.3 ha * 10 * 25 kg/công = 325 kg')",
                                "quantity_kg": "float (Kết quả cuối cùng của phép tính)",
                                "instructions": "string (ĐOẠN VĂN HƯỚNG DẪN CHI TIẾT)"
                            }}
                        ],
                        "important_notes": "string"
                    }}
                ],
                "additional_advice": "string"
            }}
            ```
        """
        return prompt

