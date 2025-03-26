#!/usr/bin/env python3
import os
from setuptools import setup, find_packages

BASEDIR = os.path.abspath(os.path.dirname(__file__))


def get_version():
    """ Find the version of the package"""
    version_file = os.path.join(BASEDIR, 'ovos_tts_plugin_nos', 'version.py')
    major, minor, build, alpha = (None, None, None, None)
    with open(version_file) as f:
        for line in f:
            if 'VERSION_MAJOR' in line:
                major = line.split('=')[1].strip()
            elif 'VERSION_MINOR' in line:
                minor = line.split('=')[1].strip()
            elif 'VERSION_BUILD' in line:
                build = line.split('=')[1].strip()
            elif 'VERSION_ALPHA' in line:
                alpha = line.split('=')[1].strip()

            if ((major and minor and build and alpha) or
                    '# END_VERSION_BLOCK' in line):
                break
    version = f"{major}.{minor}.{build}"
    if alpha and int(alpha) > 0:
        version += f"a{alpha}"
    return version


def get_package_data():
    """Function to collect all necessary package data files."""
    data_files = []

    for root, dirs, files in os.walk(f'{BASEDIR}/ovos_tts_plugin_nos'):
        for file in files:
            data_files.append(os.path.relpath(os.path.join(root, file), 'ovos_tts_plugin_nos'))

    return data_files



def required(requirements_file):
    """ Read requirements file and remove comments and empty lines. """
    with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
        requirements = f.read().splitlines()
        if 'MYCROFT_LOOSE_REQUIREMENTS' in os.environ:
            print('USING LOOSE REQUIREMENTS!')
            requirements = [r.replace('==', '>=').replace('~=', '>=') for r in requirements]
        return [pkg for pkg in requirements
                if pkg.strip() and not pkg.startswith("#")]


PLUGIN_ENTRY_POINT = 'ovos-tts-plugin-nos = ' \
                     'ovos_tts_plugin_nos:NosTTSPlugin'


setup(
    name='ovos-tts-plugin-nos',
    version=get_version(),
    description='A galician tts plugin for OVOS',
    url='https://github.com/OpenVoiceOS/ovos-tts-plugin-nos',
    author='JarbasAi',
    author_email='jarbasai@mailfence.com',
    license='Apache-2.0',
    packages=find_packages(include=['ovos_tts_plugin_nos', 'ovos_tts_plugin_nos.*']),
    package_data={
        'ovos_tts_plugin_nos': get_package_data(),
    },
    install_requires=required("requirements.txt"),
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Linguistic',
        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='mycroft ovos plugin tts',
    entry_points={'mycroft.plugin.tts': PLUGIN_ENTRY_POINT}
)
