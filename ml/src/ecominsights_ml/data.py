from csv import DictReader
from pathlib import Path

_here = Path(__file__).resolve()
_candidates = [
    _here.parents[2] / "data" / "sample_prices.csv",
    _here.parents[1] / "ml" / "data" / "sample_prices.csv",
    _here.parents[2] / "ml" / "data" / "sample_prices.csv",
]
SAMPLE_DATA_PATH = next((p for p in _candidates if p.is_file()), _candidates[0])


def load_sample_prices(path: Path | None = None) -> list[dict[str, str]]:
    """Load the local synthetic CSV. This function makes no network requests."""
    effective_path = path or SAMPLE_DATA_PATH
    with effective_path.open(newline="", encoding="utf-8") as csv_file:
        return list(DictReader(csv_file))
