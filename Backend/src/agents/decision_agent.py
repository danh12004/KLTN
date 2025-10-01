import json
import pandas as pd
from datetime import datetime
from openai import OpenAI

from src.entity.models import User, Farm, AnalysisSession, db
from src.services.weather_service import WeatherService
from src.repository.user_repository import UserRepository
from src.repository.analysis_repository import AnalysisRepository
from src.utils.config import CONFIG
from src.services.vector_store_service import VectorStoreService

class DecisionAgent:
    def __init__(self, weather_service: WeatherService, user_repo: UserRepository,
                 analysis_repo: AnalysisRepository, vector_store: VectorStoreService):
        try:
            with open(CONFIG.KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
        except Exception as e:
            print(f"[LỖI] DecisionAgent không thể tải knowledge base: {e}")
            self.knowledge_base = {}

        if not vector_store:
            raise ValueError("DecisionAgent yêu cầu phải có VectorStoreService.")
        self.vector_store = vector_store

        if not weather_service:
            raise ValueError("DecisionAgent yêu cầu phải có WeatherService.")
        self.weather_service = weather_service

        if not user_repo or not analysis_repo:
            raise ValueError("DecisionAgent yêu cầu phải có UserRepository và AnalysisRepository.")
        self.user_repo = user_repo
        self.analysis_repo = analysis_repo

        self.disease_map = {
            "bacterial_leaf_blight": "Cháy bìa lá", "blast": "Đạo ôn",
            "brown_spot": "Đốm nâu", "healthy": "Khỏe mạnh"
        }
        
        self.api_key = CONFIG.OPENAI_API_KEY
        self.model_name = CONFIG.OPENAI_MODEL_NAME
        self.generation_config = CONFIG.OPENAI_GENERATION_CONFIG

        if not self.api_key:
            print("[CẢNH BÁO] Không tìm thấy OPENAI_API_KEY.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                print(f"DecisionAgent đã khởi tạo OpenAI client với model '{self.model_name}' thành công!")
            except Exception as e:
                print(f"[LỖI OpenAI] {e}")
                self.client = None

    def _score_spraying_day(self, daily_hourly_data: list) -> float:
        """Chấm điểm một ngày dựa trên mức độ phù hợp cho việc phun thuốc."""
        if not daily_hourly_data: return 0
        score = 100.0
        dry_hours_streak, max_dry_hours_streak = 0, 0
        for hour in daily_hourly_data:
            if hour.get('rain_chance', 100) > 30:
                score -= 10
                dry_hours_streak = 0
            else:
                dry_hours_streak += 1
            if hour.get('wind_kmh', 99) > 15:
                score -= 2
            max_dry_hours_streak = max(max_dry_hours_streak, dry_hours_streak)
        score += max_dry_hours_streak * 5
        return score
    
    def _summarize_daily_forecast(self, hourly_data: list):
        if not hourly_data: return []
        df = pd.DataFrame(hourly_data)
        df['date'] = pd.to_datetime(df['date'])
        
        daily_summary = df.groupby(df['date'].dt.date).agg(
            min_temp=('temperature', 'min'),
            max_temp=('temperature', 'max'),
            avg_humidity=('humidity', lambda h: round(h.mean())),
            max_rain_chance=('rain_chance', 'max'),
            max_wind_kmh=('wind_kmh', 'max')
        ).reset_index()
        daily_summary['date'] = daily_summary['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        
        return daily_summary.to_dict('records')

    def _build_llm_prompt(self, retrieved_context: str, farmer_info: dict, daily_summary: list, 
                         hourly_detail: list, farmer_id: str, disease_name_vn: str, iot_data: dict = None) -> str:
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        summary_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
        detail_json = json.dumps(hourly_detail, ensure_ascii=False, indent=2)

        iot_data_str = ""
        if iot_data:
            iot_json = json.dumps(iot_data, ensure_ascii=False, indent=2)
            iot_data_str = f"""
            6. **DỮ LIỆU CẢM BIẾN IOT HIỆN TẠI (Thời gian thực từ nông trại):**
            ```json
            {iot_json}
            ```
            """

        prompt = f"""
            **Bối cảnh:**
            Bạn là một trợ lý nông nghiệp AI chuyên gia hàng đầu. Nhiệm vụ của bạn là phân tích toàn diện dữ liệu được cung cấp và đưa ra một kế hoạch hành động chi tiết, khoa học và dễ hiểu cho người nông dân.

            **Thông tin đầu vào:**
            1. **CHẨN ĐOÁN BAN ĐẦU:** Lúa được xác định là đang bị bệnh **{disease_name_vn}**. Toàn bộ kế hoạch phải tập trung vào việc xử lý bệnh này.
            2. **KIẾN THỨC NỀN (Đã được truy xuất từ cơ sở dữ liệu vector):**
            ```
            {retrieved_context}
            ```
            3. **Thông tin nông hộ (bao gồm farmer_id='{farmer_id}'):** ```json
            {farmer_json}
            ```
            4. **TÓM TẮT dự báo thời tiết 3 ngày tới (để có cái nhìn tổng quan):**
            ```json
            {summary_json}
            ```
            5. **CHI TIẾT thời tiết theo giờ cho ngày hành động TỐT NHẤT đã được chọn sẵn:**
            ```json
            {detail_json}
            ```
            {iot_data_str}

            **Yêu cầu Phân Tích và Lập Kế Hoạch:**
            Dựa vào TOÀN BỘ thông tin trên, hãy thực hiện các bước sau:
            1.  **Đánh giá Rủi ro & Dự báo Tiến triển:** Phân tích nguy cơ bệnh sẽ tiến triển nặng hơn dựa trên loại bệnh, dự báo thời tiết **VÀ điều kiện môi trường hiện tại từ cảm biến IoT**. **Hãy nêu rõ dự báo nếu không can thiệp, bệnh sẽ như thế nào trong 3 ngày tới (lan rộng, giữ nguyên, hay thuyên giảm).**
            2.  **Xác định Thời điểm Vàng:** Chọn ra NGÀY và BUỔI (Sáng/Chiều) TỐT NHẤT để phun thuốc (điều trị hoặc phòng ngừa).
            3.  **Lập Kế hoạch Hành động Toàn diện:**
                - **Nếu có bệnh:** Đưa ra kế hoạch điều trị.
                - **Nếu không có bệnh nhưng môi trường rủi ro:** Đưa ra kế hoạch **phòng ngừa** và chăm sóc chủ động.
            4.  **Đề xuất Thuốc:** Chọn MỘT loại thuốc phù hợp nhất (điều trị hoặc phòng bệnh).
            5.  **TÍNH TOÁN LIỀU LƯỢNG:** Dựa vào liều lượng tiêu chuẩn và diện tích `area_ha`, tính toán tổng lượng thuốc cần dùng.
            6.  **Dự báo Kết quả (Prognosis):** Nêu rõ kết quả dự kiến **sau khi thực hiện kế hoạch này**, ví dụ: "Nếu phun thuốc đúng lịch, bệnh sẽ được kiểm soát trong vòng 5-7 ngày và lúa sẽ phục hồi, tiếp tục giai đoạn làm đòng."
            7.  **Tư vấn Bón phân:** Dựa trên tình trạng bệnh và thông tin nông hộ, đề xuất loại phân bón và cách bón phù hợp (nếu có thông tin) để giúp cây phục hồi và tăng sức đề kháng. Bỏ qua nếu không có thông tin liên quan.
            
            **Lưu ý quan trọng về ngôn ngữ:** Toàn bộ nội dung trả về phải bằng tiếng Việt, sử dụng ngôn ngữ gần gũi, dễ hiểu cho nông dân. Khi đề cập đến thuốc, luôn ưu tiên sử dụng **tên thương mại (sản phẩm tham khảo)**.

            **Định dạng đầu ra:**
            Hãy trả lời bằng một đối tượng JSON DUY NHẤT có cấu trúc chính xác như sau. **Hãy chắc chắn rằng giá trị của 'farmer_id' trong 'action_details_for_system' khớp với farmer_id được cung cấp trong phần Thông tin nông hộ.**
            ```json
            {{
                "analysis": {{
                    "risk_assessment": "string",
                    "weather_summary": "string"
                }},
                "treatment_plan": {{
                    "is_actionable": true,
                    "main_message": "string",
                    "optimal_spray_day": {{
                        "date": "string (YYYY-MM-DD)",
                        "session": "string (Sáng hoặc Chiều)",
                        "reason": "string"
                    }},
                    "drug_info": {{
                        "sản_phẩm_tham_khảo": "string",
                        "hoạt_chất": "string",
                        "liều_lượng": "string (Đã tính toán theo diện tích)",
                        "cách_dùng": "string"
                    }},
                    "additional_actions": ["string"]
                }},
                "fertilizer_advice": {{
                    "recommendation": "string",
                    "reason": "string"
                }},
                "prognosis": "string",
                "action_details_for_system": {{
                    "farmer_id": "string",
                    "drug_info": {{
                        "sản_phẩm_tham_khảo": "string",
                        "liều_lượng": "string",
                        "cách_dùng": "string"
                    }}
                }}
            }}
            ```
        """
        return prompt

    def create_treatment_plan(self, model_disease_name: str, farmer_id: str, image_path_to_save: str = None, iot_data=None):
        if not self.client:
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        disease_name_vn = self.disease_map.get(model_disease_name, "Khỏe mạnh")
        
        user = self.user_repo.get_user_with_farm(farmer_id)
        if not user or not user.farms.first():
            return {"error": f"Không tìm thấy nông trại cho người dùng với ID {farmer_id}."}
        farm = user.farms.first()

        farmer_info_for_llm = {
            "farmer_id": user.id, "full_name": user.full_name,
            "farm_name": farm.name, "area_ha": farm.area_ha,
            "planting_date": str(farm.planting_date),
            "location": {"province": farm.province}
        }
        query_for_retrieval = f"""
            Các biện pháp tổng hợp để quản lý bệnh {disease_name_vn} trên cây lúa, 
            bao gồm cả biện pháp hóa học, sinh học, canh tác và chế độ dinh dưỡng, 
            bón phân phù hợp để cây tăng sức đề kháng và phục hồi sau bệnh.
        """
        retrieved_context = self.vector_store.retrieve(query_for_retrieval, k=7)
        
        province = farm.province
        hourly_forecast = self.weather_service.get_forecast(province)
        if not hourly_forecast:
            return {"error": f"Không thể lấy dữ liệu thời tiết cho tỉnh {province}."}

        df = pd.DataFrame(hourly_forecast)
        df['date'] = pd.to_datetime(df['date'])
        
        today = pd.to_datetime(datetime.now().date())
        end_date = today + pd.Timedelta(days=2)
        df_3_days = df[(df['date'] >= today) & (df['date'] <= end_date)]

        if df_3_days.empty:
            return {"error": "Không có đủ dữ liệu thời tiết cho 3 ngày tới."}

        daily_groups = df_3_days.groupby(df_3_days['date'].dt.date)
        scored_days = []
        for date_val, group in daily_groups:
            score = self._score_spraying_day(group.to_dict('records'))
            scored_days.append({'date': date_val, 'score': score, 'data': group.to_dict('records')})
        
        if not scored_days:
            return {"error": "Không thể chấm điểm các ngày dự báo."}
        
        best_day = max(scored_days, key=lambda x: x['score'])
        hourly_detail_for_target_date = best_day['data']
        print(f"[AGENT RA QUYẾT ĐỊNH] Ngày tốt nhất để hành động được chọn là: {best_day['date'].strftime('%Y-%m-%d')}")

        for hour_data in hourly_detail_for_target_date:
            if 'date' in hour_data and not isinstance(hour_data['date'], str):
                if hasattr(hour_data['date'], 'strftime'):
                    hour_data['date'] = hour_data['date'].strftime('%Y-%m-%d %H:%M:%S')
        
        daily_summary = self._summarize_daily_forecast(df_3_days.to_dict('records'))
        
        prompt = self._build_llm_prompt(
            retrieved_context,
            farmer_info_for_llm,
            daily_summary, 
            hourly_detail_for_target_date,
            str(farmer_id),
            disease_name_vn,
            iot_data=iot_data
        )
        
        new_session = self.analysis_repo.create_session(
            farm_id=farm.id,
            initial_detection=disease_name_vn,
            image_path=image_path_to_save
        )
        
        response_content = ""
        try:
            print(f"[AGENT RA QUYẾT ĐỊNH] Đang phân tích kế hoạch cho nông hộ {farmer_id}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.6),
                top_p=self.generation_config.get("top_p", 0.9)
            )
            response_content = response.choices[0].message.content
            plan = json.loads(response_content)
            
            self.analysis_repo.update_session_plan(new_session, plan)
            self.analysis_repo.commit()
            
            print(f"[AGENT RA QUYẾT ĐỊNH] Đã nhận và LƯU thành công kế hoạch cho session {new_session.id}.")
            
            return {"session_id": new_session.id, "plan": plan}
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AGENT RA QUYẾT ĐỊNH] Lỗi khi phân tích JSON từ LLM: {e}")
            print(f"Phản hồi nhận được từ LLM: {response_content}")
            return {"error": "Trợ lý AI đã phản hồi không hợp lệ. Vui lòng thử lại."}
        except Exception as e:
            self.analysis_repo.rollback()
            print(f"[AGENT RA QUYẾT ĐỊNH] Lỗi khi gọi API hoặc logic khác: {e}")
            return {"error": "Rất tiếc, đã có lỗi kết nối đến trợ lý AI. Vui lòng thử lại sau."}

    def _build_update_prompt(self, current_plan: dict, user_message: str) -> str:
        current_plan_json = json.dumps(current_plan, ensure_ascii=False, indent=2)
        
        prompt = f"""
            **Bối cảnh:**
            Bạn là một trợ lý nông nghiệp AI. Bạn đã đưa ra một kế hoạch điều trị ban đầu. Bây giờ, người nông dân có một yêu cầu thay đổi.

            **Kế hoạch ban đầu của bạn:**
            ```json
            {current_plan_json}
            ```

            **Phản hồi của nông dân:**
            "{user_message}"

            **Yêu cầu:**
            1.  **Phân tích yêu cầu:** Hiểu rõ nông dân muốn thay đổi gì.
            2.  **Đánh giá tính hợp lý:** Xem xét yêu cầu này có hợp lý không.
            3.  **Cập nhật kế hoạch:** Nếu hợp lý, cập nhật lại toàn bộ đối tượng JSON. Nếu không, giữ nguyên và giải thích trong `main_message`. **Lưu ý:** Nếu người dùng thay đổi thuốc hoặc liều lượng, hãy tính toán lại tổng liều lượng theo diện tích.
            4.  **Tạo thông điệp mới:** Luôn viết lại `main_message` để phản hồi trực tiếp yêu cầu của nông dân.

            **Lưu ý quan trọng về ngôn ngữ:** Giữ nguyên văn phong tiếng Việt gần gũi, dễ hiểu cho nông dân. Khi đề cập đến thuốc, luôn ưu tiên sử dụng **tên thương mại (sản phẩm tham khảo)**.

            **Định dạng đầu ra:**
            Chỉ trả về đối tượng JSON của kế hoạch đã được cập nhật, giữ nguyên cấu trúc như kế hoạch ban đầu.
        """
        return prompt

    def update_plan_from_feedback(self, current_plan: dict, user_message: str):
        if not self.client:
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        print(f"[AGENT RA QUYẾT ĐỊNH] Đang xử lý phản hồi: '{user_message}'")
        prompt = self._build_update_prompt(current_plan, user_message)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.6),
                top_p=self.generation_config.get("top_p", 0.9)
            )
            response_content = response.choices[0].message.content
            updated_plan = json.loads(response_content)
            print("[AGENT RA QUYẾT ĐỊNH] Đã cập nhật kế hoạch thành công.")
            return updated_plan
        except Exception as e:
            print(f"[AGENT RA QUYẾT ĐỊNH] Lỗi khi cập nhật kế hoạch: {e}")
            return {"error": "Rất tiếc, đã có lỗi khi xử lý yêu cầu của bác. Vui lòng thử lại."}

    
    
