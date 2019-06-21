#
#   module tank.core.run
#

import os
import tempfile
from time import time

import sh
from cement import fs
import yaml

from tank.core.testcase import TestCase


class Run:
    """
    Single run of a tank testcase.
    """

    @classmethod
    def new_run(cls, app, testcase: TestCase):
        # TODO fancy names
        run_id = str(int(time()))

        fs.ensure_dir_exists(cls._runs_dir(app))

        temp_dir = tempfile.mkdtemp(prefix=run_id, dir=cls._runs_dir(app))
        cls._save_meta(temp_dir, testcase)

        # make a copy to make sure any alterations of the source won't affect us
        testcase.save(fs.join(temp_dir, 'testcase.yml'))

        os.rename(temp_dir, fs.join(cls._runs_dir(app), run_id))

        return cls(app, run_id)


    def __init__(self, app, run_id: str):
        self._app = app
        self.run_id = run_id

        self._testcase = TestCase(fs.join(self._dir, 'testcase.yml'))

    def init(self):
        """
        Download plugins, modules for Terraform.
        """
        self._generate_tf_plan()

        sh.Command(self._app.terraform_run_command)(
            "init", "-backend-config", "path={}".format(self._tf_state_file), self._tf_plan_dir,
            _env=self._make_env())

    def create(self):
        raise NotImplementedError()

    def dependency(self):
        raise NotImplementedError()

    def provision(self):
        raise NotImplementedError()


    @classmethod
    def _runs_dir(cls, app) -> str:
        return fs.join(app.user_dir, 'run')

    @classmethod
    def _save_meta(cls, run_dir: str, testcase: TestCase):
        meta = {
            'testcase_filename': fs.abspath(testcase.filename),
            'created': int(time()),
        }

        with open(fs.join(run_dir, 'meta.yml'), 'w') as fh:
            yaml.dump(meta, fh, default_flow_style=False)


    def _make_env(self):
        fs.ensure_dir_exists(self._tf_data_dir)
        fs.ensure_dir_exists(self._log_dir)

        env = self._app.app_env

        env["TF_LOG_PATH"] = fs.join(self._log_dir, 'terraform.log')
        env["TF_DATA_DIR"] = self._tf_data_dir
        env["TF_VAR_state_path"] = self._tf_state_file

        env["ANSIBLE_ROLES_PATH"] = fs.join(self._dir, "ansible_roles")
        env["ANSIBLE_CONFIG"] = fs.join(fs.abspath(os.path.dirname(__file__)), '..', 'tools', 'ansible', 'ansible.cfg')

        return env

    def _generate_tf_plan(self):
        """
        Generation of Terraform manifests specific for this run and user preferences.
        """

        # for common_key in self.config.keys(self.Meta.label):
        #     env["TF_VAR_" + common_key] = \
        #         self.config.get(self.Meta.label, common_key)
        # for provider_key in self.config.keys(self.provider):
        #     env["TF_VAR_" + provider_key] = \
        #         self.config.get(self.provider, provider_key)

        raise NotImplementedError()


    @property
    def _dir(self) -> str:
        return fs.join(self.__class__._runs_dir(self._app), self.run_id)

    @property
    def _tf_data_dir(self) -> str:
        return fs.join(self._dir, 'tf_data')

    @property
    def _tf_plan_dir(self) -> str:
        return fs.join(self._dir, 'tf_plan')

    @property
    def _tf_state_file(self) -> str:
        return fs.join(self._dir, "blockchain.tfstate")

    @property
    def _log_dir(self) -> str:
        return fs.join(self._dir, 'log')

