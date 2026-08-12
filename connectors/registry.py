from connectors.base import BaseConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector


def get_connectors() -> list[BaseConnector]:
    """Return ATS connectors supported by the production application pipeline."""
    return [GreenhouseConnector(), LeverConnector()]
