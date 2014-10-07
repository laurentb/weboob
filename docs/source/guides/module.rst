Write a new module
==================

This guide aims to learn how to write a new module for `Weboob <http://weboob.org>`_.

Before read it, you should :doc:`setup your development environment </guides/setup>`.

What is a module
****************

A module is an interface between a website and Weboob. It represents the python code which is stored
in repositories.

Weboob applications need *backends* to interact with websites. A *backend* is an instance of a *module*, usually
with several parameters like your username, password, or other options. You can create multiple *backends*
for a single *module*.

Select capabilities
*******************

Each module implements one or many :doc:`capabilities </api/capabilities/index>` to tell what kind of features the
website provides. A capability is a class derived from :class:`weboob.capabilities.base.Capability` and with some abstract
methods (which raise ``NotImplementedError``).

A capability needs to be as generic as possible to allow a maximum number of modules to implement it.
Anyway, if you really need to handle website specificities, you can create more specific sub-capabilities.

For example, there is the :class:`CapMessages <weboob.capabilities.messages.CapMessages>` capability, with the associated
:class:`CapMessagesPost <weboob.capabilities.messages.CapMessagesPost>` capability to allow answers to messages.

Pick an existing capability
---------------------------

When you want to create a new module, you may have a look on existing capabilities to decide which one can be
implemented. It is quite important, because each already existing capability is supported by at least one application.
So if your new module implements an existing capability, it will be usable from the existing applications right now.

Create a new capability
-----------------------

If the website you want to manage implements some extra-features which are not implemented by any capability,
you can introduce a new capability.

You should read the related guide to know :doc:`how to create a capability </guides/capability>`.

The module tree
***************

Create a new directory in ``modules/`` with the name of your module. In this example, we assume that we want to create a
module for a bank website which URL is http://www.example.com. So we will call our module **example**, and the selected
capability is :class:`CapBank <weboob.capabilities.bank.CapBank>`.

It is recommended to use the helper tool ``tools/boilerplate.py`` to build your
module tree. There are several templates available:

* **base** - create only base files
* **comic** - create a comic module
* **cap** - create a module for a given capability

For example, use this command::

    $ tools/boilerplate.py cap example CapBank

In a module directory, there are commonly these files:

* **__init__.py** - needed in every python modules, it exports your :class:`Module <weboob.tools.backend.Module>` class.
* **module.py** - defines the main class of your module, which derives :class:`Module <weboob.tools.backend.Module>`.
* **browser.py** - your browser, derived from :class:`Browser <weboob.browser.browsers.Browser>`, is called by your module to interact with the supported website.
* **pages.py** - all website's pages handled by the browser are defined here
* **test.py** - functional tests
* **favicon.png** - a 64x64 transparent PNG icon

Update modules list
-------------------

As you are in development mode, to see your new module in ``weboob-config``'s list, you have to update ``modules/modules.list`` with this command::

    $ weboob-config update

To be sure your module is correctly added, use this command::

    $ weboob-config info example
    .------------------------------------------------------------------------------.
    | Module example                                                               |
    +-----------------.------------------------------------------------------------'
    | Version         | 201405191420
    | Maintainer      | John Smith <john.smith@example.com>
    | License         | AGPLv3+
    | Description     | Example bank website
    | Capabilities    | CapBank, CapCollection
    | Installed       | yes
    | Location        | /home/me/src/weboob/modules/example
    '-----------------'

If the last command does not work, check your :doc:`repositories setup </guides/setup>`.

Module class
*************

Edit ``module.py``. It contains the main class of the module derived from :class:`Module <weboob.tools.backend.Module>` class::

    class ExampleModule(Module, CapBank):
        NAME = 'example'                         # The name of module
        DESCRIPTION = u'Example bank website'    # Description of your module
        MAINTAINER = u'John Smith'               # Name of maintainer of this module
        EMAIL = 'john.smith@example.com'         # Email address of the maintainer
        LICENSE = 'AGPLv3+'                      # License of your module
        VERSION = '0.i'                          # Version of weboob

In the code above, you can see that your ``ExampleModule`` inherits :class:`CapBank <weboob.capabilities.bank.CapBank>`, as
we have selected it for the supported website.

