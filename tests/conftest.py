from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def bay_area_html() -> str:
    return (FIXTURES / "bay_area_sample.html").read_text(encoding="utf-8")
