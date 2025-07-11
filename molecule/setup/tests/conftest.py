import docker
import pytest
import json
from testinfra.utils.ansible_runner import AnsibleRunner
from testinfra import get_host
import os

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


@pytest.fixture
def ansible_vars():
    """Fixture providing access to Ansible variables from the playbook"""
    host_name = hosts[0]
    host = get_host(f'ansible://{host_name}')

    # Use debug module to get all host variables
    result = host.ansible('debug', 'var=hostvars[inventory_hostname]')
    return result['hostvars[inventory_hostname]']


@pytest.fixture
def tls_cert_paths():
    """Fixture providing TLS certificate file paths"""
    return {
        'ca_cert': '/etc/docker/certs/ca.pem',
        'server_cert': '/etc/docker/certs/server.pem',
        'server_key': '/etc/docker/certs/server-key.pem',
        'certs_dir': '/etc/docker/certs'
    }


@pytest.fixture
def docker_config_paths():
    """Fixture providing Docker configuration file paths"""
    return {
        'daemon_json': '/etc/docker/daemon.json',
        'systemd_override_dir': '/etc/systemd/system/docker.service.d',
        'systemd_override_file': '/etc/systemd/system/docker.service.d/override.conf'
    }


def get_docker_networks(client):
    """Helper function to get Docker networks as a dict"""
    networks = client.networks.list()
    return {net.name: net for net in networks}


def parse_daemon_json(content):
    """Helper function to parse Docker daemon.json content"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None
