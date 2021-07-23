import py
import pytest


@pytest.fixture
def datadir(request):
    return py.path.local(py.path.local(__file__).dirname).join("data")


@pytest.fixture(scope="session", params=["defcon", "ufoLib2"])
def ufo_module(request):
    return pytest.importorskip(request.param)


# Provide a --run-regression-tests CLI option to run slow regression tests separately.
def pytest_addoption(parser):
    parser.addoption(
        "--run-regression-tests",
        action="store_true",
        help="Run (slow) regression tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "regression_test: mark test as a (slow) regression test"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-regression-tests"):
        # --run-regression-tests given in cli: do not skip slow tests
        return
    skip_regression_test = pytest.mark.skip(
        reason="need --run-regression-tests option to run"
    )
    for item in items:
        if "regression_test" in item.keywords:
            item.add_marker(skip_regression_test)
