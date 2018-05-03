#!/usr/bin/env python
from __future__ import print_function


import os
import pkgutil
import shutil
import sys

try:
    _mnfe = ModuleNotFoundError
except NameError:
    ModuleNotFoundError = ImportError

try:
    import pandokia
except (ImportError, NameError, ModuleNotFoundError):
    pandokia = False

try:
    import numpy
except ImportError:
    print("numpy not found, please install it.", file=sys.stderr)
    exit(1)

try:
    from astropy import wcs
except ImportError:
    print("astropy not found, please install it.", file=sys.stderr)
    exit(1)

from glob import glob
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install
from subprocess import check_call, CalledProcessError


if not pkgutil.find_loader('relic'):
    relic_local = os.path.exists('relic')
    relic_submodule = (relic_local and
                       os.path.exists('.gitmodules') and
                       not os.listdir('relic'))
    try:
        if relic_submodule:
            check_call(['git', 'submodule', 'update', '--init', '--recursive'])
        elif not relic_local:
            check_call(['git', 'clone', 'https://github.com/spacetelescope/relic.git'])

        sys.path.insert(1, 'relic')
    except CalledProcessError as e:
        print(e)
        exit(1)

import relic.release

NAME = 'drizzlepac'
CMDCLASS = {}
version = relic.release.get_info()
relic.release.write_template(version, NAME)

# Setup C module include directories
include_dirs = []
numpy_includes = [numpy.get_include()]
wcs_includes = [os.path.join(wcs.get_include(), 'astropy_wcs'),
                os.path.join(wcs.get_include(), 'wcslib')]

include_dirs.extend(numpy_includes)
include_dirs.extend(wcs_includes)

# Setup C module macros
define_macros = []

# Handle MSVC `wcsset` redefinition
if sys.platform == 'win32':
    define_macros += [
        ('_CRT_SECURE_NO_WARNING', None),
        ('__STDC__', 1)
    ]

# Deprecation warning:
#    Pandokia integration will be removed in a later release.
if pandokia:
    fctx_includes = [os.path.join(os.path.dirname(pandokia.__file__),
                                  'runners', 'maker')]
    include_dirs.extend(fctx_includes)

# Distribute compiled documentation alongside the installed package
docs_compiled_src = os.path.normpath('build/sphinx/html')
docs_compiled_dest = os.path.normpath('{0}/htmlhelp'.format(NAME))


class InstallCommand(install):
    """Ensure drizzlepac's C extensions are available when imported relative
    to the documentation, instead of relying on `site-packages`. What comes
    from `site-packages` may not be the same drizzlepac that was *just*
    compiled.
    """
    def run(self):
        build_cmd = self.reinitialize_command('build_ext')
        build_cmd.inplace = 1
        self.run_command('build_ext')
        install.run(self)
        if not os.path.exists(docs_compiled_dest):
            print('warning: Sphinx "htmlhelp" documentation was '
                  'NOT bundled!', file=sys.stderr)


CMDCLASS['install'] = InstallCommand


try:
    from sphinx.cmd.build import build_main
    from sphinx.setup_command import BuildDoc

    class BuildSphinx(BuildDoc):
        """Build Sphinx documentation after compiling C extensions"""

        description = 'Build Sphinx documentation'

        def initialize_options(self):
            BuildDoc.initialize_options(self)

        def finalize_options(self):
            BuildDoc.finalize_options(self)

        def run(self):
            build_cmd = self.reinitialize_command('build_ext')
            build_cmd.inplace = 1
            self.run_command('build_ext')
            build_main(['-b', 'html', 'doc/source', 'build/sphinx/html'])

            # Bundle documentation inside of drizzlepac
            if os.path.exists(docs_compiled_src):
                if os.path.exists(docs_compiled_dest):
                    shutil.rmtree(docs_compiled_dest)

                shutil.copytree(docs_compiled_src, docs_compiled_dest)

    CMDCLASS['build_sphinx'] = BuildSphinx

except ImportError:
    print('warning: Sphinx is not installed! "htmlhelp" documention cannot '
          'be compiled!', file=sys.stderr)


setup(
    name=NAME,
    version=version.pep386,
    author='Megan Sosey, Warren Hack, Christopher Hanley, '
           'Chris Sontag, Mihai Cara',
    author_email='help@stsci.edu',
    description='drizzle tools: combines astronomical images, including '
                'modeling distortion, removing cosmic rays, and generally '
                'improving fidelity of data in the final image',
    url='https://github.com/spacetelescope/drizzlepac',
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    setup_requires=[
        'numpydoc',
        'stsci_rtd_theme',
        'sphinx',
        'sphinx-automodapi',
        'sphinx_rtd_theme',
    ],
    install_requires=[
        'astropy',
        'fitsblender',
        'nictools',
        'nose',
        'numpy',
        'scipy',
        'spherical_geometry',
        'stsci.tools',
        'stsci.convolve',
        'stsci.image>=2.3.0',
        'stsci.imagemanip',
        'stsci.imagestats',
        'stsci.ndimage',
        'stsci.stimage',
        'stwcs',
    ],
    packages=find_packages(),
    package_data={
        'drizzlepac': [
            'pars/*',
            '*.help',
            'htmlhelp/*',
            'htmlhelp/_*/*',
            'htmlhelp/_*/*/*',
        ]
    },
    entry_points={
        'console_scripts': [
            'mdriz=drizzlepac.mdriz:main',
            'resetbits=drizzlepac.resetbits:main',
            'updatenpol=drizzlepac.updatenpol:main',
            'runastrodriz=drizzlepac.runastrodriz:main'
        ],
    },
    ext_modules=[
        Extension('drizzlepac.cdriz',
                  glob('src/*.c'),
                  include_dirs=include_dirs,
                  define_macros=define_macros),
    ],
    cmdclass=CMDCLASS,
)
