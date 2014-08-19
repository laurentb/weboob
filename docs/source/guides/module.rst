Write a new module
==================

This guide aims to learn how to write a new module for `Weboob <http://weboob.org>`_.

Before read it, you should :doc:`setup your development environment </guides/setup>`.

What is a module
****************

A module is an interface between a website and Weboob. It represents the python code which are stored
in repositories.

Weboob applications need *backends* to interact with websites. A *backend* is a configured *module*, usually
with several parameters like your username, password, or other options. You can create multiple *backends*
for a single *module*.

Select capabilities
*******************

Each module implements one or many :doc:`capabilities </api/capabilities/index>` to tell what kind of features the
website provides. A capability is a class derived from :class:`weboob.capabilities.base.CapBase` and with some abstract
methods (which raise ``NotImplementedError``).

A capability needs to be as generic as possible to allow a maximum number of modules to implements it.
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
module for a forum website which URL is http://www.example.com. So we will call our module **example**, and the selected
capability is :class:`CapMessages <weboob.capabilities.messages.CapMessages>`.

So, use this command::

    $ mkdir modules/example/

In a module directory, there are commonly these files:

* **__init__.py** - needed in every python modules, it exports your :class:`BaseBackend <weboob.tools.backend.BaseBackend>` class.
* **backend.py** - defines the main class of your module, which derives :class:`BaseBackend <weboob.tools.backend.BaseBackend>`.
* **browser.py** - your browser, derived from :class:`BaseBrowser <weboob.tools.browser.browser.BaseBrowser>`, is called by your module to interact with the supported website.
* **pages.py** - all website's pages handled by the browser are defined here
* **test.py** - functional tests
* **favicon.png** - a 64x64 PNG icon

Backend class
*************

Firstly, create the file ``__init__.py`` and write in::

    from .backend import ExampleBackend

    __all__ = ['ExampleBackend']

Then, you can edit ``backend.py`` and create your :class:`BaseBackend <weboob.tools.backend.BaseBackend>` class::

    # -*- coding: utf-8 -*-

    from weboob.capabilities.messages import CapMessages
    from weboob.tools.backend import BaseBackend

    __all__ = ['ExampleBackend']

    class ExampleBackend(BaseBackend, CapMessages):
        # The name of module
        NAME = 'example'
        # Name of maintainer of this backend
        MAINTAINER = u'John Smith'
        # Email address of the maintainer
        EMAIL = 'john.smith@example.com'
        # Version of weboob
        VERSION = '0.c'
        # Description of your module
        DESCRIPTION = 'Example forum website'
        # License of your module
        LICENSE = 'AGPLv3+'

In the code above, you can see that your ``ExampleBackend`` inherits :class:`CapMessages <weboob.capabilities.messages.CapMessages>`, as
we have selected it for the supported website.

Update modules list
-------------------

As you are in development mode, to see your new module in ``weboob-config``'s list, you have to update ``modules/modules.list`` with this command::

    $ weboob-config update

To be sure your module is correctly added, use this command::

    $ weboob-config info example
    .------------------------------------------------------------------------------.
    | Module example                                                               |
    +-----------------.------------------------------------------------------------'
    | Version         | 201203261420
    | Maintainer      | John Smith <john.smith@example.com>
    | License         | AGPLv3+
    | Description     | Example forum website
    | Capabilities    | CapMessages
    | Installed       | yes
    | Location        | /home/me/src/weboob/modules/example
    '-----------------'

If the last command does not work, check your :doc:`repositories setup </guides/setup>`.

Configuration
-------------

When a module is instanced as a backend, you probably want to ask parameters to user. It is manager by the ``CONFIG`` class
attribute. It supports key/values with default values and some other parameters. The :class:`Value <weboob.tools.value.Value>`
class is used to define a value.

Parameters of :class:`Value <weboob.tools.value.Value>` are:

