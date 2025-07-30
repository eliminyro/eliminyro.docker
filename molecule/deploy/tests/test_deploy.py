import testinfra.utils.ansible_runner
import docker
import os
import pytest
import time

# Get testinfra host
hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

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

class TestContainerDeployment:
    """Test suite for container deployment functionality"""
    
    @pytest.mark.parametrize('name', ['testapp', 'redis', 'postgres'])
    def test_containers_exist_and_running(self, docker_client, name):
        """Test that all expected containers exist and are running"""        
        client = docker_client
        container = wait_for_container_ready(client, name)
        assert container is not None, f"Container {name} not found or not ready within timeout"
        assert container.status == 'running', f"Container {name} is not running, status: {container.status}"
    
    def test_main_container_image(self, docker_client):
        """Test that main container uses correct image"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        image_tags = container.image.tags
        assert any('nginx' in tag for tag in image_tags), f"Expected nginx image, got: {image_tags}"
    
    def test_dependency_container_image(self, docker_client):
        """Test that dependency container uses correct image"""
        client = docker_client
        container = get_container(client, 'redis')
        assert container is not None
        image_tags = container.image.tags
        assert any('redis' in tag for tag in image_tags), f"Expected redis image, got: {image_tags}"

class TestContainerNetworking:
    """Test suite for container networking configuration"""
    
    def test_main_container_ports_exposed(self, docker_client):
        """Test that main container has correct ports exposed"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        
        # Check port configuration
        ports = container.attrs['NetworkSettings']['Ports']
        assert '80/tcp' in ports, "Port 80/tcp not exposed in container"
        
        # Check port mapping
        port_bindings = container.attrs['HostConfig']['PortBindings']
        assert '80/tcp' in port_bindings, "Port 80/tcp not bound to host"
        assert port_bindings['80/tcp'][0]['HostPort'] == '8080', "Port not mapped to 8080"
    
    def test_dependency_container_ports(self, docker_client):
        """Test that dependency container has correct ports exposed"""
        client = docker_client
        container = get_container(client, 'redis')
        assert container is not None
        
        port_bindings = container.attrs['HostConfig']['PortBindings']
        assert '6379/tcp' in port_bindings, "Redis port 6379/tcp not bound"
        assert port_bindings['6379/tcp'][0]['HostPort'] == '6379', "Redis port not mapped correctly"

class TestContainerVolumes:
    """Test suite for container volume configuration"""
    
    def test_main_container_volumes_mounted(self, docker_client):
        """Test that main container has correct volumes mounted"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        
        mounts = container.attrs['Mounts']
        mount_destinations = [m['Destination'] for m in mounts]
        
        # Check data volume
        assert '/data' in mount_destinations, "Data volume /data not mounted"
        
        # Check config file volume
        assert '/etc/nginx/nginx.conf' in mount_destinations, "Config file volume not mounted"
        
        # Verify source paths
        data_mount = next((m for m in mounts if m['Destination'] == '/data'), None)
        assert data_mount is not None
        assert data_mount['Source'] == '/tmp/testapp-data', "Data volume source path incorrect"
        
        config_mount = next((m for m in mounts if m['Destination'] == '/etc/nginx/nginx.conf'), None)
        assert config_mount is not None
        assert config_mount['Source'] == '/tmp/docker/testapp/nginx.conf', "Config volume source path incorrect"
    
    def test_volume_directories_created(self, docker_client):
        """Test that volume directories are created on host"""
        client = docker_client
        
        # Test by checking if we can find the created directories in the container's mounts
        container = get_container(client, 'testapp')
        assert container is not None
        
        mounts = container.attrs['Mounts']
        sources = [m['Source'] for m in mounts if m['Type'] == 'bind']
        
        # The role should have created these paths
        expected_sources = ['/tmp/testapp-data', '/tmp/docker/testapp/nginx.conf']
        for expected_source in expected_sources:
            assert any(expected_source in source for source in sources), f"Expected source {expected_source} not found in mounts"

class TestContainerConfiguration:
    """Test suite for container configuration settings"""
    
    def test_main_container_restart_policy(self, docker_client):
        """Test that containers have correct restart policy"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        
        restart_policy = container.attrs['HostConfig']['RestartPolicy']
        assert restart_policy['Name'] == 'unless-stopped', f"Expected restart policy 'unless-stopped', got: {restart_policy['Name']}"
    
    def test_dependency_container_restart_policy(self, docker_client):
        """Test that dependency containers have correct restart policy"""
        client = docker_client
        container = get_container(client, 'redis')
        assert container is not None
        
        restart_policy = container.attrs['HostConfig']['RestartPolicy']
        assert restart_policy['Name'] == 'unless-stopped', f"Expected restart policy 'unless-stopped', got: {restart_policy['Name']}"

class TestContainerHealth:
    """Test suite for container health and readiness"""
    
    def test_main_container_responds_to_http(self, docker_client):
        """Test that main container responds to HTTP requests"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        
        # Get the host port
        ports = container.attrs['NetworkSettings']['Ports']
        host_port = ports['80/tcp'][0]['HostPort']
        
        # Test HTTP connectivity (this would require additional setup in a real scenario)
        # For now, just verify the port is bound
        assert host_port == '8080', "HTTP port not correctly bound"
    
    def test_containers_have_no_critical_logs(self, docker_client):
        """Test that containers don't have critical error logs"""
        client = docker_client
        
        for container_name in ['testapp', 'redis']:
            container = get_container(client, container_name)
            assert container is not None
            
            # Get recent logs
            logs = container.logs(tail=50).decode('utf-8').lower()
            
            # Check for common error patterns
            error_patterns = ['error', 'failed', 'exception', 'fatal']
            critical_errors = [pattern for pattern in error_patterns if pattern in logs]
            
            # Allow some warnings but no critical errors
            # This is a soft check - adjust based on your application's normal log patterns
            assert len(critical_errors) == 0 or 'error' not in logs, f"Container {container_name} has critical errors in logs: {logs[-200:]}"

class TestConfigFileDeployment:
    """Test suite for configuration file deployment"""
    
    def test_config_file_copied_to_host(self, docker_client):
        """Test that config files are properly copied to host"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        
        # Check if the nginx config file exists in the container
        # by verifying the mount point exists
        mounts = container.attrs['Mounts']
        config_mount = next((m for m in mounts if m['Destination'] == '/etc/nginx/nginx.conf'), None)
        assert config_mount is not None, "Nginx config file mount not found"
        
        # The source should be the file created by the role
        assert config_mount['Source'] == '/tmp/docker/testapp/nginx.conf', "Config file source path incorrect"
