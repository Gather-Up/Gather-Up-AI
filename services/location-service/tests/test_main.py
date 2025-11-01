import importlib


def test_root_endpoint():
    main = importlib.import_module("main")
    data = main.root()
    assert isinstance(data, dict)
    assert data.get("status") == "running"
    assert "GatherUp AI - Location Service" in data.get("service", "")


def test_health_check():
    main = importlib.import_module("main")
    data = main.health_check()
    assert isinstance(data, dict)
    assert data.get("status") == "healthy"
    assert data.get("service") == "location-service"
