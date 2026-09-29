from collections.abc import Iterable
from uuid import uuid4

from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    RawRecord,
    SourceKind,
)
from vbe_hub.normalization.adapters import CommunityNormalizer, MediaNormalizer
from vbe_hub.normalization.errors import NormalizationError

NORMALIZER_VERSION = "1.0.0"


class NormalizationService:
    def normalize_batch(self, records: Iterable[RawRecord]) -> list[NormalizedRecord]:
        results: list[NormalizedRecord] = []
        for record in records:
            try:
                adapter = (
                    MediaNormalizer()
                    if record.source_kind is SourceKind.MEDIA
                    else CommunityNormalizer()
                )
                normalized_data = adapter.normalize(record)
                status = NormalizationStatus(state=ProcessingState.SUCCEEDED)
            except NormalizationError as error:
                normalized_data = {}
                status = NormalizationStatus.failed(
                    code="invalid_field",
                    message=str(error),
                    retryable=False,
                )
            results.append(
                NormalizedRecord(
                    id=uuid4(),
                    raw_record_id=record.id,
                    normalizer_version=NORMALIZER_VERSION,
                    status=status,
                    normalized_data=normalized_data,
                )
            )
        return results
