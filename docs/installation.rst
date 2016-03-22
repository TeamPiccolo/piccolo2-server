====================
Check Python version
====================

The Piccolo software is written in Python. Version 3 or later must be installed on both the Raspberry Pi and the laptop.

Python may be installed by default on the Raspberry Pi. To check, type::

  python3

in a terminal.

=====================================
Connect the Raspberry Pi to a network
=====================================

This can be done with a network (Ethernet) cable or a USB wireless adapter. (Neither of these is provided with the Piccolo.)

To test, type:

  ping www.google.com

=============================
Check packages are up to date
=============================

Type::

  sudo apt-get update

===============================
Install required Python modules
===============================

The Piccolo software requires a number of additional Python modules to be installed on the Raspberry Pi (in addition to those that come with the *Raspbian* operating system).

*ConfigObj* is a Python module for reading configuration files, more often known as *ini* files on Windows systems. It is required by the Piccolo software to read the *server configuration file*.

To install *ConfigObj* on the Raspberry Pi, first ensure that a network connection is available, then type::

  sudo apt-get install python3-configobj

To check that *ConfigObj* has been installed, start Python (by typing python3 in a terminal) and try to import the module:

  import configobj

If no error is reported then *ConfigObj* has been successfully installed.


sudo apt-get install python-jsonrpc2
sudo apt-get install python-jsonrpclib


Step 1: Install required modules.



Cherrypy is a web framework used by ```piccolo_server```.


=========================================
Add *Piccolo Server* to the *Python path*
=========================================

Type::

  export PYTHONPATH=/home/pi/piccolo/piccolo_server

==================
Run Piccolo server
==================

There are a number of different ways to start *Piccolo server*. If *Piccolo server* is not already started, it can run from a terminal by typing::

  python3 piccolo-server.py
