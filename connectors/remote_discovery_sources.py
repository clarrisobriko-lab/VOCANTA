from connectors.hidden_sources import PublicHiddenSourceConnector


class InclusivelyRemoteConnector(PublicHiddenSourceConnector):
    source_name = "InclusivelyRemote"
    source_url = "https://inclusivelyremote.com/"


class RemoteRocketshipConnector(PublicHiddenSourceConnector):
    source_name = "RemoteRocketship"
    source_url = "https://www.remoterocketship.com/"


class WorkingNomadsConnector(PublicHiddenSourceConnector):
    source_name = "WorkingNomads"
    source_url = "https://www.workingnomads.com/jobs"


class JobspressoConnector(PublicHiddenSourceConnector):
    source_name = "Jobspresso"
    source_url = "https://jobspresso.co/remote-work/"
