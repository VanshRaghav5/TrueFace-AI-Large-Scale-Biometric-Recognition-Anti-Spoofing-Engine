import json
import os
from typing import Dict, Optional

class IdentityMapping:
    """Manages mapping between vector store integer offsets and pseudonymous subject IDs."""

    def __init__(self, mapping_file: Optional[str] = None):
        self.mapping_file = mapping_file
        self._index_to_subject: Dict[int, str] = {}
        self._subject_to_index: Dict[str, int] = {}
        if mapping_file and os.path.exists(mapping_file):
            self.load(mapping_file)

    def register(self, index_id: int, subject_id: str):
        self._index_to_subject[index_id] = subject_id
        self._subject_to_index[subject_id] = index_id

    def get_subject_id(self, index_id: int) -> Optional[str]:
        return self._index_to_subject.get(index_id)

    def get_index_id(self, subject_id: str) -> Optional[int]:
        return self._subject_to_index.get(subject_id)

    def remove(self, subject_id: str):
        if subject_id in self._subject_to_index:
            idx = self._subject_to_index.pop(subject_id)
            self._index_to_subject.pop(idx, None)

    def save(self, file_path: str):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in self._index_to_subject.items()}, f, indent=2)

    def load(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._index_to_subject = {int(k): v for k, v in data.items()}
            self._subject_to_index = {v: int(k) for k, v in data.items()}