* **label** - human readable description of a value
* **required** - if ``True``, the backend can't loaded if the key isn't found in its configuration
* **default** - an optional default value, used when the key is not in config. If there is no default value and the key
  is not found in configuration, the **required** parameter is implicitly set
* **masked** - if ``True``, the value is masked. It is useful for applications to know if this key is a password
* **regexp** - if specified, on load the specified value is checked against this regexp, and an error is raised if it doesn't match
* **choices** - if this parameter is set, the value must be in the list

There is a special class, :class:`ValueBackendPassword <weboob.tools.value.ValueBackendPassword>`, which is used to manage
private parameters of the config (like passwords or sensible information).

For example::

    from weboob.tools.value import Value, ValueBool, ValueInt, ValueBackendPassword
    from weboob.tools.backend import BackendConfig

    # ...
    class ExampleBackend(BaseBackend, CapMessages):
        # ...
        CONFIG = BackendConfig(Value('username',                label='Username', regexp='.+'),
                               ValueBackendPassword('password', label='Password'),
                               ValueBool('get_news',            label='Get newspapers', default=True),
                               Value('choice',                  label='Choices', choices={'value1': 'Label 1',
                                                                                          'value2': 'Label 2'}, default='1'),
                               Value('regexp',                  label='Birthday', regexp='^\d+/\d+/\d+$'),
                               ValueInt('integer',              label='A number', required=True))

Storage
-------

The application can provide a storage to let your backend store data. So, you can define the structure of your storage space::

    STORAGE = {'seen': {}}

To store and read data in your storage space, use the ``storage`` attribute of your :class:`BaseBackend <weboob.tools.backend.BaseBackend>`
object.

It implements the methods of :class:`BackendStorage <weboob.tools.backend.BackendStorage>`.

Implement capabilities
----------------------

You need to implement each method of all of the capabilities your module implements. For example, in our case::

    # ...
    class ExampleBackend(BaseBackend, CapMessages):
        # ...

        def iter_threads(self):
            raise NotImplementedError()

        def get_thread(self, id):
            raise NotImplementedError()

        def iter_unread_messages(self):
            raise NotImplementedError()

        def set_message_read(self, message):
            raise NotImplementedError()

Read :class:`documentation of the capability <weboob.capabilities.messages.CapMessages>` to know what are types of arguments,
what are expected returned objects, and what exceptions it may raises.


Browser
*******

Most of modules use a class derived from :class:`BaseBrowser <weboob.tools.browser.browser.BaseBrowser>` to interact with a website.

Edit ``browser.py`` and write in::

    # -*- coding: utf-8 -*-

    from weboob.tools.browser import BaseBrowser

    __all__ = ['ExampleBrowser']

    class ExampleBrowser(BaseBrowser):
        DOMAIN = 'example.com'
        PROTOCOL = 'https'
        ENCODING = 'utf-8'
        USER_AGENT = BaseBrowser.USER_AGENTS['desktop_firefox']
        PAGES = {}

There are several attributes:

* **DOMAIN** - hostname of the website.
* **PROTOCOL** - what protocol to use to access to website (http or https).
* **ENCODING** - what is the encoding of HTML pages. If you set it to ``None``, it will use the web server one.
* **USER_AGENT** - what *UserAgent* to use to access to website. Sometimes, websites provide different behaviors when you use different user agents.
                   You can use one of the :class:`predefined user-agents <weboob.tools.browser.browser.StandardBrowser.USER_AGENTS>`, or write your
                   own string.
* **PAGES** - list of handled pages, and the associated :class:`BasePage <weboob.tools.browser.browser.BasePage>` class.

Pages
-----

For each page you want to handle, you have to create an associated class derived from :class:`BasePage <weboob.tools.browser.browser.BasePage>`.

Create ``pages.py`` and write in::

    # -*- coding: utf-8 -*-

    from weboob.tools.browser import BasePage

    __all__ = ['IndexPage', 'ListPage']

    class IndexPage(BasePage):
        pass

    class ListPage(BasePage):
        def iter_threads_list(self):
            return iter([])

