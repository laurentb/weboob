Setup your development environment
==================================

To develop on Weboob, you have to setup a development environment.

Git installation
----------------

Clone a git repository with this command::

    $ git clone https://git.weboob.org/weboob/weboob.git

We don't want to install Weboob on the whole system, so we create local directories where
we will put symbolic links to sources::

    $ mkdir ~/bin/
    $ export PATH=$PATH:$HOME/bin/
    $ mkdir ~/python/
    $ export PYTHONPATH=$PYTHONPATH:$HOME/python/

All executables in ~/bin/ will be accessible in console, and all python modules in ~/python/ will
be loadable. Add symbolic links::

    $ ln -s $HOME/src/weboob/weboob ~/python/
    $ find $HOME/src/weboob/scripts -type f -exec ln -s \{\} ~/bin/ \;

Repositories setup
------------------

As you may know, Weboob installs modules from `remote repositories <http://weboob.org/modules>`_. As you
probably want to use modules in sources instead of stable ones, because you will change them, or create
a new one, you have to add this line at end of ``~/.config/weboob/sources.list``::

    file:///home/me/src/weboob/modules

Then, run this command::

    $ weboob-config update

Run Weboob without installation
-------------------------------

This does not actually install anything, but lets you run Weboob from the source code,
while also using the modules from that source::

    $ ./tools/local_run.sh APPLICATION COMMANDS

For example, instead of running `videoob -b youtube search plop`, you would run::

    $ ./tools/local_run.sh videoob -b youtube search plop


Conclusion
----------

You can now edit sources, :doc:`create a module </guides/module>` or :doc:`an application </guides/application>`.
