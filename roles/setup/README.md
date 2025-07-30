# Ansible Role: setup

This role configures Docker networking and TLS on a host. It can create custom
Docker networks, generate TLS certificates using a cfssl API, configure the
Docker daemon and verify that TLS is functioning.

## Requirements

- Ansible 2.10+ and Python 3.x on the control node.
- The `community.general` collection for the `docker_network` module.
- Root or sudo privileges on the target host.
- Docker installed on the target host.
- CFSSL API instance

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

| Variable              | Default                   | Description                                                                                                                                                              | Required |
| --------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| `docker_net_setup`    | `false`                   | Whether to create Docker networks defined in `docker_networks`.                                                                                                          | No       |
| `docker_tls_setup`    | `false`                   | Whether to configure Docker daemon TLS. Requires `docker_csr_template`, `cfssl_url` and `docker_server_name`.                                                            | No       |
| `docker_tls_port`     | `2376`                    | Port on which the Docker daemon listens for TLS connections.                                                                                                             | No       |
| `docker_tls_verify`   | `true`                    | Whether to verify server certificates during TLS validation.                                                                                                             | No       |
| `docker_networks`     | `[ { name: "default" } ]` | List of network definitions. Each item may include `ipam_config` and `driver_options`.                                                                                   | No       |
| `docker_config_setup` | `false`                   | Whether to write `daemon.json` and systemd override even when TLS is disabled.                                                                                           | No       |
| `docker_csr_template` | `server-csr.json.j2`      | Jinja2 template used to build the JSON CSR body for cfssl. Must exist in the role’s `templates/` directory or be supplied by the playbook. Required when TLS is enabled. | When TLS |
| `cfssl_url`           | _none_                    | Base URL of the cfssl API. Required when TLS is enabled.                                                                                                                 | When TLS |
| `docker_server_name`  | inventory hostname        | FQDN or IP address of the Docker host used for TLS verification. Defaults to `inventory_hostname` if not provided.                                                       | When TLS |

### `docker_networks` example

```yaml
docker_networks:
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
        docker_net_setup: true
        docker_tls_setup: true
        docker_server_name: "{{ ansible_fqdn }}"
        cfssl_url: "https://cfssl.example.com"
        docker_csr_template: "server-csr.json.j2"
        docker_networks:
          - name: mynet
            ipam_config:
              subnet: "172.30.0.0/16"
```

## Handlers

The role triggers the following handlers during execution: • reload systemd –
Reloads the systemd daemon after installing the override. • restart docker –
Restarts the Docker service after configuration changes.

## Author

Pavel Eliminyro public@eliminyro.me
