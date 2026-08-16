import pytest

from follow_up_runtime import build_recipient_resolver, build_sender_from_environment, main, smtp_configured


def test_recipient_resolver_uses_published_role_mailbox():
    resolver=build_recipient_resolver(lambda url:'Apply now. Questions: careers@acme.com')
    assert resolver('Acme','https://jobs.acme.com/123')=='careers@acme.com'


def test_recipient_resolver_does_not_guess():
    resolver=build_recipient_resolver(lambda url:'Apply now')
    assert resolver('Acme','https://acme.com/jobs')==''


def test_sender_requires_runtime_secrets(monkeypatch):
    for key in ('VOCANTA_SMTP_HOST','VOCANTA_SMTP_USERNAME','VOCANTA_SMTP_PASSWORD'):
        monkeypatch.delenv(key,raising=False)
    assert smtp_configured() is False
    with pytest.raises(RuntimeError):
        build_sender_from_environment()


def test_scheduled_main_skips_safely_without_secrets(monkeypatch,capsys):
    for key in ('VOCANTA_SMTP_HOST','VOCANTA_SMTP_USERNAME','VOCANTA_SMTP_PASSWORD'):
        monkeypatch.delenv(key,raising=False)
    assert main()==0
    assert 'delivery skipped safely' in capsys.readouterr().out


def test_sender_loads_runtime_configuration(monkeypatch):
    monkeypatch.setenv('VOCANTA_SMTP_HOST','smtp.example.com')
    monkeypatch.setenv('VOCANTA_SMTP_USERNAME','candidate@example.com')
    monkeypatch.setenv('VOCANTA_SMTP_PASSWORD','secret')
    monkeypatch.setenv('VOCANTA_SMTP_PORT','')
    assert smtp_configured() is True
    sender=build_sender_from_environment()
    assert sender.host=='smtp.example.com'
    assert sender.port==587
    assert sender.username=='candidate@example.com'
