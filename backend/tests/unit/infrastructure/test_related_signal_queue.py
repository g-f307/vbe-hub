from uuid import UUID

from vbe_hub.infrastructure.related_queue import RelatedSignalJob, RelatedSignalQueue

SIGNAL = UUID("00000000-0000-0000-0000-000000000001")


class RedisDouble:
    def __init__(self):
        self.items = []
        self.ids = set()

    async def eval(self, script, numkeys, queue_key, dedupe_key, capacity, payload):
        if dedupe_key in self.ids:
            return 0
        if len(self.items) >= int(capacity):
            return -1
        self.ids.add(dedupe_key)
        self.items.append(payload)
        return 1

    async def blpop(self, key, timeout):
        if not self.items:
            return None
        return key.encode(), self.items.pop(0).encode()

    async def rpush(self, key, payload):
        self.items.append(payload)
        return len(self.items)

    async def delete(self, key):
        self.ids.discard(key)


async def test_queue_is_idempotent_and_returns_one_job() -> None:
    redis = RedisDouble()
    queue = RelatedSignalQueue(redis=redis, capacity=2, pop_timeout_seconds=1)

    assert await queue.enqueue(SIGNAL) is True
    assert await queue.enqueue(SIGNAL) is False
    assert await queue.pop() == RelatedSignalJob(signal_id=SIGNAL, attempt=1)


async def test_queue_rejects_new_work_when_capacity_is_reached() -> None:
    queue = RelatedSignalQueue(redis=RedisDouble(), capacity=1, pop_timeout_seconds=1)
    await queue.enqueue(SIGNAL)

    assert await queue.enqueue(UUID(int=2)) is False


async def test_retry_is_controlled_and_ack_releases_deduplication() -> None:
    redis = RedisDouble()
    queue = RelatedSignalQueue(redis=redis, capacity=2, pop_timeout_seconds=1, max_attempts=2)
    await queue.enqueue(SIGNAL)
    first = await queue.pop()

    assert first is not None
    assert await queue.retry(first) is True
    second = await queue.pop()
    assert second == RelatedSignalJob(signal_id=SIGNAL, attempt=2)
    assert await queue.retry(second) is False
    await queue.ack(second)
    assert await queue.enqueue(SIGNAL) is True
