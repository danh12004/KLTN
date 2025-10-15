import json
from datetime import datetime, timedelta
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

    def create_treatment_plan(self, model_disease_name: str, farmer_id: str, image_path_to_save: str = None, iot_data=None):
        """Tạo kế hoạch điều trị dựa trên bệnh được phát hiện."""
        if not self.client:
            logger.warning("TreatmentAgent không thể tạo kế hoạch vì Trợ lý AI chưa sẵn sàng.")
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        disease_name_vn = self.disease_map.get(model_disease_name, "Không xác định")
        
        user, farm = self._get_user_and_farm(farmer_id)
        if not farm:
            logger.warning(f"Không tìm thấy nông trại cho người dùng ID {farmer_id} khi tạo kế hoạch điều trị.")
            return {"error": f"Không tìm thấy nông trại cho người dùng ID {farmer_id}."}

        # --- IMPROVEMENT: Calculate days_since_planting for better context ---
        days_since_planting = "không rõ"
        if farm.planting_date:
            try:
                days_since_planting = (datetime.now().date() - farm.planting_date).days
            except TypeError:
                # Handle case where planting_date might not be a date object
                pass

        farmer_info_for_llm = {
            "farmer_id": user.id, "full_name": user.full_name,
            "farm_name": farm.name, "area_ha": farm.area_ha,
            "planting_date": str(farm.planting_date),
            "days_since_planting": days_since_planting, 
            "location": {"province": farm.province}
        }
        
        query_for_retrieval = f"""
            Thông tin chi tiết về cách phòng và điều trị bệnh {disease_name_vn} trên lúa, 
            bao gồm triệu chứng, thuốc đặc trị, biện pháp canh tác, và các lưu ý về dinh dưỡng
            để giúp cây phục hồi.
        """
        retrieved_context = self.vector_store.retrieve(model_disease_name, query_for_retrieval, k=7)
        
        province = farm.province
        hourly_forecast = self.weather_service.get_forecast(province)
        if not hourly_forecast:
            logger.error(f"Không thể lấy dữ liệu thời tiết cho tỉnh {province}.")
            return {"error": f"Không thể lấy dữ liệu thời tiết cho tỉnh {province}."}

        df = pd.DataFrame(hourly_forecast)
        df['date'] = pd.to_datetime(df['date'])
        today = pd.to_datetime(datetime.now().date())
        end_date = today + pd.Timedelta(days=2)

        df_3_days = df[(df['date'] >= today) & (df['date'] <= end_date)].copy()
        df_3_days['date_str'] = df_3_days['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        if df_3_days.empty:
            logger.error(f"Không có đủ dữ liệu thời tiết cho 3 ngày tới tại {province}.")
            return {"error": "Không có đủ dữ liệu thời tiết cho 3 ngày tới."}

        daily_groups = df_3_days.groupby(df['date'].dt.date)

        scored_days = [{'date': date_val, 'score': self._score_spraying_day(g.to_dict('records')), 'data': g.to_dict('records')} for date_val, g in daily_groups]
        
        if not scored_days:
            logger.error("Không thể chấm điểm các ngày dự báo thời tiết.")
            return {"error": "Không thể chấm điểm các ngày dự báo."}
        
        best_day = max(scored_days, key=lambda x: x['score'])
        hourly_detail_for_target_date = best_day['data']
        for hour_data in hourly_detail_for_target_date:
            if 'date' in hour_data and not isinstance(hour_data['date'], str):
                hour_data['date'] = hour_data.get('date_str', str(hour_data['date']))
        
        daily_summary = self._summarize_daily_forecast(df_3_days.to_dict('records'))
        
        prompt = self._build_treatment_prompt(
            retrieved_context, farmer_info_for_llm, daily_summary, 
            hourly_detail_for_target_date, str(farmer_id), disease_name_vn, iot_data=iot_data
        ) 
        
        new_session = self.analysis_repo.create_session(
            farm_id=farm.id,
            initial_detection=disease_name_vn,
            image_path=image_path_to_save
        )
        
        response_content = ""
        try:
            logger.info(f"Đang tạo kế hoạch điều trị cho nông hộ {farmer_id}...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self.generation_config.get("temperature", 0.6),
                top_p=self.generation_config.get("top_p", 0.9)
            )
            response_content = response.choices[0].message.content
            plan = json.loads(response_content)
            
            self.analysis_repo.update_session_plan(new_session, plan)
            self.analysis_repo.commit()
            
            logger.info(f"Đã tạo và LƯU thành công kế hoạch cho session {new_session.id}.")
            
            return {"session_id": new_session.id, "plan": plan}
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Lỗi khi phân tích JSON từ LLM cho session {new_session.id}: {e}")
            logger.error(f"Phản hồi nhận được từ LLM: {response_content}")
            return {"error": "Trợ lý AI đã phản hồi không hợp lệ. Vui lòng thử lại."}
        except Exception:
            self.analysis_repo.rollback()
            logger.exception(f"Lỗi không xác định khi tạo kế hoạch cho session {new_session.id}.")
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
                                hourly_detail: list, farmer_id: str, disease_name_vn: str, iot_data: dict = None) -> str:
        """Xây dựng prompt chuyên cho việc điều trị bệnh."""
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        summary_json = json.dumps(daily_summary, ensure_ascii=False, indent=2)
        detail_json = json.dumps(hourly_detail, ensure_ascii=False, indent=2)

        iot_data_str = ""
        if iot_data:
            iot_json = json.dumps(iot_data, ensure_ascii=False, indent=2)
            iot_data_str = f"""
            6. **DỮ LIỆU CẢM BIẾN IOT (Thông tin thực tế tại ruộng):**
            ```json
            {iot_json}
            ```
            """

        prompt = f"""
            **Bối cảnh:**
            Bạn là một trợ lý nông nghiệp AI chuyên gia hàng đầu, có khả năng đưa ra lời khuyên chuyên môn cao nhưng được diễn đạt một cách rõ ràng, súc tích và dễ hiểu cho người nông dân.

            **Thông tin đầu vào:**
            1. **CHẨN ĐOÁN BAN ĐẦU:** Lúa được xác định là đang bị bệnh **{disease_name_vn}**.
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

            **Yêu cầu Phân Tích và Lập Kế Hoạch:**
            
            **QUY TẮC VÀNG (BẮT BUỘC TUÂN THỦ):** Mọi phân tích, đặc biệt là về rủi ro và thời tiết, PHẢI được chứng minh bằng SỐ LIỆU CỤ THỂ (ví dụ: nhiệt độ 27°C, độ ẩm 92%, xác suất mưa 80%) lấy từ các mục "Thông tin đầu vào". NGHIÊM CẤM đưa ra các nhận định chung chung, không có bằng chứng.

            **HƯỚNG DẪN CHI TIẾT:** Dựa trên toàn bộ thông tin trên, hãy suy nghĩ như một chuyên gia nông học dày dạn kinh nghiệm. Phân tích của bạn phải dựa trên bằng chứng cụ thể. Hãy điền vào cấu trúc JSON ở cuối.
            
            ***VÍ DỤ VỀ CÁCH TRẢ LỜI SAI (KHÔNG LÀM THEO):***
            - "risk_assessment": "Rủi ro cao do độ ẩm cao và trời sắp mưa." (Lỗi: quá chung chung).

            ***VÍ DỤ VỀ CÁCH TRẢ LỜI ĐÚNG (BẮT BUỘC LÀM THEO):***
            - "risk_assessment": "Rủi ro bùng phát dịch là RẤT CAO. Bằng chứng: Cảm biến IoT ghi nhận độ ẩm không khí liên tục ở mức 92% trong 6 giờ qua, vượt ngưỡng an toàn là 85%. Kết hợp với dự báo thời tiết cho ngày mai có mưa rào với xác suất 80% và nhiệt độ ban đêm duy trì ở 26°C, tạo ra điều kiện 'giờ sương' hoàn hảo cho nấm đạo ôn phát triển và phát tán."
            
            Bây giờ, hãy phân tích và tạo ra kế hoạch theo ví dụ ĐÚNG ở trên.

            1.  **Đánh giá Rủi ro (`analysis.risk_assessment`):**
                -   **Tổng hợp & Trích dẫn Dữ liệu:** Bắt đầu bằng một nhận định chung. Sau đó, **BẮT BUỘC PHẢI** chứng minh nhận định đó bằng cách trích dẫn số liệu cụ thể từ các nguồn đầu vào (IoT, dự báo thời tiết).
                -   **Cú pháp trích dẫn:** Khi dùng dữ liệu, hãy ghi rõ nguồn. Ví dụ: "độ ẩm không khí là 92% (từ cảm biến IoT)", "dự báo có mưa với xác suất 70% (từ dự báo thời tiết)".
                -   **Phân tích Nguyên nhân:** Giải thích *tại sao* các số liệu được trích dẫn đó, khi kết hợp với nhau, lại tạo ra môi trường lây lan lý tưởng.
                -   **Liên hệ Giai đoạn Sinh trưởng:** Kết nối rủi ro với `days_since_planting`.

            2.  **Tóm tắt Thời tiết (`analysis.weather_summary`):** - Phân tích hai khía cạnh riêng biệt và rõ ràng, **luôn kèm theo số liệu**:
                -   **Gây Hại (Tác động đến bệnh):** Dùng dữ liệu dự báo để giải thích thời tiết sắp tới sẽ thúc đẩy bệnh {disease_name_vn} như thế nào. Ví dụ: "Dự báo ngày mai (YYYY-MM-DD) sẽ có mưa rào (xác suất 75%) và độ ẩm trung bình duy trì trên 88%, tạo điều kiện cho bệnh phát triển không ngừng."
                -   **Thuận Lợi (Tác động đến phun thuốc):** Dùng **CHI TIẾT thời tiết theo giờ** để chỉ ra 'cửa sổ thời gian vàng' và giải thích tại sao. Ví dụ: "Tuy nhiên, có một 'cửa sổ thời gian vàng' vào sáng mai từ 7h-11h khi trời tạnh ráo (xác suất mưa 0%) và gió chỉ cấp 2 (dưới 10km/h). Đây là cơ hội duy nhất để phun thuốc hiệu quả."

            3.  **Thông điệp chính (`treatment_plan.main_message`):**
                -   Viết một câu duy nhất, súc tích, là hành động quan trọng nhất.

            4.  **Xác định Thời điểm Vàng (`treatment_plan.optimal_spray_day`):**
                -   Chọn NGÀY và BUỔI (Sáng/Chiều) tốt nhất.
                -   Phần `reason` phải giải thích một cách khoa học.

            5.  **Kế hoạch Thuốc (`treatment_plan.drug_info`):**
                -   `sản_phẩm_tham_khảo`: Đề xuất MỘT loại thuốc phổ biến.
                -   `liều_lượng`: **Phải có 2 phần**: (1) Hướng dẫn cách pha và (2) **Tính toán chính xác tổng lượng** cần dùng cho toàn bộ diện tích.
                -   `cách_dùng`: Hướng dẫn chi tiết các bước.

            6.  **Hành động Bổ sung (`treatment_plan.additional_actions`):** - Liệt kê ít nhất 1-2 biện pháp canh tác hỗ trợ.

            7.  **Tư vấn Bón phân (`fertilizer_advice`):**
                -   `recommendation`: Đề xuất cụ thể loại phân, liều lượng.
                -   `reason`: Giải thích ngắn gọn vai trò.

            8.  **Dự báo Kết quả (`prognosis`):** - Đưa ra dự báo có mốc thời gian rõ ràng.

            **Định dạng đầu ra:**
            Hãy trả lời bằng một đối tượng JSON DUY NHẤT có cấu trúc chính xác như sau.
            ```json
            {{
                "analysis": {{
                    "risk_assessment": "string (Phân tích chi tiết, BẮT BUỘC kết nối dữ liệu và giải thích nguyên nhân)",
                    "weather_summary": "string (Phân tích 2 khía cạnh, BẮT BUỘC dùng số liệu cụ thể)"
                }},
                "treatment_plan": {{
                    "is_actionable": true,
                    "main_message": "string (Một câu tóm tắt hành động chính, rõ ràng và súc tích)",
                    "optimal_spray_day": {{
                        "date": "string (YYYY-MM-DD)",
                        "session": "string (Sáng hoặc Chiều)",
                        "reason": "string (Giải thích khoa học lý do chọn thời điểm này)"
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
                    "recommendation": "string (Đề xuất cụ thể loại phân và liều lượng nếu cần)",
                    "reason": "string (Giải thích ngắn gọn vai trò của việc bón phân đó)"
                }},
                "prognosis": "string (Dự báo chuyên môn có mốc thời gian rõ ràng)",
                "action_details_for_system": {{
                    "farmer_id": "{farmer_id}",
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

