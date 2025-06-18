from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import os
import platform

class AravisBuildExt(build_ext):
    def build_extensions(self):
        # Add compiler flags
        if sys.platform == 'win32':
            self.compiler.compiler_so = ['/MD']
            # Add MSYS2 paths for Windows
            msys2_path = os.environ.get('MSYS2_PATH', 'C:/msys64')
            self.compiler.include_dirs.extend([
                f'{msys2_path}/mingw64/include',
                f'{msys2_path}/mingw64/include/aravis-0.8'
            ])
            self.compiler.library_dirs.extend([
                f'{msys2_path}/mingw64/lib'
            ])
        build_ext.build_extensions(self)

# Define the extension module
aravis_module = Extension(
    'aravis',
    sources=['aravis_binding.c'],
    libraries=['aravis-0.8'],  # Link against Aravis library
    include_dirs=[
        '/usr/include/aravis-0.8',  # Linux
        '/usr/local/include/aravis-0.8',  # macOS
        '/usr/include/glib-2.0',  # GLib main headers
        '/usr/lib/aarch64-linux-gnu/glib-2.0/include',  # GLib generated headers
    ],
    library_dirs=[
        '/usr/lib',  # Linux
        '/usr/local/lib',  # macOS
    ],
)

# Platform-specific dependencies
if platform.system() == 'Windows':
    install_requires = []
    setup_requires = ['setuptools>=42', 'wheel']
else:
    install_requires = []
    setup_requires = ['setuptools>=42', 'wheel']

setup(
    name='python-aravis',
    version='0.1.0',
    description='Python bindings for Aravis library',
    author='Your Name',
    author_email='your.email@example.com',
    ext_modules=[aravis_module],
    cmdclass={'build_ext': AravisBuildExt},
    install_requires=install_requires,
    setup_requires=setup_requires,
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Image Recognition',
        'Topic :: Multimedia :: Video :: Capture',
    ],
) 