Installation
============

If you install Weboob from sources, you'll want to install the Python egg in development mode.
You'll be able to update the git repository with remote changes, without re-installing the software.
And if you plan to hack on Weboob, you'll see your own changes apply the same way.

Install
-------

As root:

``# ./setup.py develop``

The development mode installation doesn't copies files, but creates an egg-link
in the Python system packages directory:

* ``/usr/lib/python2.5/site-packages`` for Python 2.5
* ``/usr/local/lib/python2.6/dist-packages`` for Python 2.6

Scripts are copied to:

* ``/usr/bin`` for Python 2.5
* ``/usr/local/bin`` for Python 2.6

Uninstall
---------

* remove the ``/usr/local/lib/python2.6/dist-packages/weboob.egg-link``
* remove the weboob line from ``/usr/local/lib/python2.6/dist-packages/easy-install.pth``
