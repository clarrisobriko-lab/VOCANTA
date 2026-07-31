from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class Job:
    company: str
    title: str
    location: str
    source: str
    url: str
    description: str = ""
    salary: str = ""
    employment_type: str = ""
    score: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "company", "title", "location", "source", "url",
            "description", "salary", "employment_type",
        ):
            value = getattr(self, field_name)
            if value is None:
                value = ""
            elif not isinstance(value, str):
                value = str(value)
            object.__setattr__(self, field_name, value.strip())
        object.__setattr__(self, "score", max(0, min(int(self.score), 100)))

    @property
    def is_valid(self) -> bool:
        return bool(self.company and self.title and self.source and self.url)

    def with_score(self, score: int) -> "Job":
        return replace(self, score=score)
