Setup your development environment
==================================

To develop on Weboob, you have to setup a development environment.

Git installation
----------------

Clone a git repository with this command::

    $ git clone git://git.symlink.me/pub/weboob/devel.git

We don't want to install Weboob on the whole system, so we create local directories where
we will put symbolic links to sources::

    $ mkdir ~/bin/
    $ export PATH=$PATH:$HOME/bin/
    $ mkdir ~/python/
    $ export PYTHONPATH=$PYTHONPATH:$HOME/python/

All executables in ~/bin/ will be accessible in console, and all python modules in ~/python/ will
be loadable. Add symbolic links::

    $ ln -s $HOME/src/weboob/weboob ~/python/
    $ find $HOME/src/weboob/scripts -exec ln -s \{\} ~/bin/ \;

Repositories setup
------------------

As you may know, Weboob installs modules from `remote repositories <http://weboob.org/modules>`_. As you
probably want to use modules in sources instead of stable ones, because you will change them, or create
a new one, you have to add this line at end of ``~/.config/weboob/sources.list``::

    file:///home/me/src/weboob/modules

Then, run this command::

    $ weboob-config update

Conclusion
----------

You can now edit sources, :doc:`create a module </guides/module>` or :doc:`an application </guides/application>`.
