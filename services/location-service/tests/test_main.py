import os
import importlib.util


def _load_main_from_path():
    here = os.path.dirname(__file__)
    service_dir = os.path.abspath(os.path.join(here, os.pardir))
    main_path = os.path.join(service_dir, "main.py")
    spec = importlib.util.spec_from_file_location("service_main", main_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module) 
    return module


def test_root_endpoint():
    main = _load_main_from_path()
    data = main.root()
    assert isinstance(data, dict)
    assert data.get("status") == "running"
    assert "GatherUp AI - Location Service" in data.get("service", "")


def test_health_check():
    main = _load_main_from_path()
    data = main.health_check()
    assert isinstance(data, dict)
    assert data.get("status") == "healthy"
    assert data.get("service") == "location-service"
