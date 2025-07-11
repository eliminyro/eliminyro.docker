# Ansible Role: setup

This Ansible role sets up Docker networking and TLS configuration on a host. It
can create Docker networks, configure Docker daemon TLS, and validate the setup.

## Requirements

- Ansible 2.10+
- Access to the target host with appropriate privileges
- `community.general` collection for Docker network management

## Role Variables

| Variable            | Description                                                 | Default                   | Required |
| ------------------- | ----------------------------------------------------------- | ------------------------- | -------- |
| docker_net_setup    | Whether to set up Docker networks                           | `False`                   | No       |
| docker_tls_setup    | Whether to set up Docker TLS                                | `False`                   | No       |
| docker_tls_port     | Docker TLS port                                             | `2376`                    | No       |
| docker_tls_verify   | Whether to verify Docker TLS certificates                   | `True`                    | No       |
| docker_networks     | List of Docker networks to create (see below for structure) | `[ { name: "default" } ]` | No       |
| docker_csr_template | Jinja2 template for the server CSR (for cfssl)              | `server-csr.json.j2`      | No\*     |
| cfssl_url           | URL to the cfssl API for certificate generation             | _none_                    | Yes\*    |

- Required if `docker_tls_setup` is `True`. If so, `docker_csr_template` must be
  supplied by a playbook (both the value of the variable and the template file).

### Example `docker_networks` structure

```yaml
docker_networks:
  - name: "my_network"
    ipam_config:
      subnet: "172.20.0.0/16"
    driver_options:
      com.docker.network.bridge.name: "br0"
```

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: setup
      vars:
        docker_net_setup: true
        docker_tls_setup: true
        cfssl_url: "https://cfssl.example.com"
        docker_csr_template: "server-csr.json.j2"
```

## Handlers

- `reload systemd`: Reloads systemd daemon
- `restart docker`: Restarts Docker service

## Author

Pavel Eliminyro <public@eliminyro.me>
