from models import Event


def test_an_event_is_always_physical_and_cannot_be_digital():
    assert Event().isDigital is False
