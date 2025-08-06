import pytest
import docker


class TestConfigFileDeployment:
    """Test suite specifically for configuration file deployment functionality"""

    def test_playbook_app_directory_exists_and_permissions(self, host, ansible_vars):
        """Test that playbook_app directory exists with correct permissions"""
        dockerdir = ansible_vars['dockerdir']
        playbook_app = ansible_vars['playbook_app']
        app_dir_path = f"{dockerdir}/{playbook_app}"

        app_dir = host.file(app_dir_path)
        assert app_dir.exists, f"playbook_app directory {app_dir_path} does not exist"
        assert app_dir.is_directory, f"playbook_app path {app_dir_path} exists but is not a directory"
        assert app_dir.mode == 0o755, f"playbook_app directory has incorrect permissions: expected 0755, got {oct(app_dir.mode)}"

    def test_config_files_exist_on_host(self, host):
        """Test that configuration files are created on the host"""
        # Check if the nginx config file was created
        config_file = host.file("/tmp/docker/testapp/nginx.conf")
        assert config_file.exists, "Nginx configuration file not found on host"
        assert config_file.is_file, "Nginx config path exists but is not a file"

        # Check if the data directory was created
        data_dir = host.file("/tmp/testapp-data")
        assert data_dir.exists, "Data directory not found on host"
        assert data_dir.is_directory, "Data path exists but is not a directory"

    def test_config_file_content(self, host):
        """Test that configuration files have expected content"""
        config_file = host.file("/tmp/docker/testapp/nginx.conf")
        assert config_file.exists, "Nginx configuration file not found"

        content = config_file.content_string

        # Check for expected nginx configuration elements
        assert "server_name  localhost;" in content, "Server name not found in nginx config"
        assert "listen       80;" in content, "Listen port not found in nginx config"
        assert "worker_processes  1;" in content, "Worker processes not configured"
        assert "events {" in content, "Events block not found in nginx config"
        assert "http {" in content, "HTTP block not found in nginx config"

    def test_config_file_permissions(self, host):
        """Test that configuration files have correct permissions"""
        config_file = host.file("/tmp/docker/testapp/nginx.conf")
        assert config_file.exists, "Configuration file not found"

        # Check file permissions (should be readable)
        assert config_file.mode == 0o644, f"Config file has incorrect permissions: {oct(config_file.mode)}"

    def test_volume_directories_permissions(self, host):
        """Test that volume directories have correct permissions"""
        data_dir = host.file("/tmp/testapp-data")
        assert data_dir.exists, "Data directory not found"

        # Check directory permissions
        assert data_dir.is_directory, "Data path is not a directory"
        # Directory should be accessible
        assert data_dir.mode & 0o755 == 0o755, f"Data directory has incorrect permissions: {oct(data_dir.mode)}"


class TestVolumeToDirectoryMapping:
    """Test suite for volume to directory mapping functionality (vols2dirs.yml)"""

    def test_bind_mount_sources_created(self, host, docker_client):
        """Test that bind mount source directories/files are created"""
        client = docker_client

        try:
            container = client.containers.get('testapp')
        except docker.errors.NotFound:
            pytest.fail("Container 'testapp' not found")

        mounts = container.attrs['Mounts']
        bind_mounts = [m for m in mounts if m['Type'] == 'bind']

        assert len(bind_mounts) > 0, "No bind mounts found in container"

        # Check each bind mount source exists
        for mount in bind_mounts:
            source_path = mount['Source']
            destination_path = mount['Destination']

            # Check that source exists on host
            source_file = host.file(source_path)
            assert source_file.exists, f"Bind mount source {source_path} does not exist on host"

            # Log for debugging
            print(f"Mount: {source_path} -> {destination_path}")

    def test_volume_path_parsing(self, host, docker_client):
        """Test that volume path parsing works correctly"""
        client = docker_client

        try:
            container = client.containers.get('testapp')
        except docker.errors.NotFound:
            pytest.fail("Container 'testapp' not found")

        mounts = container.attrs['Mounts']

        # Expected volume mappings from converge.yml
        expected_mappings = {
            '/tmp/testapp-data': '/data',
            '/tmp/docker/testapp/nginx.conf': '/etc/nginx/nginx.conf'
        }

        actual_mappings = {}
        for mount in mounts:
            if mount['Type'] == 'bind':
                actual_mappings[mount['Source']] = mount['Destination']

        # Verify expected mappings exist
        for source, destination in expected_mappings.items():
            assert source in actual_mappings, f"Expected source {source} not found in mounts"
            assert actual_mappings[
                source] == destination, f"Mount destination mismatch for {source}"

    def test_file_vs_directory_creation(self, host):
        """Test that files and directories are created appropriately"""
        # Test directory creation
        data_dir = host.file("/tmp/testapp-data")
        assert data_dir.exists, "Data directory not created"
        assert data_dir.is_directory, "Data path should be a directory"

        # Test file creation
        config_file = host.file("/tmp/docker/testapp/nginx.conf")
        assert config_file.exists, "Config file not created"
        assert config_file.is_file, "Config path should be a file"


class TestConfigListProcessing:
    """Test suite for configuration list processing"""

    def test_config_file_deployment_from_list(self, host, docker_client):
        """Test that config files are deployed according to configlist variable"""
        # This tests the configfiles.yml functionality
        client = docker_client

        try:
            container = client.containers.get('testapp')
        except docker.errors.NotFound:
            pytest.fail("Container 'testapp' not found")

        # Check that the config file mount exists
        mounts = container.attrs['Mounts']
        config_mounts = [m for m in mounts if m['Destination']
                         == '/etc/nginx/nginx.conf']

        assert len(config_mounts) == 1, "Expected exactly one nginx config mount"

        config_mount = config_mounts[0]
        assert config_mount['Source'] == '/tmp/docker/testapp/nginx.conf', "Config mount source path incorrect"
        assert config_mount['Type'] == 'bind', "Config mount should be a bind mount"

    def test_config_file_source_matches_converge_spec(self, host):
        """Test that config file source matches what's specified in converge.yml"""
        # The converge.yml specifies this config file should be copied
        config_file = host.file("/tmp/docker/testapp/nginx.conf")
        assert config_file.exists, "Expected config file not found"

        # Read the content and verify it matches our test nginx.conf
        expected_content_snippets = [
            "user  nginx;",
            "worker_processes  1;",
            "server_name  localhost;",
            "listen       80;"
        ]

        content = config_file.content_string
        for snippet in expected_content_snippets:
            assert snippet in content, f"Expected content snippet '{snippet}' not found in config file"