``IndexPage`` is the class we will use to get information from the home page of the website, and ``ListPage`` will handle pages
which list forum threads. To associate them to URLs, change the ``ExampleBrowser.PAGES`` dictionary::

    from .pages import IndexPage, ListPage

    # ...
    class ExampleBrowser(BaseBrowser):
        # ...
        PAGES = {'https://example\.com/':      IndexPage,
                 'https://example\.com/posts': ListPage,
                }

Easy, isn't it? The key is a regexp, and the value is your class. Each time you will go on the home page, ``IndexPage`` will be
instanced and set as the ``page`` attribute.

To check on what page the browser is currently, you can use :func:`is_on_page <weboob.tools.browser.browser.BaseBrowser.is_on_page>`.

For example, we can now implement the ``home`` method in ``ExampleBrowser``::

    class ExampleBrowser(BaseBrowser):
        # ...
        def home(self):
            self.location('/')

            assert self.is_on_page(IndexPage)

        def iter_threads_list(self):
            self.location('/posts')

            assert self.is_on_page(ListPage)
            return self.page.iter_threads_list()

``home`` is automatically called when an instance of ``ExampleBrowser`` is created. We also have defined ``iter_threads_list``
to go on the corresponding page and get list of threads. For now, ``ListPage.iter_threads_list`` returns an empty iterator, but
we will implement it later.

Use it in backend
-----------------

Once you have a functional browser, you can use it in your class ``ExampleBackend`` by defining it with the ``BROWSER`` attribute::

    from .browser import ExampleBrowser

    # ...
    class ExampleBackend(BaseBackend, CapMessages):
        # ...
        BROWSER = ExampleBrowser

You can now access it with member ``browser``. The class is instanced at the first call to this attribute. It is often better to use
your browser only in a ``with`` block, to prevent problems when your backend is called in a multi-threading environment.

For example, we can now implement :func:`CapMessages.iter_threads <weboob.capabilities.messages.CapMessages.iter_threads>`::

    def iter_threads(self):
        with self.browser:
            for thread in self.browser.iter_threads_list():
                yield thread

For this method, we only call immediately ``ExampleBrowser.iter_threads_list``, as there isn't anything else to do around.

Login management
----------------

When the website requires to be authenticated, you have to give credentials to the constructor of the browser. You can redefine
the method :func:`create_default_browser <weboob.tools.backend.BaseBackend.create_default_browser>`::

    class ExampleBackend(BaseBackend, CapMessages):
        # ...
        def create_default_browser(self):
            return self.create_browser(self.config['username'].get(), self.config['password'].get())

On the browser side, the important thing to know is that every times you call
:func:`location <weboob.tools.browser.browser.BaseBrowser.location>`, the method
:func:`is_logged <weboob.tools.browser.browser.BaseBrowser.is_logged>` is called to know if we are logged or not.
It is useful when the browser is launched to automatically login, or when your session has expired on website and you
need to re-login.

When you are not logged, the method :func:`login <weboob.tools.browser.browser.BaseBrowser.login>` is called.

For example::

    from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

    # ...
    class ExampleBrowser(BaseBrowser):
        # ...
        PAGES = {'https://example\.com/':      IndexPage,
                 'https://example\.com/login': LoginPage,
                 'https://example\.com/posts': ListPage,
                }

        def is_logged(self):
            return self.is_on_page(LoginPage) == False

        def login(self):
            if not self.is_on_page(LoginPage):
                self.location('/login', no_login=True)

            self.page.login(self.username, self.password)

            if not self.is_logged():
                raise BrowserIncorrectPassword()

The way to know if we are logged or not is different between websites. In this hypothetical case, we assume the website
isn't accessible if you aren't logged, and you are always redirected to ``login/`` until you are authenticated.

.. note::

   The parameter ``no_login`` have to be used in this case to prevent an infinite loop.

