import importlib


def test_root_returns_running_status():
    # Import the app module
    main = importlib.import_module("main")

    # Call the root handler directly (no network calls)
    data = main.root()

    assert isinstance(data, dict)
    assert data.get("status") == "running"
    assert "GatherUp AI - API Gateway" in data.get("service", "")
