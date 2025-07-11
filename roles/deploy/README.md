# Ansible Role: deploy

This role is part of the `eliminyro.docker` collection and automates the
deployment of containerized applications on a Docker host. It supports preparing
host directories, copying configuration files, rendering templates, deploying
optional sidecar/dependency containers and deploying the main application
container with flexible runtime options. A final command can also be executed
after deployment.

## Requirements

- Ansible 2.10+ and Python 3.x on the control node.
- The `community.general` collection for the `docker_container` module.
- Docker must already be installed on the target host.

## Overview

The role uses the variable `playbook_app` as the prefix for all other inputs.
For a given application name `myapp`, you define variables like `myapp_image`,
`myapp_ports`, etc., in your inventory or playbook. The role then maps these
variables to internal variables such as `deploy_image`, `deploy_ports` and so
on. This dynamic resolution avoids hard‑coding variable names inside the role.

The deployment follows these steps:

1. **Create directories and files** – Parses the host portion of volume mappings
   and ensures directories or placeholder files exist.
2. **Copy/render configuration files** – Processes lists of static config files
   or Jinja2 templates and places them in a per‑application configuration
   directory.
3. **Deploy dependency containers** – Optionally runs any sidecar/dependency
   containers before the main container.
4. **Deploy the main application container** – Starts the application container
   with the specified image, tags, networks, volumes, ports and other options.
5. **Run finishing commands** – Optionally executes arbitrary shell commands at
   the end of deployment.

## Role Variables

Variables are looked up dynamically based on `playbook_app`. The following
tables describe both the internal variables used by the role and the
corresponding user‑defined variables.

### Required

| Variable       | Default | Description                                                                                                                                |
| -------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `playbook_app` | _none_  | Name of the application/container. This value is used as a prefix for all dynamic variables and becomes the name of the running container. |

### Dynamic Variable Mapping

For an application called `myapp`, the role looks up user variables with the
`myapp_*` prefix and assigns them to internal variables. You can omit variables
you do not need; they will default to `omit` and not be passed to the
`docker_container` module.

| Internal variable       | User‑defined variable                         | Description                                                                       |
| ----------------------- | --------------------------------------------- | --------------------------------------------------------------------------------- |
| `deploy_image`          | `<playbook_app>_image`                        | Image name of the main container. **Required**.                                   |
| `deploy_image_tag`      | `<playbook_app>_image_tag` (default `latest`) | Image tag/version.                                                                |
| `deploy_command`        | `<playbook_app>_command`                      | Command executed in the container.                                                |
| `deploy_entrypoint`     | `<playbook_app>_entrypoint`                   | Override default entrypoint.                                                      |
| `deploy_pull`           | `<playbook_app>_pull`                         | Whether to pull the image. Boolean or `omit`.                                     |
| `deploy_restart_policy` | `<playbook_app>_restart_policy`               | Restart policy (e.g., `unless-stopped`). Defaults to `unless-stopped` if omitted. |
| `deploy_networks`       | `<playbook_app>_networks`                     | List of Docker networks to attach.                                                |
| `deploy_network_mode`   | `<playbook_app>_network_mode`                 | Network mode (e.g., `host`).                                                      |
| `deploy_healthcheck`    | `<playbook_app>_healthcheck`                  | Dictionary for health check configuration.                                        |
| `deploy_capabilities`   | `<playbook_app>_capabilities`                 | Additional Linux capabilities to add.                                             |
| `deploy_security_opt`   | `<playbook_app>_security_opt`                 | Security options.                                                                 |
| `deploy_privileged`     | `<playbook_app>_privileged`                   | Run container in privileged mode. Boolean.                                        |
| `deploy_user`           | `<playbook_app>_user`                         | User to run inside the container.                                                 |
| `deploy_hostname`       | `<playbook_app>_hostname`                     | Hostname for the container.                                                       |
| `deploy_env`            | `<playbook_app>_env`                          | Dictionary of environment variables.                                              |
| `deploy_ports`          | `<playbook_app>_ports`                        | List of port mappings (e.g., `"8080:80"`).                                        |
| `deploy_labels`         | `<playbook_app>_labels`                       | Dictionary of Docker labels.                                                      |
| `deploy_volumes`        | `<playbook_app>_volumes`                      | List of volume mappings (`host_path:container_path`).                             |
| `deploy_devices`        | `<playbook_app>_devices`                      | List of device mappings.                                                          |
| `deploy_auto_remove`    | `<playbook_app>_auto_remove`                  | Whether to remove the container on exit.                                          |
| `deploy_recreate`       | `<playbook_app>_recreate`                     | Whether to recreate the container when configuration changes.                     |
| `log_driver`            | `<playbook_app>_log_driver`                   | Log driver to use (e.g., `json-file`).                                            |
| `log_opt`               | `<playbook_app>_log_opt`                      | Dictionary of log driver options.                                                 |
| `deploy_deps`           | `<playbook_app>_deps`                         | List of dependency containers (see below).                                        |
| `deploy_deps_run`       | `<playbook_app>_deps_run` (default `false`)   | Whether to actually run dependency containers.                                    |
| `deploy_configlist`     | `<playbook_app>_configlist`                   | List of static files to copy into the configuration directory.                    |
| `deploy_templatelist`   | `<playbook_app>_templatelist`                 | List of Jinja2 templates to render.                                               |
| `deploy_finish`         | `<playbook_app>_finish`                       | Shell command(s) executed at the end of the deployment.                           |

#### Dependency containers (`deploy_deps`)

The `deploy_deps` list allows you to define sidecar or dependency containers.
Each item should be a dictionary with keys such as `name`, `image`, `tag`,
`command`, `entrypoint`, `pull`, `restart_policy`, `networks`, `network_mode`,
`healthcheck`, `capabilities`, `security_opt`, `privileged`, `user`, `env`,
`labels`, `ports`, `hostname`, `volumes`, `devices`, `auto_remove`, and
`recreate`. Unspecified keys will be omitted when launching the container.

#### Configuration files and templates

Use `deploy_configlist` to copy static files and `deploy_templatelist` to render
templates. Each entry must include `name` and `path` (relative inside the
container); optional keys are `user`, `group`, `mode` and `alt_app` to override
`playbook_app`. Files are sourced from `<role_path>/files/<playbook_app>/<name>`
and templates from `<role_path>/templates/<playbook_app>/<name>.j2`.

When volume mappings are provided, the role parses the host paths and ensures
directories exist. If a path appears to be a file (has an extension other than
`.sock`), a placeholder file is created with preserved timestamps.

### Finishing commands

If `deploy_finish` is set, its contents are executed on the remote host via the
`raw` module at the end of the deployment. Use this to perform any additional
initialization or cleanup tasks.

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: eliminyro.docker.deploy
      vars:
        playbook_app: myapp
        myapp_image: myorg/myapp
        myapp_image_tag: latest
        myapp_ports:
          - "8080:80"
        myapp_networks:
          - name: "mynetwork"
        myapp_volumes:
          - /srv/myapp/data:/data
        myapp_deps_run: true
        myapp_deps:
          - name: redis
            image: redis
            tag: "7"
            ports:
              - "6379:6379"
            networks:
              - name: "mynetwork"
```

## Capabilities and Idempotency

This role is idempotent: running it multiple times will not redeploy unchanged
containers or recreate existing files/directories. It does not implement
rollback; you can remove created containers manually or via docker rm if
necessary.
