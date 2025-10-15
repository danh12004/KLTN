import json
import openai
from datetime import datetime
from src.utils.config import CONFIG
from src.logging.logger import logger

class QAAgent:
    """
    QAAgent hoạt động như một Orchestrator, điều phối các tác vụ đến các agent chuyên biệt.
    """
    def __init__(self, vector_store, nutrient_agent, treatment_agent, water_agent, environmental_agent):
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
        
        self.environmental_agent = environmental_agent
        self.available_tools = {
            "answer_general_question": self._handle_general_qa,
            "get_nutrient_recommendation": self._execute_nutrient_tool,
            "get_treatment_plan": self._execute_treatment_tool,
            "get_watering_advice": self._execute_water_tool,
            "run_proactive_diagnosis": self._execute_proactive_diagnosis, 
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
    
    def _execute_nutrient_tool(self, farmer_info: dict, **kwargs) -> str:
        """Hàm trung gian chuẩn bị và gọi NutrientAgent."""
        logger.info("Điều phối tới NutrientAgent...")
        farmer_id = farmer_info.get("id")
        if not farmer_id:
            return "Lỗi: Không tìm thấy ID của nông dân để tạo kế hoạch bón phân."
        
        result = self.nutrient_agent.create_fertilization_plan(farmer_id=str(farmer_id))
        
        if result.get("error"):
            return result["error"]
        if result.get("plan"):
            summary = result["plan"].get("main_summary", "một kế hoạch chi tiết")
            return f"Dạ, tôi đã tạo {summary}. Bác có thể xem trong mục 'Kế hoạch canh tác' ạ."
        return "Đã có lỗi xảy ra khi tạo kế hoạch bón phân."

    def _execute_treatment_tool(self, farmer_info: dict, symptom_description: str, **kwargs) -> str:
        """Hàm trung gian chuẩn bị và gọi TreatmentAgent."""
        logger.info("Điều phối tới TreatmentAgent...")
        
        disease_map = {
            "đốm nâu": "brown_spot",
            "cháy bìa lá": "bacterial_leaf_blight",
            "đạo ôn": "blast"
        }
        model_disease_name = None
        for keyword, disease_code in disease_map.items():
            if keyword in symptom_description.lower():
                model_disease_name = disease_code
                break

        if not model_disease_name:
            return "Dạ, bác có thể mô tả kỹ hơn về triệu chứng hoặc gửi ảnh để tôi chẩn đoán chính xác hơn được không ạ?"

        farmer_id = farmer_info.get("id")
        if not farmer_id:
            return "Lỗi: Không tìm thấy ID của nông dân để tạo kế hoạch điều trị."

        result = self.treatment_agent.create_treatment_plan(model_disease_name=model_disease_name, farmer_id=str(farmer_id))
        
        if result.get("error"):
            return result["error"]
        if result.get("plan"):
            message = result["plan"]["treatment_plan"].get("main_message", "kế hoạch điều trị phù hợp")
            return f"Dạ, tôi đã phân tích và đề xuất {message}. Bác vui lòng xem chi tiết trong mục **'Thông báo'** nhé."
        return "Đã có lỗi xảy ra khi tạo kế hoạch điều trị."

    def _execute_water_tool(self, farmer_info: dict, **kwargs) -> str:
        """Hàm trung gian chuẩn bị và gọi WaterAgent."""
        logger.info("Điều phối tới WaterAgent...")
        farmer_id = farmer_info.get("id")
        if not farmer_id:
            return "Lỗi: Không tìm thấy ID của nông dân để tạo tư vấn tưới nước."

        result = self.water_agent.create_water_management_plan(farmer_id=str(farmer_id))
        
        if result.get("error"):
            return result["error"]
        if result.get("plan"):
            recommendation = result["plan"].get("main_recommendation", "hành động phù hợp")
            reason = result["plan"].get("reason", "dựa trên các điều kiện thực tế")
            return f"Dạ, khuyến nghị của tôi là **{recommendation}** vì {reason}."
        return "Đã có lỗi xảy ra khi tạo tư vấn quản lý nước."
    
    def _execute_proactive_diagnosis(self, farmer_info: dict, **kwargs) -> str:
        """Hàm trung gian gọi EnvironmentalMonitoringAgent để phân tích tự động."""
        logger.info("Điều phối tới EnvironmentalMonitoringAgent để chẩn đoán chủ động...")
        farmer_id = farmer_info.get("id")
        if not farmer_id:
            return "Lỗi: Không tìm thấy ID của nông dân để chạy chẩn đoán."

        result = self.environmental_agent.run_single_automated_analysis(farmer_id=str(farmer_id))

        if result.get("error"):
            return result["error"]

        if result.get("detection") == "healthy":
            return "Dạ, qua phân tích hình ảnh mới nhất, tôi thấy lúa nhà bác đang phát triển khỏe mạnh, chưa có dấu hiệu sâu bệnh ạ."

        if result.get("plan"):
            message = result["plan"]["treatment_plan"].get("main_message", "kế hoạch điều trị phù hợp")
            return f"Dạ, qua phân tích hình ảnh, tôi phát hiện có dấu hiệu bệnh và đã đề xuất {message}. Bác vui lòng xem chi tiết trong mục **'Thông báo'** nhé."

        return "Đã có lỗi xảy ra trong quá trình phân tích hình ảnh."


    def _define_tools(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": "answer_general_question",
                    "description": "Sử dụng khi người dùng hỏi các câu hỏi kiến thức chung, định nghĩa, giải thích khái niệm. Không dùng cho các yêu cầu đề xuất giải pháp cụ thể.",
                    "parameters": {"type": "object", "properties": {"question": {"type": "string", "description": "Câu hỏi gốc của người dùng."}}, "required": ["question"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_nutrient_recommendation",
                    "description": "Sử dụng khi người dùng hỏi về dinh dưỡng, bón phân (loại gì, liều lượng, thời điểm).",
                    "parameters": {"type": "object", "properties": {"problem_description": {"type": "string", "description": "Mô tả của người dùng về vấn đề liên quan đến phân bón."}}, "required": ["problem_description"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_treatment_plan",
                    "description": "Sử dụng khi người dùng mô tả một triệu chứng sâu bệnh (ví dụ: lá vàng, có sâu) và cần một giải pháp hoặc kế hoạch điều trị.",
                    "parameters": {"type": "object", "properties": {"symptom_description": {"type": "string", "description": "Mô tả chi tiết về triệu chứng sâu bệnh."}}, "required": ["symptom_description"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_watering_advice",
                    "description": "Sử dụng khi người dùng hỏi về việc tưới nước, lịch tưới, hoặc các vấn đề liên quan đến độ ẩm.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Câu hỏi của người dùng về việc tưới nước."}}, "required": ["query"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_proactive_diagnosis",
                    "description": "Sử dụng khi người dùng hỏi chung chung về tình trạng sức khỏe của cây lúa (ví dụ: 'lúa có bệnh không?', 'kiểm tra ruộng giúp tôi') mà KHÔNG mô tả triệu chứng cụ thể. Tool này sẽ tự động phân tích hình ảnh mới nhất từ camera/drone.",
                    "parameters": {"type": "object", "properties": {}}, 
                },
            },
        ]

    def _handle_general_qa(self, farmer_info: dict, question: str, history: list) -> str:
        logger.info(f"Tool 'answer_general_question' được kích hoạt cho câu hỏi: '{question}'")
        retrieved_context = self.vector_store.retrieve("general_qa", question, k=5)
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
            **Bối cảnh:**
            Bạn là một trợ lý nông nghiệp AI thân thiện, đang nói chuyện trực tiếp với một người nông dân. Nhiệm vụ của bạn là trả lời câu hỏi của họ một cách chính xác và dễ hiểu nhất có thể, dựa trên dữ liệu về chính nông hộ của họ và ngữ cảnh cuộc trò chuyện.
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
            **Yêu cầu:**
            Soạn một câu trả lời ngắn gọn, trực tiếp, và thân thiện bằng tiếng Việt. Sử dụng cách xưng hô "bác" và "tôi". Câu trả lời phải mạch lạc và phù hợp với cuộc hội thoại trước đó.

            **Câu trả lời của bạn:**
        """
        return prompt