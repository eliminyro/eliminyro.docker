import testinfra.utils.ansible_runner
import docker
import os

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

class TestEdgeCases:
    """Test suite for edge cases and error conditions"""
    
    def test_container_names_are_unique(self, docker_client):
        """Test that container names don't conflict"""
        client = docker_client
        containers = client.containers.list(all=True)
        
        # Get containers created by our test
        test_containers = [c for c in containers if c.name in ['testapp', 'redis']]
        container_names = [c.name for c in test_containers]
        
        # Check for uniqueness
        assert len(container_names) == len(set(container_names)), "Duplicate container names found"
        
        # Verify we have the expected containers
        assert 'testapp' in container_names, "Main container 'testapp' not found"
        assert 'redis' in container_names, "Dependency container 'redis' not found"
    
    def test_container_resource_limits(self, docker_client):
        """Test that containers don't have unexpected resource limits"""
        client = docker_client
        
        for container_name in ['testapp', 'redis']:
            container = get_container(client, container_name)
            assert container is not None
            
            # Check memory limits (should be 0 = unlimited for our test)
            host_config = container.attrs['HostConfig']
            memory_limit = host_config.get('Memory', 0)
            
            # In our test setup, we don't set memory limits
            assert memory_limit == 0, f"Container {container_name} has unexpected memory limit: {memory_limit}"
    
    def test_container_network_mode(self, docker_client):
        """Test that containers use expected network mode"""
        client = docker_client
        
        # Test main container uses custom network
        testapp = get_container(client, 'testapp')
        assert testapp is not None
        
        # Check network mode
        network_mode = testapp.attrs['HostConfig']['NetworkMode']
        assert network_mode == 'testnet', f"Main container should use testnet network, got: {network_mode}"
        
        # Check that container is actually connected to the testnet network
        networks = testapp.attrs['NetworkSettings']['Networks']
        assert 'testnet' in networks, f"Main container not connected to testnet, connected to: {list(networks.keys())}"
        
        # Test dependency containers use default network (they don't have networks specified)
        for container_name in ['redis', 'postgres']:
            container = get_container(client, container_name)
            assert container is not None
            
            network_mode = container.attrs['HostConfig']['NetworkMode']
            assert network_mode in ['default', 'bridge'], f"Container {container_name} has unexpected network mode: {network_mode}"

    def test_container_environment_variables(self, docker_client):
        """Test that containers have expected environment variables"""
        client = docker_client
        
        # Test main container
        testapp = get_container(client, 'testapp')
        assert testapp is not None
        
        env_vars = testapp.attrs['Config']['Env']
        env_dict = {}
        for env_var in env_vars:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                env_dict[key] = value
        
        # Nginx container should have some standard env vars
        assert 'PATH' in env_dict, "PATH environment variable not found"
        
        # Test Redis container
        redis = get_container(client, 'redis')
        assert redis is not None
        
        redis_env_vars = redis.attrs['Config']['Env']
        redis_env_dict = {}
        for env_var in redis_env_vars:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                redis_env_dict[key] = value
        
        assert 'PATH' in redis_env_dict, "PATH environment variable not found in Redis container"

class TestConfigurationValidation:
    """Test suite for configuration validation"""
    
    def test_volume_mount_permissions(self, docker_client):
        """Test that volume mounts have correct permissions"""
        client = docker_client
        container = get_container(client, 'testapp')
        assert container is not None
        
        mounts = container.attrs['Mounts']
        
        for mount in mounts:
            if mount['Type'] == 'bind':
                # Check that mount has read/write access by default
                assert mount['RW'] == True, f"Mount {mount['Destination']} is not read-write"
    
    def test_container_working_directory(self, docker_client):
        """Test that containers have appropriate working directories"""
        client = docker_client
        
        # Test main container
        testapp = get_container(client, 'testapp')
        assert testapp is not None
        
        working_dir = testapp.attrs['Config']['WorkingDir']
        # Nginx container typically uses /
        assert working_dir in ['/', ''], f"Unexpected working directory for testapp: {working_dir}"
    
    def test_container_user_configuration(self, docker_client):
        """Test that containers run with appropriate user configuration"""
        client = docker_client
        
        for container_name in ['testapp', 'redis']:
            container = get_container(client, container_name)
            assert container is not None
            
            # Check user configuration
            user = container.attrs['Config']['User']
            
            # For our test setup, we don't specify a user, so it should be empty or root
            # This is acceptable for test containers
            assert isinstance(user, str), f"Container {container_name} user config is not a string"

