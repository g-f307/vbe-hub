import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CorrelationExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    dataset_version: str = Field(min_length=1)
    dataset_sha256: str
    split: Literal["calibration", "evaluation"]
    seed: int
    commit: str = Field(min_length=1)
    normalizer_version: str = Field(min_length=1)
    extraction_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    representation_version: str = Field(min_length=1)
    relation_model: str = Field(min_length=1)
    relation_prompt_version: str = Field(min_length=1)
    max_neighbors: int = Field(gt=0)
    temporal_window_days: int = Field(ge=0)
    geographic_level: Literal["country", "state", "municipality", "district"]
    minimum_semantic_score: float = Field(ge=0, le=1)
    minimum_total_score: float = Field(ge=0, le=1)

    def model_post_init(self, __context: object) -> None:
        if not _SHA256.fullmatch(self.dataset_sha256):
            raise ValueError("dataset_sha256 must be a lowercase SHA-256 digest")

    @property
    def identity(self) -> str:
        canonical = json.dumps(self.model_dump(), separators=(",", ":"), sort_keys=True).encode()
        return hashlib.sha256(canonical).hexdigest()[:16]