Code of ``LoginPage`` in ``pages.py`` may be something like that::

    class LoginPage(BasePage):
        def login(self, username, password):
            self.browser.select_form(name='login')
            self.browser['login'] = username
            self.browser['password'] = password
            self.browser.submit()

It selects the form named **login**, fill fields and submit it. You can also simulate the request by hand with::

    import urllib
    class ExampleBrowser(BaseBrowser):
        # ...
        def login(self):
            if not self.is_on_page(LoginPage):
                self.loaction('/login', no_login=True)

            d = {'login':    self.username,
                 'password': self.password,
                }
            self.location('/', urllib.urlencode(d), no_login=True)

            if not self.is_logged():
                raise BrowserIncorrectPassword()

Parsing of pages
----------------

To parse pages in your classes derived from :class:`BasePage <weboob.tools.browser.browser.BasePage>`, there are several tools and things to know.

Firstly, your object has these attributes:

* **browser** - your ``ExampleBrowser`` class
* **parser** - parser used to parse the HTML page (by default this is *lxml*)
* **document** - parsed document
* **url** - URL
* **logger** - context logger

To find an element, there are two methods:

* **xpath** - xpath expressions
* **cssselect** - CSS selectors

For example::

    from weboob.capabilities.messages import Thread
    class ListPage(BasePage):
        def iter_threads_list(self):
            for el in self.document.xpath('//ul[@id="list"]/li'):
                id = el.attrib['id']
                thread = Thread(id)
                thread.title = el.xpath('./h3').text
                yield thread

An alternative with ``cssselect``::

    from weboob.capabilities.messages import Thread
    class ListPage(BasePage):
        def iter_threads_list(self):
            for el in self.document.getroot().cssselect('ul#list li'):
                id = el.attrib['id']
                thread = Thread(id)
                thread.title = el.find('h3').text
                yield thread

.. note::

   All objects ID must be unique, and useful to get more information later


Your module is now functional and you can use this command::

    $ boobmsg -b example list

Tests
*****

Every modules must have a tests suite to detect when there are changes on websites, or when a commit
breaks the behavior of the module.

Create ``test.py`` and write it, for example::

    # -*- coding: utf-8 -*-
    from weboob.tools.test import BackendTest

    __all__ = ['DLFPTest']

    class ExampleTest(BackendTest):
        BACKEND = 'example'

        def test_iter_threads(self):
            threads = list(self.backend.iter_threads())

            self.assertTrue(len(threads) > 0)

To try running test of your module, launch::

    $ tools/run_tests.sh example

Advanced topics
***************

Filling objects
---------------

An object returned by a method of a capability can be not fully completed.

The class :class:`BaseBackend <weboob.tools.backend.BaseBackend>` provides a method named
:func:`fillobj <weboob.tools.backend.BaseBackend.fillobj>`, which can be called by an application to
fill some unloaded fields of a specific object, for example with::

    backend.fillobj(video, ['url', 'author'])

The ``fillobj`` method will check on the object what fields, in the ones given in list, which are
not loaded (equal to ``NotLoaded``, which is the default value), to reduce the list to the real
uncompleted fields, and call the method associated to the type of the object.

To define what objects are supported to be filled, and what method to call, define the ``OBJECTS``
class attribute in your ``ExampleBackend``::

    OBJECTS = {Thread: fill_thread}

The prototype of the function might be::

    def func(self, obj, fields)

Then, the function might, for each requested fields, fetch the right data and fill the object. For example::

    def fill_thread(self, thread, fields):
        if 'root' in fields or \
           'date' in fields:
            return self.get_thread(thread)

        return thread

Here, when the application has got a :class:`Thread <weboob.capabilities.messages.Thread>` object with
:func:`iter_threads <weboob.capabilities.messages.CapMessages.iter_threads>`, only two fields
are empty (set to ``NotLoaded``):

* **root** - tree of messages in the thread
* **date** - date of thread

As our method :func:`get_thread <weboob.capabilities.messages.CapMessages.get_thread>` will get all
of the missing data, we just call it with the object as parameter to complete it.
