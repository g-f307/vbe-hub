import sys
from uuid import UUID

from vbe_hub.synthetic import __main__ as command
from vbe_hub.synthetic.demo import DemoLoadResult


def test_demo_load_command_routes_to_the_canonical_loader(monkeypatch) -> None:
    calls: list[bool] = []

    async def fake_demo_load() -> DemoLoadResult:
        calls.append(True)
        return DemoLoadResult(created={"signals": 3}, signal_ids=())

    monkeypatch.setattr(command, "_demo_load", fake_demo_load, raising=False)
    monkeypatch.setattr(sys, "argv", ["vbe_hub.synthetic", "demo-load"])

    command.main()

    assert calls == [True]


def test_demo_populate_command_routes_to_the_expanded_individual_loader(monkeypatch) -> None:
    signal_ids = (UUID(int=1), UUID(int=2))
    calls: list[object] = []

    async def fake_demo_populate() -> DemoLoadResult:
        calls.append("loaded")
        return DemoLoadResult(created={"individual_signals": 2}, signal_ids=signal_ids)

    async def fake_enqueue(queued_signal_ids) -> int:
        calls.append(tuple(queued_signal_ids))
        return 2

    monkeypatch.setattr(command, "_demo_populate", fake_demo_populate, raising=False)
    monkeypatch.setattr(command, "_enqueue_demo_signals", fake_enqueue, raising=False)
    monkeypatch.setattr(sys, "argv", ["vbe_hub.synthetic", "demo-populate"])

    command.main()

    assert calls == ["loaded", signal_ids]
