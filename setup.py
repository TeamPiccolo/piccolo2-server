from setuptools import setup, find_packages

setup(
    name = "piccolo2-server",
    version = "0.1",
    namespace_packages = ['piccolo2'],
    packages = find_packages(),
    install_requires = [
        "piccolo2-common",
        "python-jsonrpc",
        "psutil",
        "CherryPy > 5"
    ],
    entry_points={
        'console_scripts': [
            'piccolo2-server = piccolo2.pserver:main',
        ],
    },
)
