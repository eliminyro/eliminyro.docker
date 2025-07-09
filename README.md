# Ansible Role: docker_deploy

This Ansible role automates the deployment of Docker containers, including
dependencies, configuration files and directory creation. It is designed for
flexible, parameterized deployments of containerized applications.

## Features

- Creates required directories for Docker volumes
- Prepares and deploys configuration files and templates
- Deploys dependency containers (sidecars, etc.)
- Deploys the main application container
- Supports custom finishing commands

## Requirements

- Ansible 2.10+
- Python 3.x
- Required collections:
  - `community.general` (for `docker_container`)
- Docker must be installed on the target host

## Role Variables

### Dynamic Variable Resolution

Most variables for this role are dynamically resolved based on the value of
`playbook_app`. For example, if `playbook_app: myapp`, then the role will look
for variables like `myapp_image`, `myapp_ports`, `myapp_deps`, etc. You can
define these variables in your playbook or inventory. The role will
automatically map them to the correct internal variables.

#### Example Mapping

| Internal Variable     | Looks up variable      |
| --------------------- | ---------------------- |
| deploy_image          | `myapp_image`          |
| deploy_ports          | `myapp_ports`          |
| deploy_deps           | `myapp_deps`           |
| deploy_configlist     | `myapp_configlist`     |
| deploy_templatelist   | `myapp_templatelist`   |
| deploy_volumes        | `myapp_volumes`        |
| deploy_env            | `myapp_env`            |
| deploy_command        | `myapp_command`        |
| deploy_restart_policy | `myapp_restart_policy` |
| ...                   | ...                    |

> **Note:** Replace `myapp` with your actual `playbook_app` value.

### Main Application Variables

| Variable              | Type   | Description                                                                         |
| --------------------- | ------ | ----------------------------------------------------------------------------------- |
| playbook_app          | string | Name of the main application/container. Used as a prefix for all dynamic variables. |
| deploy_image          | string | Docker image for the main container (from `<playbook_app>_image`).                  |
| deploy_image_tag      | string | Tag for the main image (from `<playbook_app>_image_tag`). Default: `latest`.        |
| deploy_command        | string | Command to run in the main container.                                               |
| deploy_pull           | bool   | Whether to pull the image.                                                          |
| deploy_restart_policy | string | Docker restart policy.                                                              |
| deploy_networks       | list   | List of Docker networks to connect.                                                 |
| deploy_network_mode   | string | Docker network mode.                                                                |
| deploy_healthcheck    | dict   | Healthcheck configuration.                                                          |
| deploy_capabilities   | list   | Linux capabilities to add.                                                          |
| deploy_security_opt   | list   | Security options.                                                                   |
| deploy_privileged     | bool   | Run container in privileged mode.                                                   |
| deploy_user           | string | User to run as.                                                                     |
| deploy_env            | dict   | Environment variables.                                                              |
| deploy_ports          | list   | Port mappings.                                                                      |
| deploy_hostname       | string | Hostname for the container.                                                         |
| deploy_volumes        | list   | Volume mappings.                                                                    |
| deploy_devices        | list   | Device mappings.                                                                    |
| log_driver            | string | Docker log driver.                                                                  |
| log_opt               | dict   | Log driver options.                                                                 |

### Dependencies

- `deploy_deps` (list): List of dependency containers. Each item should be a
  dict with keys like `name`, `image`, `tag`, `command`, `networks`, etc.
  (resolved from `<playbook_app>_deps`).

### Configuration Files

- `deploy_configlist` (list): List of config files to copy (from
  `<playbook_app>_configlist`). Each item should be a dictionary as described
  below.
- `deploy_templatelist` (list): List of Jinja2 templates to render (from
  `<playbook_app>_templatelist`). Each item should be a dictionary as described
  below.

| Key   | Type   | Description                                             |
| ----- | ------ | ------------------------------------------------------- |
| name  | string | Filename of the config file or template.                |
| path  | string | Relative path inside the container or config directory. |
| user  | string | (Optional) File owner. Defaults to `ansible_user`.      |
| group | string | (Optional) File group. Defaults to `ansible_user`.      |
| mode  | string | (Optional) File mode (e.g. `0644`). Defaults to `0644`. |

### Directory Creation

- `deploy_volumes` (list): List of volume paths to create as directories (from
  `<playbook_app>_volumes`).

When you specify volume mappings, this role will:

1. Parse each volume string (e.g., `/host/path:/container/path`) and extract the
   host-side path.
2. For each host path:
   - If the path does not look like a file (does not end with a file extension),
     it will ensure the directory exists, creating it if necessary, with the
     current Ansible user as owner and group.
   - If the path looks like a file (matches a file extension, but not `.sock`),
     it will ensure the file exists (using `state: touch`), preserving access
     and modification times, and setting the current Ansible user as owner and
     group.

This ensures that all required directories and files for Docker volume mounts
exist on the host before containers are started, preventing Docker errors due to
missing paths or from creation of directories where files should be.

> **Note:** Socket files (ending with `.sock`) are ignored and not created.

### Finishing Commands (Optional)

- `deploy_finish` (string): Raw shell command(s) to run at the end of the
  deployment (from `<playbook_app>_finish`).

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: eliminyro.docker_deploy
      vars:
        playbook_app: myapp
        myapp_image: myorg/myapp
        myapp_image_tag: latest
        myapp_ports:
          - "8080:80"
        myapp_networks:
          - name: network
        myapp_volumes:
          - /srv/myapp/data:/data
        myapp_deps:
          - name: redis
            image: redis
            tag: 7
            ports:
              - "6379:6379"
            networks:
              - name: network
        myapp_adguard_url: "http://adguard.local:3000"
        myapp_adguard_username: "admin"
        myapp_adguard_password: "secret"
        myapp_domain_name: "myapp.local"
        myapp_adguard_answer: "192.168.1.100"
```

## License

MIT

## Author Information

Pavel Eliminyro <public@eliminyro.me>
