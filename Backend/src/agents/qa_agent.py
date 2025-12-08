import json
import openai
from datetime import datetime
from .base_agent import BaseAgent 
from src.utils.config import CONFIG
from src.logging.logger import logger

class QAAgent(BaseAgent):
    """
    [CẢI TỔ] QAAgent hoạt động như một Intelligent Assistant/Orchestrator Cấp người dùng.
    Đã tinh giản các Tool cũ thành Quick Retrieval và Planning Service.
    """
    def __init__(self, weather_service, user_repo, analysis_repo, vector_store, nutrient_agent, treatment_agent, water_agent, environmental_agent, iot_service):
        super().__init__(weather_service, user_repo, analysis_repo, vector_store)
        self.api_key = CONFIG.OPENAI_API_KEY
        self.client = None
        self.model_name = CONFIG.OPENAI_MODEL_NAME
        self.generation_config = CONFIG.OPENAI_GENERATION_CONFIG

        if not vector_store:
            raise ValueError("QAAgent yêu cầu phải có VectorStoreService.")
        self.vector_store = vector_store

        self.nutrient_agent = nutrient_agent
        self.treatment_agent = treatment_agent
        self.water_agent = water_agent
        self.iot_service = iot_service
        self.environmental_agent = environmental_agent
        
        self.available_tools = {
            "answer_general_question": self._handle_general_qa,
            "get_nutrient_recommendation": self._execute_quick_nutrient_retrieval,
            "get_watering_advice": self._execute_quick_water_retrieval, 
            "run_proactive_diagnosis": self._execute_health_check_via_image, 
            "create_new_plan": self._execute_planning_tool, 
            "update_existing_plan": self._execute_update_tool, 
            "get_plan_history": self._execute_plan_history_retrieval, 
        }

        if self.api_key:
            try:
                logger.info("Đang cấu hình và khởi tạo client OpenAI cho QAAgent...")
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"Khởi tạo client OpenAI cho QAAgent với model '{self.model_name}' thành công!")
            except Exception as e:
                logger.error(f"[LỖI CẤU HÌNH OPENAI] {e}")
        else:
            logger.warning("[CẢNH BÁO] Không tìm thấy API Key. QAAgent sẽ không hoạt động.")
            
    def _get_latest_iot_data(self, farmer_id: str):
        """Hàm hỗ trợ lấy dữ liệu IoT, có thể được dùng chung."""
        try:
            user, farm = self._get_user_and_farm(farmer_id)
            if not farm: return {"error": "Không tìm thấy thông tin nông trại."}
            
            iot_data = self.iot_service.get_latest_data(farm_id=farm.id) 
            logger.info(f"Đã lấy dữ liệu IoT mới nhất cho {farmer_id}.")
            return iot_data
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu IoT cho {farmer_id}: {e}")
            return {"error": f"Lỗi hệ thống khi lấy dữ liệu IoT: {e}"}

    def _execute_quick_nutrient_retrieval(self, farmer_info: dict, problem_description: str, **kwargs) -> str:
        """[CẬP NHẬT] Tool trả lời nhanh về dinh dưỡng/gợi ý bón phân bằng RAG (KHÔNG TẠO PLAN)."""
        logger.info("Điều phối Tool: Lấy thông tin gợi ý bón phân nhanh (RAG Cấp 1).")
        
        user, farm = self._get_user_and_farm(farmer_info.get("farmer_id"))
        if not farm: return "Lỗi: Không tìm thấy thông tin nông trại."
        
        days_after_planting = (datetime.now().date() - farm.planting_date).days if farm.planting_date else -1
        
        query = f"Lúa {days_after_planting} NSS: {problem_description}. Có nên bón phân lúc này không?"
        retrieved_context = self.vector_store.retrieve("fertilizer_management", query, k=20)
        
        return self._handle_general_qa(farmer_info, f"Nên làm gì về phân bón? {problem_description}", kwargs.get('history', []), retrieved_context)
        
    def _execute_quick_water_retrieval(self, farmer_info: dict, query: str, **kwargs) -> str:
        """[CẬP NHẬT] Tool trả lời nhanh về quản lý nước bằng RAG (KHÔNG TẠO PLAN)."""
        logger.info("Điều phối Tool: Lấy tư vấn quản lý nước nhanh (RAG Cấp 1).")
        
        user, farm = self._get_user_and_farm(farmer_info.get("farmer_id"))
        if not farm: return "Lỗi: Không tìm thấy thông tin nông trại."
        days_after_planting = (datetime.now().date() - farm.planting_date).days if farm.planting_date else -1

        query_rag = f"Khuyến nghị tưới nước cho lúa {days_after_planting} NSS: {query}"
        retrieved_context = self.vector_store.retrieve("water_management", query_rag, k=20)
        
        return self._handle_general_qa(farmer_info, f"Câu hỏi về tưới nước: {query}", kwargs.get('history', []), retrieved_context)

    def _execute_health_check_via_image(self, farmer_info: dict, **kwargs) -> str:
        """[CẬP NHẬT] Tool chẩn đoán thô bằng hình ảnh."""
        logger.info("Điều phối Tool: Chẩn đoán Sức khỏe cây trồng (Image Agent).")
        farmer_id = str(farmer_info.get("farmer_id"))

        iot_data = self._get_latest_iot_data(farmer_id)
        if iot_data.get("error"): return iot_data["error"]
        image_url = iot_data.get("image_url")
        if not image_url: return "Dạ, tôi chưa có hình ảnh giám sát mới nhất từ thiết bị để thực hiện chẩn đoán."

        analysis_data = self.environmental_agent.image_agent.detect_image(farmer_id, image_url)
        
        if analysis_data.get("error"):
             return f"Lỗi phân tích hình ảnh: {analysis_data['error']}"

        detected_disease = analysis_data.get("detected_disease_name", "healthy")
        disease_name_vn = self.environmental_agent.disease_map.get(detected_disease, detected_disease)

        if detected_disease == "healthy":
            return "Dạ, qua phân tích hình ảnh mới nhất, tôi thấy lúa nhà bác đang phát triển **khỏe mạnh**, chưa có dấu hiệu sâu bệnh ạ."
        
        return f"Dạ, qua phân tích hình ảnh, tôi phát hiện có dấu hiệu bệnh **{disease_name_vn}**. **Bác có muốn tôi tạo kế hoạch điều trị chi tiết** ngay bây giờ không ạ?"

    def _execute_planning_tool(self, farmer_info: dict, plan_type: str, disease_name: str = None, **kwargs) -> str:
        """[CẬP NHẬT] Tool gọi Agent chuyên biệt để TẠO KẾ HOẠCH MỚI."""
        
        farmer_id = str(farmer_info.get("farmer_id"))
        iot_data = self._get_latest_iot_data(farmer_id)
        if iot_data.get("error"): return iot_data["error"]
        
        image_path_to_save = None
        
        if plan_type == 'treatment':
            if not disease_name: return "Vui lòng cho tôi biết bệnh cụ thể hoặc chạy chẩn đoán trước."
            
            analysis_data = self.environmental_agent.image_agent.detect_image(farmer_id, iot_data.get('image_url'))
            image_path_to_save = analysis_data.get('image_path')
            
            result = self.treatment_agent.create_treatment_plan(
                disease_name=disease_name, 
                farmer_id=farmer_id,
                image_path_to_save=image_path_to_save,
                iot_data=iot_data
            )
            plan_summary = result.get("plan", {}).get("treatment_plan", {}).get("main_message", "kế hoạch điều trị phù hợp")
            
        elif plan_type == 'fertilizer':
            result = self.nutrient_agent.create_fertilization_plan(
                farmer_id=farmer_id, 
                iot_data=iot_data,
                context_data_from_ema=None 
            )
            plan_summary = result.get("plan", {}).get("main_message", "kế hoạch bón phân phù hợp")
            
        elif plan_type == 'water':
            result = self.water_agent.create_water_management_plan(
                farmer_id=farmer_id, 
                iot_data=iot_data,
                context_data_from_ema=None 
            )
            plan_summary = result.get("plan", {}).get("immediate_command", "tư vấn quản lý nước")
            
        else:
            return f"Loại kế hoạch '{plan_type}' không hợp lệ."

        if result.get("error"):
            return result["error"]
            
        return f"Dạ, tôi đã tạo {plan_summary} cho bác. Bác vui lòng xem chi tiết trong mục Điều trị nhé."

    def _execute_update_tool(self, farmer_info: dict, plan_type: str, user_feedback: str, history) -> str:
        """Hàm trung gian tìm và cập nhật kế hoạch đang chờ dựa trên phản hồi người dùng."""
        
        farm_id = farmer_info.get('farmer_id') 
        
        latest_session = self.analysis_repo.get_latest_session_for_farm_by_type(farm_id, plan_type)
        if not latest_session or latest_session.status not in ["Chờ xác nhận", "Đang xử lý"]:
            return f"Tôi không tìm thấy kế hoạch {plan_type} nào đang chờ để cập nhật. Bác có thể yêu cầu tôi tạo một kế hoạch mới được không ạ?"

        try:
            current_plan = json.loads(latest_session.final_plan_json)
        except:
            return "Lỗi hệ thống: Không đọc được kế hoạch hiện tại."

        if plan_type == 'treatment':
            agent = self.treatment_agent
        elif plan_type == 'fertilizer':
            agent = self.nutrient_agent
        elif plan_type == 'water':
            agent = self.water_agent
        else:
            return "Loại kế hoạch không hợp lệ."
            
        updated_plan_dict = agent.update_plan_from_feedback(current_plan, user_feedback)

        if updated_plan_dict.get("error"):
            return updated_plan_dict["error"]
            
        latest_session.final_plan_json = json.dumps(updated_plan_dict)
        self.analysis_repo.commit()
        
        return f"Dạ, tôi đã cập nhật kế hoạch {plan_type} theo yêu cầu của bác. Nội dung mới: **{updated_plan_dict.get('main_message', 'Đã điều chỉnh')}**."
        
    def _execute_plan_history_retrieval(self, farmer_info: dict, plan_type: str, num_sessions: int = 3) -> str:
        """
        Tool tra cứu N phiên kế hoạch gần nhất, ưu tiên trạng thái Đang xử lý/Đã xử lý.
        Sử dụng LLM để tóm tắt và diễn giải (RAG Cấp Cao).
        """
        logger.info(f"Điều phối Tool: Tra cứu lịch sử {num_sessions} kế hoạch {plan_type} gần nhất.")
        
        farm_id = farmer_info.get('farm_id') 
        if not farm_id: return "Lỗi: Không tìm thấy ID nông trại."
        if plan_type not in ["treatment", "fertilizer", "water"]: 
            return "Loại kế hoạch không hợp lệ. Vui lòng hỏi về 'treatment', 'fertilizer', hoặc 'water'."
            
        try:
            latest_sessions = self.analysis_repo.get_sessions_for_farm_by_type_prioritized(farm_id, plan_type, limit=num_sessions)

            if not latest_sessions:
                return f"Dạ, tôi chưa tìm thấy kế hoạch {plan_type} nào trong lịch sử gần đây của bác."

            context_data_list = []
            for i, session in enumerate(latest_sessions):
                plan_json = session.final_plan_json or session.suggested_plan_json
                
                plan_name_vn, main_diagnosis, risk_value = self.analysis_repo._parse_plan_summary(session)
                
                context_data_list.append({
                    "session_index": i + 1,
                    "status": session.status,
                    "date": session.created_at.strftime('%Y-%m-%d'),
                    "diagnosis_summary": main_diagnosis,
                    "risk_level_summary": risk_value,
                    "plan_json_content": plan_json 
                })
                
            raw_context_json = json.dumps(context_data_list, ensure_ascii=False, indent=2)

            prompt = self._build_plan_history_summary_prompt(plan_type, raw_context_json)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Lỗi khi tra cứu lịch sử kế hoạch {plan_type}: {e}")
            return "Rất tiếc, đã có lỗi hệ thống khi tra cứu lịch sử kế hoạch."

    def _build_plan_history_summary_prompt(self, plan_type: str, raw_context_json: str) -> str:
        """Xây dựng prompt cho LLM để tóm tắt lịch sử kế hoạch."""
        return f"""
            **Nhiệm vụ:** Bạn là một trợ lý nông nghiệp. Hãy phân tích dữ liệu lịch sử kế hoạch dưới đây 
            và tóm tắt lại cho người nông dân bằng giọng điệu thân thiện (xưng "bác" và "tôi").

            **Dữ liệu thô (JSON):**
            ```json
            {raw_context_json}
            ```

            **Yêu cầu Tóm tắt:**
            1. **Khẳng định:** Cho biết có kế hoạch đang chờ/thực thi hay không (dựa trên trạng thái).
            2. **Tóm tắt ngắn:** Với mỗi phiên, nêu rõ ngày, trạng thái, và **ý chính** của kế hoạch (ví dụ: "Bón Thúc 2" hoặc "Tháo nước khẩn cấp").
            3. **Ngôn ngữ:** Sử dụng tiếng Việt thân thiện, KHÔNG dùng các từ kỹ thuật (như JSON, session, index).

            **Đầu ra mong muốn:** Bắt đầu bằng "Dạ, đây là lịch sử kế hoạch..." và kết thúc bằng câu hỏi mở (ví dụ: "Bác muốn xem chi tiết hơn về phiên nào không ạ?").
        """

    def _define_tools(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": "answer_general_question",
                    "description": "Sử dụng cho MỌI câu hỏi kiến thức chung, định nghĩa, giải thích, thông tin về giai đoạn sinh trưởng, hoặc các câu hỏi không yêu cầu tạo kế hoạch/đề xuất can thiệp cụ thể.",
                    "parameters": {"type": "object", "properties": {"question": {"type": "string", "description": "Câu hỏi gốc của người dùng."}}, "required": ["question"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_nutrient_recommendation",
                    "description": "Sử dụng khi người dùng hỏi chung chung về **NGUYÊN TẮC/GỢI Ý** bón phân cho giai đoạn hiện tại (KHÔNG YÊU CẦU TẠO KẾ HOẠCH LƯU DB).",
                    "parameters": {"type": "object", "properties": {"problem_description": {"type": "string", "description": "Mô tả của người dùng về vấn đề liên quan đến phân bón."}}, "required": ["problem_description"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_watering_advice",
                    "description": "Sử dụng khi người dùng hỏi chung chung về **NGUYÊN TẮC/GỢI Ý** quản lý nước (KHÔNG YÊU CẦU TẠO KẾ HOẠCH LƯU DB).",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Câu hỏi của người dùng về việc tưới nước."}}, "required": ["query"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_proactive_diagnosis",
                    "description": "Sử dụng khi người dùng hỏi chung chung về sự có mặt của sâu bệnh (ví dụ: 'lúa có bệnh không?', 'kiểm tra ruộng giúp tôi'). Tool này sẽ tự động phân tích hình ảnh mới nhất từ camera/drone để tìm dấu hiệu bệnh và chỉ nên được gọi khi câu hỏi liên quan đến sức khỏe và sâu bệnh.",
                    "parameters": {"type": "object", "properties": {}}, 
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_new_plan",
                    "description": "Sử dụng khi người dùng YÊU CẦU TẠO MỚI một KẾ HOẠCH (bón phân, tưới nước, điều trị). Không sử dụng để trả lời câu hỏi chung. Yêu cầu phải xác định rõ loại kế hoạch.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "plan_type": {"type": "string", "enum": ["treatment", "fertilizer", "water"], "description": "Loại kế hoạch cần tạo: treatment, fertilizer, hoặc water."},
                            "disease_name": {"type": "string", "description": "Tên bệnh (dạng tiếng Việt) nếu plan_type là 'treatment', nếu không thì để trống."}
                        }, 
                        "required": ["plan_type"]
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_existing_plan",
                    "description": "Sử dụng khi người dùng muốn ĐIỀU CHỈNH hoặc PHẢN HỒI về một KẾ HOẠCH (điều trị/bón phân/nước) đã có. Bắt buộc phải xác định được loại kế hoạch muốn cập nhật.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "plan_type": {"type": "string", "enum": ["treatment", "fertilizer", "water"], "description": "Loại kế hoạch cần cập nhật."},
                            "user_feedback": {"type": "string", "description": "Phản hồi chi tiết của người dùng (ví dụ: 'Giảm liều lượng xuống 50%')."}
                        }, 
                        "required": ["plan_type", "user_feedback"]
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_plan_history",
                    "description": "Sử dụng khi người dùng hỏi về các KẾ HOẠCH đã thực thi hoặc đang thực thi trước đó (lịch sử) về một loại can thiệp cụ thể.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "plan_type": {"type": "string", "enum": ["treatment", "fertilizer", "water"], "description": "Loại kế hoạch muốn xem lịch sử."},
                            "num_sessions": {"type": "integer", "description": "Số lượng phiên gần nhất muốn xem (mặc định là 3)."}
                        }, 
                        "required": ["plan_type"]
                    },
                },
            },
        ]

    def _handle_general_qa(self, farmer_info: dict, question: str, history: list, retrieved_context=None) -> str:
        logger.info(f"Tool 'answer_general_question' được kích hoạt cho câu hỏi: '{question}'")
        prompt = self._build_qa_prompt(farmer_info, question, retrieved_context, history)
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.generation_config.get("temperature", 0.7),
        )
        return response.choices[0].message.content.strip()

    def answer_question(self, farmer_info: dict, question: str, history: list = None):
        if not self.client:
            return {"error": "Trợ lý AI chưa sẵn sàng.", "history": history or []}
        history = history or []
        if not farmer_info:
            return {"error": "Không tìm thấy thông tin nông hộ.", "history": history}
        
        print(f"Farmer Info Received: {farmer_info}")
        
        greetings = ["chào", "hello", "xin chào", "hi"]
        if not history and question.lower().strip() in greetings:
            answer = "Dạ chào bác, tôi là trợ lý nông nghiệp AI. Bác cần tôi giúp gì về việc đồng áng hôm nay ạ?"
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            return {"answer": answer, "history": history}

        messages = [{"role": "system", "content": "Bạn là một trợ lý nông nghiệp AI. Hãy phân tích câu hỏi của người dùng và chọn công cụ phù hợp nhất để trả lời."}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        try:
            logger.info(f"QAAgent đang phân tích câu hỏi để chọn tool: '{question}'")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self._define_tools(),
                tool_choice="auto", 
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            answer = ""
            if tool_calls:
                tool_call = tool_calls[0] 
                function_name = tool_call.function.name
                function_to_call = self.available_tools.get(function_name)
                
                if function_to_call:
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info(f"LLM quyết định gọi tool: '{function_name}' với tham số: {function_args}")
                    
                    all_args = {**function_args, 'farmer_info': farmer_info, 'history': history}
                    
                    answer = function_to_call(**all_args)
                else:
                    answer = f"Lỗi: Không tìm thấy hàm thực thi cho tool '{function_name}'."
            else:
                logger.info("LLM không chọn tool, mặc định xử lý như câu hỏi chung.")
                answer = self._handle_general_qa(farmer_info, question, history)

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            if len(history) > 10:
                history = history[-10:]
            
            return {"answer": answer, "history": history}

        except Exception as e:
            logger.error(f"Lỗi khi điều phối câu trả lời: {e}", exc_info=True)
            return {"error": "Rất tiếc, đã có lỗi xảy ra. Vui lòng thử lại.", "history": history}

    def _build_qa_prompt(self, farmer_info: dict, question: str, retrieved_context: str, history: list) -> str:
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        today = datetime.now().date()
        planting_date_str = farmer_info.get("farm_properties", {}).get("planting_date")
        days_since_planting = "không rõ"
        if planting_date_str:
            try:
                planting_date = datetime.strptime(planting_date_str, "%Y-%m-%d").date()
                days_since_planting = (today - planting_date).days
            except ValueError:
                pass 
        history_str = ""
        if history:
            formatted_lines = ["**Lịch sử trò chuyện gần đây:**"]
            for message in history:
                role = "Bác nông dân" if message["role"] == "user" else "Trợ lý AI"
                formatted_lines.append(f"- {role}: {message['content']}")
            history_str = "\n".join(formatted_lines) + "\n"

        prompt = f"""
            **VAI TRÒ & QUY TẮC CỐT LÕI:**
            Bạn là một trợ lý nông nghiệp AI thân thiện, đang nói chuyện trực tiếp với một người nông dân. 
            Nhiệm vụ của bạn là trả lời câu hỏi của họ một cách chính xác, dễ hiểu và CHỈ DỰA TRÊN 
            DỮ LIỆU ĐƯỢC CUNG CẤP TRONG MỤC **'Dữ liệu về nông hộ này'** và **'KIẾN THỨC NỀN'**.

            **CẤM TUYỆT ĐỐI:**
            1. **KHÔNG** suy diễn, thêm, hoặc bịa đặt thông tin không có trong 'Dữ liệu về nông hộ' hoặc 'KIẾN THỨC NỀN'.
            2. Nếu thông tin cần thiết để trả lời không có trong các mục trên, BẮT BUỘC phải trả lời: "Rất tiếc, tôi không có đủ thông tin chi tiết để trả lời chính xác câu hỏi này."
            3. **KHÔNG** trả lời các câu hỏi ngoài lề hoặc không liên quan đến nông nghiệp (Ví dụ: Hỏi về chính trị, thể thao, hay các vấn đề không liên quan đến lúa).

            Dữ liệu về lịch sử trò chuyện
            {history_str}
            **Dữ liệu về nông hộ này (tính đến hôm nay, ngày {today.strftime('%Y-%m-%d')}):**
            ```json
            {farmer_json}
            ```
            **KIẾN THỨC NỀN (Từ cơ sở dữ liệu tri thức):**
            ```
            {retrieved_context}
            ```
            **Thông tin bổ sung:**
            - Hôm nay là ngày thứ {days_since_planting} sau khi gieo sạ.
            
            **Câu hỏi MỚI NHẤT của nông dân:**
            "{question}"
            
            **Yêu cầu đầu ra:**
            Soạn một câu trả lời ngắn gọn, đầy đủ, trực tiếp và thân thiện bằng tiếng Việt. Sử dụng cách xưng hô "bác" và "tôi". Câu trả lời phải mạch lạc, phù hợp với cuộc hội thoại và **chỉ sử dụng thông tin từ các mục đã cho**.

            **Câu trả lời của bạn:**
        """
        return prompt