from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_version: str = Field(min_length=1)
    dataset_sha256: str
    split: Literal["calibration", "evaluation"]
    seed: int
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    normalizer_version: str = Field(min_length=1)

    def model_post_init(self, __context: object) -> None:
        if not _SHA256.fullmatch(self.dataset_sha256):
            raise ValueError("dataset_sha256 must be a lowercase SHA-256 digest")

    @property
    def identity(self) -> str:
        canonical = json.dumps(
            self.model_dump(), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode()
        return hashlib.sha256(canonical).hexdigest()[:16]