Configuration
-------------

When a module is instanced as a backend, you probably want to ask parameters to user. It is managed by the ``CONFIG`` class
attribute. It supports key/values with default values and some other parameters. The :class:`Value <weboob.tools.value.Value>`
class is used to define a value.

Available parameters of :class:`Value <weboob.tools.value.Value>` are:

* **label** - human readable description of a value
* **required** - if ``True``, the backend can't loaded if the key isn't found in its configuration
* **default** - an optional default value, used when the key is not in config. If there is no default value and the key
  is not found in configuration, the **required** parameter is implicitly set
* **masked** - if ``True``, the value is masked. It is useful for applications to know if this key is a password
* **regexp** - if specified, on load the specified value is checked against this regexp, and an error is raised if it doesn't match
* **choices** - if this parameter is set, the value must be in the list

.. note::

    There is a special class, :class:`ValueBackendPassword <weboob.tools.value.ValueBackendPassword>`, which is used to manage
    private parameters of the config (like passwords or sensible information).

For example::

    from weboob.tools.value import Value, ValueBool, ValueInt, ValueBackendPassword
    from weboob.tools.backend import BackendConfig

    # ...
    class ExampleModule(Module, CapBank):
        # ...
        CONFIG = BackendConfig(Value('username',                label='Username', regexp='.+'),
                               ValueBackendPassword('password', label='Password'),
                               ValueBool('get_news',            label='Get newspapers', default=True),
                               Value('choice',                  label='Choices', choices={'value1': 'Label 1',
                                                                                          'value2': 'Label 2'}, default='1'),
                               Value('regexp',                  label='Birthday', regexp='^\d+/\d+/\d+$'),
                               ValueInt('integer',              label='A number', required=True))


Implement capabilities
----------------------

You need to implement each method of all of the capabilities your module implements. For example, in our case::

    # ...
    class ExampleModule(Module, CapBank):
        # ...

        def iter_accounts(self):
            raise NotImplementedError()

        def get_account(self, id):
            raise NotImplementedError()

        def iter_history(self, account):
            raise NotImplementedError()

        def iter_coming(self, account):
            raise NotImplementedError()

If you ran the ``boilerplate`` script command ``cap``, every methods are already in ``module.py`` and documented.

Read :class:`documentation of the capability <weboob.capabilities.bank.CapBank>` to know what are types of arguments,
what are expected returned objects, and what exceptions it may raises.


Browser
*******

Most of modules use a class derived from :class:`PagesBrowser <weboob.browser.browsers.PagesBrowser>` or
:class:`LoginBrowser <weboob.browser.browsers.LoginBrowser>` (for authenticated websites) to interact with a website.

Edit ``browser.py``::

    # -*- coding: utf-8 -*-

    from weboob.browser import PagesBrowser

    __all__ = ['ExampleBrowser']

    class ExampleBrowser(PagesBrowser):
        BASEURL = 'https://www.example.com'

There are several possible class attributes:

* **BASEURL** - base url of website used for absolute paths given to :class:`open() <weboob.browser.browsers.PagesBrowser.open>` or :class:`location() <weboob.browser.browsers.PagesBrowser.location>`
* **PROFILE** - defines the behavior of your browser against the website. By default this is Firefox, but you can import other profiles
* **TIMEOUT** - defines the timeout for requests (defaults to 10 seconds)
* **VERIFY** - SSL verification (if the protocol used is **https**)

Pages
-----

For each page you want to handle, you have to create an associated class derived from one of these classes:

* :class:`HTMLPage <weboob.browser.pages.HTMLPage>` - a HTML page
* :class:`XMLPage <weboob.browser.pages.XMLPage>` - a XML document
* :class:`JsonPage <weboob.browser.pages.JsonPage>` - a Json object
* :class:`CsvPage <weboob.browser.pages.CsvPage>` - a CSV table

In the file ``pages.py``, you can write, for example::

    # -*- coding: utf-8 -*-

    from weboob.browser.pages import HTMLPage

    __all__ = ['IndexPage', 'ListPage']

    class IndexPage(HTMLPage):
        pass

    class ListPage(HTMLPage):
        def iter_accounts():
            return iter([])

