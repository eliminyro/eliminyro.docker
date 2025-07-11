from conftest import parse_daemon_json
import requests
import pytest
import tempfile
import os
import warnings
from cryptography import x509


class TestTLSCertificateSetup:
    """Test suite for Docker TLS certificate setup"""

    def test_tls_certs_directory_exists(self, host, tls_cert_paths):
        """Test that TLS certificates directory exists with correct permissions"""
        certs_dir = host.file(tls_cert_paths['certs_dir'])
        assert certs_dir.exists, "TLS certificates directory does not exist"
        assert certs_dir.is_directory, "TLS certificates path is not a directory"
        assert certs_dir.mode == 0o750, f"TLS directory has incorrect permissions: {oct(certs_dir.mode)}"

    def test_ca_certificate_exists(self, host, tls_cert_paths):
        """Test that CA certificate exists and has correct properties"""
        ca_cert = host.file(tls_cert_paths['ca_cert'])
        assert ca_cert.exists, "CA certificate file does not exist"
        assert ca_cert.is_file, "CA certificate path is not a file"
        assert ca_cert.mode == 0o640, f"CA certificate has incorrect permissions: {oct(ca_cert.mode)}"

        # Check certificate content format
        content = ca_cert.content_string
        assert "-----BEGIN CERTIFICATE-----" in content, "CA certificate does not have proper PEM format"
        assert "-----END CERTIFICATE-----" in content, "CA certificate does not have proper PEM format"

    def test_server_certificate_exists(self, host, tls_cert_paths):
        """Test that server certificate exists and has correct properties"""
        server_cert = host.file(tls_cert_paths['server_cert'])
        assert server_cert.exists, "Server certificate file does not exist"
        assert server_cert.is_file, "Server certificate path is not a file"
        assert server_cert.mode == 0o640, f"Server certificate has incorrect permissions: {oct(server_cert.mode)}"

        # Check certificate content format
        content = server_cert.content_string
        assert "-----BEGIN CERTIFICATE-----" in content, "Server certificate does not have proper PEM format"
        assert "-----END CERTIFICATE-----" in content, "Server certificate does not have proper PEM format"

    def test_server_private_key_exists(self, host, tls_cert_paths):
        """Test that server private key exists and has correct properties"""
        server_key = host.file(tls_cert_paths['server_key'])
        assert server_key.exists, "Server private key file does not exist"
        assert server_key.is_file, "Server private key path is not a file"
        assert server_key.mode == 0o640, f"Server private key has incorrect permissions: {oct(server_key.mode)}"

        # Check private key content format
        content = server_key.content_string
        assert "-----BEGIN" in content and "PRIVATE KEY-----" in content, "Server private key does not have proper PEM format"
        assert "-----END" in content and "PRIVATE KEY-----" in content, "Server private key does not have proper PEM format"

    def test_certificate_subject_matches_hostname(self, host, tls_cert_paths, ansible_vars):
        """Test that server certificate subject matches expected hostname"""
        server_cert = host.file(tls_cert_paths['server_cert'])
        assert server_cert.exists, "Server certificate does not exist"

        # Use cryptography library to check certificate subject
        cert_content = server_cert.content
        try:
            cert = x509.load_pem_x509_certificate(cert_content)

            # Extract Common Name from subject
            subject_cn = None
            for attribute in cert.subject:
                if attribute.oid == x509.NameOID.COMMON_NAME:
                    subject_cn = attribute.value
                    break

            expected_hostname = ansible_vars['setup_docker_server_name']
            assert subject_cn == expected_hostname, \
                f"Server certificate CN '{subject_cn}' does not match expected hostname '{expected_hostname}'"
        except Exception as e:
            pytest.fail(f"Failed to parse server certificate: {e}")

    def test_certificate_subject_alternative_names(self, host, tls_cert_paths):
        """Test that server certificate includes required Subject Alternative Names"""
        server_cert = host.file(tls_cert_paths['server_cert'])
        assert server_cert.exists, "Server certificate does not exist"

        # Use cryptography library to check SAN
        cert_content = server_cert.content
        try:
            cert = x509.load_pem_x509_certificate(cert_content)

            # Extract Subject Alternative Names
            san_extension = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san_names = [str(name.value) for name in san_extension.value]

            # Check for required hostnames in SAN
            required_hosts = ['localhost', '127.0.0.1', '172.25.0.1']
            for required_host in required_hosts:
                assert required_host in san_names, f"Server certificate SAN does not include {required_host}. Found: {san_names}"
        except x509.ExtensionNotFound:
            pytest.fail(
                "Server certificate does not have Subject Alternative Name extension")
        except Exception as e:
            pytest.fail(f"Failed to parse server certificate SAN: {e}")


