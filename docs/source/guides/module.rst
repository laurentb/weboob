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

When you want to create a new module, you may have a look at existing capabilities to decide which one can be
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

.. note::

    A module can implement multiple capabilities, even though the ``tools/boilerplate.py`` script can only generate a
    template for a single capability. You can freely add inheritance from other capabilities afterwards in
    ``module.py``.

Update modules list
-------------------

As you are in development mode, to see your new module in ``weboob-config``'s list, you have to update ``modules/modules.list`` with this command::

    $ weboob update

To be sure your module is correctly added, use this command::

    $ weboob-config info example
    .------------------------------------------------------------------------------.
    | Module example                                                               |
    +-----------------.------------------------------------------------------------'
    | Version         | 201405191420
    | Maintainer      | John Smith <john.smith@example.com>
    | License         | LGPLv3+
    | Description     | Example bank website
    | Capabilities    | CapBank, CapCollection
    | Installed       | yes
    | Location        | /home/me/src/weboob/modules/example
    '-----------------'

If the last command does not work, check your :doc:`repositories setup
</guides/setup>`. In particular, when you want to edit an already existing
module, you should take great care of setting your development environment
correctly, or your changes to the module will not have any effect. You can also
use ``./tools/local_run.sh`` script as a quick and dirty method of forcing
Weboob applications to use local modules rather than remote ones.


Module class
*************

Edit ``module.py``. It contains the main class of the module derived from :class:`Module <weboob.tools.backend.Module>` class::

    from weboob.tools.backend import Module
    from weboob.capabilities.bank import CapBank

    class ExampleModule(Module, CapBank):
        NAME = 'example'                         # The name of module
        DESCRIPTION = u'Example bank website'    # Description of your module
        MAINTAINER = u'John Smith'               # Name of maintainer of this module
        EMAIL = 'john.smith@example.com'         # Email address of the maintainer
        LICENSE = 'LGPLv3+'                      # License of your module
        # Version of weboob
        VERSION = '2.0'

In the code above, you can see that your ``ExampleModule`` inherits :class:`CapBank <weboob.capabilities.bank.CapBank>`, as
we have selected it for the supported website.

Configuration
-------------

When a module is instanced as a backend, you probably want to ask parameters to user. It is managed by the ``CONFIG`` class
attribute. It supports key/values with default values and some other parameters. The :class:`Value <weboob.tools.value.Value>`
class is used to define a value.

Available parameters of :class:`Value <weboob.tools.value.Value>` are:

* **label** - human readable description of a value
* **required** - if ``True``, the backend can't be loaded if the key isn't found in its configuration
* **default** - an optional default value, used when the key is not in config. If there is no default value and the key
  is not found in configuration, the **required** parameter is implicitly set
* **masked** - if ``True``, the value is masked. It is useful for applications to know if this key is a password
* **regexp** - if specified, the specified value is checked against this regexp upon loading, and an error is raised if
  it doesn't match
* **choices** - if this parameter is set, the value must be in the list

.. note::

    There is a special class, :class:`ValueBackendPassword <weboob.tools.value.ValueBackendPassword>`, which is used to manage
    private parameters of the config (like passwords or sensitive information).

.. note::

    Other classes are available to store specific types of configuration options. See :mod:`weboob.tools.value
    <weboob.tools.value>` for a full list of them.

For example::

    from weboob.tools.backend import Module, BackendConfig
    from weboob.capabilities.bank import CapBank
    from weboob.tools.value import Value, ValueBool, ValueInt, ValueBackendPassword

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

    from weboob.tools.backend import Module
    from weboob.capabilities.bank import CapBank

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
what are expected returned objects, and what exceptions it may raise.

When you are done writing your module, you should remove all the not implemented methods from your module, as the base
capability code will anyway ``raise NotImplementedError()``.


Browser
*******

Most of modules use a class derived from :class:`PagesBrowser <weboob.browser.browsers.PagesBrowser>` or
:class:`LoginBrowser <weboob.browser.browsers.LoginBrowser>` (for authenticated websites) to interact with a website or
:class:`APIBrowser <weboob.browser.browsers.APIBrowser>` to interact with an API.

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

.. note::

    You can handle parameters in the URL using ``(?P<someName>)``. You can then use a keyword argument `someName` to
    bind a value to this parameter in :func:`stay_or_go() <weboob.browser.url.URL.stay_or_go>`.

Each time you will go on the home page, ``IndexPage`` will be instanced and set as the ``page`` attribute.

