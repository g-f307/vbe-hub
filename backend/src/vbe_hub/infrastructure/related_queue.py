from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

_ENQUEUE_SCRIPT = """
if redis.call('EXISTS', KEYS[2]) == 1 then return 0 end
if redis.call('LLEN', KEYS[1]) >= tonumber(ARGV[1]) then return -1 end
redis.call('SET', KEYS[2], '1')
redis.call('RPUSH', KEYS[1], ARGV[2])
return 1
"""


class RedisQueueClient(Protocol):
    async def eval(self, script: str, numkeys: int, *values: object) -> int: ...

    async def blpop(self, key: str, timeout: int) -> object: ...

    async def rpush(self, key: str, value: str) -> int: ...

    async def delete(self, key: str) -> int: ...


@dataclass(frozen=True, slots=True)
class RelatedSignalJob:
    signal_id: UUID
    attempt: int


class RelatedSignalQueue:
    def __init__(
        self,
        *,
        redis: RedisQueueClient,
        capacity: int,
        pop_timeout_seconds: int,
        max_attempts: int = 3,
        queue_key: str = "vbe:related-signals:v1",
    ) -> None:
        if capacity <= 0 or pop_timeout_seconds <= 0 or max_attempts <= 0:
            raise ValueError("queue limits must be positive")
        self._redis = redis
        self._capacity = capacity
        self._pop_timeout = pop_timeout_seconds
        self._max_attempts = max_attempts
        self._queue_key = queue_key

    async def enqueue(self, signal_id: UUID) -> bool:
        job = RelatedSignalJob(signal_id=signal_id, attempt=1)
        result = await self._redis.eval(
            _ENQUEUE_SCRIPT,
            2,
            self._queue_key,
            self._dedupe_key(signal_id),
            self._capacity,
            self._serialize(job),
        )
        return int(result) == 1

    async def pop(self) -> RelatedSignalJob | None:
        item = await self._redis.blpop(self._queue_key, timeout=self._pop_timeout)
        if item is None:
            return None
        payload = item[1]
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        parsed = json.loads(payload)
        return RelatedSignalJob(signal_id=UUID(parsed["signal_id"]), attempt=int(parsed["attempt"]))

    async def retry(self, job: RelatedSignalJob) -> bool:
        if job.attempt >= self._max_attempts:
            return False
        retried = RelatedSignalJob(job.signal_id, job.attempt + 1)
        await self._redis.rpush(self._queue_key, self._serialize(retried))
        return True

    async def ack(self, job: RelatedSignalJob) -> None:
        await self._redis.delete(self._dedupe_key(job.signal_id))

    def _dedupe_key(self, signal_id: UUID) -> str:
        return f"{self._queue_key}:pending:{signal_id}"

    @staticmethod
    def _serialize(job: RelatedSignalJob) -> str:
        return json.dumps(
            {"signal_id": str(job.signal_id), "attempt": job.attempt}, separators=(",", ":")
        )