class TestTLSConnectivity:
    """Test suite for Docker TLS connectivity"""

    def test_docker_tls_port_listening(self, host, ansible_vars):
        """Test that Docker TLS port is listening"""
        tls_port = ansible_vars['setup_docker_tls_port']
        socket = host.socket(f"tcp://0.0.0.0:{tls_port}")
        assert socket.is_listening, f"Docker TLS port {tls_port} is not listening"

    def test_docker_tls_api_responds(self, host, tls_cert_paths, ansible_vars):
        """Test that Docker TLS API responds to requests"""
        tls_port = ansible_vars['setup_docker_tls_port']
        server_name = ansible_vars['setup_docker_server_name']

        # Verify certificate files exist and are readable
        ca_cert_file = host.file(tls_cert_paths['ca_cert'])
        server_cert_file = host.file(tls_cert_paths['server_cert'])
        server_key_file = host.file(tls_cert_paths['server_key'])

        assert ca_cert_file.exists, f"CA certificate not found: {tls_cert_paths['ca_cert']}"
        assert server_cert_file.exists, f"Server certificate not found: {tls_cert_paths['server_cert']}"
        assert server_key_file.exists, f"Server key not found: {tls_cert_paths['server_key']}"

        # Create temporary files with certificate content that Python can access
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as ca_temp:
            ca_temp.write(ca_cert_file.content_string)
            ca_temp_path = ca_temp.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as cert_temp:
            cert_temp.write(server_cert_file.content_string)
            cert_temp_path = cert_temp.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_temp:
            key_temp.write(server_key_file.content_string)
            key_temp_path = key_temp.name

        # Test TLS connection using requests with temporary certificates
        try:
            response = requests.get(
                f"https://{server_name}:{tls_port}/version",
                cert=(cert_temp_path, key_temp_path),
                verify=ca_temp_path,
                timeout=10
            )
            response.raise_for_status()
            version_data = response.json()
            assert "Version" in version_data, "Docker API did not return version information"
        except Exception as e:
            pytest.fail(f"Failed to connect to Docker TLS API: {e}")
        finally:
            # Clean up temporary files
            for temp_path in [ca_temp_path, cert_temp_path, key_temp_path]:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def test_docker_tls_api_rejects_insecure_connections(self, host, ansible_vars):
        """Test that Docker TLS API rejects connections without certificates"""
        tls_port = ansible_vars['setup_docker_tls_port']
        server_name = ansible_vars['setup_docker_server_name']

        # Test connection without certificates should fail
        # Suppress the expected insecure request warning
        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)

            try:
                response = requests.get(
                    f"https://{server_name}:{tls_port}/version",
                    verify=False,  # Skip CA verification
                    timeout=10
                )
                # If we get here, the connection succeeded when it shouldn't have
                pytest.fail(
                    "Docker TLS API should reject connections without client certificates")
            except requests.exceptions.SSLError:
                # This is expected - SSL error due to missing client certificates
                pass
            except requests.exceptions.ConnectionError:
                # This is also acceptable - connection refused/reset
                pass


class TestDockerTLSConfiguration:
    """Test suite for Docker daemon TLS configuration"""

    def test_docker_daemon_tls_configuration(self, host, docker_config_paths, ansible_vars):
        """Test that Docker daemon is configured for TLS"""
        daemon_json = host.file(docker_config_paths['daemon_json'])
        assert daemon_json.exists, "Docker daemon.json configuration file does not exist"

        content = daemon_json.content_string
        config = parse_daemon_json(content)
        assert config is not None, "Docker daemon.json is not valid JSON"

        # Check TLS configuration
        expected_tls_port = ansible_vars['setup_docker_tls_port']
        expected_hosts = [f"tcp://0.0.0.0:{expected_tls_port}"]

        assert 'hosts' in config, "Docker daemon configuration missing 'hosts' setting"
        assert any(f":{expected_tls_port}" in host for host in config['hosts']), \
            f"Docker daemon not configured to listen on TLS port {expected_tls_port}"

        # Check TLS settings
        assert config.get('tls', False), "Docker daemon TLS not enabled"
        assert config.get(
            'tlsverify', False), "Docker daemon TLS verification not enabled"
        assert config.get(
            'tlscert', '') == '/etc/docker/certs/server.pem', "Docker daemon TLS cert path incorrect"
        assert config.get(
            'tlskey', '') == '/etc/docker/certs/server-key.pem', "Docker daemon TLS key path incorrect"
        assert config.get(
            'tlscacert', '') == '/etc/docker/certs/ca.pem', "Docker daemon TLS CA cert path incorrect"
