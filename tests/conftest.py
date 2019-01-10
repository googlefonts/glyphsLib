import py
import pytest


@pytest.fixture
def datadir(request):
    return py.path.local(py.path.local(__file__).dirname).join("data")
