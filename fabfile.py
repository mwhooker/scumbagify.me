import os.path
from fabric.api import *

env.name = 'scumbagify'

env.user = 'ec2-user'
env.repo = 'git://github.com/mwhooker/scumbagify.me.git'
env.deploy = '/home/%s/www' % env.user
env.forward_agent = True

root = os.path.dirname(__file__)

def all():
    provision()
    deploy()

def restart():
    with settings(hide('stdout')):
        run('sudo supervisorctl restart scumbagify')

def provision():
    deps = [
        'git',
        'python-devel',
        'supervisor',
        'libevent-devel',
        'nginx',
        'zlib-devel',
        'libjpeg-devel'
    ]
    with settings(hide('stdout')):
        """
        run("grep 'enabled=1' %s || sudo sed --in-place '0,/enabled=0/s//enabled=1/' %s" % (
            '/etc/yum.repos.d/epel.repo', '/etc/yum.repos.d/epel.repo')
        )
        run('sudo find /home/ec2-user -type d -exec chmod a+x {} \;')
        """
        run('sudo yum groupinstall --assumeyes "Development Tools"')
        run('sudo yum install --assumeyes %s' % ' '.join(deps))
        run('sudo easy_install "supervisor == 3.0a12"')
        run('sudo easy_install virtualenv')
        run('mkdir -p %s' % env.deploy)
        put(
            os.path.join(root, 'deploy', 'supervisord.conf'),
            '/etc/', use_sudo=True
        )
        put(
            os.path.join(root, 'deploy', 'nginx.conf'),
            '/etc/nginx/conf.d/default.conf', use_sudo=True
        )
        with cd(env.deploy):
            run('stat venv || virtualenv ./venv')
            run('stat scumbagify || git clone %s scumbagify' % env.repo)
        put(
            os.path.join(root, 'scumbagify', 'config.py'),
            env.deploy + '/scumbagify/scumbagify/'
        )
        run('stat /tmp/supervisord.pid || sudo supervisord')
        run('sudo /etc/init.d/nginx restart')

def deploy():
    with settings(hide('stdout')):
        with cd(os.path.join(env.deploy, 'scumbagify')):
            run('git remote update && git reset --hard origin/master')
            with prefix('. ../venv/bin/activate'):
                run('python setup.py clean --all')
                run('python setup.py install')
    restart()
