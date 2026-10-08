"""Generate the controlled synthetic daily demand dataset."""

from __future__ import annotations

from pathlib import Path

from experiments.common import ExperimentConfig, write_synthetic_dataset

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "synthetic_demand.csv"


def generate_dataset(
    output_path: Path = DATASET_PATH,
    config: ExperimentConfig | None = None,
) -> Path:
    """Generate and save the synthetic dataset with a fixed default seed."""
    write_synthetic_dataset(output_path, config or ExperimentConfig())
    return output_path


def main() -> None:
    """Generate the repository's reproducible synthetic demand CSV."""
    path = generate_dataset()
    print(f"Generated 730 synthetic daily observations: {path}")


if __name__ == "__main__":
    main()