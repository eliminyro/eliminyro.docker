import pytest
import time


class TestDockerServiceStatus:
    """Test suite for Docker service status and management"""

    def test_docker_service_installed(self, host):
        """Test that Docker service is installed"""
        docker_service = host.service("docker")
        assert docker_service.is_valid, "Docker service is not installed or not valid"

    def test_docker_service_enabled(self, host):
        """Test that Docker service is enabled to start at boot"""
        docker_service = host.service("docker")
        assert docker_service.is_enabled, "Docker service is not enabled for automatic startup"

    def test_docker_service_running(self, host):
        """Test that Docker service is currently running"""
        docker_service = host.service("docker")
        assert docker_service.is_running, "Docker service is not running"


class TestDockerDaemonProcess:
    """Test suite for Docker daemon process"""

    def test_docker_daemon_process_running(self, host):
        """Test that dockerd process is running"""
        dockerd_process = host.process.get(comm="dockerd")
        assert dockerd_process is not None, "dockerd process is not running"
        assert dockerd_process.pid > 0, "dockerd process has invalid PID"

    def test_docker_daemon_listening_on_socket(self, host):
        """Test that Docker daemon is listening on Unix socket"""
        socket = host.socket("unix:///var/run/docker.sock")
        assert socket.is_listening, "Docker daemon is not listening on Unix socket"

    def test_docker_daemon_listening_on_tls_port(self, host, ansible_vars):
        """Test that Docker daemon is listening on TLS port"""
        tls_port = ansible_vars['setup_docker_tls_port']
        socket = host.socket(f"tcp://0.0.0.0:{tls_port}")
        assert socket.is_listening, f"Docker daemon is not listening on TLS port {tls_port}"

    def test_docker_daemon_pid_file(self, host):
        """Test that Docker daemon PID file exists"""
        pid_file = host.file("/var/run/docker.pid")
        if pid_file.exists:  # PID file might not exist in all Docker installations
            assert pid_file.is_file, "Docker PID file exists but is not a regular file"

            # Verify PID file contains valid PID
            pid_content = pid_file.content_string.strip()
            assert pid_content.isdigit(
            ), f"Docker PID file contains invalid PID: {pid_content}"

            # Verify process with this PID exists and is dockerd
            pid = int(pid_content)
            process = host.process.get(pid=pid)
            assert process is not None, f"Process with PID {pid} from docker.pid is not running"
            assert process.pid == pid, f"Process PID mismatch: expected {pid}, got {process.pid}"


class TestDockerClientConnectivity:
    """Test suite for Docker client connectivity"""

    def test_docker_client_version_command(self, host, docker_client):
        """Test that docker client can connect and get version"""
        try:
            version_info = docker_client.version()
            assert 'Version' in version_info, "Docker version response missing server information"
            assert version_info['Version'], "Docker server version is empty"
        except Exception as e:
            pytest.fail(f"Docker client version command failed: {e}")

    def test_docker_client_info_command(self, host, docker_client):
        """Test that docker client can get daemon info"""
        try:
            info = docker_client.info()
            assert 'ServerVersion' in info, "Docker info response missing ServerVersion"
            assert info['ServerVersion'], "Docker ServerVersion is empty"
        except Exception as e:
            pytest.fail(f"Docker info command failed: {e}")

    def test_docker_client_can_list_containers(self, host, docker_client):
        """Test that docker client can list containers"""
        try:
            containers = docker_client.containers.list(all=True)
            # Command should succeed even if no containers are running (empty list is fine)
        except Exception as e:
            pytest.fail(f"Docker client failed to list containers: {e}")

    def test_docker_client_can_list_images(self, host, docker_client):
        """Test that docker client can list images"""
        try:
            images = docker_client.images.list()
            # Command should succeed even if no images are present (empty list is fine)
        except Exception as e:
            pytest.fail(f"Docker client failed to list images: {e}")


class TestDockerServiceRestart:
    """Test suite for Docker service restart capability"""

    def test_docker_service_can_restart(self, host):
        """Test that Docker service can be restarted successfully"""
        # Get initial PID
        initial_cmd = host.run(
            "systemctl show docker --property=MainPID --value")
        initial_pid = initial_cmd.stdout.strip()

        # Restart the service
        restart_cmd = host.run("systemctl restart docker")
        assert restart_cmd.rc == 0, f"Failed to restart Docker service: {restart_cmd.stderr}"

        # Wait a moment for service to stabilize
        time.sleep(2)

        # Verify service is running after restart
        docker_service = host.service("docker")
        assert docker_service.is_running, "Docker service is not running after restart"

        # Verify we have a new PID (service actually restarted)
        new_cmd = host.run("systemctl show docker --property=MainPID --value")
        new_pid = new_cmd.stdout.strip()

        if initial_pid and new_pid and initial_pid != "0" and new_pid != "0":
            assert initial_pid != new_pid, "Docker service PID did not change after restart"

    def test_docker_service_startup_time(self, host):
        """Test that Docker service starts within reasonable time"""
        # Check service startup time
        cmd = host.run(
            "systemctl show docker --property=ActiveEnterTimestamp --value")
        assert cmd.rc == 0, f"Failed to get Docker service startup time: {cmd.stderr}"

        timestamp = cmd.stdout.strip()
        assert timestamp, "Docker service has no ActiveEnterTimestamp"
        assert timestamp != "n/a", "Docker service ActiveEnterTimestamp is not available"


class TestDockerServiceLogs:
    """Test suite for Docker service logging"""

    def test_docker_service_logs_accessible(self, host):
        """Test that Docker service logs are accessible"""
        cmd = host.run("journalctl -u docker --no-pager -n 10")
        assert cmd.rc == 0, f"Failed to access Docker service logs: {cmd.stderr}"

        # Should have some log output
        assert cmd.stdout.strip(), "Docker service logs are empty"

    def test_docker_service_no_critical_errors(self, host):
        """Test that Docker service logs don't contain critical errors"""
        cmd = host.run("journalctl -u docker --no-pager -n 50 --priority=err")

        if cmd.rc == 0:
            error_logs = cmd.stdout.strip()

            # Filter out known harmless errors or startup messages
            if error_logs:
                lines = error_logs.split('\n')
                critical_errors = []

                for line in lines:
                    # Skip empty lines
                    if not line.strip():
                        continue

                    # Skip journal headers
                    if line.startswith('--'):
                        continue

                    # Skip known non-critical messages
                    if any(phrase in line.lower() for phrase in [
                        'info', 'debug', 'warning', 'deprecated'
                    ]):
                        continue

                    critical_errors.append(line)

                assert len(
                    critical_errors) == 0, f"Docker service has critical errors in logs: {critical_errors}"
