

from logging import exception
import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingManager:

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print("Initializing embedding model...")
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Error loading model: {e}")

    def Get_embadding(self, texts) -> np.ndarray:
        if not self.model:
            raise ValueError("Model not loaded")
        embedding = self.model.encode(texts, show_progress_bar=True)
        return embedding


    
