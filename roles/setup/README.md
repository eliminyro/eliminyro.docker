# Ansible Role: setup

This role configures Docker networking and TLS on a host. It can create custom
Docker networks, generate TLS certificates using a cfssl API, configure the
Docker daemon and verify that TLS is functioning.

## Requirements

- Ansible 2.15+ and Python 3.x on the control node.
- The `community.general` and `community.docker` collections.
- Root or sudo privileges on the target host.
- Docker installed on the target host.
- CFSSL API instance (when TLS setup is enabled)

## Capabilities

- **Docker networks** – Creates one or more user‑defined bridge networks.
- **TLS certificate generation** – Contacts a cfssl API to generate a CA and
  server certificate/key and stores them under `/etc/docker/certs`.
- **Daemon configuration** – Writes `/etc/docker/daemon.json` and an override
  file under `docker.service.d` to enable TLS and any additional daemon options.
- **TLS verification** – Performs a version check against the Docker API over
  HTTPS to verify the certificates.
- The role is idempotent: re‑running it does not recreate existing networks or
  certificates.

## Role Variables

| Variable                            | Default               | Description                                                                                                                                                              | Required |
| ----------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| `setup_docker_net`                  | `false`               | Whether to create Docker networks defined in `setup_docker_networks`.                                                                                                    | No       |
| `setup_docker_tls`                  | `false`               | Whether to configure Docker daemon TLS. Requires `setup_docker_csr_template`, `setup_cfssl_url` and `setup_docker_server_name`.                                          | No       |
| `setup_docker_tls_port`             | `2376`                | Port on which the Docker daemon listens for TLS connections.                                                                                                             | No       |
| `setup_docker_tls_verify`           | `true`                | Whether to verify server certificates during TLS validation.                                                                                                             | No       |
| `setup_docker_tls_certs_regenerate` | `false`               | Whether to force regeneration of existing TLS certificates.                                                                                                              | No       |
| `setup_docker_networks`             | `[{name: "default"}]` | List of network definitions. Each item may include `ipam_config` and `driver_options`.                                                                                   | No       |
| `setup_docker_config`               | `false`               | Whether to write `daemon.json` and systemd override even when TLS is disabled.                                                                                           | No       |
| `setup_docker_csr_template`         | `server-csr.json.j2`  | Jinja2 template used to build the JSON CSR body for cfssl. Must exist in the role's `templates/` directory or be supplied by the playbook. Required when TLS is enabled. | When TLS |
| `setup_cfssl_url`                   | _none_                | Base URL of the cfssl API. Required when TLS is enabled.                                                                                                                 | When TLS |
| `setup_docker_server_name`          | inventory hostname    | FQDN or IP address of the Docker host used for TLS verification. Defaults to `inventory_hostname` if not provided.                                                       | When TLS |

### `setup_docker_networks` example

```yaml
setup_docker_networks:
  - name: mynet
    ipam_config:
      subnet: "172.20.0.0/16"
    driver_options:
      com.docker.network.bridge.name: br0
```

## Example playbook

```yaml
- hosts: docker_hosts
  become: true
  roles:
    - role: eliminyro.docker.setup
      vars:
        setup_docker_net: true
        setup_docker_tls: true
        setup_docker_server_name: "{{ ansible_fqdn }}"
        setup_cfssl_url: "https://cfssl.example.com"
        setup_docker_csr_template: "server-csr.json.j2"
        setup_docker_networks:
          - name: mynet
            ipam_config:
              subnet: "172.30.0.0/16"
```

## Author

Pavel Eliminyro public@eliminyro.me
