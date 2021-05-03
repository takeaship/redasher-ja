from setuptools import setup, find_packages
from redasher import __version__
def read(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

setup(
    name = 'redasher',
    version = __version__,
    author = 'Som Energia SCCL',
    author_email = 'itcrowd@somenergia.coop',
    license = 'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
    description = 'Manage Redash objects as files, enabling version control and development environments',
    long_description = read("README.md"),
    long_description_content_type = "text/markdown",
    url = 'https://github.com/som-energia/redasher',
    py_modules = [
        'redasher',
    ],
    packages = find_packages(exclude=['*[tT]est*']),
    install_requires = read('requirements.txt').splitlines(),
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Operating System :: POSIX",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    entry_points = '''
        [console_scripts]
        redasher=redasher.cli:cli
    ''',
)
