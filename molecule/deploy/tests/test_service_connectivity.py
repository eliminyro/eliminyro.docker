import pytest
import requests
import socket
import time
import redis
import docker
import psycopg2
from conftest import get_container, wait_for_container_ready


class TestServiceConnectivity:
    """Test suite for service connectivity and inter-container communication"""

    def test_nginx_http_response(self, docker_client, testnet_gateway):
        """Test that nginx container responds to HTTP requests"""
        client = docker_client
        container = wait_for_container_ready(client, 'testapp', timeout=60)
        assert container is not None, "testapp container not ready"

        # Get the host port
        ports = container.attrs['NetworkSettings']['Ports']
        assert '80/tcp' in ports, "Port 80/tcp not exposed"
        host_port = ports['80/tcp'][0]['HostPort']

        # Test HTTP connectivity with retries using testnet gateway
        max_retries = 10
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f'http://{testnet_gateway}:{host_port}', timeout=5)
                assert response.status_code == 200, f"HTTP request failed with status {response.status_code}"
                assert len(response.content) > 0, "HTTP response is empty"
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == max_retries - 1:
                    pytest.fail(
                        f"HTTP connectivity test failed after {max_retries} attempts: {e}")
                time.sleep(2)

    def test_redis_connectivity(self, docker_client, testnet_gateway):
        """Test Redis container connectivity"""
        client = docker_client
        container = wait_for_container_ready(client, 'redis', timeout=60)
        assert container is not None, "redis container not ready"

        # Get Redis port
        ports = container.attrs['NetworkSettings']['Ports']
        assert '6379/tcp' in ports, "Redis port 6379/tcp not exposed"
        host_port = ports['6379/tcp'][0]['HostPort']

        # Test Redis connectivity with retries
        max_retries = 10
        for attempt in range(max_retries):
            try:
                r = redis.Redis(host=testnet_gateway, port=int(
                    host_port), socket_timeout=5)
                # Test basic Redis operations
                r.set('test_key', 'test_value')
                value = r.get('test_key')
                assert value.decode(
                    'utf-8') == 'test_value', "Redis key-value operation failed"
                r.delete('test_key')
                break
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                if attempt == max_retries - 1:
                    pytest.fail(
                        f"Redis connectivity test failed after {max_retries} attempts: {e}")
                time.sleep(2)

    def test_postgres_connectivity(self, testnet_gateway, docker_client):
        """Test PostgreSQL container connectivity"""
        client = docker_client
        container = wait_for_container_ready(client, 'postgres', timeout=60)
        assert container is not None, "postgres container not ready"

        # Get PostgreSQL port
        ports = container.attrs['NetworkSettings']['Ports']
        assert '5432/tcp' in ports, "PostgreSQL port 5432/tcp not exposed"
        host_port = ports['5432/tcp'][0]['HostPort']

        # Test PostgreSQL connectivity with retries
        max_retries = 10
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(
                    host=testnet_gateway,
                    port=int(host_port),
                    database='testdb',
                    user='testuser',
                    password='testpass',
                    connect_timeout=5
                )

                # Test basic database operations
                cursor = conn.cursor()
                cursor.execute('SELECT version()')
                version = cursor.fetchone()
                assert version is not None, "PostgreSQL version query failed"
                assert 'PostgreSQL' in version[0], "Unexpected database type"

                cursor.close()
                conn.close()
                break
            except psycopg2.Error as e:
                if attempt == max_retries - 1:
                    pytest.fail(
                        f"PostgreSQL connectivity test failed after {max_retries} attempts: {e}")
                time.sleep(2)

    def test_port_accessibility(self, docker_client, testnet_gateway, expected_containers):
        """Test that all container ports are accessible from host"""
        client = docker_client

        port_mappings = {
            'testapp': {'80/tcp': '8080'},
            'redis': {'6379/tcp': '6379'},
            'postgres': {'5432/tcp': '5432'}
        }

        for container_name in expected_containers:
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            if container_name in port_mappings:
                for container_port, expected_host_port in port_mappings[container_name].items():
                    # Check port binding
                    port_bindings = container.attrs['HostConfig']['PortBindings']
                    assert container_port in port_bindings, f"Port {container_port} not bound for {container_name}"
                    host_port = port_bindings[container_port][0]['HostPort']
                    assert host_port == expected_host_port, f"Port mapping incorrect for {container_name}"

                    # Test socket connectivity
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    try:
                        result = sock.connect_ex(
                            (testnet_gateway, int(host_port)))
                        assert result == 0, f"Cannot connect to {container_name} on port {host_port}"
                    finally:
                        sock.close()


