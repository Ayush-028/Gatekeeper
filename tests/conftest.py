import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """No test should ever touch the network."""
    monkeypatch.delenv("GATEKEEPER_L3_URL", raising=False)
    monkeypatch.delenv("GATEKEEPER_LAYER3", raising=False)
    import gatekeeper.layer3 as l3
    monkeypatch.setattr(l3, "_notice_shown", False)
