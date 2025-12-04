import json
import pandas as pd
from datetime import datetime, timezone
from .base_agent import BaseAgent
from src.logging.logger import logger

class NutrientAgent(BaseAgent):
    """
    Agent chuyên trách việc lập kế hoạch bón phân CHI TIẾT cho GIAI ĐOẠN HIỆN TẠI của cây lúa.
    Cần tích hợp phân tích thời tiết và IoT để đưa ra khuyến nghị thực tế.
    """
    def _determine_current_fertilizer_stage(self, days_after_planting: int) -> str:
        if days_after_planting < 0:
            return "Bón Lót/Chưa sạ"
        elif days_after_planting <= 10:
            return "Bón Thúc 1 - Phục hồi và Đẻ nhánh sớm"
        
        elif days_after_planting <= 25:
            return "Bón Thúc 1 - Đẻ Nhánh Rộ/Dưỡng lá"
        
        elif days_after_planting <= 34:
            return "Giai đoạn Đệm - Dưỡng lá và Kiểm soát chồi vô hiệu"
        
        elif days_after_planting <= 45:
            return "Bón Thúc 2 - Làm Đòng/Đón Đòng"
        
        elif days_after_planting <= 59:
            return "Giai đoạn Trổ Bông/Trổ Xong (Không bón chính)"

        elif days_after_planting <= 80:
            return "Bón Nuôi Hạt (Nếu cần bón lá để tăng hạt chắc)"
        
        else:
            return "Giai đoạn Chờ Thu hoạch (Quá ngày 80 NSS)"
    
    def _score_fertilizing_day(self, daily_hourly_data: list) -> float:
        """
        Chấm điểm một ngày dựa trên mức độ phù hợp cho việc bón phân.
        Tiêu chí: Ưu tiên khô ráo (ít mưa), ít gió (dưới 15km/h).
        """
        if not daily_hourly_data: return 0
        score = 100.0
        
        for hour in daily_hourly_data:
            if hour.get('rain_chance', 0) > 30:
                score -= 15
            if hour.get('wind_kmh', 99) > 15:
                score -= 5 
            
            if 20 <= hour.get('temp_c', 25) <= 35 and hour.get('rain_chance', 100) < 5:
                score += 1 
                
        temps = [h.get('temp_c', 25) for h in daily_hourly_data]
        if max(temps) > 40 or min(temps) < 15:
             score -= 10 
             
        return max(0, score)
    
    def create_fertilization_plan(self, farmer_id: str, iot_data=None, context_data_from_ema: dict = None): 
        if not self.client:
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        user, farm = self._get_user_and_farm(farmer_id)
        if not farm:
            return {"error": f"Không tìm thấy nông trại cho người dùng ID {farmer_id}."}
        
        hourly_forecast = None
        
        if context_data_from_ema:
            logger.info("[Nutrient] Sử dụng Context Data từ Orchestrator (EMA).")
            days_after_planting = context_data_from_ema.get('days_after_planting', -1)
            
            province = farm.province
            hourly_forecast = self.weather_service.get_forecast(province) 
            
            daily_summary = context_data_from_ema.get('daily_weather_summary', 
                                                    self._summarize_daily_forecast(hourly_forecast))
        else:
            logger.warning("[Nutrient] Thiếu Context Data từ EMA. Đang tự tính toán lại Context/Weather.")
            days_after_planting = (datetime.now().date() - farm.planting_date).days if farm.planting_date else -1
            province = farm.province
            hourly_forecast = self.weather_service.get_forecast(province)
            if not hourly_forecast: 
                return {"error": f"Không thể lấy dữ liệu thời tiết cho tỉnh {province}."}
            df_full = pd.DataFrame(hourly_forecast)
            daily_summary = self._summarize_daily_forecast(df_full.to_dict('records'))
        
        current_stage = self._determine_current_fertilizer_stage(days_after_planting)
        
        farmer_info_for_llm = {
            "farmer_id": user.id, "farm_name": farm.name, "area_ha": farm.area_ha,
            "planting_date": str(farm.planting_date), "days_after_planting": days_after_planting,
            "rice_variety": getattr(farm, 'rice_variety', 'chưa rõ giống'), 
            "soil_type": getattr(farm, 'soil_type', 'chưa rõ loại đất'),
            "current_fertilization_stage": current_stage
        }
        
        scenario = "new"
        session_to_update = None 
        executed_plan_json_for_review = None 
        pending_plan_json_for_review = None 

        latest_session = self.analysis_repo.get_latest_session_for_farm_by_type(farm.id, 'fertilizer')

        if latest_session:
            try:
                plan_data_str = latest_session.final_plan_json or latest_session.suggested_plan_json
                if not plan_data_str:
                    raise Exception("Không có JSON plan nào để đọc")
                
                plan_data = json.loads(latest_session.final_plan_json)
                plan_stage = plan_data.get('stage_name')

                if plan_stage == current_stage:
                    if latest_session.status == "Đã xử lý":
                        scenario = "supplementary"
                        executed_plan_json_for_review = latest_session.final_plan_json
                        logger.info(f"Tìm thấy kế hoạch ĐÃ THỰC THI (ID: {latest_session.id}). Sẽ đánh giá bón bổ sung.")
                    elif latest_session.status == "Đang xử lý":
                        scenario = "suggest_update"
                        session_to_update = latest_session
                        pending_plan_json_for_review = latest_session.final_plan_json
                        logger.info(f"Tìm thấy kế hoạch ĐANG THỰC THI (ID: {latest_session.id}). Sẽ tạo gợi ý cập nhật.")
                    elif latest_session.status in ["Chờ xử lý", "Chờ xác nhận"]:
                        scenario = "new_plan"
                        logger.info(f"Tìm thấy kế hoạch ĐANG CHỜ (ID: {latest_session.id}). Sẽ đánh giá lại và cập nhật.")
                else:
                    scenario = "new_plan"
            except Exception as e:
                logger.warning(f"Lỗi khi đọc JSON của session {latest_session.id}: {e}. Sẽ tạo kế hoạch mới.")
                scenario = "new_plan"
                
        if not hourly_forecast:
            return {"error": "Lỗi hệ thống: Không thể tính toán thời điểm bón phân tối ưu do thiếu dữ liệu thời tiết chi tiết."}

        df = pd.DataFrame(hourly_forecast)
        df['date'] = pd.to_datetime(df['date'])
        today = pd.to_datetime(datetime.now().date())
        end_date = today + pd.Timedelta(days=2)
        df_3_days = df[(df['date'] >= today) & (df['date'] <= end_date)].copy()
        df_3_days['date_str'] = df_3_days['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        if df_3_days.empty:
            return {"error": "Không có đủ dữ liệu thời tiết cho 3 ngày tới."}

        daily_groups = df_3_days.groupby(df['date'].dt.date)
        scored_days = [{'date': date_val, 'score': self._score_fertilizing_day(g.to_dict('records')), 'data': g.to_dict('records')} for date_val, g in daily_groups]
        
        if not scored_days:
            return {"error": "Không thể chấm điểm các ngày dự báo."}
            
        best_day = max(scored_days, key=lambda x: x['score'])
        hourly_detail_for_target_date = best_day['data']
        
        for hour_data in hourly_detail_for_target_date:
            if 'date' in hour_data and not isinstance(hour_data['date'], str):
                hour_data['date'] = hour_data.get('date_str', str(hour_data['date']))
        
        query_for_retrieval = f"Công thức và liều lượng bón phân chi tiết giai đoạn {current_stage} cho lúa {farmer_info_for_llm['rice_variety']}..."
        retrieved_context = self.vector_store.retrieve("fertilizer_management", query_for_retrieval, k=6)

        prompt = self._build_fertilization_prompt(
            retrieved_context, 
            farmer_info_for_llm,
            farmer_id, 
            daily_summary, 
            hourly_detail_for_target_date, 
            iot_data,
            pending_plan_json=pending_plan_json_for_review, 
            executed_plan_json=executed_plan_json_for_review 
        )
        
        try:
            logger.info(f"Đang tạo/đánh giá kế hoạch bón phân giai đoạn {current_stage} cho {farmer_id}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, 
                temperature=self.generation_config.get("temperature", 0.2) 
            )
            plan = json.loads(response.choices[0].message.content)
            logger.info(f"Đã tạo/đánh giá thành công kế hoạch bón phân cho {farmer_id}.")
            
            is_action_needed_by_llm = plan.get("is_action_needed", True)
            
            if not is_action_needed_by_llm:
                logger.info(f"LLM quyết định không cần hành động. Lý do: {plan.get('main_message')}")
                
                if scenario == "suggest_update" and session_to_update:
                    logger.info(f"Plan (ID: {session_to_update.id}) đang chờ xử lý vẫn ổn. Gỡ bỏ gợi ý.")
                    session_to_update.suggested_plan_json = None 
                    self.analysis_repo.commit()
                    original_plan_dict = None
                    try: original_plan_dict = json.loads(session_to_update.final_plan_json) 
                    except Exception: pass
                    
                    return { "session_id": session_to_update.id, "plan": None, "original_plan": original_plan_dict, "status": session_to_update.status, "message": "No action needed (suggestion)." }
                else:
                    logger.info("Tạo session mới để ghi lại quyết định 'Không cần hành động'.")
                    new_session = self.analysis_repo.create_session(
                        farm_id=farm.id,
                        initial_detection=f"Đánh giá Bón phân ({current_stage}) - Không cần hành động",
                        plan_type="fertilizer",
                        status="Không hành động" 
                    )
                    self.analysis_repo.update_session_plan(new_session, plan) 
                    self.analysis_repo.commit()
                    
                    return { "session_id": new_session.id, "plan": plan, "original_plan": None, "status": new_session.status, "message": "No action needed." }
                    
            if scenario == "suggest_update" and session_to_update:
                logger.info(f"Lưu kế hoạch GỢI Ý vào suggested_plan_json cho Session ID: {session_to_update.id}")
                session_to_update.suggested_plan_json = json.dumps(plan)
                self.analysis_repo.commit()
                
                original_plan_dict = None
                try: original_plan_dict = json.loads(session_to_update.final_plan_json)
                except Exception: pass
                
                return { "session_id": session_to_update.id, "plan": plan, "original_plan": original_plan_dict, "status": session_to_update.status, "message": "Đã tạo gợi ý cập nhật." }
            else: 
                detection_msg = f"Kế hoạch Bón phân ({current_stage})"
                if scenario == "supplementary":
                    logger.info("Đang tạo Session MỚI cho kế hoạch BÓN BỔ SUNG.")
                    detection_msg = f"Kế hoạch Bón Bổ Sung ({current_stage})"
                else: 
                    logger.info("Đang tạo Session MỚI cho kế hoạch.")
                    
                new_session = self.analysis_repo.create_session(
                    farm_id=farm.id,
                    initial_detection=detection_msg,
                    plan_type="fertilizer",
                    status="Chờ xác nhận"
                )
                self.analysis_repo.update_session_plan(new_session, plan)
                self.analysis_repo.commit()
                return { "session_id": new_session.id, "plan": plan, "original_plan": None, "status": new_session.status, "message": "Tạo kế hoạch mới thành công." }

        except Exception as e:
            logger.error(f"Lỗi khi gọi API OpenAI hoặc lưu DB cho {farmer_id}: {e}")
            self.analysis_repo.rollback()
            return {"error": "Rất tiếc, đã có lỗi khi tạo/cập nhật kế hoạch bón phân."}

    def _build_fertilization_prompt(self, retrieved_context: str, farmer_info: dict, farmer_id, daily_summary: list,
                                 hourly_detail: list, iot_data: dict = None,
                                 pending_plan_json: str = None, 
                                 executed_plan_json: str = None) -> str:
        """Xây dựng prompt động dựa trên việc tạo mới, cập nhật (pending) hay bón bổ sung (executed)."""
        current_time_utc = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        summary_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
        detail_json = json.dumps(hourly_detail, ensure_ascii=False, indent=2)
        area_ha = farmer_info.get('area_ha', 1.0) 
        days_after_planting = farmer_info.get('days_after_planting', -1)
        current_stage = farmer_info.get('current_fertilization_stage', 'Không xác định')
        standard_cong_conversion = "1 ha = 10 công (1 công = 1000m²)"

        iot_data_str = ""
        if iot_data:
            iot_json = json.dumps(iot_data, ensure_ascii=False, indent=2)
            iot_data_str = f"""
            6. **DỮ LIỆU CẢM BIẾN IOT & GPS (Thông tin thực tế tại ruộng):**
            ```json
            {iot_json}
            ```
            """
        
        previous_plan_str = ""
        analysis_requirement = ""
        
        if pending_plan_json:
            role_mission = "**Nhiệm vụ: ĐÁNH GIÁ VÀ CẬP NHẬT KẾ HOẠCH ĐANG CHỜ**"
            main_goal = f"Đánh giá lại kế hoạch **đang chờ** (Mục 8) cho giai đoạn {current_stage} dựa trên dữ liệu thời tiết (Mục 5) và IoT (Mục 6) mới nhất."
            previous_plan_str = f"8. **KẾ HOẠCH ĐANG CHỜ (CẦN XEM XÉT ĐIỀU CHỈNH):**\n```json\n{pending_plan_json}\n```\n"
            
            analysis_requirement = """
                - **Nếu có kế hoạch cũ (Mục 8):** So sánh với dữ liệu IoT mới (Mục 6) và thời tiết (Mục 5).
                - **Nếu CÓ THAY ĐỔI LỚN:** Chỉ tạo kế hoạch mới (và đặt `is_action_needed: true`) nếu có thay đổi ĐÁNG KỂ về:
                    1. `execution_date` (thay đổi ngày bón do thời tiết).
                    2. `quantity_kg` (liều lượng).
                    3. `type` (loại phân).
                - **Nếu KHÔNG CÓ THAY ĐỔI LỚN:** Nếu kế hoạch ở Mục 8 vẫn tối ưu về (ngày bón, liều lượng, loại phân), BẠN BẮT BUỘC PHẢI trả về `"is_action_needed": false` và `main_message` giải thích rằng kế hoạch hiện tại vẫn là tối ưu.
                - **BẮT BUỘC:** Nêu rõ các thay đổi (hoặc lý do không thay đổi) trong `main_message`.
            """
        elif executed_plan_json:
            role_mission = "**Nhiệm vụ: ĐÁNH GIÁ NHU CẦU BÓN BỔ SUNG**"
            main_goal = f"Đánh giá xem có cần bón **bổ sung** cho giai đoạn {current_stage} không, dựa trên những gì **đã bón** (Mục 8) và dữ liệu mới (Mục 5, 6)."
            previous_plan_str = f"8. **KẾ HOẠCH ĐÃ THỰC THI (XEM XÉT BÓN BỔ SUNG):**\n```json\n{executed_plan_json}\n```\n"
            analysis_requirement = """
                - **Nếu có kế hoạch cũ (Mục 8):** Phân tích xem liều lượng đã bón có đủ không, dựa trên IoT mới (Mục 6) và tài liệu (Mục 2).
                - **Nếu ĐỦ:** BẮT BUỘC trả về `is_action_needed: false` và `main_message` giải thích "Đã bón đủ cho giai đoạn này."
                - **Nếu THIẾU (cần bón bổ sung):** Tạo một kế hoạch bón bổ sung (ví dụ: bón lá) với liều lượng hợp lý. Ghi rõ đây là "Bón bổ sung" trong `main_message` và đặt `is_action_needed: true`.
            """
        else: 
            role_mission = "**Nhiệm vụ: TẠO KẾ HOẠCH MỚI**"
            main_goal = f"Tạo kế hoạch bón phân mới cho **GIAI ĐOẠN HIỆN TẠI** là **{current_stage}**."
            previous_plan_str = "" 
            analysis_requirement = "- **Nếu không có kế hoạch cũ:** Phân tích từ đầu dựa trên (Mục 2, 5, 6)."

        prompt = f"""
            **Bối cảnh & Vai trò:**
            Bạn là một chuyên gia nông học hàng đầu về dinh dưỡng cây lúa.
            
            **THỜI GIAN HIỆN TẠI (Để tham chiếu thời gian thực):** {current_time_utc} (ISO 8601 UTC)
            
            {role_mission}

            **MỤC TIÊU ĐẶC BIỆT:**
            {main_goal}

            **QUY TẮC BẮT BUỘC VỀ PHÂN TÍCH:**
            1. Phải lồng ghép số liệu cụ thể từ thời tiết và IoT (nếu có) vào lời văn.
            2. Mọi thông tin quan trọng rút ra từ KIẾN THỨC NỀN **PHẢI KÈM THEO MÃ TRÍCH DẪN** (ví dụ: (1)).
            3. Nếu quyết định không cần hành động (đã bón đủ), BẮT BUỘC trả về `"is_action_needed": false`.
            
            **Thông tin đầu vào:**
            1. **GIAI ĐOẠN TRỌNG TÂM:** **{current_stage}** ({days_after_planting} NSS).
            2. **KIẾN THỨC NỀN (Tài liệu nông nghiệp):**
            ```
            {retrieved_context}
            ```
            3. **Thông tin nông hộ:**
            ```json
            {farmer_json}
            ```
            4. **DỰ BÁO thời tiết 3 ngày tới (tham khảo):**
            ```json
            {summary_json}
            ```
            5. **CHI TIẾT thời tiết ngày TỐT NHẤT (DỮ LIỆU MỚI NHẤT):**
            ```json
            {detail_json}
            ```
            {iot_data_str}
            7. **Giả định chuẩn hóa:** {standard_cong_conversion}
            {previous_plan_str} 
            
            **Yêu cầu Phân Tích & Lập Kế hoạch Chi tiết:**
            
            **A. Phân tích Điều kiện Thực thi (`analysis`):**
            
            1. **Đánh giá Nhu cầu Dinh dưỡng (`analysis.nutrient_need_assessment`):**
            {analysis_requirement}

            2. **Đánh giá Thời điểm Lý tưởng (`analysis.optimal_timing_summary`):**
            - Phân tích dữ liệu thời tiết MỚI NHẤT (Mục 5) để tìm NGÀY/GIỜ bón tối ưu.
            - **BẮT BUỘC:** Phải gán `execution_date` trong JSON đầu ra là thời điểm **bắt đầu** của khung giờ lý tưởng (ví dụ: 7h sáng theo giờ địa phương) và CHUYỂN ĐỔI sang định dạng **ISO 8601 UTC** đầy đủ (ví dụ: `"2025-11-05T00:00:00Z"` nếu 7h sáng giờ VN là 00:00 UTC, hoặc `"2025-11-05T07:00:00Z"` nếu bạn quyết định giờ đó là UTC). Phải có chữ 'Z' ở cuối.
            
            **Định dạng đầu ra (JSON BẮT BUỘC):**
            ```json
            {{
                "is_action_needed": "boolean (True nếu cần bón/cập nhật, False nếu đã bón đủ)",
                "execution_date": "YYYY-MM-DDTHH:MM:SSZ (BẮT BUỘC. Thời điểm bắt đầu thực thi, múi giờ UTC, ví dụ: '2025-11-05T07:00:00Z')",
                "stage_name": "string (Tên giai đoạn: {current_stage})",
                "main_message": "string (Tóm tắt hành động. Ghi rõ nếu là CẬP NHẬT, BÓN BỔ SUNG, hay KHÔNG CẦN BÓN)",
                "analysis": {{
                    "nutrient_need_assessment": "string (Phân tích nhu cầu NPK, có so sánh nếu cần)",
                    "optimal_timing_summary": "string (Phân tích ngày/giờ bón tối ưu MỚI NHẤT)"
                }},
                "fertilizer_stage_detail": [
                    {{
                        "timing": "string (Khoảng ngày NSS, ví dụ: '7-10 NSS')",
                        "objective": "string",
                        "key_indicators": "string (Dấu hiệu nhận biết, kèm trích dẫn)",
                        "fertilizers": [
                            {{
                                "type": "string",
                                "recommended_dosage_per_unit": "string (Trích dẫn liều lượng khuyến nghị, (1))",
                                "calculation_details": "string (Hiển thị phép tính cho {area_ha} ha)",
                                "quantity_kg": "float",
                                "instructions": "string (Hướng dẫn kỹ thuật bón, mực nước)"
                            }}
                        ],
                        "important_notes": "string (Cảnh báo, lưu ý)"
                    }}
                ],
                "next_key_stage": "string (Giai đoạn bón phân quan trọng tiếp theo)",
                "action_details_for_system": {{ 
                    "farmer_id": "{farmer_id}",
                    "gps_data": {{ 
                        "lat": "float/string",
                        "lon": "float/string"
                    }}
                }}
            }}
            ```
        """
        return prompt
    
    def _build_update_prompt(self, current_plan: dict, user_message: str) -> str:
        current_plan_json = json.dumps(current_plan, ensure_ascii=False, indent=2)

        prompt = f"""
            **Bối cảnh & Vai trò:**
            Bạn là một chuyên gia AI về nông học, có nhiệm vụ DUY NHẤT là điều chỉnh kế hoạch bón phân hiện tại (JSON) dựa trên phản hồi của nông dân.

            **QUY TẮC RÀNG BUỘC CỐT LÕI:**
            1. **Chỉ Cập nhật Dữ liệu:** Nhiệm vụ của bạn chỉ là cập nhật dữ liệu (liều lượng, loại phân, ngày bón).
            2. **KHÔNG** được thêm thông tin ngoài lề, kiến thức chung, hoặc nội dung không liên quan đến VIỆC BÓN PHÂN này vào bất kỳ trường nào (nhất là `main_message`).
            3. Nếu yêu cầu của nông dân **mơ hồ** hoặc **không thể xác định** thay đổi cụ thể trong kế hoạch (ví dụ: "tôi không thích kế hoạch này"), **BẮT BUỘC** bạn phải giữ nguyên kế hoạch cũ và giải thích trong `main_message` rằng thông tin chưa rõ ràng.

            **Kế hoạch Bón phân HIỆN TẠI (Định dạng JSON):**
            ```json
            {current_plan_json}
            ```
            
            **Phản hồi của Nông dân (Yêu cầu Điều chỉnh):**
            "{user_message}"

            **Yêu cầu Xử lý:**
            1. **Phân tích:** Xác định chính xác các thay đổi được yêu cầu (ví dụ: Thay đổi liều lượng NPK Thúc 2 từ 229.5 kg thành 180 kg).
            2. **Điều chỉnh:** Cập nhật **HOÀN TOÀN** đối tượng JSON của kế hoạch bón phân để phản ánh những thay đổi.
            3. **Tính toán (nếu cần):** Nếu thay đổi liều lượng/loại phân, hãy cập nhật lại `calculation_details` và `quantity_kg` một cách hợp lý.
            4. **Định dạng đầu ra:** Trả lời bằng **MỘT** đối tượng JSON **HOÀN CHỈNH** theo định dạng của `current_plan`. 
            5. **Tóm tắt:** Cập nhật `main_message` để phản ánh sự thay đổi đã thực hiện (ví dụ: "Đã điều chỉnh liều lượng NPK Thúc 2 từ 229.5 kg thành 180.0 kg...").
            
            **Định dạng đầu ra:**
            Chỉ trả về đối tượng JSON của kế hoạch đã được cập nhật, giữ nguyên cấu trúc như kế hoạch ban đầu.
        """
        return prompt
    
    def update_plan_from_feedback(self, current_plan: dict, user_message: str):
        """Cập nhật kế hoạch bón phân dựa trên phản hồi của người dùng bằng cách gọi LLM."""
        if not self.client:
            logger.warning("Không thể cập nhật kế hoạch vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        logger.info(f"Đang xử lý phản hồi về kế hoạch bón phân: '{user_message}'")
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
            logger.info("Đã cập nhật kế hoạch bón phân từ phản hồi của người dùng thành công.")
            return updated_plan
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật kế hoạch bón phân từ phản hồi: {e}")
            return {"error": "Rất tiếc, đã có lỗi khi xử lý yêu cầu điều chỉnh. Vui lòng thử lại."}
