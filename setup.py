from setuptools import setup, find_packages

setup(
    name = "piccolo2-server",
    version = "0.1",
    namespace_packages = ['piccolo2'],
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        "piccolo2-common",
        "python-jsonrpc",
        "psutil",
        "CherryPy > 5",
        "python-daemon",
        "lockfile >= 0.9",
    ],
    entry_points={
        'console_scripts': [
            'piccolo2-server = piccolo2.pserver:main',
        ],
    },

    # metadata for upload to PyPI
    author = "Magnus Hagdorn, Alasdair MacArthur, Iain Robinson",
    description = "Part of the piccolo2 system. This package provides the piccolo2 server",
    license = "GPL",
    url = "https://bitbucket.org/uoepiccolo/piccolo2-server",
)
