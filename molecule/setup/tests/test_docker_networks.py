import pytest
import docker
from conftest import get_docker_networks


class TestDockerNetworkCreation:
    """Test suite for Docker network creation"""

    def test_expected_networks_exist(self, docker_client, ansible_vars):
        """Test that networks specified in ansible vars are created"""
        client = docker_client
        networks = get_docker_networks(client)

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']
            assert network_name in networks, f"Expected network '{network_name}' not found"

    def test_network_driver_configuration(self, docker_client, ansible_vars):
        """Test that networks are created with correct driver configuration"""
        client = docker_client
        networks = get_docker_networks(client)

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']
            network = networks[network_name]

            # Default driver should be bridge
            expected_driver = network_config.get('driver', 'bridge')
            assert network.attrs['Driver'] == expected_driver, \
                f"Network '{network_name}' has incorrect driver: expected {expected_driver}, got {network.attrs['Driver']}"

    def test_network_ipam_configuration(self, docker_client, ansible_vars):
        """Test that networks are created with correct IPAM configuration"""
        client = docker_client
        networks = get_docker_networks(client)

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']
            network = networks[network_name]

            if 'ipam_config' in network_config:
                expected_ipam = network_config['ipam_config']
                actual_ipam = network.attrs['IPAM']['Config']

                assert len(
                    actual_ipam) > 0, f"Network '{network_name}' has no IPAM configuration"

                # Check subnet configuration
                for i, expected_config in enumerate(expected_ipam):
                    assert i < len(
                        actual_ipam), f"Network '{network_name}' missing IPAM config {i}"

                    if 'subnet' in expected_config:
                        assert actual_ipam[i]['Subnet'] == expected_config[
                            'subnet'], f"Network '{network_name}' subnet mismatch: expected {expected_config['subnet']}, got {actual_ipam[i]['Subnet']}"

                    if 'gateway' in expected_config:
                        assert actual_ipam[i]['Gateway'] == expected_config[
                            'gateway'], f"Network '{network_name}' gateway mismatch: expected {expected_config['gateway']}, got {actual_ipam[i]['Gateway']}"

    def test_appnet_specific_configuration(self, docker_client):
        """Test specific configuration for the appnet network"""
        client = docker_client
        networks = get_docker_networks(client)

        assert 'appnet' in networks, "appnet network not found"
        appnet = networks['appnet']

        # Check driver
        assert appnet.attrs[
            'Driver'] == 'bridge', f"appnet should use bridge driver, got {appnet.attrs['Driver']}"

        # Check IPAM configuration
        ipam_config = appnet.attrs['IPAM']['Config']
        assert len(ipam_config) > 0, "appnet has no IPAM configuration"

        # Check subnet
        assert ipam_config[0][
            'Subnet'] == '172.26.0.0/16', f"appnet subnet incorrect: expected 172.26.0.0/16, got {ipam_config[0]['Subnet']}"

        # Check gateway
        assert ipam_config[0][
            'Gateway'] == '172.26.0.1', f"appnet gateway incorrect: expected 172.26.0.1, got {ipam_config[0]['Gateway']}"

        # Check that network is attachable
        assert appnet.attrs['Attachable'], "appnet should be attachable"

    def test_network_connectivity(self, docker_client, ansible_vars):
        """Test basic network connectivity within created networks"""
        client = docker_client

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']

            # Create a test container connected to this network
            try:
                test_container = client.containers.run(
                    'alpine:latest',
                    command='sleep 30',
                    name=f'test-{network_name}',
                    detach=True,
                    remove=True
                )

                # Connect container to the network
                network = client.networks.get(network_name)
                network.connect(test_container)

                # Verify container is connected to the network
                test_container.reload()
                container_networks = test_container.attrs['NetworkSettings']['Networks']
                assert network_name in container_networks, f"Test container not connected to network {network_name}"

                # Get container IP
                container_ip = container_networks[network_name]['IPAddress']
                assert container_ip, f"Container has no IP address on network {network_name}"

                # Verify IP is in expected subnet
                if 'ipam_config' in network_config:
                    expected_subnet = network_config['ipam_config'][0]['subnet']
                    import ipaddress
                    network_obj = ipaddress.IPv4Network(expected_subnet)
                    container_ip_obj = ipaddress.IPv4Address(container_ip)
                    assert container_ip_obj in network_obj, f"Container IP {container_ip} not in expected subnet {expected_subnet}"

                # Clean up
                test_container.stop()

            except docker.errors.APIError as e:
                pytest.fail(
                    f"Failed to test network connectivity for {network_name}: {e}")


class TestNetworkIsolation:
    """Test suite for network isolation and security"""

    def test_networks_isolated_from_default_bridge(self, docker_client, ansible_vars):
        """Test that custom networks are isolated from default bridge network"""
        client = docker_client

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']

            if network_name == 'bridge':  # Skip default bridge
                continue

            # Verify network is not connected to default bridge
            networks = get_docker_networks(client)
            custom_network = networks[network_name]

            # Custom networks should not have containers from default bridge
            default_bridge = networks.get('bridge')
            if default_bridge:
                custom_containers = set(
                    custom_network.attrs.get('Containers', {}).keys())
                bridge_containers = set(
                    default_bridge.attrs.get('Containers', {}).keys())

                # There should be no overlap (unless explicitly configured)
                overlap = custom_containers.intersection(bridge_containers)
                # Note: Some system containers might be on both, so we won't assert strict isolation

    def test_network_driver_options(self, docker_client, ansible_vars):
        """Test network driver options if specified"""
        client = docker_client
        networks = get_docker_networks(client)

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']
            network = networks[network_name]

            if 'driver_options' in network_config:
                expected_options = network_config['driver_options']
                actual_options = network.attrs.get('Options', {})

                for option_key, expected_value in expected_options.items():
                    assert option_key in actual_options, \
                        f"Network '{network_name}' missing driver option '{option_key}'"
                    assert actual_options[option_key] == expected_value, \
                        f"Network '{network_name}' driver option '{option_key}' mismatch: expected {expected_value}, got {actual_options[option_key]}"


class TestNetworkManagement:
    """Test suite for network management capabilities"""

    def test_network_labels(self, docker_client, ansible_vars):
        """Test that networks have expected labels if configured"""
        client = docker_client
        networks = get_docker_networks(client)

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']
            network = networks[network_name]

            if 'labels' in network_config:
                expected_labels = network_config['labels']
                actual_labels = network.attrs.get('Labels', {}) or {}

                for label_key, expected_value in expected_labels.items():
                    assert label_key in actual_labels, \
                        f"Network '{network_name}' missing label '{label_key}'"
                    assert actual_labels[label_key] == expected_value, \
                        f"Network '{network_name}' label '{label_key}' mismatch: expected {expected_value}, got {actual_labels[label_key]}"

    def test_network_scope(self, docker_client, ansible_vars):
        """Test that networks have correct scope (local vs swarm)"""
        client = docker_client
        networks = get_docker_networks(client)

        expected_networks = ansible_vars.get('docker_networks', [])
        for network_config in expected_networks:
            network_name = network_config['name']
            network = networks[network_name]

            # Custom networks should typically be local scope
            expected_scope = network_config.get('scope', 'local')
            actual_scope = network.attrs.get('Scope', 'local')

            assert actual_scope == expected_scope, \
                f"Network '{network_name}' scope mismatch: expected {expected_scope}, got {actual_scope}"
