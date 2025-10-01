import faiss
import numpy as np
import json
import re
from sentence_transformers import SentenceTransformer
import os

class VectorStoreService:
    def __init__(self, config_paths):
        print("[VectorStore] Khởi tạo dịch vụ...")
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.documents = [] 
        self.index = None   
        self._build_or_load_index(config_paths)

    def _chunk_text(self, text, chunk_size=1000, overlap=50):
        sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                current_chunk += sentence + " "
            else:
                chunks.append(current_chunk.strip())
                overlap_content = ' '.join(current_chunk.split()[-overlap:])
                current_chunk = overlap_content + " " + sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def _flatten_json_to_text(self, data, prefix=""):
        text_parts = []
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix} {key}".strip()
                text_parts.append(self._flatten_json_to_text(value, new_prefix))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_prefix = f"{prefix} {i + 1}".strip()
                text_parts.append(self._flatten_json_to_text(item, new_prefix))
        else:
            return f"{prefix}: {data}."
        
        return " ".join(filter(None, text_parts))

    def _load_and_process_sources(self, config_paths):
        try:
            rice_path = config_paths.get("rice_varieties_path")
            if rice_path and os.path.exists(rice_path):
                with open(rice_path, 'r', encoding='utf-8') as f:
                    rice_data = json.load(f)
                    for rice_name, info in rice_data.items():
                        content = self._flatten_json_to_text(info, f"Giống lúa {rice_name}")
                        chunks = self._chunk_text(content)
                        for chunk in chunks:
                            self.documents.append({
                                "content": chunk,
                                "source": "rice_varieties.json",
                                "rice_variety": rice_name
                            })
                print(f"[VectorStore] Đã xử lý thành công file: {rice_path}")
            else:
                print(f"[CẢNH BÁO VectorStore] Không tìm thấy file rice_varieties.json tại: {rice_path}")
        except Exception as e:
            print(f"[LỖI VectorStore] Không thể tải rice_varieties.json: {e}")

        try:
            disease_path = config_paths.get("knowledge_base_path")
            if disease_path and os.path.exists(disease_path):
                with open(disease_path, 'r', encoding='utf-8') as f:
                    disease_data = json.load(f)
                    for disease_name, info in disease_data.items():
                        content = self._flatten_json_to_text(info, f"Bệnh {disease_name}")
                        chunks = self._chunk_text(content)
                        for chunk in chunks:
                            self.documents.append({
                                "content": chunk,
                                "source": "knowledge_base.json",
                                "disease_name": disease_name 
                            })
                print(f"[VectorStore] Đã xử lý thành công file: {disease_path}")
            else:
                print(f"[CẢNH BÁO VectorStore] Không tìm thấy file knowledge_base.json tại: {disease_path}")
        except Exception as e:
            print(f"[LỖI VectorStore] Không thể tải knowledge_base.json: {e}")

        try:
            fertilizer_path = config_paths.get("fertilizer_path")
            if fertilizer_path and os.path.exists(fertilizer_path):
                with open(fertilizer_path, 'r', encoding='utf-8') as f:
                    fertilizer_text = f.read()
                    chunks = self._chunk_text(fertilizer_text)
                    for chunk in chunks:
                        self.documents.append({
                            "content": chunk,
                            "source": "fertilizer.txt"
                        })
                print(f"[VectorStore] Đã xử lý thành công file: {fertilizer_path}")
        except Exception as e:
            print(f"[LỖI VectorStore] Không thể tải file fertilizer.txt: {e}")

    def _save_index(self, index_path, documents_path):
        print("[VectorStore] Đang lưu index và documents vào ổ đĩa...")
        vector_store_dir = os.path.dirname(index_path)
        os.makedirs(vector_store_dir, exist_ok=True)
        faiss.write_index(self.index, index_path)
        with open(documents_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        print(f"[VectorStore] Đã lưu thành công vào: {vector_store_dir}")

    def _load_index(self, index_path, documents_path):
        print("[VectorStore] Đang tải index và documents từ ổ đĩa...")
        self.index = faiss.read_index(index_path)
        with open(documents_path, 'r', encoding='utf-8') as f:
            self.documents = json.load(f)
        print(f"[VectorStore] Tải thành công {self.index.ntotal} vector từ cache.")

    def _build_or_load_index(self, config_paths):
        index_path = config_paths.get("vector_index_path")
        docs_path = config_paths.get("vector_documents_path")

        if index_path and docs_path and os.path.exists(index_path) and os.path.exists(docs_path):
            try:
                self._load_index(index_path, docs_path)
                return 
            except Exception as e:
                print(f"[CẢNH BÁO VectorStore] Lỗi khi tải index từ cache: {e}. Sẽ tiến hành xây dựng lại.")
        
        print("[VectorStore] Không tìm thấy cache. Bắt đầu xây dựng cơ sở dữ liệu vector mới...")
        self._load_and_process_sources(config_paths)

        if not self.documents:
            print("[CẢNH BÁO VectorStore] Không có tài liệu nào để index. Vui lòng kiểm tra đường dẫn file.")
            return

        print("[VectorStore] Bắt đầu tạo embeddings cho các tài liệu...")
        texts_to_embed = [doc['content'] for doc in self.documents]
        embeddings = self.model.encode(texts_to_embed, convert_to_tensor=False, show_progress_bar=True)
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings, dtype=np.float32))
        print(f"[VectorStore] Xây dựng thành công! Tổng cộng {self.index.ntotal} vector từ {len(self.documents)} đoạn tri thức đã được index.")

        if self.index and index_path and docs_path:
            self._save_index(index_path, docs_path)

    def retrieve(self, query: str, k: int = 3) -> str:
        if self.index is None:
            return "Lỗi: Cơ sở tri thức chưa được khởi tạo hoặc xây dựng thất bại."

        query_embedding = self.model.encode([query])
        
        distances, indices = self.index.search(np.array(query_embedding, dtype=np.float32), k)
        
        retrieved_docs_data = [self.documents[i] for i in indices[0]]
        retrieved_contents = [doc['content'] for doc in retrieved_docs_data]
        
        context = "\n---\n".join(retrieved_contents)
        
        print(f"[VectorStore] Đã truy xuất {len(retrieved_contents)} đoạn văn bản cho câu hỏi: '{query}'")
        return context
