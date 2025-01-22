import json
from pathlib import Path
from typing import Dict
from .models import BotConfig, FlowConfig, FlowNodeConfig


def validate_flow_config(flow_config: FlowConfig) -> None:
    """Validate flow configuration.

    Args:
        flow_config: Flow configuration to validate

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate initial node exists
    if flow_config.initial_node not in flow_config.nodes:
        raise ValueError(
            f"Initial node '{flow_config.initial_node}' not found in nodes"
        )

    # Validate node transitions
    for node_name, node in flow_config.nodes.items():
        if node.functions:
            for func in node.functions:
                if func["type"] == "transition":
                    target = func["function"]["transition_to"]
                    if target not in flow_config.nodes:
                        raise ValueError(
                            f"Invalid transition target '{target}' in node '{node_name}'"
                        )


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

    config = BotConfig(**config_data)

    # Validate flow configuration if present
    if config.flow_config:
        validate_flow_config(config.flow_config)

    return config
