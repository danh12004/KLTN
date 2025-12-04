import json
from datetime import datetime, timezone
import pandas as pd
from .base_agent import BaseAgent
from src.logging.logger import logger

class TreatmentAgent(BaseAgent):
    def __init__(self, weather_service, user_repo, analysis_repo, vector_store):
        super().__init__(weather_service, user_repo, analysis_repo, vector_store)
        self.disease_map = {
            "bacterial_leaf_blight": "Cháy bìa lá", "blast": "Đạo ôn",
            "brown_spot": "Đốm nâu", "healthy": "Khỏe mạnh"
        }

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
    
    def _compare_critical_plan_sections(self, plan1: dict, plan2: dict) -> bool:
        """
        So sánh các trường quan trọng có tính hành động giữa hai kế hoạch bằng LLM. 
        Trả về True nếu nội dung cốt lõi KHÔNG CÓ sự khác biệt đáng kể.
        """
        if not self.client:
            logger.warning("AI client not ready for comparison. Assuming difference.")
            return False 

        plan1_json = json.dumps(plan1, ensure_ascii=False, indent=2)
        plan2_json = json.dumps(plan2, ensure_ascii=False, indent=2)
        
        prompt = f"""
            **Nhiệm vụ:** Bạn là một công cụ so sánh. Hãy so sánh Kế hoạch A (Kế hoạch cũ) và Kế hoạch B (Kế hoạch mới) dựa trên các tiêu chí cốt lõi có tính hành động.

            **Quy tắc:**
            1. Trả về `true` nếu sự khác biệt **chỉ** nằm ở `main_message`, `analysis`, `prognosis`, hoặc các chi tiết nhỏ (ví dụ: làm tròn số trong liều lượng, thay đổi múi giờ/thời gian phút giây không ảnh hưởng đến ngày phun).
            2. Trả về `false` nếu có sự thay đổi **đáng kể** về: Loại thuốc, Liều lượng, Ngày phun (YYYY-MM-DD), Buổi phun (Sáng/Chiều), Giờ phun (giờ).

            **Kế hoạch A (Cũ):**
            ```json
            {plan1_json}
            ```
            
            **Kế hoạch B (Mới):**
            ```json
            {plan2_json}
            ```
            
            **Yêu cầu đầu ra:** Chỉ trả về đối tượng JSON theo schema.
            ```json
                {{"is_essentially_same": True nếu kế hoạch có sự thay đổi **mạnh** về liều lượng, ngày phun, buổi phun, thời gian (giờ), False nếu kế hoạch không có gì thay đổi đáng kể}}
            ```
            """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, 
                temperature=0.0
            )
            response_content = response.choices[0].message.content
            result = json.loads(response_content)
            logger.info(f"LLM Comparison Result: {result.get('is_essentially_same')}")
            return result.get("is_essentially_same", False)
        except Exception as e:
            logger.error(f"Error calling LLM for plan comparison: {e}. Defaulting to False (significant difference).")
            return False

    def create_treatment_plan(self, disease_name: str, farmer_id: str, image_path_to_save: str = None, iot_data=None):
        if not self.client:
            logger.warning("TreatmentAgent không thể tạo kế hoạch vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        disease_name_vn = self.disease_map.get(disease_name, "Không xác định")
        
        user, farm = self._get_user_and_farm(farmer_id)
        if not farm:
            logger.warning(f"Không tìm thấy nông trại cho người dùng ID {farmer_id} khi tạo kế hoạch điều trị.")
            return {"error": f"Không tìm thấy nông trại cho người dùng ID {farmer_id}."}

        days_since_planting = "không rõ"
        if farm.planting_date:
            try:
                days_since_planting = (datetime.now().date() - farm.planting_date).days
            except TypeError:
                pass

        farmer_info_for_llm = {
            "farmer_id": user.id, "full_name": user.full_name,
            "farm_name": farm.name, "area_ha": farm.area_ha,
            "planting_date": str(farm.planting_date),
            "days_since_planting": days_since_planting, 
            "location": {"province": farm.province}
        }
        
        scenario = "new"
        session_to_update = None 
        executed_plan_json_for_review = None 
        pending_plan_json_for_review = None 
        
        disease_name_vn = self.disease_map.get(disease_name, "Không xác định")

        latest_session = self.analysis_repo.get_latest_session_for_farm_by_type(farm.id, 'treatment')
        if latest_session:
             try:
                 plan_data_str = latest_session.final_plan_json or latest_session.suggested_plan_json
                 if not plan_data_str: raise Exception("Không có JSON plan")
                 plan_detection = latest_session.initial_detection 
                 if disease_name_vn in plan_detection: 
                     if latest_session.status == "Đã xử lý":
                         scenario = "supplementary"
                         executed_plan_json_for_review = latest_session.final_plan_json
                     elif latest_session.status == "Đang xử lý":
                         scenario = "suggest_update"
                         session_to_update = latest_session
                         pending_plan_json_for_review = latest_session.final_plan_json
                     elif latest_session.status in ["Chờ xử lý", "Chờ xác nhận"]:
                         scenario = "new_plan"
                 else:
                     scenario = "new_plan"
             except Exception:
                 scenario = "new"
             
        province = farm.province    
        hourly_forecast = self.weather_service.get_forecast(province)
        if not hourly_forecast:
            return {"error": f"Không thể lấy dữ liệu thời tiết cho tỉnh {province}."}

        df = pd.DataFrame(hourly_forecast)
        df['date'] = pd.to_datetime(df['date'])
        today = pd.to_datetime(datetime.now().date())
        end_date = today + pd.Timedelta(days=2)
        df_3_days = df[(df['date'] >= today) & (df['date'] <= end_date)].copy()
        df_3_days['date_str'] = df_3_days['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        if df_3_days.empty: return {"error": "Không có đủ dữ liệu thời tiết cho 3 ngày tới."}
        daily_groups = df_3_days.groupby(df['date'].dt.date)
        scored_days = [{'date': date_val, 'score': self._score_spraying_day(g.to_dict('records')), 'data': g.to_dict('records')} for date_val, g in daily_groups]
        if not scored_days: return {"error": "Không thể chấm điểm các ngày dự báo."}
        
        best_day = max(scored_days, key=lambda x: x['score'])
        hourly_detail_for_target_date = best_day['data']
        for hour_data in hourly_detail_for_target_date:
            if 'date' in hour_data and not isinstance(hour_data['date'], str):
                hour_data['date'] = hour_data.get('date_str', str(hour_data['date']))
        
        daily_summary = self._summarize_daily_forecast(df_3_days.to_dict('records'))

        if disease_name_vn == "healthy":
            weather_info_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
            hourly_info_json = json.dumps(hourly_detail_for_target_date, ensure_ascii=False, indent=2)
            iot_info_json = json.dumps(iot_data, ensure_ascii=False, indent=2) if iot_data else "{}"
            retrieved_context = f"Cây lúa khỏe mạnh... (Dữ liệu thời tiết và IoT: {weather_info_json}, {hourly_info_json}, {iot_info_json})"
        else:
            query = f"Liều lượng, cách dùng thuốc và kỹ thuật phun cho bệnh {disease_name_vn} giai đoạn {days_since_planting} NSS."
            retrieved_context = self.vector_store.retrieve(disease_name, query, k=6)

        prompt = self._build_treatment_prompt(
            retrieved_context, farmer_info_for_llm, daily_summary, 
            hourly_detail_for_target_date, str(farmer_id), disease_name_vn, 
            iot_data=iot_data,
            pending_plan_json=pending_plan_json_for_review,
            executed_plan_json=executed_plan_json_for_review 
        )
        
        response_content = ""
        try:
             response = self.client.chat.completions.create(
                 model=self.model_name,
                 messages=[{"role": "user", "content": prompt}],
                 response_format={"type": "json_object"},
                 temperature=self.generation_config.get("temperature", 0.6),
                 top_p=self.generation_config.get("top_p", 0.9)
             )
             response_content = response.choices[0].message.content
             plan = json.loads(response_content)
             
             is_action_needed_by_llm = plan.get("is_action_needed", True)
             if not is_action_needed_by_llm and scenario != "new": 
                 if scenario == "suggest_update" and session_to_update:
                     session_to_update.suggested_plan_json = None 
                     self.analysis_repo.commit()
                     original_plan_dict = json.loads(session_to_update.final_plan_json)
                     return { "conversation_id": session_to_update.id, "plan": None, "original_plan": original_plan_dict, "status": session_to_update.status, "message": "No action needed (suggestion)." }
                 else:
                     new_session = self.analysis_repo.create_session(farm_id=farm.id, initial_detection=disease_name_vn, plan_type="treatment", status="Không hành động", image_path=image_path_to_save)
                     self.analysis_repo.update_session_plan(new_session, plan) 
                     self.analysis_repo.commit()
                     return { "conversation_id": new_session.id, "plan": plan, "original_plan": None, "status": new_session.status, "message": "No action needed." }

             if scenario == "suggest_update" and session_to_update:
                 session_to_update.suggested_plan_json = json.dumps(plan)
                 self.analysis_repo.commit()
                 original_plan_dict = json.loads(session_to_update.final_plan_json)
                 return { "conversation_id": session_to_update.id, "plan": plan, "original_plan": original_plan_dict, "status": session_to_update.status, "message": "Đã tạo gợi ý cập nhật." }
             else: 
                 detection_msg = f"Kế hoạch điều trị: {disease_name_vn}"
                 if scenario == "supplementary": detection_msg = f"Kế hoạch phun bổ sung: {disease_name_vn}"
                     
                 new_session = self.analysis_repo.create_session(farm_id=farm.id, initial_detection=detection_msg, plan_type="treatment", status="Chờ xác nhận", image_path=image_path_to_save)
                 self.analysis_repo.update_session_plan(new_session, plan)
                 self.analysis_repo.commit()
                 return { "conversation_id": new_session.id, "plan": plan, "original_plan": None, "status": new_session.status, "message": "Tạo kế hoạch mới thành công." }

        except Exception as e:
            self.analysis_repo.rollback()
            logger.error(f"Lỗi khi tạo/đánh giá kế hoạch điều trị cho {farmer_id}: {e}", exc_info=True)
            logger.error(f"Phản hồi LLM (nếu có): {response_content}")
            return {"error": "Rất tiếc, đã có lỗi khi tạo kế hoạch điều trị."}

    def _build_update_prompt(self, current_plan: dict, user_message: str) -> str:
        current_plan_json = json.dumps(current_plan, ensure_ascii=False, indent=2)

        prompt = f"""
            **BỐI CẢNH & VAI TRÒ:**
            Bạn là một chuyên gia AI về nông học, có nhiệm vụ DUY NHẤT là điều chỉnh kế hoạch điều trị hiện tại (JSON) dựa trên phản hồi cụ thể của nông dân.

            **QUY TẮC RÀNG BUỘC CỐT LÕI (Content Grounding & An toàn):**
            1. **Giới hạn Nội dung:** KHÔNG được thêm thông tin ngoài lề, kiến thức chung, hay nội dung không liên quan đến kế hoạch điều trị này vào bất kỳ trường nào (nhất là `main_message`).
            2. **An toàn Liều lượng:** Khi thay đổi liều lượng thuốc, hãy luôn đảm bảo liều lượng mới **vẫn nằm trong phạm vi an toàn** theo nguyên tắc nông học. Nếu yêu cầu của nông dân vượt quá giới hạn an toàn, hãy đặt liều lượng ở mức tối đa an toàn và giải thích cảnh báo trong `main_message`.
            3. **Xử lý Mơ hồ:** Nếu yêu cầu của nông dân **mơ hồ** hoặc **không thể xác định** thay đổi cụ thể (ví dụ: "tôi không thích thuốc này"), BẮT BUỘC giữ nguyên kế hoạch cũ và giải thích trong `main_message` rằng thông tin chưa rõ ràng.

            **Kế hoạch ban đầu của bạn (Định dạng JSON):**
            ```json
            {current_plan_json}
            ```

            **Phản hồi của Nông dân (Yêu cầu Điều chỉnh):**
            "{user_message}"

            **Yêu cầu Xử lý:**
            1. **Phân tích yêu cầu:** Hiểu rõ nông dân muốn thay đổi gì.
            2. **Đánh giá tính hợp lý:** Xem xét yêu cầu này có hợp lý không (dựa trên Quy tắc Cốt lõi số 2).
            3. **Cập nhật kế hoạch:** Nếu hợp lý, cập nhật lại toàn bộ đối tượng JSON. Nếu không, giữ nguyên và giải thích trong `main_message`. **Lưu ý:** Nếu người dùng thay đổi thuốc hoặc liều lượng, hãy tính toán lại **tổng liều lượng theo diện tích (`area_ha`)** và cập nhật cả `liều_lượng` (trong `drug_info`) và `main_message`.
            4. **Tạo thông điệp mới:** Luôn viết lại `main_message` để phản hồi trực tiếp yêu cầu của nông dân.

            **Lưu ý quan trọng về ngôn ngữ:** Giữ nguyên văn phong tiếng Việt gần gũi, dễ hiểu cho nông dân. Khi đề cập đến thuốc, luôn ưu tiên sử dụng **tên thương mại (sản phẩm tham khảo)**.

            **Định dạng đầu ra:**
            Chỉ trả về đối tượng JSON của kế hoạch đã được cập nhật, giữ nguyên cấu trúc như kế hoạch ban đầu.
        """
        return prompt
    
    def update_plan_from_feedback(self, current_plan: dict, user_message: str):
        """Cập nhật kế hoạch điều trị dựa trên phản hồi của người dùng."""
        if not self.client:
            logger.warning("Không thể cập nhật kế hoạch vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        logger.info(f"Đang xử lý phản hồi từ người dùng: '{user_message}'")
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
            logger.info("Đã cập nhật kế hoạch từ phản hồi của người dùng thành công.")
            return updated_plan
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật kế hoạch từ phản hồi: {e}")
            return {"error": "Rất tiếc, đã có lỗi khi xử lý yêu cầu của bác. Vui lòng thử lại."}
    
    def _build_treatment_prompt(self, retrieved_context: str, farmer_info: dict, daily_summary: list,
                                 hourly_detail: list, farmer_id: str, disease_name: str, 
                                 iot_data: dict = None,
                                 pending_plan_json: str = None, 
                                 executed_plan_json: str = None 
                                 ) -> str:
        """Xây dựng prompt chuyên cho việc điều trị bệnh."""
        current_time_utc = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        summary_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
        detail_json = json.dumps(hourly_detail, ensure_ascii=False, indent=2)

        iot_data_str = ""
        image_url_for_output = ""
        if iot_data:
            iot_json = json.dumps(iot_data, ensure_ascii=False, indent=2)
            iot_data_str = f"""
            6. **DỮ LIỆU CẢM BIẾN IOT & GPS (Thông tin thực tế tại ruộng):**
            ```json
            {iot_json}
            ```
            """
            image_url_for_output = iot_data.get('image_url', '')
        
        previous_plan_str = ""
        analysis_requirement_str = ""
        role_mission = ""
        main_goal = ""

        if pending_plan_json:
            role_mission = "**Nhiệm vụ: ĐÁNH GIÁ VÀ CẬP NHẬT KẾ HOẠCH PHUN THUỐC ĐANG CHỜ**"
            main_goal = f"Đánh giá lại kế hoạch **đang chờ** (Mục 8) cho bệnh **{disease_name}**."
            previous_plan_str = f"8. **KẾ HOẠCH ĐANG CHỜ (CẦN XEM XÉT ĐIỀU CHỈNH):**\n```json\n{pending_plan_json}\n```\n"
            analysis_requirement_str = """
                - **BƯỚC BẮT BUỘC (Đánh giá Kế hoạch đang chờ):** Phân tích kế hoạch đang chờ (Mục 8) so với dữ liệu mới (Thời tiết Mục 5, IoT Mục 6).
                
                - **QUYẾT ĐỊNH CẬP NHẬT (`is_action_needed: true`):** Chỉ tạo kế hoạch mới nếu phát hiện thay đổi ĐÁNG KỂ, bao gồm: thay đổi ngày/giờ phun tối ưu do thời tiết *không còn phù hợp*; thay đổi loại thuốc; hoặc liều lượng chênh lệch >10% so với kế hoạch cũ.
                
                - **QUYẾT ĐỊNH KHÔNG HÀNH ĐỘNG (`is_action_needed: false` - Tối ưu hóa hệ thống):**
                Nếu kế hoạch cũ vẫn tối ưu (không có thay đổi đáng kể nào kể trên) → BẮT BUỘC đặt `"is_action_needed": false` và `main_message` PHẢI là "Kế hoạch cũ vẫn còn tối ưu, không cần cập nhật thêm." **LƯU Ý QUAN TRỌNG: Nếu `is_action_needed: false`, BẮT BUỘC KHÔNG ĐƯỢC ĐIỀN bất kỳ dữ liệu nào vào các trường con của `treatment_plan`, `fertilizer_advice`, và `action_details_for_system` (chỉ điền `farmer_id` cho `action_details_for_system`).**
            """
        elif executed_plan_json:
            role_mission = "**Nhiệm vụ: ĐÁNH GIÁ NHU CẦU PHUN BỔ SUNG**"
            main_goal = f"Đánh giá xem có cần phun **bổ sung** cho bệnh **{disease_name}** không, dựa trên những gì **đã phun** (Mục 8)."
            previous_plan_str = f"8. **KẾ HOẠCH ĐÃ THỰC THI (XEM XÉT BÓN BỔ SUNG):**\n```json\n{executed_plan_json}\n```\n"
            analysis_requirement_str = """
                - **Nếu có kế hoạch cũ (Mục 8):** Phân tích xem liều lượng đã phun có đủ không.
                - **Nếu ĐỦ:** BẮT BUỘC trả về `is_action_needed: false` và `main_message` giải thích "Đã phun đủ cho đợt bệnh này. Bác nên theo dõi thêm..."
                - **Nếu THIẾU (cần phun bổ sung):** Tạo một kế hoạch phun bổ sung (ví dụ: đổi loại thuốc) và đặt `is_action_needed: true`.
            """
        else: 
            role_mission = "**Nhiệm vụ: TẠO KẾ HOẠCH MỚI**"
            main_goal = f"Tạo kế hoạch điều trị/chăm sóc mới cho chẩn đoán **{disease_name}**."
            previous_plan_str = "" 
            analysis_requirement_str = f"""
                - **Xác nhận trạng thái:** Bắt đầu bằng việc **khẳng định rõ ràng tình trạng bệnh hiện tại** (ví dụ: "Lúa đã được chẩn đoán mắc bệnh {disease_name}...") trước khi đi vào mức độ rủi ro.
                - **Diễn đạt tự nhiên & Rủi ro:** Sau đó, chuyển sang nhận định về **nguy cơ bùng phát** (ví dụ: "...và rủi ro bùng phát bệnh này đang ở mức RẤT CAO").
                - **Giải thích nguyên nhân:** Giải thích *tại sao* lại có rủi ro đó bằng cách **lồng ghép các số liệu** (độ ẩm, khả năng mưa...) một cách mượt mà vào câu văn.
                - **Liên hệ thực tế:** Kết nối các phân tích đó với tình trạng thực tế của cây lúa (giai đoạn sinh trưởng `days_since_planting`) để tăng tính thuyết phục.
            """

        prompt = f"""
            **Bối cảnh:**
            Bạn là một trợ lý nông nghiệp AI chuyên gia hàng đầu, có nhiệm vụ cung cấp kế hoạch điều trị lúa chi tiết, chính xác, và phù hợp với điều kiện thời tiết thực tế tại Việt Nam.

            **THỜI GIAN HIỆN TẠI (Để tham chiếu thời gian thực):** {current_time_utc} (ISO 8601 UTC)
            
            {role_mission}

            **MỤC TIÊU ĐẶC BIỆT:**
            {main_goal}

            **Thông tin đầu vào:**
            1. **CHẨN ĐOÁN BAN ĐẦU:** Lúa được xác định là đang bị bệnh **{disease_name}**.
            2. **KIẾN THỨC NỀN (Đã được truy xuất từ cơ sở dữ liệu vector):**
            ```
            {retrieved_context}
            ```
            3. **Thông tin nông hộ (bao gồm farmer_id='{farmer_id}'):** ```json
            {farmer_json}
            ```
            4. **DỰ BÁO thời tiết 3 ngày tới (dùng để tham khảo):**
            ```json
            {summary_json}
            ```
            5. **CHI TIẾT thời tiết theo giờ cho ngày hành động TỐT NHẤT đã được chọn sẵn:**
            ```json
            {detail_json}
            ```
            {iot_data_str}
            {previous_plan_str}

            **Yêu cầu Phân Tích và Lập Kế Hoạch:**
            
            **QUY TẮC VÀNG (BẮT BUỘC TUÂN THỦ):** Mọi phân tích, đặc biệt là `risk_assessment` và `weather_summary`, PHẢI lồng ghép các SỐ LIỆU CỤ THỂ từ Mục 4, 5, 6 để chứng minh cho nhận định của bạn. KHÔNG sử dụng ngôn ngữ chung chung.

            ***VÍ DỤ VỀ CÁCH TRẢ LỜI SAI (Chung chung):*** "Rủi ro cao vì thời tiết thuận lợi cho bệnh nấm. Thời tiết sắp tới rất nóng và có mưa."
            ***VÍ DỤ VỀ CÁCH TRẢ LỜI ĐÚNG (Có số liệu):*** "Lúa đã chẩn đoán mắc bệnh Đốm nâu. Rủi ro bùng phát đang ở mức RẤT CAO vì độ ẩm trung bình trong ngày là 92% (Mục 4), đặc biệt là vào buổi tối và sáng sớm có độ ẩm lên đến 99%. Nhiệt độ duy trì ở mức 28-32°C là điều kiện lý tưởng để bào tử nấm lây lan mạnh mẽ."
            
            Bây giờ, hãy phân tích và tạo ra kế hoạch theo ví dụ ĐÚNG ở trên.

            1. **Đánh giá Rủi ro (`analysis.risk_assessment`):**
                {analysis_requirement_str}

            2. **Phân tích Thời tiết (`analysis.weather_summary`):**
                - **Kể một câu chuyện:** Diễn giải thời tiết 3 ngày tới.
                - **Mặt bất lợi:** Phân tích các yếu tố (ví dụ: độ ẩm, nhiệt độ cao) làm tăng nguy cơ bệnh.
                - **Mặt thuận lợi (Cơ hội hành động):** Chỉ ra các yếu tố (ví dụ: ngày khô, ít gió) tạo điều kiện phun thuốc tốt nhất.

            3. **Thông điệp chính (`treatment_plan.main_message`):**
                - Viết một câu duy nhất, súc tích, là hành động quan trọng nhất. (Ghi rõ nếu là CẬP NHẬT, PHUN BỔ SUNG, hay KHÔNG CẦN HÀNH ĐỘNG/Kế hoạch cũ vẫn tối ưu).

            4. **Xác định Thời điểm Vàng (`treatment_plan.optimal_spray_day`):**
                - Chọn NGÀY và BUỔI (Sáng/Chiều) tốt nhất.
                - Phần `reason` phải giải thích đơn giản, tập trung vào lợi ích: Tại sao phun lúc đó lại hiệu quả nhất? (ví dụ: thuốc bám tốt, không bị rửa trôi,...)

            5. **Kế hoạch Thuốc (`treatment_plan.drug_info`):**
                - `sản_phẩm_tham_khảo`: Đề xuất MỘT loại thuốc phổ biến.
                - `hoạt_chất`: Chỉ rõ hoạt chất chính.
                - `liều_lượng`: **Phải có 2 phần**: (1) Hướng dẫn cách pha cho 1 bình và (2) **Tính toán chính xác tổng lượng** cần dùng cho toàn bộ diện tích (`area_ha`).
                - `cách_dùng`: Hướng dẫn chi tiết các bước phun an toàn, hiệu quả.

            6. **Hành động Bổ sung (`treatment_plan.additional_actions`):**
                - Liệt kê ít nhất 1-2 biện pháp canh tác hỗ trợ.

            7. **Tư vấn Bón phân (`fertilizer_advice`):**
                - `recommendation`: Đề xuất cụ thể loại phân, liều lượng (Ví dụ: "Tăng cường Kali, giảm Đạm").
                - `reason`: Giải thích ngắn gọn vai trò.

            8. **Dự báo Kết quả (`prognosis`):**
                - Đưa ra dự báo có mốc thời gian rõ ràng.
                
            **BẮT BUỘC về Định dạng Thời gian:** Phải gán `date` trong JSON đầu ra là thời điểm **bắt đầu** của khung giờ lý tưởng và CHUYỂN ĐỔI sang định dạng **ISO 8601 UTC** đầy đủ (ví dụ: `'2025-11-05T07:00:00Z'`). Phải có chữ 'Z' ở cuối.

            **Định dạng đầu ra:**
            Hãy trả lời bằng một đối tượng JSON DUY NHẤT có cấu trúc chính xác như sau.
            ```json
            {{
                "is_action_needed": "boolean (True nếu cần phun/cập nhật, False nếu đã đủ/không đổi)",
                "analysis": {{
                    "risk_assessment": "string (Văn phong tự nhiên, giải thích nguyên nhân bằng cách lồng ghép số liệu)",
                    "weather_summary": "string (Đoạn văn liền mạch phân tích 2 khía cạnh bất lợi và thuận lợi, có số liệu)"
                }},
                "treatment_plan": {{
                    "is_actionable": true,
                    "main_message": "string (Một câu tóm tắt hành động chính, rõ ràng và súc tích)",
                    "optimal_spray_day": {{
                        "date": "YYYY-MM-DDTHH:MM:SSZ (BẮT BUỘC. Thời điểm bắt đầu thực thi, múi giờ UTC)",
                        "session": "string (Sáng hoặc Chiều)",
                        "reason": "string (Giải thích đơn giản, tập trung vào lợi ích)"
                    }},
                    "drug_info": {{
                        "sản_phẩm_tham_khảo": "string",
                        "hoạt_chất": "string",
                        "liều_lượng": "string (BẮT BUỘC có cả cách pha và tổng liều lượng)",
                        "cách_dùng": "string (Hướng dẫn chi tiết kỹ thuật phun và an toàn)"
                    }},
                    "additional_actions": ["string (Liệt kê các biện pháp canh tác cụ thể)"]
                }},
                "fertilizer_advice": {{
                    "recommendation": "string (Đề xuất cụ thể)",
                    "reason": "string (Giải thích ngắn gọn)"
                }},
                "prognosis": "string (Dự báo chuyên môn có mốc thời gian rõ ràng)",
                "action_details_for_system": {{
                    "farmer_id": "{farmer_id}",
                    "gps_data": {{  
                        "lat": "float/string",
                        "lon": "float/string"
                    }},
                    "drug_info": {{
                        "sản_phẩm_tham_khảo": "string",
                        "liều_lượng": "string",
                        "cách_dùng": "string"
                    }}
                }},
                "image_url": "{image_url_for_output}"
            }}
            ```
        """
        return prompt
