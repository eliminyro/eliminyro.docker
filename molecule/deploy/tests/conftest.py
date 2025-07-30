import docker
import pytest

@pytest.fixture
def docker_client():
    client = docker.from_env()
    try:
        yield client
    finally:
        client.close()
