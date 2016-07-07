import os

from contextlib import contextmanager as _contextmanager
from fabric.context_managers import prefix
from fabric.operations import get, run, sudo
from fabric.state import env
from fabric.contrib import django

django.project('hhypermap_searchlayers_api')


environments = {
    'production':{
        'hosts': os.environ.get('HOST'),
        'source_code': '/home/ubuntu/hhypermap-searchlayers-api',
        'supervisor': [
            'supervisorctl restart all',
        ],
        'virtualenv': {
            'virtualenv_name': 'hhypermap_searchlayers_api',
            'virtualenv_sh': '/usr/local/bin/virtualenvwrapper.sh',
        },
        'git':{
            'parent':'origin',
            'branch':'master',
        }
    }
}


# Utils
@_contextmanager
def virtualenv():
    """ Wrapper to run commands in the virtual env context """
    environment = environments['default']
    workon_home = environment['virtualenv'].get('workon_home', '~/.virtualenvs')
    with prefix('export WORKON_HOME={0}'.format(workon_home)):
        virtualenv_sh = environment['virtualenv'].get('virtualenv_sh', '/etc/bash_completion.d/virtualenvwrapper')
        with prefix('source {0}'.format(virtualenv_sh)):
            virtualenv_name = environment['virtualenv'].get('virtualenv_name')
            with prefix('workon {0}'.format(virtualenv_name)):
                source_code = environment['source_code']
                with prefix('cd {0}'.format(source_code)):
                    yield


def django(command):
    with virtualenv():
        full_command = 'python manage.py {0}'.format(command)
        run(full_command)


# setup
def production():
    environments['default'] = environments['production']
    env.hosts = environments['production']['hosts']
    env.key_filename = os.environ.get("HOSTKEY")


def git_pull():
    with virtualenv():
        run('git pull %s %s' % (environments['default']['git']['parent'], environments['default']['git']['branch']))
        #run('git pull')


def pyclean():
    with virtualenv():
        run('find . -type f -name "*.py[co]" -exec rm -f \{\} \;')


def supervisor_restart():
    sudo(environments['default']['supervisor'][0])

def deploy():
    git_pull()
    pyclean()
    supervisor_restart()

