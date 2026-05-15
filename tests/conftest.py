from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

REGIONAL_FIXTURES = {
    "BayArea": FIXTURES / "bay_area_sample.html",
    "LosAngeles": FIXTURES / "los_angeles_sample.html",
}


@pytest.fixture
def bay_area_html() -> str:
    return REGIONAL_FIXTURES["BayArea"].read_text(encoding="utf-8")


@pytest.fixture(params=sorted(REGIONAL_FIXTURES))
def regional_html(request) -> tuple[str, str]:
    region = request.param
    html = REGIONAL_FIXTURES[region].read_text(encoding="utf-8")
    return region, html
