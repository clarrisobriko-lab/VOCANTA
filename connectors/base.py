from abc import ABC, abstractmethod
from collections.abc import Sequence
from core.models import Job


class BaseConnector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fetch_jobs(self) -> Sequence[Job]:
        raise NotImplementedError
