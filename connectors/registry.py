from connectors.base import BaseConnector
from connectors.greenhouse import GreenhouseConnector


def get_connectors() -> list[BaseConnector]:
    """Return the production connector set.

    VOCANTA 3.3 is Greenhouse-only at ATS level, while Greenhouse discovery is
    employer-curated through the fail-closed employer registry.
    """
    return [GreenhouseConnector()]
