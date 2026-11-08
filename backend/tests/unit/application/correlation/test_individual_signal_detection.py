from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from vbe_hub.application.correlation.detection import IndividualSignalDetectionService

NOW = datetime(2026, 11, 8, 12, tzinfo=UTC)
NORMALIZED = UUID(int=1)
SIGNAL = UUID(int=2)


class Repository:
    async def get_or_create_signal(self, normalized_record_id, contract_version, created_at):
        assert (normalized_record_id, contract_version, created_at) == (
            NORMALIZED,
            "individual-signal-v1",
            NOW,
        )
        return SimpleNamespace(id=SIGNAL, normalized_record_id=NORMALIZED)


class Queue:
    def __init__(self):
        self.ids = []

    async def enqueue(self, signal_id):
        self.ids.append(signal_id)
        return True


async def test_detection_persists_individual_signal_and_schedules_precomputation() -> None:
    queue = Queue()
    service = IndividualSignalDetectionService(repository=Repository(), queue=queue)

    detected = await service.detect(NORMALIZED, detected_at=NOW)

    assert detected.id == SIGNAL
    assert queue.ids == [SIGNAL]
