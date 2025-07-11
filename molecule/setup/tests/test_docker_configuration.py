from conftest import parse_daemon_json


class TestDockerDaemonConfiguration:
    """Test suite for Docker daemon configuration"""

    def test_docker_daemon_json_exists(self, host, docker_config_paths):
        """Test that Docker daemon.json configuration file exists"""
        daemon_json = host.file(docker_config_paths['daemon_json'])
        assert daemon_json.exists, "Docker daemon.json configuration file does not exist"
        assert daemon_json.is_file, "Docker daemon.json path is not a file"
        assert daemon_json.mode == 0o644, f"Docker daemon.json has incorrect permissions: {oct(daemon_json.mode)}"

    def test_docker_daemon_json_valid_format(self, host, docker_config_paths):
        """Test that Docker daemon.json is valid JSON"""
        daemon_json = host.file(docker_config_paths['daemon_json'])
        assert daemon_json.exists, "Docker daemon.json does not exist"

        content = daemon_json.content_string
        config = parse_daemon_json(content)
        assert config is not None, f"Docker daemon.json is not valid JSON: {content}"
        assert isinstance(
            config, dict), "Docker daemon.json should contain a JSON object"

    def test_docker_daemon_hosts_configuration(self, host, docker_config_paths, ansible_vars):
        """Test that Docker daemon is configured with correct hosts"""
        daemon_json = host.file(docker_config_paths['daemon_json'])
        content = daemon_json.content_string
        config = parse_daemon_json(content)

        assert 'hosts' in config, "Docker daemon configuration missing 'hosts' setting"
        hosts_list = config['hosts']
        assert isinstance(
            hosts_list, list), "Docker daemon 'hosts' should be a list"

        # Check for TLS host configuration
        tls_port = ansible_vars['setup_docker_tls_port']
        expected_tls_host = f"tcp://0.0.0.0:{tls_port}"

        tls_hosts = [h for h in hosts_list if str(tls_port) in h]
        assert len(
            tls_hosts) > 0, f"Docker daemon not configured to listen on TLS port {tls_port}"

    def test_docker_daemon_tls_settings(self, host, docker_config_paths, tls_cert_paths):
        """Test that Docker daemon TLS settings are correctly configured"""
        daemon_json = host.file(docker_config_paths['daemon_json'])
        content = daemon_json.content_string
        config = parse_daemon_json(content)

        # Check TLS is enabled
        assert config.get('tls', False), "Docker daemon TLS not enabled"
        assert config.get(
            'tlsverify', False), "Docker daemon TLS verification not enabled"

        # Check certificate paths
        assert config.get('tlscert') == tls_cert_paths['server_cert'], \
            f"Docker daemon TLS cert path incorrect: expected {tls_cert_paths['server_cert']}, got {config.get('tlscert')}"
        assert config.get('tlskey') == tls_cert_paths['server_key'], \
            f"Docker daemon TLS key path incorrect: expected {tls_cert_paths['server_key']}, got {config.get('tlskey')}"
        assert config.get('tlscacert') == tls_cert_paths['ca_cert'], \
            f"Docker daemon TLS CA cert path incorrect: expected {tls_cert_paths['ca_cert']}, got {config.get('tlscacert')}"


class TestSystemdConfiguration:
    """Test suite for Docker systemd configuration"""

    def test_systemd_override_directory_exists(self, host, docker_config_paths):
        """Test that systemd override directory exists with correct permissions"""
        override_dir = host.file(docker_config_paths['systemd_override_dir'])
        assert override_dir.exists, "Systemd override directory does not exist"
        assert override_dir.is_directory, "Systemd override path is not a directory"
        assert override_dir.mode == 0o755, f"Systemd override directory has incorrect permissions: {oct(override_dir.mode)}"

    def test_systemd_override_file_exists(self, host, docker_config_paths):
        """Test that systemd override file exists with correct permissions"""
        override_file = host.file(docker_config_paths['systemd_override_file'])
        assert override_file.exists, "Systemd override file does not exist"
        assert override_file.is_file, "Systemd override path is not a file"
        assert override_file.mode == 0o644, f"Systemd override file has incorrect permissions: {oct(override_file.mode)}"

    def test_systemd_override_file_content(self, host, docker_config_paths):
        """Test that systemd override file has expected content"""
        override_file = host.file(docker_config_paths['systemd_override_file'])
        assert override_file.exists, "Systemd override file does not exist"

        content = override_file.content_string

        # Check for systemd unit configuration
        assert "[Service]" in content, "Systemd override file missing [Service] section"

        # Check that ExecStart is cleared and redefined (common pattern for Docker TLS)
        lines = content.strip().split('\n')
        service_section_found = False
        for line in lines:
            if line.strip() == "[Service]":
                service_section_found = True
                break

        assert service_section_found, "Systemd override file missing proper [Service] section"

    def test_docker_service_enabled_and_running(self, host):
        """Test that Docker service is enabled and running"""
        docker_service = host.service("docker")
        assert docker_service.is_enabled, "Docker service is not enabled"
        assert docker_service.is_running, "Docker service is not running"

    def test_systemd_daemon_reloaded(self, host):
        """Test that systemd daemon has been reloaded (no failing units)"""
        # Check for any failed units that might indicate systemd issues
        cmd = host.run("systemctl --failed --no-pager --no-legend")

        # Filter out any non-Docker related failures
        failed_units = cmd.stdout.strip()
        if failed_units:
            docker_failures = [line for line in failed_units.split(
                '\n') if 'docker' in line.lower()]
            assert len(
                docker_failures) == 0, f"Docker-related systemd units are failing: {docker_failures}"


class TestDockerConfigurationValidation:
    """Test suite for validating Docker configuration consistency"""

    def test_docker_daemon_configuration_syntax(self, host, docker_config_paths):
        """Test Docker daemon configuration syntax"""
        daemon_json = host.file(docker_config_paths['daemon_json'])
        assert daemon_json.exists, "Docker daemon.json configuration file does not exist"

        # Test JSON syntax by parsing the content
        content = daemon_json.content_string
        config = parse_daemon_json(content)
        assert config is not None, f"Docker daemon.json has invalid JSON syntax: {content}"

    def test_certificate_files_readable_by_docker(self, host, tls_cert_paths):
        """Test that certificate files are readable by the Docker daemon"""
        # Check that files exist and have appropriate permissions for Docker daemon
        for cert_name, cert_path in tls_cert_paths.items():
            if cert_name != 'certs_dir':  # Skip directory entry
                cert_file = host.file(cert_path)
                assert cert_file.exists, f"Certificate file {cert_path} does not exist"

                # Test readability - check file has read permissions
                assert cert_file.mode & 0o444, f"Certificate file {cert_path} is not readable (no read permissions)"
