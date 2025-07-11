import pytest
import docker
from conftest import get_container, wait_for_container_ready, get_container_env_dict


class TestContainerDeployment:
    """Consolidated test suite for container deployment functionality"""

    def test_all_containers_exist_and_running(self, docker_client, ansible_vars):
        """Test that all expected containers exist and are running"""
        client = docker_client

        # Get container names from ansible vars
        expected_containers = [ansible_vars['playbook_app']]
        expected_containers.extend([dep['name']
                                   for dep in ansible_vars['testapp_deps']])

        for container_name in expected_containers:
            container = wait_for_container_ready(
                client, container_name, timeout=60)
            assert container is not None, f"Container {container_name} not found or not ready within timeout"
            assert container.status == 'running', f"Container {container_name} is not running, status: {container.status}"

    def test_container_images(self, docker_client, ansible_vars):
        """Test that containers use correct images"""
        client = docker_client

        # Test main container image
        main_container = get_container(client, ansible_vars['playbook_app'])
        assert main_container is not None, f"Container {ansible_vars['playbook_app']} not found"

        image_tags = main_container.image.tags
        expected_image = ansible_vars['testapp_image']
        assert any(expected_image in tag for tag in image_tags), \
            f"Expected {expected_image} image for {ansible_vars['playbook_app']}, got: {image_tags}"

        # Test dependency container images
        for dep_config in ansible_vars['testapp_deps']:
            container_name = dep_config['name']
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            image_tags = container.image.tags
            expected_image = dep_config['image']
            assert any(expected_image in tag for tag in image_tags), \
                f"Expected {expected_image} image for {container_name}, got: {image_tags}"

    def test_container_restart_policies(self, docker_client, ansible_vars):
        """Test that all containers have correct restart policy"""
        client = docker_client

        # Test main container restart policy
        main_container = get_container(client, ansible_vars['playbook_app'])
        assert main_container is not None, f"Container {ansible_vars['playbook_app']} not found"

        restart_policy = main_container.attrs['HostConfig']['RestartPolicy']
        expected_policy = ansible_vars['testapp_restart_policy']
        assert restart_policy['Name'] == expected_policy, \
            f"Expected restart policy '{expected_policy}' for {ansible_vars['playbook_app']}, got: {restart_policy['Name']}"

        # Test dependency containers restart policies
        for dep_config in ansible_vars['testapp_deps']:
            container_name = dep_config['name']
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            restart_policy = container.attrs['HostConfig']['RestartPolicy']
            expected_policy = dep_config['restart_policy']
            assert restart_policy['Name'] == expected_policy, \
                f"Expected restart policy '{expected_policy}' for {container_name}, got: {restart_policy['Name']}"

    def test_container_port_configuration(self, docker_client):
        """Test that containers have correct port configuration"""
        client = docker_client

        expected_ports = {
            'testapp': {'80/tcp': '8080'},
            'redis': {'6379/tcp': '6379'},
            'postgres': {'5432/tcp': '5432'}
        }

        for container_name, port_mapping in expected_ports.items():
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            # Check port bindings
            port_bindings = container.attrs['HostConfig']['PortBindings']

            for container_port, expected_host_port in port_mapping.items():
                assert container_port in port_bindings, \
                    f"Port {container_port} not bound for {container_name}"
                assert port_bindings[container_port][0]['HostPort'] == expected_host_port, \
                    f"Port {container_port} not mapped to {expected_host_port} for {container_name}"

    def test_container_volume_mounts(self, docker_client, expected_volumes):
        """Test that containers have correct volume mounts"""
        client = docker_client

        # Test main container volumes
        testapp = get_container(client, 'testapp')
        assert testapp is not None, "testapp container not found"

        mounts = testapp.attrs['Mounts']
        actual_mappings = {}
        for mount in mounts:
            if mount['Type'] == 'bind':
                actual_mappings[mount['Source']] = mount['Destination']

        # Verify expected volume mappings
        for source, destination in expected_volumes.items():
            assert source in actual_mappings, f"Expected volume source {source} not found"
            assert actual_mappings[source] == destination, \
                f"Volume destination mismatch for {source}: expected {destination}, got {actual_mappings[source]}"

        # Test dependency container volumes
        dependency_volumes = {
            'redis': {'/tmp/redis-data': '/data'},
            'postgres': {'/tmp/postgres-data': '/var/lib/postgresql/data'}
        }

        for container_name, volumes in dependency_volumes.items():
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            container_mounts = container.attrs['Mounts']
            container_mappings = {}
            for mount in container_mounts:
                if mount['Type'] == 'bind':
                    container_mappings[mount['Source']] = mount['Destination']

            for source, destination in volumes.items():
                assert source in container_mappings, \
                    f"Expected volume source {source} not found for {container_name}"
                assert container_mappings[source] == destination, \
                    f"Volume destination mismatch for {container_name}"

    def test_container_environment_variables(self, docker_client):
        """Test that containers have correct environment variables"""
        client = docker_client

        # Test main container environment
        testapp = get_container(client, 'testapp')
        assert testapp is not None, "testapp container not found"

        testapp_env = get_container_env_dict(testapp)
        assert 'TEST_ENV_VAR' in testapp_env, "TEST_ENV_VAR not set in testapp"
        assert testapp_env['TEST_ENV_VAR'] == 'molecule-test-value', \
            f"TEST_ENV_VAR has incorrect value: {testapp_env['TEST_ENV_VAR']}"

        # Test PostgreSQL environment variables
        postgres = get_container(client, 'postgres')
        assert postgres is not None, "postgres container not found"

        postgres_env = get_container_env_dict(postgres)
        assert 'POSTGRES_DB' in postgres_env, "POSTGRES_DB not set in postgres"
        assert postgres_env['POSTGRES_DB'] == 'testdb', \
            f"POSTGRES_DB has incorrect value: {postgres_env['POSTGRES_DB']}"
        assert 'POSTGRES_USER' in postgres_env, "POSTGRES_USER not set in postgres"
        assert postgres_env['POSTGRES_USER'] == 'testuser', \
            f"POSTGRES_USER has incorrect value: {postgres_env['POSTGRES_USER']}"

    def test_container_labels(self, docker_client, expected_containers):
        """Test that containers have correct labels"""
        client = docker_client

        expected_labels = {
            'testapp': {'app': 'testapp', 'environment': 'test', 'version': '1.0'},
            'redis': {'app': 'redis', 'environment': 'test'},
            'postgres': {'app': 'postgres', 'environment': 'test'}
        }

        for container_name in expected_containers:
            if container_name in expected_labels:
                container = get_container(client, container_name)
                assert container is not None, f"Container {container_name} not found"

                labels = container.attrs['Config']['Labels'] or {}
                expected = expected_labels[container_name]

                for label_key, expected_value in expected.items():
                    assert label_key in labels, f"{label_key} label not found in {container_name}"
                    assert labels[label_key] == expected_value, \
                        f"{label_key} label incorrect for {container_name}: expected {expected_value}, got {labels[label_key]}"

    def test_container_network_configuration(self, docker_client):
        """Test that containers are properly configured on networks"""
        client = docker_client

        # Verify custom network exists
        try:
            network = client.networks.get('testnet')
        except docker.errors.NotFound:
            pytest.fail("Custom network 'testnet' not found")

        assert network.attrs['Driver'] == 'bridge', "testnet network driver is not bridge"

        # All containers should be on testnet (based on updated converge.yml)
        containers_on_testnet = ['testapp', 'redis', 'postgres']

        for container_name in containers_on_testnet:
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            networks = container.attrs['NetworkSettings']['Networks']
            assert 'testnet' in networks, f"Container {container_name} not connected to testnet"

            # Verify IP address is in expected subnet
            testnet_ip = networks['testnet']['IPAddress']
            assert testnet_ip, f"Container {container_name} has no IP address on testnet"

            import ipaddress
            ip_obj = ipaddress.IPv4Address(testnet_ip)
            network_obj = ipaddress.IPv4Network('172.25.0.0/16')
            assert ip_obj in network_obj, \
                f"Container {container_name} IP {testnet_ip} not in expected subnet"

    def test_container_resource_configuration(self, docker_client, expected_containers):
        """Test container resource limits and configuration"""
        client = docker_client

        for container_name in expected_containers:
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            host_config = container.attrs['HostConfig']

            # Check that we don't have unexpected resource limits (our test setup doesn't set any)
            memory_limit = host_config.get('Memory', 0)
            assert memory_limit == 0, f"Container {container_name} has unexpected memory limit: {memory_limit}"

            # Check working directory is appropriate
            working_dir = container.attrs['Config']['WorkingDir']
            # Most containers use / or empty string as working directory
            assert isinstance(
                working_dir, str), f"Working directory is not string for {container_name}"

            # Check user configuration
            user = container.attrs['Config']['User']
            assert isinstance(
                user, str), f"User config is not string for {container_name}"
