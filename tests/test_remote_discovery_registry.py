from connectors.registry import get_connectors


def test_remote_discovery_sources_are_enabled():
    names = [connector.name for connector in get_connectors()]
    for expected in (
        "HiddenRoles",
        "UnlistedRemote",
        "InclusivelyRemote",
        "RemoteRocketship",
        "Remotive",
        "WorkingNomads",
        "Jobspresso",
    ):
        assert expected in names


def test_production_ats_remain_first_in_registry():
    names = [connector.name for connector in get_connectors()]
    assert names[:5] == ["Greenhouse", "Lever", "Ashby", "SmartRecruiters", "Workday"]
