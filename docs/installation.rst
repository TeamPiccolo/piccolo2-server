Installation
************

The Piccolo includes a Raspberry Pi which runs *Piccolo Server*. This software controls the Piccolo's hardware (spectrometers, shutters, ...), handles the recording of data, and provides an application programming interface that can be used to control the Piccolo. The Piccolo is usually remotely-controlled from a laptop via a network or radio link.

The Piccolo software is installed on the memory card of the Raspberry Pi that is included with the Piccolo. These instructions are therefore not required for a new instrument. The procedure described here can be used to install the software on a new memory card.

========
Raspbian
========

The Raspberry Pi is a miniature computer which runs an operating system, *Raspbian*, which is a variant of Linux.

*Raspbian* can be obtained from the `downloads page <https://www.raspberrypi.org/downloads>`_ at the `Raspberry Pi Foundation <https://www.raspberrypi.org/>`_. At the time of writing, the latest version is *Raspbian Jessie*, released on 18th March 2016. (*Raspbian Jessie Lite* has not been tested with the Piccolo.)

Download the zip (or Torrent) file and follow `their instructions <https://www.raspberrypi.org/documentation/installation/installing-images/README.md>` instructions to image it onto a memory (SD) card.

==============
Python version
==============

The Piccolo software is written in Python. Piccolo Server can be run in Python 2.

==================
Network connection
==================

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

There are two tools which may be used to install Python modules on the Raspberry Pi:

* apt-get
* pip

*ConfigObj* is a Python module for reading configuration files, more often known as *ini* files on Windows systems. It is required by the Piccolo software to read the *server configuration file*.

To install *ConfigObj* on the Raspberry Pi, first ensure that a network connection is available, then type::

  sudo apt-get install python3-configobj

or::

  sudo apt-get install python-configobj

for Python 2.

To check that *ConfigObj* has been installed, start Python (by typing python3 in a terminal) and try to import the module:

  import configobj

If no error is reported then *ConfigObj* has been successfully installed.

*Ch

sudo apt-get install python-jsonrpc2
sudo apt-get install python-jsonrpclib

*CherryPy* is a small web framework for Python. It allows the Piccolo software to use an application programming interface based on popular and standard protocols designed for the world-wide web. *CherryPy* cannot be installed with apt-get because it gives an error (missing encoding module). Instead use pip:

  sudo apt-get install python-pip
  sudo pip install cherrypy

*psutil* is Python module that can monitor...something. Type::

  sudo apt-get install python-psutil

(*psutil* cannot be installed on Ubuntu with *pip*. A file called *Python.h* is missing.)

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

or

  python piccolo-server.py

This should produce the error message::

  no such configuration file

===========================
Create a configuraiton file
===========================

The default configuration file can be found in the source code to piccolo.PiccoloConfig.py. Copy and paste this text into the file in the pdata directory: /home/pi/piccolo/pdata.

The shutter channels upwelling and downwelling must be defined. (Channel names should be case insensitive, so upwelling and Upwelling refer to the same channel.) Currently shutters are not implemented, so set the shutter to -1 for all channels.

==============
Piccolo Server
==============

Once the configuration file is in place, Piccolo server can be started::

  python piccolo-server.py

A number of messages should appear, including::

  Serving on http://localhost:8080
  Bus STARTED

This final message indicates that *Piccolo Server* is running, and that the address to which commands should be sent is (the default)::

  http://localhost:8080