``IndexPage`` is the class we will use to get information from the home page of the website, and ``ListPage`` will handle pages
which list accounts.

Then, you have to declare them in your browser, with the :class:`URL <weboob.browser.url.URL>` object::

    from weboob.browser import PagesBrowser, URL
    from .pages import IndexPage, ListPage

    # ...
    class ExampleBrowser(PagesBrowser):
        # ...

        home = URL('/$', IndexPage)
        accounts = URL('/accounts$', ListPage)

Easy, isn't it? The first parameters are regexps of the urls (if you give only a path, it uses the ``BASEURL`` class attribute), and the last one is the class used to handle the response.

Each time you will go on the home page, ``IndexPage`` will be instanced and set as the ``page`` attribute.

For example, we can now implement some methods in ``ExampleBrowser``::

    class ExampleBrowser(PagesBrowserr):
        # ...
        def go_home(self):
            self.home.go()

            assert self.home.is_here()

        def iter_accounts_list(self):
            self.accounts.stay_or_go()

            return self.page.iter_accounts()

When calling the :func:`go() <weboob.browser.url.URL.go>` method, it reads the first regexp url of our :class:`URL <weboob.browser.url.URL>` object, and go on the page.

:func:`stay_or_go() <weboob.browser.url.URL.stay_or_go>` is used when you want to relocate on the page only if we aren't already on it.

Once we are on the ``ListPage``, we can call every methods of the ``page`` object.

Use it in backend
-----------------

Now you have a functional browser, you can use it in your class ``ExampleModule`` by defining it with the ``BROWSER`` attribute::

    from .browser import ExampleBrowser

    # ...
    class ExampleModule(Module, CapBank):
        # ...
        BROWSER = ExampleBrowser

You can now access it with member ``browser``. The class is instanced at the first call to this attribute.

For example, we can now implement :func:`CapBank.iter_accounts <weboob.capabilities.bank.CapBank.iter_accounts`::

    def iter_accounts(self):
        return self.browser.iter_accounts_list()

For this method, we only call immediately ``ExampleBrowser.iter_accounts_list``, as there isn't anything else to do around.

Login management
----------------

When the website requires to be authenticated, you have to give credentials to the constructor of the browser. You can redefine
the method :func:`create_default_browser <weboob.tools.backend.Module.create_default_browser>`::

    class ExampleModule(Module, CapBank):
        # ...
        def create_default_browser(self):
            return self.create_browser(self.config['username'].get(), self.config['password'].get())

On the browser side, you need to inherit from :func:`LoginBrowser <weboob.browser.browsers.LoginBrowser>` and to implement the function
:func:`do_login <weboob.browser.browsers.LoginBrowser.do_login>`::

    class ExampleBrowser(LoginBrowser):
        login = URL('/login', LoginPage)
        # ...

        def do_login(self):
            self.login.stay_or_go()

            self.page.login(self.username, self.password)

            if self.login_error.is_here():
                raise BrowserIncorrectPassword(self.page.get_error())

Also, your ``LoginPage`` may look like::

    class LoginPage(HTMLPage):
        def login(self, username, password):
            form = self.get_form(name='auth')
            form['username'] = username
            form['password'] = password
            form.submit()

Then, each method on your browser which need your user to be authenticated may be decorated by :func:`need_login <weboob.browser.browsers.need_login>`::

    class ExampleBrowser(LoginBrowser):
        accounts = URL('/accounts$', ListPage)

        @need_login
        def iter_accounts(self):
            self.accounts.stay_or_go()
            return self.page.get_accounts()

The last thing to know is that :func:`need_login <weboob.browser.browsers.need_login>` checks if the current page is a logged one by
reading the attribute :func:`logged <weboob.browser.pages.Page.logged>` of the instance. You can either define it yourself, as a
class boolean attribute or as a property, or to inherit your class from :class:`LoggedPage <weboob.browser.pages.LoggedPage>`.


Parsing of pages
****************

.. note::
    Depending of the base class you use for your page, it will parse html, json, csv, etc. In our case, it will be only html documents.


