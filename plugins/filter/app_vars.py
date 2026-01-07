# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Pavel Eliminyro
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from collections.abc import Mapping

DOCUMENTATION = r'''
name: resolve_app_vars
short_description: Resolve application-prefixed variables dynamically
version_added: "1.2.0"
description:
  - Takes an application name and a variable specification dictionary.
  - Looks up variables prefixed with the app name from hostvars.
  - Returns a dictionary with resolved values or defaults.
positional: app_name, var_specs
options:
  app_name:
    description: The application name prefix (e.g., 'myapp').
    type: str
    required: true
  var_specs:
    description: >
      Dictionary mapping variable names to their defaults.
      Keys are variable suffixes (e.g., 'image'), values are defaults.
    type: dict
    required: true
  hostvars:
    description: The hostvars dictionary for the current host.
    type: dict
    required: true
author:
  - Pavel Eliminyro
'''

EXAMPLES = r'''
# In defaults/main.yml:
_app_var_specs:
  image: null
  image_tag: 'latest'
  restart_policy: 'unless-stopped'
  volumes: []

# Resolve all variables at once:
deploy: "{{ playbook_app | eliminyro.docker.resolve_app_vars(_app_var_specs, hostvars[inventory_hostname]) }}"

# Access resolved values:
# deploy.image, deploy.image_tag, deploy.restart_policy, etc.
'''

RETURN = r'''
_value:
  description: Dictionary with resolved variable values.
  type: dict
'''


class FilterModule:
    """Ansible filter plugin for resolving app-prefixed variables."""

    def filters(self):
        return {
            'resolve_app_vars': self.resolve_app_vars,
        }

    def resolve_app_vars(self, app_name, var_specs, hostvars):
        """
        Resolve application-prefixed variables from hostvars.

        Args:
            app_name: The application name prefix (e.g., 'myapp')
            var_specs: Dict mapping var names to default values
            hostvars: The hostvars dict for the current host

        Returns:
            Dict with resolved values for each variable in var_specs
        """
        if not isinstance(app_name, str):
            raise TypeError(f"app_name must be a string, got {type(app_name).__name__}")
        if not isinstance(var_specs, Mapping):
            raise TypeError(f"var_specs must be a dict-like object, got {type(var_specs).__name__}")
        if not isinstance(hostvars, Mapping):
            raise TypeError(f"hostvars must be a dict-like object, got {type(hostvars).__name__}")

        result = {}
        for var_name, default in var_specs.items():
            lookup_key = f"{app_name}_{var_name}"
            value = hostvars.get(lookup_key, default)
            # Skip None values - use .get('key', omit) in templates to handle missing keys
            if value is not None:
                result[var_name] = value

        return result
