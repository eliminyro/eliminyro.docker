import pytest
import docker
from conftest import get_container


class TestEnhancedContainerFeatures:
    """Test suite for enhanced container features - legacy tests moved to consolidated files"""

    def test_postgres_container_configuration(self, docker_client):
        """Test PostgreSQL container specific configuration"""
        client = docker_client
        container = get_container(client, 'postgres')
        assert container is not None

        # Check image
        image_tags = container.image.tags
        assert any(
            'postgres' in tag for tag in image_tags), f"Expected postgres image, got: {image_tags}"

        # Check environment variables
        env_vars = container.attrs['Config']['Env']
        env_dict = {}
        for env_var in env_vars:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                env_dict[key] = value

        assert 'POSTGRES_DB' in env_dict, "POSTGRES_DB environment variable not set"
        assert env_dict['POSTGRES_DB'] == 'testdb', "POSTGRES_DB has incorrect value"
        assert 'POSTGRES_USER' in env_dict, "POSTGRES_USER environment variable not set"
        assert env_dict['POSTGRES_USER'] == 'testuser', "POSTGRES_USER has incorrect value"

        # Check ports
        port_bindings = container.attrs['HostConfig']['PortBindings']
        assert '5432/tcp' in port_bindings, "PostgreSQL port 5432/tcp not bound"
        assert port_bindings['5432/tcp'][0]['HostPort'] == '5432', "PostgreSQL port not mapped correctly"


class TestContainerLabels:
    """Test suite for container labels"""

    def test_main_container_labels(self, docker_client):
        """Test that main container has correct labels"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None

        labels = container.attrs['Config']['Labels'] or {}

        assert 'app' in labels, "App label not found"
        assert labels['app'] == 'testapp', f"App label incorrect: {labels['app']}"
        assert 'environment' in labels, "Environment label not found"
        assert labels[
            'environment'] == 'test', f"Environment label incorrect: {labels['environment']}"
        assert 'version' in labels, "Version label not found"
        assert labels['version'] == '1.0', f"Version label incorrect: {labels['version']}"

    def test_dependency_container_labels(self, docker_client):
        """Test that dependency containers have correct labels"""
        client = docker_client

        # Test Redis labels
        redis = get_container(client, 'redis')
        assert redis is not None
        redis_labels = redis.attrs['Config']['Labels'] or {}
        assert 'app' in redis_labels, "Redis app label not found"
        assert redis_labels['app'] == 'redis', f"Redis app label incorrect: {redis_labels['app']}"
        assert 'environment' in redis_labels, "Redis environment label not found"
        assert redis_labels[
            'environment'] == 'test', f"Redis environment label incorrect: {redis_labels['environment']}"

        # Test PostgreSQL labels
        postgres = get_container(client, 'postgres')
        assert postgres is not None
        postgres_labels = postgres.attrs['Config']['Labels'] or {}
        assert 'app' in postgres_labels, "PostgreSQL app label not found"
        assert postgres_labels[
            'app'] == 'postgres', f"PostgreSQL app label incorrect: {postgres_labels['app']}"
        assert 'environment' in postgres_labels, "PostgreSQL environment label not found"
        assert postgres_labels[
            'environment'] == 'test', f"PostgreSQL environment label incorrect: {postgres_labels['environment']}"


class TestContainerEnvironmentVariables:
    """Test suite for container environment variables"""

    def test_main_container_environment_variables(self, docker_client):
        """Test that main container has correct environment variables"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None

        env_vars = container.attrs['Config']['Env']
        env_dict = {}
        for env_var in env_vars:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                env_dict[key] = value

        assert 'TEST_ENV_VAR' in env_dict, "TEST_ENV_VAR environment variable not set"
        assert env_dict[
            'TEST_ENV_VAR'] == 'molecule-test-value', f"TEST_ENV_VAR has incorrect value: {env_dict['TEST_ENV_VAR']}"


class TestContainerNetworking:
    """Test suite for container networking"""

    def test_containers_on_custom_network(self, docker_client):
        """Test that containers are connected to custom network"""
        client = docker_client

        # Check if the custom network exists
        try:
            network = client.networks.get('testnet')
        except docker.errors.NotFound:
            pytest.fail("Custom network 'testnet' not found")

        # Verify network configuration
        assert network.attrs['Driver'] == 'bridge', "Network driver is not bridge"

        # Check if containers are connected to the network
        container = get_container(client, 'testapp')
        assert container is not None

        networks = container.attrs['NetworkSettings']['Networks']
        assert 'testnet' in networks, "Container not connected to testnet"


