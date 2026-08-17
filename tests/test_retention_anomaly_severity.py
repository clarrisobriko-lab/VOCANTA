from analytics import retention_anomaly_severity


def test_retention_anomaly_severity_levels():
    assert retention_anomaly_severity(10,10,2) == 'normal'
    assert retention_anomaly_severity(16,10,2) == 'elevated'
    assert retention_anomaly_severity(18,10,2) == 'high'
    assert retention_anomaly_severity(22,10,2) == 'critical'


def test_retention_anomaly_severity_handles_zero_deviation():
    assert retention_anomaly_severity(11,10,0) == 'critical'
    assert retention_anomaly_severity(10,10,0) == 'normal'


def test_retention_anomaly_severity_reports_warming_without_history():
    assert retention_anomaly_severity(100,10,2,enough_history=False) == 'warming'
