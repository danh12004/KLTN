import faiss
import numpy as np
import json
import re
import os
from sentence_transformers import SentenceTransformer
from src.logging.logger import logger

class VectorStoreService:
    """
    Dịch vụ quản lý nhiều kho vector tri thức chuyên biệt.
    Mỗi kho được tải hoặc xây dựng một cách linh hoạt khi được yêu cầu lần đầu tiên (lazy loading).
    """
    def __init__(self, config):
        logger.info("Khởi tạo VectorStoreService (Manager)...")
        self.config = config
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self._stores = {} 

    def _get_store_paths(self, store_name: str):
        """Tạo đường dẫn file động cho một kho tri thức cụ thể."""
        base_dir = self.config.VECTOR_STORE_DIR
        index_path = os.path.join(base_dir, f"faiss_index_{store_name}.bin")
        docs_path = os.path.join(base_dir, f"documents_{store_name}.json")
        return index_path, docs_path

    def _build_store(self, store_name: str):
        """Xây dựng một kho vector mới từ các nguồn dữ liệu được cấu hình."""
        logger.info(f"Không tìm thấy cache cho kho '{store_name}'. Bắt đầu xây dựng mới...")
        
        sources_config = self.config.KNOWLEDGE_SOURCES.get(store_name)
        if not sources_config:
            logger.error(f"Không tìm thấy cấu hình nguồn tri thức cho kho '{store_name}'.")
            return None

        documents = self._load_and_process_sources(sources_config)
        if not documents:
            logger.warning(f"Không có tài liệu nào để index cho kho '{store_name}'.")
            return None

        logger.info(f"Bắt đầu tạo embeddings cho {len(documents)} tài liệu của kho '{store_name}'...")
        texts_to_embed = [doc['content'] for doc in documents]
        embeddings = self.model.encode(texts_to_embed, convert_to_tensor=False, show_progress_bar=True)
        
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings, dtype=np.float32))
        logger.info(f"Xây dựng kho '{store_name}' thành công! Tổng cộng {index.ntotal} vector.")

        index_path, docs_path = self._get_store_paths(store_name)
        self._save_index(index, documents, index_path, docs_path)

        return {"index": index, "documents": documents}

    def get_store(self, store_name: str):
        """
        Lấy một kho tri thức cụ thể. Tải từ cache nếu có, nếu không thì xây dựng mới.
        """
        if store_name in self._stores:
            return self._stores[store_name]

        index_path, docs_path = self._get_store_paths(store_name)

        if os.path.exists(index_path) and os.path.exists(docs_path):
            try:
                logger.info(f"Đang tải kho '{store_name}' từ cache...")
                index = faiss.read_index(index_path)
                with open(docs_path, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                logger.info(f"Tải thành công kho '{store_name}' với {index.ntotal} vector.")
                
                store_instance = {"index": index, "documents": documents}
                self._stores[store_name] = store_instance
                return store_instance
            except Exception as e:
                logger.warning(f"Lỗi khi tải kho '{store_name}' từ cache: {e}. Sẽ xây dựng lại.")

        store_instance = self._build_store(store_name)
        if store_instance:
            self._stores[store_name] = store_instance
        return store_instance
    
    def retrieve(self, store_name: str, query: str, k: int = 5) -> str:
        """Thực hiện truy vấn trên một kho tri thức chuyên biệt."""
        store = self.get_store(store_name)
        if not store or store.get("index") is None:
            logger.error(f"Truy vấn thất bại: Kho tri thức '{store_name}' chưa được khởi tạo.")
            return f"Lỗi: Cơ sở tri thức '{store_name}' không khả dụng."

        index = store["index"]
        documents = store["documents"]
        
        query_embedding = self.model.encode([query])
        
        try:
            _, indices = index.search(np.array(query_embedding, dtype=np.float32), k)
            retrieved_docs = [documents[i] for i in indices[0]]
            context = "\n---\n".join([doc['content'] for doc in retrieved_docs])
            
            logger.info(f"Đã truy xuất {len(retrieved_docs)} đoạn văn bản từ kho '{store_name}' cho câu hỏi: '{query[:50]}...'")
            return context
        except Exception as e:
            logger.error(f"Lỗi trong quá trình truy xuất từ kho '{store_name}': {e}")
            return "Lỗi: Đã xảy ra sự cố khi tìm kiếm thông tin."

    def _save_index(self, index, documents, index_path, docs_path):
        logger.info(f"Đang lưu index và documents vào: {os.path.dirname(index_path)}")
        try:
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            faiss.write_index(index, index_path)
            with open(docs_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi khi lưu vector store: {e}")

    def _load_and_process_sources(self, sources_config):
        all_documents = []
        for source_info in sources_config:
            path = source_info["path"]
            if not os.path.exists(path):
                logger.warning(f"Không tìm thấy file nguồn: {path}")
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    source_type = source_info["type"]
                    metadata = source_info.get("metadata", {})
                    if source_type == "json":
                        data = json.load(f)
                        for key, value in data.items():
                            content = self._flatten_json_to_text(value, f"{metadata.get('topic', '')} {key}".strip())
                            for chunk in self._chunk_text(content):
                                doc = {"content": chunk, "source": os.path.basename(path), **metadata}
                                if "sub_topic_key" in metadata:
                                    doc[metadata["sub_topic_key"]] = key
                                all_documents.append(doc)
                    elif source_type == "txt":
                        text_content = f.read()
                        for chunk in self._chunk_text(text_content):
                            all_documents.append({"content": chunk, "source": os.path.basename(path), **metadata})
                logger.info(f"Đã xử lý thành công nguồn: {source_info['id']}")
            except Exception as e:
                logger.error(f"Không thể xử lý file {path}: {e}")
        return all_documents

    def _chunk_text(self, text, chunk_size=1000, overlap=200):
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
                text_parts.append(self._flatten_json_to_text(value, f"{prefix} {key}".strip().replace("_", " ")))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                text_parts.append(self._flatten_json_to_text(item, f"{prefix} mục {i + 1}".strip()))
        else:
            return f"{prefix}: {data}."
        return " ".join(filter(None, text_parts))

