import backend


def test_package_importable() -> None:
    assert backend is not None
