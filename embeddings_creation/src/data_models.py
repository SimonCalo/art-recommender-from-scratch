from dataclasses import dataclass


@dataclass
class EmbeddingData:
    id: str
    distance: float
    image_path: str
    embedding: list[float]