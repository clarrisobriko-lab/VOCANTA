from connectors.ashby import AshbyConnector
from connectors.base import BaseConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.hidden_sources import HiddenRolesConnector, UnlistedRemoteConnector
from connectors.lever import LeverConnector
from connectors.remote_discovery_sources import InclusivelyRemoteConnector, JobspressoConnector, RemoteRocketshipConnector, WorkingNomadsConnector
from connectors.remotive import RemotiveConnector
from connectors.smartrecruiters import SmartRecruitersConnector
from connectors.taskfavour import TaskFavourConnector
from connectors.workday import WorkdayConnector


def get_connectors() -> list[BaseConnector]:
    """Return production ATS and guarded public discovery connectors."""
    return [
        GreenhouseConnector(),
        LeverConnector(),
        AshbyConnector(),
        SmartRecruitersConnector(),
        WorkdayConnector(),
        HiddenRolesConnector(),
        UnlistedRemoteConnector(),
        InclusivelyRemoteConnector(),
        RemoteRocketshipConnector(),
        RemotiveConnector(),
        WorkingNomadsConnector(),
        JobspressoConnector(),
        TaskFavourConnector(),
    ]