class TestInterContainerCommunication:
    """Test suite for inter-container communication within custom network"""

    def test_containers_on_same_network(self, docker_client):
        """Test that containers can communicate within the custom network"""
        client = docker_client

        # Verify testnet network exists
        try:
            network = client.networks.get('testnet')
        except docker.errors.NotFound:
            pytest.fail("Custom network 'testnet' not found")

        # Get containers connected to testnet
        network_containers = []
        for container_name in ['testapp', 'redis', 'postgres']:
            container = get_container(client, container_name)
            if container:
                networks = container.attrs['NetworkSettings']['Networks']
                if 'testnet' in networks:
                    network_containers.append(container_name)

        assert len(
            network_containers) > 0, "No containers found on testnet network"

    def test_network_isolation(self, docker_client):
        """Test network isolation and connectivity within testnet"""
        client = docker_client

        # Get testapp container (should be on testnet)
        testapp = get_container(client, 'testapp')
        assert testapp is not None, "testapp container not found"

        # Verify it's on testnet
        networks = testapp.attrs['NetworkSettings']['Networks']
        assert 'testnet' in networks, "testapp not connected to testnet"

        # Get network IP address
        testnet_ip = networks['testnet']['IPAddress']
        assert testnet_ip, "testapp has no IP address on testnet"

        # Verify IP is in expected subnet (172.25.0.0/16 from prepare.yml)
        import ipaddress
        ip_obj = ipaddress.IPv4Address(testnet_ip)
        network_obj = ipaddress.IPv4Network('172.25.0.0/16')
        assert ip_obj in network_obj, f"Container IP {testnet_ip} not in expected subnet {network_obj}"


class TestServiceHealth:
    """Test suite for service health and readiness checks"""

    def test_services_startup_time(self, docker_client, expected_containers):
        """Test that all services start within reasonable time"""
        client = docker_client

        startup_times = {}
        for container_name in expected_containers:
            start_time = time.time()
            container = wait_for_container_ready(
                client, container_name, timeout=60)
            end_time = time.time()

            assert container is not None, f"Container {container_name} failed to start within timeout"
            startup_times[container_name] = end_time - start_time

        # Log startup times for debugging
        for container_name, startup_time in startup_times.items():
            print(f"{container_name} startup time: {startup_time:.2f}s")

        # Reasonable startup time limits
        max_startup_times = {
            'testapp': 30,  # nginx should start quickly
            'redis': 20,    # redis starts fast
            'postgres': 45  # postgres may take longer
        }

        for container_name, max_time in max_startup_times.items():
            if container_name in startup_times:
                assert startup_times[container_name] <= max_time, \
                    f"{container_name} took too long to start: {startup_times[container_name]:.2f}s"

    def test_service_logs_health(self, docker_client, expected_containers):
        """Test that services don't have critical errors in logs"""
        client = docker_client

        # Critical error patterns that indicate service problems
        critical_patterns = [
            'fatal error',
            'segmentation fault',
            'out of memory',
            'permission denied',
            'connection refused',
            'bind: address already in use'
        ]

        for container_name in expected_containers:
            container = get_container(client, container_name)
            assert container is not None, f"Container {container_name} not found"

            # Get recent logs
            logs = container.logs(tail=100).decode(
                'utf-8', errors='ignore').lower()

            # Check for critical error patterns
            found_errors = []
            for pattern in critical_patterns:
                if pattern in logs:
                    found_errors.append(pattern)

            assert len(found_errors) == 0, \
                f"Container {container_name} has critical errors in logs: {found_errors}"
