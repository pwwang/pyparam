
pyparam
=======

`
.. image:: https://img.shields.io/pypi/v/pyparam.svg?style=flat-square
   :target: https://img.shields.io/pypi/v/pyparam.svg?style=flat-square
   :alt: pypi
 <https://pypi.org/project/pyparam/>`_ `
.. image:: https://img.shields.io/github/tag/pwwang/pyparam.svg?style=flat-square
   :target: https://img.shields.io/github/tag/pwwang/pyparam.svg?style=flat-square
   :alt: pypi
 <https://github.com/pwwang/pyparam>`_ `
.. image:: https://img.shields.io/travis/pwwang/pyparam.svg?style=flat-square
   :target: https://img.shields.io/travis/pwwang/pyparam.svg?style=flat-square
   :alt: travis
 <https://travis-ci.org/pwwang/pyparam>`_ `
.. image:: https://img.shields.io/readthedocs/pyparam.svg?style=flat-square
   :target: https://img.shields.io/readthedocs/pyparam.svg?style=flat-square
   :alt: docs
 <https://pyparam.readthedocs.io/en/latest/>`_ `
.. image:: https://img.shields.io/codacy/grade/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
   :target: https://img.shields.io/codacy/grade/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
   :alt: codacy quality
 <https://app.codacy.com/project/pwwang/pyparam/dashboard>`_ `
.. image:: https://img.shields.io/codacy/coverage/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
   :target: https://img.shields.io/codacy/coverage/a34b1afaccf84019a6b138d40932d566.svg?style=flat-square
   :alt: codacy quality
 <https://app.codacy.com/project/pwwang/pyparam/dashboard>`_ 
.. image:: https://img.shields.io/pypi/pyversions/pyparam.svg?style=flat-square
   :target: https://img.shields.io/pypi/pyversions/pyparam.svg?style=flat-square
   :alt: pyver


Powerful parameter processing

Features
--------


* Command line argument parser (with subcommand support)
* ``list/array``\ , ``dict``\ , ``positional`` and ``verbose`` options support
* Type overwriting for parameters
* Rich API for Help page redefinition
* Parameter loading from configuration files
* Shell completions

Installation
------------

.. code-block:: shell

   pip install pyparam
   # install latest version via poetry
   git clone https://github.com/pwwang/pyparam.git
   cd pyparam
   poetry install

Basic usage
-----------

``examples/basic.py``

.. code-block:: python

   from pyparam import params
   # define arguments
   params.version      = False
   params.version.desc = 'Show the version and exit.'
   params.quiet        = False
   params.quiet.desc   = 'Silence warnings'
   params.v            = 0
   # verbose option
   params.v.type = 'verbose'
   # alias
   params.verbose = params.v
   # list/array options
   params.packages      = []
   params.packages.desc = 'The packages to install.'
   params.depends       = {}
   params.depends.desc  = 'The dependencies'

   print(params._parse())

.. code-block:: shell

   > python example/basic.py


.. image:: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/help.png
   :target: https://raw.githubusercontent.com/pwwang/pyparam/master/docs/static/help.png
   :alt: help


.. code-block:: shell

   > python examples/basic.py -vv --quiet \
       --packages numpy pandas pyparam \
       --depends.completions 0.0.1
   {'h': False, 'help': False, 'H': False,
    'v': 2, 'verbose': 2, 'version': False,
    'V': False, 'quiet': True, 'packages': ['numpy', 'pandas', 'pyparam'],
    'depends': {'completions': '0.0.1'}}

Documentation
-------------

`ReadTheDocs <https://pyparam.readthedocs.io/en/latest/>`_
