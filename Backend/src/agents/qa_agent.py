import json
import openai # 1. Thay thế thư viện google.generativeai
from datetime import datetime
from src.utils.config import CONFIG # 2. Sử dụng CONFIG đã được import
from src.services.vector_store_service import VectorStoreService 

class QAAgent:
    def __init__(self, vector_store: VectorStoreService):
        self.api_key = CONFIG.OPENAI_API_KEY
        self.client = None
        self.model_name = CONFIG.OPENAI_MODEL_NAME 
        self.generation_config = CONFIG.OPENAI_GENERATION_CONFIG

        if not vector_store:
            raise ValueError("QAAgent yêu cầu phải có VectorStoreService.")
        self.vector_store = vector_store

        if self.api_key:
            try:
                print("Đang cấu hình và khởi tạo client OpenAI cho QAAgent...")
                self.client = openai.OpenAI(api_key=self.api_key)
                print(f"Khởi tạo client OpenAI với model '{self.model_name}' thành công!")
            except Exception as e:
                print(f"[LỖI CẤU HÌNH OPENAI] {e}")
                self.client = None
        else:
            print("[CẢNH BÁO] Không tìm thấy API Key. QAAgent sẽ không hoạt động.")

    def _build_qa_prompt(self, farmer_info: dict, question: str, retrieved_context: str) -> str:
        farmer_json = json.dumps(farmer_info, ensure_ascii=False, indent=2)
        
        today = datetime.now()
        planting_date_str = farmer_info.get("farm_properties", {}).get("planting_date")
        days_since_planting = "không rõ"
        if planting_date_str:
            try:
                planting_date = datetime.strptime(planting_date_str, "%Y-%m-%d")
                days_since_planting = (today - planting_date).days
            except ValueError:
                pass 

        prompt = f"""
            **Bối cảnh:**
            Bạn là một trợ lý nông nghiệp AI thân thiện, đang nói chuyện trực tiếp với một người nông dân. Nhiệm vụ của bạn là trả lời câu hỏi của họ một cách chính xác và dễ hiểu nhất có thể, dựa trên dữ liệu về chính nông hộ của họ.

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

            **Câu hỏi của nông dân:**
            "{question}"

            **Yêu cầu:**
            1.  **Phân tích câu hỏi:** Hiểu rõ nông dân đang muốn biết về vấn đề gì (giai đoạn phát triển, cách bón phân, lịch sử bệnh, v.v.).
            2.  **Tìm kiếm thông tin:** Trích xuất thông tin liên quan từ file JSON dữ liệu nông hộ để trả lời.
            3.  **Trả lời:** Soạn một câu trả lời ngắn gọn, trực tiếp, và thân thiện bằng tiếng Việt. Sử dụng cách xưng hô "bác" và "tôi".

            **Ví dụ:**
            - Nếu hỏi về giai đoạn: "Dạ thưa bác, lúa của bác đã được {days_since_planting} ngày tuổi, đang trong giai đoạn làm đòng ạ."
            - Nếu hỏi về phân bón: "Dạ, với đất có độ pH là {farmer_info.get('soil_properties', {}).get('ph')}, bác nên ưu tiên bón phân lân để cải tạo đất ạ."

            **Câu trả lời của bạn:**
        """
        return prompt

    def answer_question(self, farmer_info: dict, question: str):
        if not self.client:
            return {"error": "Trợ lý AI chưa sẵn sàng."}

        if not farmer_info:
            return {"error": "Không tìm thấy thông tin nông hộ."}
        
        greetings = ["chào", "hello", "xin chào", "hi"]
        if question.lower().strip() in greetings:
            return {"answer": "Dạ chào bác, tôi là trợ lý nông nghiệp AI. Bác cần tôi giúp gì về việc đồng áng hôm nay ạ?"}

        print(f"[Q&A AGENT] Đang truy xuất kiến thức cho câu hỏi: '{question}'")
        retrieved_context = self.vector_store.retrieve(question, k=5)

        prompt = self._build_qa_prompt(farmer_info, question, retrieved_context)
        
        try:
            print(f"[Q&A AGENT] Đang tạo câu trả lời với model {self.model_name}...")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.generation_config.get("temperature", 0.7),
                top_p=self.generation_config.get("top_p", 1.0)
            )
            
            answer = response.choices[0].message.content.strip()
            return {"answer": answer}
        except Exception as e:
            print(f"[Q&A AGENT] Lỗi khi tạo câu trả lời: {e}")
            return {"error": "Rất tiếc, tôi chưa thể trả lời câu hỏi này. Vui lòng thử lại."}