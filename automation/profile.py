import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import shutil

from config.settings import (
    APPLICANT_PROFILE_FILE,
    ASSETS_DIR,
    EXECUTIVE_ASSISTANT_CERTIFICATE_FILE,
    MASTER_COVER_LETTER_FILE,
    MASTER_CV_FILE,
    PACKAGED_EXECUTIVE_ASSISTANT_CERTIFICATE_FILE,
    PACKAGED_MASTER_COVER_LETTER_FILE,
    PACKAGED_MASTER_CV_FILE,
)


@dataclass(frozen=True, slots=True)
class EducationRecord:
    institution: str = "University of Uyo"
    degree: str = "Bachelor of Laws (LLB)"
    discipline: str = "Law"
    graduation_year: str = "2020"
    country: str = "Nigeria"


@dataclass(frozen=True, slots=True)
class EmploymentRecord:
    title: str
    employer: str = ""
    start_year: str = ""
    end_year: str = ""
    current: bool = False
    summary: str = ""


@dataclass(frozen=True, slots=True)
class ApplicantProfile:
    first_name: str
    middle_name: str
    last_name: str
    email: str
    phone: str
    city: str
    country: str
    address: str
    postal_code: str
    linkedin_url: str
    website_url: str
    work_authorization: str
    requires_sponsorship: bool
    notice_period: str
    salary_expectation: str
    nationality: str = "Nigerian"
    region: str = "Africa"
    current_location: str = "Abuja, Nigeria"
    open_to_relocation: bool = True
    remote_preference: str = "Remote preferred"
    preferred_countries: tuple[str, ...] = (
        "United Kingdom", "Ireland", "Portugal", "Estonia", "Latvia", "Lithuania"
    )
    travel_commitment: str = "Yes"
    number_of_employers: str = "4"
    highest_education: EducationRecord = field(default_factory=EducationRecord)
    employment_history: tuple[EmploymentRecord, ...] = (
        EmploymentRecord("Human Resources Manager", current=True),
        EmploymentRecord("Legal Officer"),
        EmploymentRecord("Legal Associate"),
        EmploymentRecord("Executive and administrative support"),
    )
    standard_answers: dict[str, str] = field(default_factory=dict)
    demographics: dict[str, str] = field(default_factory=dict)
    auto_fill_demographics: bool = False
    privacy_acknowledgements: bool = True
    resume_path: str = str(MASTER_CV_FILE)
    cover_letter_path: str = str(MASTER_COVER_LETTER_FILE)
    supporting_document_path: str = str(EXECUTIVE_ASSISTANT_CERTIFICATE_FILE)

    @property
    def full_name(self) -> str:
        return " ".join(part.strip() for part in (self.first_name, self.middle_name, self.last_name) if part.strip())

    @property
    def employer_last_name(self) -> str:
        return " ".join(part.strip() for part in (self.middle_name, self.last_name) if part.strip())

    def validate(self) -> list[str]:
        errors: list[str] = []
        for key, value in {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "country": self.country,
            "nationality": self.nationality,
        }.items():
            if not str(value).strip():
                errors.append(f"Missing required profile field: {key}")
        if "@" not in self.email:
            errors.append("Email address is invalid")
        if not self.highest_education.institution or not self.highest_education.degree:
            errors.append("Highest education record is incomplete")
        for label, value in (
            ("Resume", self.resume_path),
            ("Cover letter", self.cover_letter_path),
            ("Supporting document", self.supporting_document_path),
        ):
            if value and not Path(value).expanduser().is_file():
                errors.append(f"{label} file not found: {Path(value).expanduser()}")
        return errors


def _profile_payload(profile: ApplicantProfile) -> dict:
    payload = asdict(profile)
    payload["preferred_countries"] = list(profile.preferred_countries)
    payload["employment_history"] = [asdict(item) for item in profile.employment_history]
    payload["highest_education"] = asdict(profile.highest_education)
    return payload


def save_profile(profile: ApplicantProfile, path: Path = APPLICANT_PROFILE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_profile_payload(profile), indent=2, ensure_ascii=False), encoding="utf-8")


def _copy_if_missing(source: Path, destination: Path) -> None:
    if destination.is_file() or not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def ensure_persistent_assets() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    _copy_if_missing(PACKAGED_MASTER_CV_FILE, MASTER_CV_FILE)
    _copy_if_missing(PACKAGED_MASTER_COVER_LETTER_FILE, MASTER_COVER_LETTER_FILE)
    _copy_if_missing(PACKAGED_EXECUTIVE_ASSISTANT_CERTIFICATE_FILE, EXECUTIVE_ASSISTANT_CERTIFICATE_FILE)


def _legacy_profile_candidates() -> list[Path]:
    downloads = Path.home() / "Downloads"
    candidates: list[Path] = []
    for pattern in ("VOCANTA_v*", "VOCANTA*"):
        for folder in downloads.glob(pattern):
            candidates.extend([folder / "data" / "applicant_profile.json", folder / folder.name / "data" / "applicant_profile.json"])
    return candidates


def _bootstrap_approved_profile(path: Path) -> None:
    save_profile(ApplicantProfile(
        first_name="Clarris", middle_name="Phegor", last_name="Obriko",
        email="Clarrisobriko@gmail.com", phone="+2348055632432",
        city="Abuja", country="Nigeria", address="20 IW Osisiogwu Crescent, Utako",
        postal_code="900108",
        linkedin_url="https://www.linkedin.com/in/phegor-clarris-obriko-880b81104",
        website_url="", work_authorization="No, I require employer sponsorship",
        requires_sponsorship=True, notice_period="Immediately available", salary_expectation="",
    ), path)


def _repair_asset_paths(profile: ApplicantProfile) -> ApplicantProfile:
    replacements = {
        "resume_path": MASTER_CV_FILE,
        "cover_letter_path": MASTER_COVER_LETTER_FILE,
        "supporting_document_path": EXECUTIVE_ASSISTANT_CERTIFICATE_FILE,
    }
    updates: dict[str, str] = {}
    for field_name, persistent_path in replacements.items():
        current = Path(getattr(profile, field_name) or "").expanduser()
        if not current.is_file() and persistent_path.is_file():
            updates[field_name] = str(persistent_path)
    return replace(profile, **updates) if updates else profile


def _coerce_profile(data: dict) -> ApplicantProfile:
    data = dict(data)
    defaults = ApplicantProfile(
        first_name="", middle_name="", last_name="", email="", phone="", city="", country="Nigeria",
        address="", postal_code="", linkedin_url="", website_url="",
        work_authorization="No, I require employer sponsorship", requires_sponsorship=True,
        notice_period="Immediately available", salary_expectation="",
    )
    for key, value in _profile_payload(defaults).items():
        data.setdefault(key, value)
    data["preferred_countries"] = tuple(data.get("preferred_countries") or ())
    data["highest_education"] = EducationRecord(**(data.get("highest_education") or {}))
    data["employment_history"] = tuple(EmploymentRecord(**item) for item in (data.get("employment_history") or ()))
    return ApplicantProfile(**data)


def load_profile(path: Path = APPLICANT_PROFILE_FILE) -> ApplicantProfile:
    ensure_persistent_assets()
    if not path.is_file():
        for candidate in _legacy_profile_candidates():
            if candidate.is_file():
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, path)
                break
    if not path.is_file():
        _bootstrap_approved_profile(path)
    profile = _repair_asset_paths(_coerce_profile(json.loads(path.read_text(encoding="utf-8"))))
    save_profile(profile, path)
    errors = profile.validate()
    if errors:
        raise ValueError("\n".join(errors))
    return profile
