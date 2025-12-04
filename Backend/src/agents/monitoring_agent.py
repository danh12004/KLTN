import json
import pandas as pd
from datetime import datetime
import os
import io
import requests
from PIL import Image
import imagehash
from src.logging.logger import logger
from .base_agent import BaseAgent 

class EnvironmentalMonitoringAgent(BaseAgent): 
    """
    Agent Điều phối Môi trường (Orchestrator Agent).
    Sử dụng LLM để tổng hợp rủi ro, truy xuất kiến thức và quyết định ưu tiên hành động.
    """
    def __init__(self, weather_service, user_repo, analysis_repo, vector_store, treatment_agent, nutrient_agent, water_agent, image_agent):
        super().__init__(weather_service, user_repo, analysis_repo, vector_store) 
        self.treatment_agent = treatment_agent
        self.nutrient_agent = nutrient_agent
        self.water_agent = water_agent
        self.image_agent = image_agent
        self.disease_map = {
            "bacterial_leaf_blight": "Cháy bìa lá", "blast": "Đạo ôn",
            "brown_spot": "Đốm nâu", "healthy": "Khỏe mạnh"
        }
        # self.mock_api_url = "https://68a96612b115e67576eb0cec.mockapi.io/image"

    def _normalize_weather_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Chuẩn hóa các cột cần thiết (temp, pop) về dạng số."""
        if 'temperature' in df.columns:
            df['temperature'] = pd.to_numeric(df['temperature'].astype(str).str.replace('°C', '').str.strip(), errors='coerce')

        if 'rain_chance' in df.columns:
            df['rain_chance'] = pd.to_numeric(df['rain_chance'].astype(str).str.replace('%', '').str.strip(), errors='coerce')
        
        return df.dropna(subset=['temperature', 'rain_chance'])

    def _get_contextual_data(self, farm, iot_data=None):
        """Thu thập và tổng hợp DỮ LIỆU CƠ BẢN (Thời tiết, Giai đoạn, IoT)."""
        days_after_planting = int((datetime.now().date() - farm.planting_date).days) if farm.planting_date else -1
        
        hourly_forecast = self.weather_service.get_forecast(farm.province)
        daily_summary = self._summarize_daily_forecast(hourly_forecast)
        
        risk_of_heavy_rain = False
        soil_moisture = iot_data.get('soil_moisture', 50) if iot_data else 50
        
        if hourly_forecast:
            df = pd.DataFrame(hourly_forecast)
            df = self._normalize_weather_df(df.copy()) 
            
            df_72h = df.head(72).copy() 
            
            if not df_72h.empty:
                avg_rain_chance = df_72h['rain_chance'].mean()
                if avg_rain_chance > 50 or (df_72h['rain_chance'] > 80).any(): 
                    risk_of_heavy_rain = True
            
        return {
            'days_after_planting': days_after_planting,
            'soil_moisture_percent': soil_moisture,
            'risk_of_heavy_rain': risk_of_heavy_rain,
            'daily_weather_summary': daily_summary,
            'raw_iot_data': iot_data,
            'province': farm.province,
            'area_ha': farm.area_ha,
            'rice_variety': getattr(farm, 'rice_variety', 'chưa rõ')
        }
        
    def _dynamic_retrieval(self, detected_disease: str, context_data: dict) -> str:
        """Thực hiện truy xuất kiến thức Cấp 1 (Sơ bộ) cho LLM Orchestrator."""
        all_context = []
        days = context_data['days_after_planting']
        
        if detected_disease and detected_disease != 'healthy':
            query = f"Nguyên tắc ưu tiên điều trị bệnh {detected_disease} cho lúa giai đoạn {days} NSS"
            disease_context = self.vector_store.retrieve(detected_disease, query, k=5) 
            all_context.append(f"--- BỆNH/SÂU HẠI ({detected_disease.upper()}) ---\n{disease_context}")
        
        weather_text = context_data.get('daily_weather_summary')[0].get('weather_text') if context_data.get('daily_weather_summary') else "chung"
        query = f"Nguyên tắc bón phân và tưới nước cho lúa {days} ngày tuổi trong điều kiện thời tiết {weather_text}"
        
        general_context = self.vector_store.retrieve('general_qa', query, k=5)
        all_context.append(f"--- QUẢN LÝ CHUNG ---\n{general_context}")

        return "\n\n".join(all_context)
    
    def _build_orchestration_prompt(self, farmer_id: str, detected_disease: str, context_data: dict, retrieved_context: str) -> str:
        """Xây dựng prompt chuyên sâu cho việc điều phối."""
        
        context_json = json.dumps(context_data, ensure_ascii=False, indent=2)

        prompt = f"""
            **Bối cảnh:** Bạn là Trưởng Agent Điều phối cho hệ thống nông nghiệp thông minh.
            
            **MỤC TIÊU:** Phân tích tất cả dữ liệu dưới đây để quyết định **CHUỖI HÀNH ĐỘNG TỐI ƯU** cho nông hộ {farmer_id} trong 3 ngày tới, đảm bảo ưu tiên xử lý rủi ro cao nhất (Bệnh > Nước > Dinh Dưỡng).

            **DỮ LIỆU ĐẦU VÀO:**
            1. **PHÂN TÍCH ẢNH (Bệnh):** {detected_disease}
            2. **DỮ LIỆU BỐI CẢNH (IoT, Thời tiết, Giai đoạn):**
            ```json
            {context_json}
            ```
            3. **KIẾN THỨC NỀN (Truy xuất từ Vector Store):**
            ```
            {retrieved_context}
            ```

            **QUY TẮC QUYẾT ĐỊNH (PHẢI LÀM):**
            A. **Ưu tiên 1 (Bệnh):** Nếu {detected_disease} khác 'healthy', BẮT BUỘC có `treatment_agent` trong chuỗi hành động.
            B. **Ưu tiên 2 (Nước/Thời tiết):**
               - Nếu `risk_of_heavy_rain` là true HOẶC `soil_moisture_percent` < 30, BẮT BUỘC `water_agent` phải có `priority` 1 hoặc 2.
               - Trong trường hợp Mưa Lớn, phải ưu tiên WaterAgent (Tháo nước/Chuẩn bị) hơn NutrientAgent.
            C. **Ưu tiên 3 (Dinh dưỡng):** Chỉ kích hoạt `nutrient_agent` khi điều kiện thời tiết ổn định và không có rủi ro nước hoặc bệnh nghiêm trọng.
            
            **YÊU CẦU ĐẦU RA (JSON BẮT BUỘC):**
            - `reasoning` PHẢI lồng ghép các số liệu cụ thể (ví dụ: "Độ ẩm đất là 75%, nhưng dự báo có mưa lớn, nên ưu tiên WaterAgent để tháo nước trước khi bón phân").
            - `action_sequence` phải SẮP XẾP theo thứ tự ưu tiên tăng dần (1 là cao nhất).
            
            ```json
            {{
                "orchestration_decision": "true/false",
                "main_focus": "string (TREATMENT/WATER/NUTRIENT/MONITORING)",
                "reasoning": "string (Giải thích ưu tiên dựa trên số liệu)",
                "action_sequence": [
                    {{
                        "agent": "water_agent",
                        "priority": 1,
                        "purpose": "Tháo nước khẩn cấp do mưa lớn"
                    }},
                    // ... các hành động tiếp theo
                ]
            }}
            ```
        """
        return prompt
    
    def _execute_llm_decision(self, farmer_id: str, decision: dict, iot_data: dict, analysis_result: dict, context_data):
        """Thực thi chuỗi hành động do LLM quyết định."""
        execution_log = []

        if not decision.get("orchestration_decision"):
            log_msg = f"LLM quyết định không cần hành động ưu tiên. Lý do: {decision.get('reasoning')}"
            logger.info(f"[ORCHESTRATOR] {log_msg}")
            return [log_msg]

        actions = sorted(decision.get('action_sequence', []), key=lambda x: x.get('priority', 99))

        for action in actions:
            agent_name = action.get('agent')
            purpose = action.get('purpose', 'Không xác định')
            
            try:
                if agent_name == 'treatment_agent':
                    disease_name = analysis_result.get("detected_disease_name", "healthy")
                    image_path_to_save = analysis_result.get("image_path_to_save")
                    
                    self.treatment_agent.create_treatment_plan(
                        disease_name, 
                        farmer_id, 
                        image_path_to_save, 
                        iot_data
                    )
                    
                    log_msg = f"TreatmentAgent đã hoàn thành (Mục đích: {purpose})"
                    
                elif agent_name == 'water_agent':
                    self.water_agent.create_water_management_plan(
                        farmer_id, 
                        iot_data=iot_data, 
                        context_data_from_ema=context_data
                    )
                    log_msg = f"WaterAgent được kích hoạt ({purpose})."

                elif agent_name == 'nutrient_agent':
                    self.nutrient_agent.create_fertilization_plan(
                        farmer_id, 
                        iot_data=iot_data,
                        context_data_from_ema=context_data
                    )
                    log_msg = f"NutrientAgent được kích hoạt ({purpose})."
                
                else:
                    log_msg = f"Agent không xác định: {agent_name}."

                logger.info(f"[ORCHESTRATOR EXEC] Thành công: {log_msg}")
                execution_log.append(log_msg)

            except Exception as e:
                err_msg = f"Lỗi khi kích hoạt {agent_name} ({purpose}): {e}"
                logger.error(f"[ORCHESTRATOR EXEC] {err_msg}")
                execution_log.append(err_msg)
                
        return execution_log
        
    def check_risk_for_farmer(self, user, iot_data=None):
        """
        [ORCHESTRATOR] Chức năng điều phối chính.
        """
        farm = user.farms.first()
        if not farm:
            logger.warning(f"Bỏ qua User ID {user.id} vì chưa có thông tin nông trại.")
            return {"status": "skipped", "reason": "No farm info"}

        farmer_id = user.id
        logger.info(f"[ORCHESTRATOR] Bắt đầu đánh giá ưu tiên rủi ro cho nông hộ {farmer_id}...")

        if not isinstance(iot_data, dict) or 'image_url' not in iot_data:
            logger.error("Dữ liệu IoT không hợp lệ hoặc thiếu 'image_url'")
            return {"error": "Thiếu đường dẫn ảnh giám sát trong dữ liệu IoT."}
        
        image_url = iot_data['image_url']
        
        analysis_data = self.image_agent.detect_image(farmer_id, image_url) 
        
        if "error" in analysis_data:
             logger.error(f"[ORCHESTRATOR] Lỗi trong phân tích ảnh. Dừng điều phối.")
             return analysis_data
             
        detected_disease = analysis_data.get('detected_disease_name', 'healthy')
        disease_name_vn = self.disease_map.get(detected_disease, "Không xác định")
        
        context_data = self._get_contextual_data(farm, iot_data)
        
        retrieved_context = self._dynamic_retrieval(detected_disease, context_data)
        
        try:
            prompt = self._build_orchestration_prompt(farmer_id, disease_name_vn, context_data, retrieved_context)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, 
                temperature=0.1
            )
            decision_json = json.loads(response.choices[0].message.content)
            
            execution_log = self._execute_llm_decision(farmer_id, decision_json, iot_data, analysis_data, context_data)
            
            return {
                "decision": decision_json,
                "execution_log": execution_log,
                "status": "orchestration_complete"
            }

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Lỗi trong quá trình ra quyết định/thực thi bằng LLM: {e}", exc_info=True)
            return {"error": "Lỗi hệ thống khi ra quyết định điều phối."}
        
    
    def run_single_automated_analysis(self, farmer_id: str, iot_data=None, is_scheduled: bool = False):
        """
        Thực hiện một quy trình phân tích tự động hoàn chỉnh, bao gồm kiểm tra trùng lặp ảnh.
        """
        log_prefix = "[GIÁM SÁT ĐỊNH KỲ]" if is_scheduled else "[PHÂN TÍCH THỦ CÔNG]"
        logger.info(f"{log_prefix} Bắt đầu phân tích cho nông hộ {farmer_id}.")
        
        if not isinstance(iot_data, dict) or 'image_url' not in iot_data:
            logger.error(f"{log_prefix} Dữ liệu IoT không hợp lệ hoặc thiếu 'image_url'. Dừng lại.")
            return {"error": "Thiếu đường dẫn ảnh giám sát trong dữ liệu IoT."}

        image_url = iot_data['image_url'] 
        
        try:
            logger.info(f"{log_prefix} Đang tải ảnh từ URL: {image_url}")
            
            # --- Đoạn code cũ (dùng Mock API) được giữ nguyên comment ---
            # logger.info(f"{log_prefix} Đang lấy link ảnh từ API giám sát...")
            # # Use mockapi
            # # api_response = requests.get(self.mock_api_url)
            # # api_response.raise_for_status()
            # # image_url = api_response.json()[0]['image']
            
            # # Lỗi cú pháp đã bị xóa/sửa
            # # image_url = iot_data.image_url 
            # # logger.info(f"{log_prefix} Lấy được link ảnh: {image_url}")
            # -----------------------------------------------------------

            # 2. Tải ảnh trực tiếp từ URL Firebase Storage
            with requests.get(image_url, stream=True) as r:
                r.raise_for_status()
                image_bytes = r.content
            logger.info(f"{log_prefix} Đã tải ảnh thành công vào bộ nhớ.")

            detection_result = self.image_agent.analyze_image(image_bytes)

            if isinstance(detection_result, dict) and "error" in detection_result:
                logger.error(f"{log_prefix} Lỗi từ agent nhận diện ảnh: {detection_result['error']}. Dừng lại.")
                return {"error": "Không thể phân tích được hình ảnh."}

            if not isinstance(detection_result, str):
                error_detail = f"Dữ liệu nhận được: {str(detection_result)[:500]}..."
                logger.error(f"{log_prefix} Lỗi: Agent nhận diện ảnh trả về định dạng không hợp lệ. {error_detail}")
                return {"error": "Lỗi hệ thống: Agent nhận diện ảnh trả về định dạng không mong muốn."}
            
            detected_disease_name = detection_result
            logger.info(f"{log_prefix} Kết quả nhận diện: '{detected_disease_name}'.")
            
            image_path_to_save = None
            is_duplicate = False
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                img_hash = imagehash.phash(pil_image)
                image_extension = ".jpg"
                unique_filename = f"{img_hash}{image_extension}"

                class_folder = os.path.join(r"D:\finalproject\KLTN\Backend\data\storage", detected_disease_name)
                os.makedirs(class_folder, exist_ok=True)
                image_path_to_save = os.path.join(class_folder, unique_filename)

                if os.path.exists(image_path_to_save):
                    logger.info(f"{log_prefix} Ảnh trùng lặp đã được phát hiện (hash: {img_hash}). Bỏ qua việc lưu ảnh mới.")
                    is_duplicate = True
                else:
                    pil_image.save(image_path_to_save)
                    logger.info(f"{log_prefix} Đã lưu ảnh mới tại: {image_path_to_save}")

            except Exception as e:
                logger.error(f"{log_prefix} Lỗi trong quá trình hashing hoặc lưu ảnh: {e}")
                return {"error": "Lỗi khi xử lý file ảnh."}

            if detected_disease_name == 'healthy':
                logger.info(f"{log_prefix} Cây trồng được xác định là khỏe mạnh. Vẫn tạo kế hoạch điều trị (loại healthy).")
                
                plan_result = self.treatment_agent.create_treatment_plan(
                    detected_disease_name,
                    farmer_id,
                    image_path_to_save=image_path_to_save,
                    iot_data=iot_data
                )
                
                if is_scheduled:
                    if "error" in plan_result:
                        logger.error(f"{log_prefix} Lỗi khi tạo kế hoạch cho {farmer_id}: {plan_result['error']}")
                    else:
                        logger.info(f"{log_prefix} Đã tạo và lưu kế hoạch (healthy) cho {farmer_id} thành công.")
                    return

                if isinstance(plan_result, dict):
                    plan_result['is_duplicate'] = is_duplicate
                    plan_result['note'] = "Cây khỏe – không cần điều trị nhưng kế hoạch vẫn được tạo."
                
                return plan_result

            logger.info(f"{log_prefix} Chuyển thông tin cho TreatmentAgent để tạo kế hoạch...")
            plan_result = self.treatment_agent.create_treatment_plan(
                detected_disease_name, 
                farmer_id,
                image_path_to_save=image_path_to_save,
                iot_data=iot_data
            )
            
            if is_scheduled:
                if "error" in plan_result:
                    logger.error(f"{log_prefix} Lỗi khi tạo kế hoạch cho {farmer_id}: {plan_result['error']}")
                else:
                    logger.info(f"{log_prefix} Đã tạo và lưu kế hoạch mới cho {farmer_id} thành công.")
                return
            
            if isinstance(plan_result, dict):
                plan_result['is_duplicate'] = is_duplicate
            
            return plan_result

        except requests.exceptions.RequestException as e:
            logger.error(f"{log_prefix} Lỗi khi tải ảnh từ URL: {image_url}. Chi tiết: {e}")
            return {"error": "Không thể tải được ảnh từ đường dẫn đã cung cấp."}
        except Exception:
            logger.exception(f"Lỗi không xác định trong quá trình phân tích cho nông hộ {farmer_id}.")
            return {"error": "Lỗi không xác định trong quá trình phân tích."}