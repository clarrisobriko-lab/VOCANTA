from automation.evidence_manifest import build_evidence_manifest, grounded_keywords
from core.models import Job


def _job(description: str) -> Job:
    return Job(company="Example", title="Executive Assistant", description=description, country="Remote", source="test", url="https://example.com/job")


def test_manifest_maps_supported_and_missing_requirements():
    manifest = build_evidence_manifest(_job("Executive support, calendar management, Salesforce and recruitment"))
    supported = {item.requirement for item in manifest.supported}
    unsupported = {item.requirement for item in manifest.unsupported}
    assert "executive support" in supported
    assert "calendar management" in supported
    assert "recruitment" in supported
    assert "salesforce" in unsupported
    assert manifest.precision == 1.0
    assert 0 < manifest.coverage < 1


def test_grounded_keywords_never_include_unsupported_requirement():
    keywords = grounded_keywords(_job("Recruitment, onboarding and Salesforce"))
    assert "recruitment" in keywords
    assert "onboarding" in keywords
    assert "salesforce" not in keywords


def test_empty_requirement_set_is_not_penalised():
    manifest = build_evidence_manifest(_job("A role with no recognised semantic requirements."))
    assert manifest.requirements == ()
    assert manifest.coverage == 1.0
    assert manifest.precision == 1.0
