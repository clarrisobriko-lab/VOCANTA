from connectors.ashby import AshbyConnector
from connectors.base import BaseConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.smartrecruiters import SmartRecruitersConnector
from connectors.workday import WorkdayConnector


def get_connectors() -> list[BaseConnector]:
    """Return ATS connectors supported by the production application pipeline."""
    return [
        GreenhouseConnector(),
        LeverConnector(),
        AshbyConnector(),
        SmartRecruitersConnector(),
        WorkdayConnector(),
    ]