For example, we can now implement some methods in ``ExampleBrowser``::

    from weboob.browser import PagesBrowser

    class ExampleBrowser(PagesBrowser):
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

    from weboob.tools.backend import Module
    from weboob.capabilities.bank import CapBank

    from .browser import ExampleBrowser

    # ...
    class ExampleModule(Module, CapBank):
        # ...
        BROWSER = ExampleBrowser

You can now access it with member ``browser``. The class is instanced at the first call to this attribute.

For example, we can now implement :func:`CapBank.iter_accounts <weboob.capabilities.bank.CapBank.iter_accounts>`::

    def iter_accounts(self):
        return self.browser.iter_accounts_list()

For this method, we only call immediately ``ExampleBrowser.iter_accounts_list``, as there isn't anything else to do around.

Login management
----------------

When the website requires to be authenticated, you have to give credentials to the constructor of the browser. You can redefine
the method :func:`create_default_browser <weboob.tools.backend.Module.create_default_browser>`::

    from weboob.tools.backend import Module
    from weboob.capabilities.bank import CapBank

    class ExampleModule(Module, CapBank):
        # ...
        def create_default_browser(self):
            return self.create_browser(self.config['username'].get(), self.config['password'].get())

On the browser side, you need to inherit from :func:`LoginBrowser <weboob.browser.browsers.LoginBrowser>` and to implement the function
:func:`do_login <weboob.browser.browsers.LoginBrowser.do_login>`::

    from weboob.browser import LoginBrowser
    from weboob.exceptions import BrowserIncorrectPassword

    class ExampleBrowser(LoginBrowser):
        login = URL('/login', LoginPage)
        # ...

        def do_login(self):
            self.login.stay_or_go()

            self.page.login(self.username, self.password)

            if self.login_error.is_here():
                raise BrowserIncorrectPassword(self.page.get_error())

You may provide a custom :func:`do_logout <weboob.browser.browsers.LoginBrowser.do_logout>`:: function if you need to customize the default logout process, which simply clears all cookies.

Also, your ``LoginPage`` may look like::

    from weboob.browser.pages import HTMLPage

    class LoginPage(HTMLPage):
        def login(self, username, password):
            form = self.get_form(name='auth')
            form['username'] = username
            form['password'] = password
            form.submit()

Then, each method on your browser which needs your user to be authenticated may be decorated by :func:`need_login <weboob.browser.browsers.need_login>`::

    from weboob.browser import LoginBrowser, URL
    from weboob.browser import need_login

    class ExampleBrowser(LoginBrowser):
        accounts = URL('/accounts$', ListPage)

        @need_login
        def iter_accounts(self):
            self.accounts.stay_or_go()
            return self.page.get_accounts()

You finally have to set correctly the :func:`logged <weboob.browser.pages.Page.logged>` attribute of each page you use.  The
:func:`need_login <weboob.browser.browsers.need_login>` decorator checks if the current page is a logged one by reading the attribute
:func:`logged <weboob.browser.pages.Page.logged>` of the instance. This attributes defaults to  ``False``, which means that :func:`need_login
<weboob.browser.browsers.need_login>` will first call :func:`do_login <weboob.browser.browsers.LoginBrowser.do_login>` before calling the
decorated method.

You can either define it yourself, as a class boolean attribute or as a property, or inherit your class from :class:`LoggedPage <weboob.browser.pages.LoggedPage>`.
In the latter case, remember that Python inheritance requires the :class:`LoggedPage <weboob.browser.pages.LoggedPage>` to be placed first such as in::
    from weboob.browser.pages import LoggedPage, HTMLPage

    class OnlyForLoggedUserPage(LoggedPage, HTMLPage):
        # ...


Parsing of pages
****************

.. note::
    Depending of the base class you use for your page, it will parse html, json, csv, etc. In this section, we will
    describe the case of HTML documents.


When your browser locates on a page, an instance of the class related to the
:class:`URL <weboob.browser.url.URL>` attribute which matches the url
is created. You can declare methods on your class to allow your browser to
interact with it.

The first thing to know is that page parsing is done in a descriptive way. You
don't have to loop on HTML elements to construct the object. Just describe how
to get correct data to construct it. It is the ``Browser`` class work to actually
construct the object.

