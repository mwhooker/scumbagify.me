from scumbagify.web import __version__
from setuptools import setup, find_packages


install_requires = [
    'flask',
    'distribute',
    'gevent',
    'boto',
    'gunicorn',
    'face_detect',
    'PIL'
]

if __name__ == '__main__':
    import distribute_setup
    distribute_setup.use_setuptools()

    setup(
        name='scumbagify',
        version=__version__,
        author='Matthew Hooker',
        author_email='mwhooker@gmail.com',
        url='https://github.com/mwhooker/scumbagify.me',
        description='Put a hat on it.',
        packages=find_packages(),
        package_data={
            '': ['config.py']
        },
        zip_safe=False,
        install_requires=install_requires,
        include_package_data=True,
    )
