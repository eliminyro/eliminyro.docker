import docker
import pytest
import time
import os
from testinfra import get_host
from testinfra.utils.ansible_runner import AnsibleRunner

# Get testinfra host
hosts = AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


@pytest.fixture
def docker_client():
    """Docker client fixture for container operations"""
    client = docker.from_env()
    try:
        yield client
    finally:
        client.close()


def get_container(client, name):
    """Helper function to get container by name"""
    try:
        return client.containers.get(name)
    except docker.errors.NotFound:
        return None


def wait_for_container_ready(client, name, timeout=30):
    """Wait for container to be in running state"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        container = get_container(client, name)
        if container and container.status == 'running':
            return container
        time.sleep(1)
    return None


def get_container_env_dict(container):
    """Extract environment variables from container as dictionary"""
    env_vars = container.attrs['Config']['Env']
    env_dict = {}
    for env_var in env_vars:
        if '=' in env_var:
            key, value = env_var.split('=', 1)
            env_dict[key] = value
    return env_dict


@pytest.fixture
def expected_containers():
    """Fixture providing list of expected test containers"""
    return ['testapp', 'redis', 'postgres']


@pytest.fixture
def expected_volumes():
    """Fixture providing expected volume mappings"""
    return {
        '/tmp/testapp-data': '/data',
        '/tmp/testapp-logs': '/var/log/nginx',
        '/tmp/docker/testapp/nginx.conf': '/etc/nginx/nginx.conf'
    }


@pytest.fixture
def testnet_gateway():
    """Fixture providing testnet gateway IP for service connectivity tests"""
    return '172.25.0.1'


@pytest.fixture
def ansible_vars():
    """Fixture providing access to Ansible variables from the playbook"""
    # Get the testinfra host object
    host_name = hosts[0]
    host = get_host(f'ansible://{host_name}')

    # Use debug module to get all host variables
    result = host.ansible('debug', 'var=hostvars[inventory_hostname]')
    return result['hostvars[inventory_hostname]']