When your browser locates on a page, an instance of the class related to the
:class:`URL <weboob.browser.url.URL>` attribute which matches the url
is created. You can declare methods on your class to allow your browser to
interact with it.

The first thing to know is that your instance owns these attributes:

* ``browser`` - your ``ExampleBrowser`` class
* ``logger`` - context logger
* ``encoding`` - the encoding of the page
* ``response`` - the ``Response`` object from ``requests``
* ``url`` - current url
* ``doc`` - parsed document with ``lxml``

The most important attribute is ``doc`` you will use to get information from the page. You can call two methods:

* ``xpath`` - xpath expressions
* ``cssselect`` - CSS selectors

For example::

    from weboob.capabilities.bank import Account

    class ListPage(LoggedPage, HTMLPage):
        def get_accounts(self):
            for el in self.doc.xpath('//ul[@id="list"]/li'):
                id = el.attrib['id']
                account = Account(id)
                account.label = el.xpath('./td[@class="name"]').text
                account.balance = Decimal(el.xpath('./td[@class="balance"]').text)
                yield account

An alternative with ``cssselect``::

    from weboob.capabilities.bank import Account

    class ListPage(LoggedPage, HTMLPage):
        def get_accounts(self):
            for el in self.document.getroot().cssselect('ul#list li'):
                id = el.attrib['id']
                account = Account(id)
                account.label = el.cssselect('td.name').text
                account.balance = Decimal(el.cssselect('td.balance').text)
                yield account

.. note::

   All objects ID must be unique, and useful to get more information later


Your module is now functional and you can use this command::

    $ boobank -b example list

Tests
*****

Every modules must have a tests suite to detect when there are changes on websites, or when a commit
breaks the behavior of the module.

Edit ``test.py`` and write, for example::

    # -*- coding: utf-8 -*-
    from weboob.tools.test import BackendTest

    __all__ = ['ExampleTest']

    class ExampleTest(BackendTest):
        MODULE = 'example'

        def test_iter_accounts(self):
            accounts = list(self.backend.iter_accounts())

            self.assertTrue(len(accounts) > 0)

To try running test of your module, launch::

    $ tools/run_tests.sh example

For more information, look at the :doc:`tests` guides.

Advanced topics
***************

Filling objects
---------------

An object returned by a method of a capability can be not fully completed.

The class :class:`Module <weboob.tools.backend.Module>` provides a method named
:func:`fillobj <weboob.tools.backend.Module.fillobj>`, which can be called by an application to
fill some unloaded fields of a specific object, for example with::

    backend.fillobj(video, ['url', 'author'])

The ``fillobj`` method will check on the object what fields, in the ones given in list, which are
not loaded (equal to ``NotLoaded``, which is the default value), to reduce the list to the real
uncompleted fields, and call the method associated to the type of the object.

To define what objects are supported to be filled, and what method to call, define the ``OBJECTS``
class attribute in your ``ExampleModule``::

    class ExampleModule(Module, CapVideo):
        # ...

        OBJECTS = {Video: fill_video}

The prototype of the function might be::

    func(self, obj, fields)

Then, the function might, for each requested fields, fetch the right data and fill the object. For example::

    class ExampleModule(Module, CapVideo):
        # ...

        def fill_video(self, video, fields):
            if 'url' in fields:
                return self.backend.get_video(video.id)

            return video

Here, when the application has got a :class:`Video <weboob.capabilities.video.BaseVideo>` object with
:func:`search_videos <weboob.capabilities.video.CapVideo.search_videos>`, in most cases, there are only some meta-data, but not the direct link to the video media.

As our method :func:`get_video <weboob.capabilities.video.CapVideo.get_video>` will get all
of the missing data, we just call it with the object as parameter to complete it.


Storage
-------

The application can provide a storage to let your backend store data. So, you can define the structure of your storage space::

    STORAGE = {'seen': {}}

To store and read data in your storage space, use the ``storage`` attribute of your :class:`Module <weboob.tools.backend.Module>`
object.

It implements the methods of :class:`BackendStorage <weboob.tools.backend.BackendStorage>`.
