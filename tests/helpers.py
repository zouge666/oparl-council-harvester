import json
from pathlib import Path

SQL_DIR = str(Path(__file__).parent.parent / "sql")
FIXTURES = Path(__file__).parent / "fixtures"

SYSTEM_URL = "https://oparl.example.test/system"
BODIES_URL = "https://oparl.example.test/bodies"
PAPERS_URL = "https://oparl.example.test/bodies/0001/papers"
PAGE_1_URL = PAPERS_URL + "?limit=10"
PAGE_2_URL = PAPERS_URL + "?page=2&limit=10"


def load_fixture(name):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)
