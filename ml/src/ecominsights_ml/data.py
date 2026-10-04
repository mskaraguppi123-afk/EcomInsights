from csv import DictReader
from pathlib import Path

SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_prices.csv"


def load_sample_prices(path: Path = SAMPLE_DATA_PATH) -> list[dict[str, str]]:
    """Load the local synthetic CSV. This function makes no network requests."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(DictReader(csv_file))
