import os
from typing import Dict
import pathlib

import sh
from tinydb import TinyDB
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal
from cement.utils import fs

from tank.core.exc import MixbytesTankError
from tank.controllers.base import Base
from tank.controllers.cluster import Cluster


def _default_config() -> Dict:
    config = init_defaults('tank',
                           'digitalocean',
                           'log.logging')

    config['tank'] = {
        'state_file': '~/.tank/tank.json',
        'provider': 'digitalocean',
        'terraform_run_command': '/usr/local/bin/terraform',
        'terraform_inventory_run_command': '/usr/local/bin/terraform-inventory',
        'blockchain_instances': 2
    }

    config['digitalocean']['private_interface'] = 'eth0'
    config['log.logging']['level'] = 'info'

    return config


def extend_tinydb(app):
    state_file = app.config.get('tank', 'state_file')
    state_file = fs.abspath(state_file)
    state_dir = os.path.dirname(state_file)
    if not os.path.exists(state_dir):
        os.makedirs(state_dir)

    app.extend('state', TinyDB(state_file))


class MixbytesTank(App):
    """MixBytes Tank primary application."""

    class Meta:
        label = 'tank'

        # configuration defaults
        config_defaults = _default_config()

        # call sys.exit() on close
        close_on_exit = True

        # load additional framework extensions
        extensions = [
            'yaml',
            'colorlog',
            'jinja2',
        ]

        # List of configuration directory
        config_dirs = ['~/.tank']

        # configuration handler
        config_handler = 'yaml'

        # configuration file suffix
        config_file_suffix = '.yml'

        # set the log handler
        log_handler = 'colorlog'

        # set the output handler
        output_handler = 'jinja2'

        template_handler = 'jinja2'

        # register handlers
        handlers = [
            Base,
            Cluster
        ]

        # register hooks
        hooks = [
            ('post_setup', extend_tinydb),
        ]


    def setup(self):
        super(MixbytesTank, self).setup()
        self.root_dir = os.path.realpath(os.path.dirname(__file__))+"/"

        self.provider = self.config.get(self.Meta.label, "provider")
        self.terraform_plan_dir = fs.join(self.root_dir, 'providers', self.provider)

    @property
    def app_env(self) -> Dict:
        env = os.environ.copy()
        env["TF_LOG"] = "TRACE"
        env["TF_IN_AUTOMATION"] = "true"
        return env

    @property
    def blockchain_instances(self) -> int:
        return int(self.config.get(self.Meta.label, 'blockchain_instances'))

    @property
    def terraform_run_command(self) -> str:
        return self.config.get(self.Meta.label, 'terraform_run_command')

    @property
    def terraform_inventory_run_command(self) -> str:
        return self.config.get(self.Meta.label, 'terraform_inventory_run_command')

    @property
    def user_dir(self) -> str:
        return fs.abspath(fs.join(pathlib.Path.home(), '.tank'))


    def _check_terraform_availability(self):
        try:
            sh.Command(self.terraform_run_command, "--version")
        except Exception:
            raise MixbytesTankError("Error calling Terraform at '{}'".format(self.terraform_run_command))

    def _check_terraform_inventory_availability(self):
        try:
            sh.Command(self.terraform_inventory_run_command, "-version")
        except Exception:
            raise MixbytesTankError("Error calling Terraform Inventory at '{}'".format(
                self.terraform_inventory_run_command))


class MixbytesTankTest(TestApp, MixbytesTank):
    """A sub-class of MixbytesTank that is better suited for testing."""

    class Meta:
        label = 'tank'


def main():
    with MixbytesTank() as app:
        try:
            app._check_terraform_availability()
            app._check_terraform_inventory_availability()
            app.run()

        except MixbytesTankError as e:
            print('MixbytesTankError: {}'.format(e))
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        # FIXME better signal handling
        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()
