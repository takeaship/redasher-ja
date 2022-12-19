from setuptools import setup, find_packages
from redasher_ja import __version__
def read(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

setup(
    name = 'redasher-ja',
    version = __version__,
    author = 'Takeshi Masukawa',
    author_email = 'spiral.spirit.spider@gmail.com',
    license = 'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
    description = 'Manage Redash objects as files, enabling version control and development environments. This is a Japanese specialized version of redasher.',
    long_description = read("README.md"),
    long_description_content_type = "text/markdown",
    url = 'https://github.com/takeaship/redasher-ja',
    py_modules = [
        'redasher_ja',
    ],
    packages = find_packages(exclude=['*[tT]est*']),
    install_requires = read('requirements.txt').splitlines(),
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3.11",
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
