import py
import pytest


@pytest.fixture
def datadir(request):
    return py.path.local(py.path.local(__file__).dirname).join("data")


@pytest.fixture(scope="session", params=["defcon", "ufoLib2"])
def ufo_module(request):
    return pytest.importorskip(request.param)
