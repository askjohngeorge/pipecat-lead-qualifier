import json
from pathlib import Path
from .models import BotConfig


def load_config(config_path: str) -> BotConfig:
    """Load bot configuration from a JSON file.

    Args:
        config_path: Path to the configuration JSON file

    Returns:
        BotConfig: Loaded and validated configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        config_data = json.load(f)

    return BotConfig(**config_data)
