import json
from src.utils.config import CONFIG
from openai import OpenAI
from src.logging.logger import logger

class ActionAgent:
    """
    Agent thực thi, chịu trách nhiệm gửi lệnh đến các hệ thống vật lý (mô phỏng)
    và ghi lại log chi tiết cho từng loại hành động.
    """
    def __init__(self):
        self.api_key = CONFIG.OPENAI_API_KEY
        self.model_name = CONFIG.OPENAI_MODEL_NAME
        self.generation_config = CONFIG.OPENAI_GENERATION_CONFIG

        if not self.api_key:
            logger.warning(f"{self.__class__.__name__}: Không tìm thấy OPENAI_API_KEY. Client sẽ không được khởi tạo.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"{self.__class__.__name__} đã khởi tạo OpenAI client thành công!")
            except Exception as e:
                logger.error(f"{self.__class__.__name__}: Lỗi khi khởi tạo OpenAI client: {e}")
                self.client = None

    def _build_treatment_extraction_prompt(self, plan_context: dict) -> str:
        """Xây dựng prompt chuyên cho việc trích xuất dữ liệu phun thuốc (Treatment)."""
        
        context_for_extraction = {
            "optimal_spray_day": plan_context.get("treatment_plan", {}).get("optimal_spray_day", {}),
            "drug_info": plan_context.get("treatment_plan", {}).get("drug_info", {}),
            "weather_summary": plan_context.get("analysis", {}).get("weather_summary", ""),
            "gps_data_source": plan_context.get("action_details_for_system", {}).get("gps_data", {}) 
        }
        
        image_url_for_output = plan_context.get("image_url", "")
        
        context_json = json.dumps(context_for_extraction, ensure_ascii=False, indent=2)

        prompt = f"""
            **Bối cảnh:** Bạn là một công cụ trích xuất dữ liệu chính xác tuyệt đối, chỉ lấy thông tin từ dữ liệu JSON bên dưới.

            **Dữ liệu đầu vào:**
            Dữ liệu JSON sau chứa:
            - `optimal_spray_day`: Thời điểm phun thuốc lý tưởng (gồm `date`, `session`, `reason`).
            - `drug_info`: Thông tin chi tiết về loại thuốc (gồm `sản_phẩm_tham_khảo`, `hoạt_chất`, `liều_lượng`, `cách_dùng`). Lưu ý: Trường `liều_lượng` chứa cả cách pha và tổng liều lượng.
            - `weather_summary`: Tóm tắt thời tiết, chỉ để tham khảo khi xác định thời điểm phun thuốc.
            - `gps_data_source`: Dữ liệu GPS/Vị trí hiện tại (lat/lon).

            ```json
            {context_json}
            ```

            **Nhiệm vụ:** Dựa trên dữ liệu trên, hãy TRÍCH XUẤT và TRẢ VỀ một đối tượng JSON DUY NHẤT theo đúng định dạng đầu ra bên dưới.
            Mọi giá trị phải được lấy từ `context_for_extraction` (không tự suy diễn hoặc thêm dữ liệu không có).

            **Hướng dẫn chi tiết:**
            1. `execution_time`: Lấy từ `optimal_spray_day.date`. Đảm bảo ở định dạng ISO 8601 UTC đầy đủ.
            2. **`drug_name`**: Lấy từ `drug_info.sản_phẩm_tham_khảo`.
            3. **`active_ingredient`**: Lấy từ `drug_info.hoạt_chất`.
            4. **`mixing_instruction`**: Lấy *phần hướng dẫn cách pha* từ `drug_info.liều_lượng`.
            5. **`total_dosage.total_volume` (QUAN TRỌNG):** Lấy *chỉ con số và đơn vị* đại diện cho **tổng lượng** thuốc cần dùng cho toàn bộ diện tích.
               *Ví dụ:* Nếu `drug_info.liều_lượng` là `"Pha 10g/bình. Tổng lượng cần 90g."`, thì `total_volume` PHẢI là `"90g"`.
               *Ví dụ:* Nếu `drug_info.liều_lượng` là `"Hướng dẫn cách pha cho 1 bình và Tính toán chính xác tổng lượng cần dùng cho toàn bộ diện tích (100g)."`, thì `total_volume` PHẢI là `"100g"`.

            6. `gps_data`: Lấy `lat` và `lon` từ `gps_data_source`.

            **Định dạng đầu ra BẮT BUỘC:**
            ```json
            {{
                "execution_time": "YYYY-MM-DDTHH:MM:SSZ",
                "drug_name": "string",
                "active_ingredient": "string",
                "mixing_instruction": "string",
                "total_volume": "string (CHỈ CHỨA CON SỐ VÀ ĐƠN VỊ TỔNG LƯỢNG)",
                "gps_data": {{
                    "lat": "float/string",
                    "lon": "float/string"
                }},
                "image_url": "{image_url_for_output}"
            }}
            ```
        """
        return prompt

    def _build_fertilizing_extraction_prompt(self, plan_context: dict) -> str:
        """
        Xây dựng prompt chuyên cho việc trích xuất dữ liệu bón phân (Fertilizing)
        — rút gọn để gửi qua thiết bị IoT (chỉ lấy thông tin cốt lõi).
        """

        context_for_extraction = {
            "execution_date": plan_context.get("execution_date", ""), 
            "stage_name": plan_context.get("stage_name", ""),
            "fertilizer_stage_detail": plan_context.get("fertilizer_stage_detail", []),
            "gps_data_source": plan_context.get("action_details_for_system", {}).get("gps_data", {}) 
        }

        context_json = json.dumps(context_for_extraction, ensure_ascii=False, indent=2)

        prompt = f"""
            **Bối cảnh:** Bạn là công cụ trích xuất dữ liệu chính xác, nhiệm vụ là lấy các thông tin BÓN PHÂN thiết yếu để gửi cho thiết bị IoT.

            **Đầu vào:**
            ```json
            {context_json}
            ```

            **Yêu cầu:**
            - Phân tích dữ liệu trên để tạo JSON đầu ra GỌN NHẸ, chỉ giữ thông tin cần thiết nhất cho thiết bị nông nghiệp tự động.
            - Nếu có nhiều giai đoạn (`fertilizer_stage_detail`), chỉ lấy **giai đoạn hiện tại hoặc sắp tới nhất**.
            - Tự động chuyển `execution_date` sang **ISO 8601 UTC**.
            - **Bổ sung GPS:** Trích xuất tọa độ GPS từ `gps_data_source`.

            **Định dạng đầu ra (bắt buộc, không giải thích thêm):**
            ```json
            {{
                "execution_time": "YYYY-MM-DDTHH:MM:SSZ",
                "summary": "string (Tóm tắt ngắn gọn lý do và mục tiêu bón)",
                "execution_stage": {{
                    "fertilizers_to_apply": [
                        {{
                            "type": "string",
                            "quantity_kg": "float",
                            "instructions": "string (ngắn gọn, dễ hiểu)"
                        }}
                    ]
                }},
                "caution": "string (nếu có, tóm tắt lưu ý kỹ thuật)",
                "gps_data": {{
                    "lat": "float/string",
                    "lon": "float/string"
                }}
            }}
            ```
        """
        return prompt

    def _build_watering_extraction_prompt(self, plan_context: dict) -> str:
        """Xây dựng prompt trích xuất dữ liệu quản lý nước (Watering) — gọn nhẹ cho hệ thống IoT."""

        context_for_extraction = {
            "main_recommendation": plan_context.get("main_recommendation", "N/A"),
            "execution_time": plan_context.get("execution_time", "N/A"),
            "water_amount_detail": plan_context.get("water_amount_detail", "N/A"),
            "three_day_plan": plan_context.get("three_day_plan", {}),
            "reason": plan_context.get("reason", ""),
            "gps_data_source": plan_context.get("action_details_for_system", {}).get("gps_data", {}), 
            "water_command_source": plan_context.get("action_details_for_system", {}).get("water_command", "")
        }

        context_json = json.dumps(context_for_extraction, ensure_ascii=False, indent=2)

        prompt = f"""
            **Bối cảnh:** Bạn là công cụ trích xuất dữ liệu chính xác cho hệ thống tưới tiêu tự động (IoT Water Controller).

            **Đầu vào:**
            ```json
            {context_json}
            ```

            **Nhiệm vụ:**
            - Dựa vào dữ liệu trên, hãy tạo JSON đầu ra *ngắn gọn, thực dụng*, chỉ gồm các thông tin cần thiết cho thiết bị điều khiển nước.
            - Trích xuất `water_command_source` làm lệnh chính.
            - **Bổ sung GPS:** Trích xuất tọa độ GPS từ `gps_data_source`.

            **Định dạng đầu ra BẮT BUỘC (Không thêm bất kỳ giải thích nào):**
            ```json
            {{
                "execution_time": "YYYY-MM-DDTHH:MM:SSZ (Thời điểm thực hiện, UTC)",
                "action": "string (VD: Tưới nước / Giảm mực nước / Ngưng tưới)",
                "target_level": "string (VD: 3.5 cm / Giữ mức nước ổn định)",
                "gps_data": {{
                    "lat": "float/string",
                    "lon": "float/string"
                }}
            }}
            ```
        """
        return prompt

    def _extract_iot_payload(self, plan_context: dict, plan_type: str) -> dict:
        """Sử dụng LLM để trích xuất thông tin từ kế hoạch và tạo payload cho IoT."""
        if not self.client:
            logger.error("LLM client chưa sẵn sàng cho việc trích xuất.")
            return {"status": "error", "message": "LLM client not configured."}
            
        if plan_type == 'treatment':
            prompt = self._build_treatment_extraction_prompt(plan_context)
        elif plan_type == 'fertilizer':
            prompt = self._build_fertilizing_extraction_prompt(plan_context)
        elif plan_type == 'water':
            prompt = self._build_watering_extraction_prompt(plan_context)
        else:
            return {"status": "error", "message": "Loại kế hoạch không hợp lệ cho việc trích xuất payload."}
            
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.1), 
            )
            response_content = response.choices[0].message.content
            payload = json.loads(response_content)
            
            if not isinstance(payload, dict):
                logger.error(f"Phản hồi LLM không phải JSON hợp lệ: {response_content}")
                return {"status": "error", "message": "LLM returned invalid JSON structure."}
                
            return payload
            
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất payload từ LLM (Type: {plan_type}): {e}")
            response_content = locals().get('response_content', 'N/A')
            logger.error(f"Phản hồi LLM gốc: {response_content}")
            return {"status": "error", "message": f"Failed to extract IoT payload from plan ({plan_type})."}


    def execute_spraying(self, farmer_id: str, plan_context: dict):
        """
        Thực thi lệnh phun thuốc.
        - Gọi LLM để trích xuất payload JSON đáng tin cậy.
        - In log tường minh cho người vận hành.
        """
        iot_command_payload = self._extract_iot_payload(plan_context, 'treatment')
        
        if iot_command_payload.get("status") == "error":
            return {"status": "error", "message": f"Không thể trích xuất lệnh phun thuốc: {iot_command_payload['message']}"}

        iot_command_payload["farmer_id"] = farmer_id 
        
        dosage = iot_command_payload.get('total_dosage', {})

        logger.info("\n" + "="*50)
        logger.info(f"ĐÃ NHẬN LỆNH [PHUN THUỐC] CHO NÔNG HỘ ID: {farmer_id}")
        logger.info("="*50)
        
        diagnosis = plan_context.get('initial_detection', 'N/A')
        logger.info("\n---- NGỮ CẢNH RA QUYẾT ĐỊNH ----")
        logger.info(f" - CHẨN ĐOÁN GỐC: {diagnosis}")
        logger.info(f" - Đánh giá rủi ro: {plan_context.get('analysis', {}).get('risk_assessment', 'N/A')}")
        logger.info(f" - Lý do chọn ngày phun: {plan_context.get('treatment_plan', {}).get('optimal_spray_day', {}).get('reason', 'N/A')}")
        
        logger.info("\n---- CHI TIẾT LỆNH THỰC THI (LLM PAYLOAD) ----")
        logger.info(f" - Gửi lệnh đến hệ thống: Drone/Robot System")
        logger.info(f" - Thời gian thực hiện: **{iot_command_payload.get('execution_time', 'N/A')}**")
        logger.info(f" - Tên thuốc: **{iot_command_payload.get('drug_name', 'N/A')}**")
        logger.info(f" - Hoạt chất: {iot_command_payload.get('active_ingredient', 'N/A')}")
        logger.info(f" - Liều lượng/Diện tích: {dosage.get('application_rate', 'N/A')} (Áp dụng cho {dosage.get('farm_area', 'N/A')})")
        logger.info(f" - Tổng lượng cần pha: {dosage.get('total_volume', 'N/A')}")
        logger.info(f" - Hướng dẫn pha chi tiết: {iot_command_payload.get('mixing_instruction', 'N/A')}")
        
        logger.info("\n" + "="*50)
        logger.info(f"HOÀN TẤT GHI NHẬN LỆNH PHUN THUỐC ID: {farmer_id}")
        logger.info("="*50 + "\n")

        return {"status": "success", 
                "message": "Lệnh phun thuốc đã được ghi nhận và trích xuất.",
                "iot_payload": iot_command_payload
            }

    def execute_fertilizing(self, farmer_id: str, plan_context: dict):
        """Thực thi lệnh bón phân và in log, sử dụng payload JSON trích xuất."""
        
        iot_command_payload = self._extract_iot_payload(plan_context, 'fertilizer')
        
        if iot_command_payload.get("status") == "error":
            return {"status": "error", "message": f"Không thể trích xuất lệnh bón phân: {iot_command_payload['message']}"}

        iot_command_payload["farmer_id"] = farmer_id 

        logger.info("\n" + "="*50)
        logger.info(f"ĐÃ NHẬN LỆNH [BÓN PHÂN] CHO NÔNG HỘ ID: {farmer_id}")
        logger.info("="*50)
        
        logger.info("\n---- THÔNG TIN THỰC THI (LLM PAYLOAD) ----")
        logger.info(f" - Thời gian thực hiện: **{iot_command_payload.get('execution_time', 'N/A')}**")
        logger.info(f" - Tóm tắt lệnh: {iot_command_payload.get('summary', 'N/A')}")
        logger.info(f" - Lưu ý cảnh báo (Caution): {iot_command_payload.get('caution', 'N/A')}")
        
        stage = iot_command_payload.get('execution_stage', {})
        logger.info(f"\n---- CHI TIẾT GIAI ĐOẠN BÓN ----")
        logger.info(f" - Thời điểm (Timing): **{stage.get('timing', 'N/A')}**") 
        
        for i, fertilizer in enumerate(stage.get('fertilizers_to_apply', [])):
            logger.info(f" --- Phân bón {i+1} ---") 
            logger.info(f" - Loại phân: **{fertilizer.get('type')}**")
            logger.info(f" - Số lượng: {fertilizer.get('quantity_kg')} kg")
            logger.info(f" - Hướng dẫn: {fertilizer.get('instructions')}")
            
        logger.info("\n" + "="*50)
        logger.info(f"HOÀN TẤT GHI NHẬN LỆNH BÓN PHÂN ID: {farmer_id}")
        logger.info("="*50 + "\n")

        return {
            "status": "success", 
            "message": "Lệnh bón phân đã được ghi nhận và trích xuất.",
            "iot_payload": iot_command_payload
        }

    def execute_watering(self, farmer_id: str, plan_context: dict):
        """Thực thi lệnh tưới nước và in log, sử dụng payload JSON trích xuất."""
        
        iot_command_payload = self._extract_iot_payload(plan_context, 'water')
        
        if iot_command_payload.get("status") == "error":
            return {"status": "error", "message": f"Không thể trích xuất lệnh quản lý nước: {iot_command_payload['message']}"}
            
        iot_command_payload["farmer_id"] = farmer_id 

        logger.info("\n" + "="*50)
        logger.info(f"ĐÃ NHẬN LỆNH [QUẢN LÝ NƯỚC] CHO NÔNG HỘ ID: {farmer_id}")
        logger.info("="*50)

        logger.info("\n---- CHI TIẾT LỆNH THỰC THI (LLM PAYLOAD) ----")
        logger.info(f" - Thời gian thực hiện: **{iot_command_payload.get('execution_time', 'N/A')}**")
        logger.info(f" - Hành động chính: **{iot_command_payload.get('action', 'N/A')}**")
        logger.info(f" - Mực nước mục tiêu: **{iot_command_payload.get('target_level', 'N/A')}**") 
        logger.info(f" - Lý do hành động: {iot_command_payload.get('reason', 'N/A')}")
        
        next_steps = iot_command_payload.get('next_steps', {})
        logger.info("\n---- KẾ HOẠCH TƯỚI TIÊU 3 NGÀY ----")
        logger.info(f" - Ngày mai: {next_steps.get('tomorrow', 'N/A')}")
        logger.info(f" - Ngày kia: {next_steps.get('day_after_tomorrow', 'N/A')}")
        
        logger.info("\n" + "="*50)
        logger.info(f"HOÀN TẤT GHI NHẬN LỆNH QUẢN LÝ NƯỚC ID: {farmer_id}")
        logger.info("="*50 + "\n")

        return {
            "status": "success", 
            "message": "Lệnh quản lý nước đã được ghi nhận và đang gửi đến hệ thống IoT.",
            "iot_payload": iot_command_payload 
        }
