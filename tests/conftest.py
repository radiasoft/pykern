import pytest


@pytest.fixture(scope="function")
def pkconfig_setup(monkeypatch):
    import py.path
    import sys

    def res(cfg=None, env=None):
        # Can't import anything yet
        data_dir = py.path.local(__file__).dirpath("pkconfig_data")
        for k, v in (env or {}).items():
            monkeypatch.setenv(k, v)
        if data_dir not in sys.path:
            sys.path.insert(0, str(data_dir))
        from pykern import pkconfig

        pkconfig.reset_state_for_testing(add_to_environ=cfg)
        return pkconfig

    return res