class TestVolumeManagement:
    """Test suite for volume management and directory creation"""

    def test_additional_volumes_mounted(self, docker_client):
        """Test that additional volumes are properly mounted"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None

        mounts = container.attrs['Mounts']
        mount_destinations = [m['Destination'] for m in mounts]

        # Check for the additional log volume
        assert '/var/log/nginx' in mount_destinations, "Nginx log volume not mounted"

        # Verify the log volume source
        log_mount = next(
            (m for m in mounts if m['Destination'] == '/var/log/nginx'), None)
        assert log_mount is not None
        assert log_mount['Source'] == '/tmp/testapp-logs', "Log volume source path incorrect"

    def test_custom_directories_created(self, host):
        """Test that custom directories specified in testapp_create_dirs are created"""
        # Check for directories specified in testapp_create_dirs
        extra_dir = host.file("/tmp/testapp-extra")
        assert extra_dir.exists, "Custom directory /tmp/testapp-extra not created"
        assert extra_dir.is_directory, "/tmp/testapp-extra is not a directory"

        custom_dir = host.file("/tmp/testapp-custom")
        assert custom_dir.exists, "Custom directory /tmp/testapp-custom not created"
        assert custom_dir.is_directory, "/tmp/testapp-custom is not a directory"

    def test_dependency_volumes_created(self, host):
        """Test that dependency container volumes are properly created"""
        # Check Redis data directory
        redis_data_dir = host.file("/tmp/redis-data")
        assert redis_data_dir.exists, "Redis data directory not created"
        assert redis_data_dir.is_directory, "Redis data path is not a directory"

        # Check PostgreSQL data directory
        postgres_data_dir = host.file("/tmp/postgres-data")
        assert postgres_data_dir.exists, "PostgreSQL data directory not created"
        assert postgres_data_dir.is_directory, "PostgreSQL data path is not a directory"


class TestTemplateDeployment:
    """Test suite for template deployment functionality"""

    def test_template_file_deployed(self, host):
        """Test that template files are properly deployed"""
        # Check if the index.html file was created from template
        index_file = host.file("/tmp/docker/testapp/index.html")
        assert index_file.exists, "Template-generated index.html file not found"
        assert index_file.is_file, "index.html path exists but is not a file"

        # Check template content
        content = index_file.content_string
        assert "Test Application Deployed Successfully" in content, "Template content not properly rendered"
        assert "testapp" in content, "Application name not in template"
        assert "molecule-test-value" in content, "Environment variable not rendered in template"


class TestFinishCommands:
    """Test suite for finish commands execution"""

    def test_finish_commands_executed(self, host):
        """Test that finish commands were executed successfully"""
        # Check if the completion file was created by finish commands
        completion_file = host.file("/tmp/testapp-deployment-complete")
        assert completion_file.exists, "Deployment completion file not found"
        assert completion_file.is_file, "Completion file path exists but is not a file"

        # Check content
        content = completion_file.content_string
        assert "Deployment completed successfully" in content, "Completion message not found in file"


class TestContainerPullAndRecreate:
    """Test suite for container pull and recreate settings"""

    def test_container_pull_settings(self, docker_client):
        """Test that containers were created with correct pull settings"""
        client = docker_client

        # This is more of a verification that the role accepted the pull parameter
        # The actual pulling behavior is harder to test in molecule
        container = get_container(client, 'testapp')
        assert container is not None

        # Verify the container was created (pull worked)
        assert container.status == 'running', "Container should be running if pull succeeded"

    def test_container_recreate_settings(self, docker_client):
        """Test that containers respect recreate settings"""
        client = docker_client

        # With recreate: False, the container should exist and be running
        container = get_container(client, 'testapp')
        assert container is not None
        assert container.status == 'running', "Container should be running"


class TestContainerSysctls:
    """Test suite for container sysctl settings"""

    def test_container_sysctl_settings(self, docker_client):
        """Test that container has correct sysctl settings applied"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None

        # Check sysctl settings in container configuration
        host_config = container.attrs['HostConfig']
        sysctls = host_config.get('Sysctls', {})

        assert 'net.core.somaxconn' in sysctls, "net.core.somaxconn sysctl not found"
        assert sysctls[
            'net.core.somaxconn'] == '1024', f"net.core.somaxconn value incorrect: {sysctls['net.core.somaxconn']}"

        assert 'net.ipv4.ip_forward' in sysctls, "net.ipv4.ip_forward sysctl not found"
        assert sysctls[
            'net.ipv4.ip_forward'] == '1', f"net.ipv4.ip_forward value incorrect: {sysctls['net.ipv4.ip_forward']}"
