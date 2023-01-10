import getpass

import pytest

from statbank import StatbankClient


@pytest.mark.integration_dapla
@pytest.fixture(scope="module", autouse=True)
def client():
    user = getpass.getpass("Lastebruker: ")
    return StatbankClient(user)


@pytest.mark.integration_dapla
def test_client_date(client):
    assert isinstance(client.approve, int)


@pytest.mark.integration_dapla
def test_client_get_descripiton(client):
    filbesk = client.get_description("05300")
    assert len(filbesk.codelists)