For example::

    from weboob.browser.pages import LoggedPage, HTMLPage
    from weboob.browser.filters.html import Attr
    from weboob.browser.filters.standard import CleanDecimal, CleanText
    from weboob.capabilities.bank import Account
    from weboob.browser.elements import method, ListElement, ItemElement

    class ListPage(LoggedPage, HTMLPage):
        @method
        class get_accounts(ListElement):
            item_xpath = '//ul[@id="list"]/li'

            class item(ItemElement):
                klass = Account

                obj_id = Attr('id')
                obj_label = CleanText('./td[@class="name"]')
                obj_balance = CleanDecimal('./td[@class="balance"]')

As you can see, we first set ``item_xpath`` which is the xpath string used to iterate over elements to access data. In a
second time we define ``klass`` which is the real class of our object. And then we describe how to fill each object's
attribute using what we call filters. To set an attribute `foobar` of the object, we should fill `obj_foobar`. It can
either be a filter, a constant or a function.

Some example of filters:

* :class:`Attr <weboob.browser.filters.html.Attr>`: extract a tag attribute
* :class:`CleanText <weboob.browser.filters.standard.CleanText>`: get a cleaned text from an element
* :class:`CleanDecimal <weboob.browser.filters.standard.CleanDecimal>`: get a cleaned Decimal value from an element
* :class:`Date <weboob.browser.filters.standard.Date>`: read common date formats
* :class:`DateTime <weboob.browser.filters.standard.Date>`: read common datetime formats
* :class:`Env <weboob.browser.filters.standard.Env>`: typically useful to get a named parameter in the URL (passed as a
  keyword argument to :func:`stay_or_go() <weboob.browser.url.URL.stay_or_go>`)
* :class:`Eval <weboob.browser.filters.standard.Eval>`: evaluate a lambda on the given value
* :class:`Format <weboob.browser.filters.standard.Format>`: a formatting filter, uses the standard Python format string
  notations.
* :class:`Link <weboob.browser.filters.html.Link>`: get the link uri of an element
* :class:`Regexp <weboob.browser.filters.standard.Regexp>`: apply a regex
* :class:`Time <weboob.browser.filters.standard.Time>`: read common time formats
* :class:`Type <weboob.browser.filters.standard.Type>`: get a cleaned value of any type from an element text

The full list of filters can be found in :doc:`weboob.browser.filters </api/browser/filters/index>`.

Filters can be combined. For example::

    obj_id = Link('./a[1]') & Regexp(r'id=(\d+)') & Type(type=int)

This code do several things, in order:

#) extract the href attribute of our item first ``a`` tag child
#) apply a regex to extract a value
#) convert this value to int type


When you want to access some attributes of your :class:`HTMLPage <weboob.browser.pages.HTMLPage>` object to fill an
attribute in a Filter, you should use the function construction for this attribute. For example::

	def obj_url(self):
		return (
			u'%s%s' % (
				self.page.browser.BASEURL,
				Link(
					u'//a[1]'
				)(self)
			)
	)

which will return a full URL, concatenating the ``BASEURL`` from the browser
with the (relative) link uri of the first ``a`` tag child.

.. note::

   All objects ID must be unique, and useful to get more information later

Your module is now functional and you can use this command::

    $ boobank -b example list

.. note::

	You can pass ``-a`` command-line argument to any Weboob application to log
	all the possible debug output (including requests and their parameters, raw
	responses and loaded HTML pages) in a temporary directory, indicated at the
	launch of the program.

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

.. note::

    Filling objects using ``fillobj`` should be used whenever you need to fill some fields automatically based on data
    fetched from the scraping. If you only want to fill some fields automatically based on some static data, you should
    just inherit the base object class and set these fields.

An object returned by a method of a capability can be not fully completed.

The class :class:`Module <weboob.tools.backend.Module>` provides a method named
:func:`fillobj <weboob.tools.backend.Module.fillobj>`, which can be called by an application to
fill some unloaded fields of a specific object, for example with::

    backend.fillobj(video, ['url', 'author'])

The ``fillobj`` method will check on the object which fields (in the ones given in the list argument) are not loaded
(equal to ``NotLoaded``, which is the default value), to reduce the list to the real uncompleted fields, and call the
method associated to the type of the object.

To define what objects are supported to be filled, and what method to call, define the ``OBJECTS``
class attribute in your ``ExampleModule``::

    from weboob.tools.backend import Module
    from weboob.capabilities.video import CapVideo

    class ExampleModule(Module, CapVideo):
        # ...

        OBJECTS = {Video: fill_video}

The prototype of the function might be::

    func(self, obj, fields)

Then, the function might, for each requested fields, fetch the right data and fill the object. For example::

    from weboob.tools.backend import Module
    from weboob.capabilities.video import CapVideo

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
