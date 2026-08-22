from connectors.registry import get_connectors


def test_registry_includes_hidden_discovery_sources_after_production_ats():
    assert [connector.name for connector in get_connectors()] == [
        "Greenhouse",
        "Lever",
        "Ashby",
        "SmartRecruiters",
        "Workday",
        "HiddenRoles",
        "UnlistedRemote",
        "InclusivelyRemote",
        "RemoteRocketship",
        "Remotive",
        "WorkingNomads",
        "Jobspresso",
        "TaskFavour",
    ]
