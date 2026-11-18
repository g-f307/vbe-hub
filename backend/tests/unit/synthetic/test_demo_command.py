import sys

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
    calls: list[bool] = []

    async def fake_demo_populate() -> DemoLoadResult:
        calls.append(True)
        return DemoLoadResult(created={"individual_signals": 40}, signal_ids=())

    monkeypatch.setattr(command, "_demo_populate", fake_demo_populate, raising=False)
    monkeypatch.setattr(sys, "argv", ["vbe_hub.synthetic", "demo-populate"])

    command.main()

    assert calls == [True]
