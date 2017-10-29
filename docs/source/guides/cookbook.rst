Cookbook
========

POST an HTML form
-----------------

::

    class LoginPage(HTMLPage):
        def login(self, username, password):
            form = self.get_form(name='something') # will select //form[@name="something"]
            form['input_name_1'] = username        # will select .//input[@name="input_name_1"]
            form['input_name_2'] = password
            form.submit()                          # will submit the form with the browser's location()

POST form data
--------------

The ``data`` argument specifies the form data to post (it can be a string, dict or OrderedDict)::

    browser.location('/quux', data={'foo': 'bar'})

Will do::

    POST /quux
    Content-Type: application/x-www-form-urlencoded

    foo=bar

It also works with :class:`weboob.browser.url.URL` instances::

    browser.myurl.go(data={'foo': 'bar'})

POST JSON
---------

Data must be encoded as a string::

    browser.location('/quux', data=json.dumps({'foo': 'bar'}), headers={'Content-Type': 'application/json'})

Will do::

    POST /quux
    Content-Type: application/json

    {"foo": "bar"}

..
    Alternatively::
    browser.location('/quux', json={'foo': 'bar'})


Add custom headers for one request
----------------------------------

The ``headers`` argument specifies additional headers::

    browser.location('/foo', headers={'X-Foo': 1, 'X-Bar': 'hello'})

Or::

    browser.myurl.go(headers={'X-Foo': 1, 'X-Bar': 'hello'})

Add headers to all requests
---------------------------

The ``build_request`` method can be reimplemented to prepare requests::

    class MyBrowser(DomainBrowser):
        def build_request(self, *args, **kwargs):
            headers = kwargs.setdefault('headers', {})
            headers['X-Foo'] = 'bar'
            return super(MyBrowser, self).build_request(*args, **kwargs)

Add query-string parameters
---------------------------

While ``data`` keyword urlencodes and passes in POST, ``params`` urlencodes and passes in URL::

    browser.location('/qux', params={'foo': 'bar&baz'})

Will do::

    GET /qux?foo=bar%26baz

It's better than::

    browser.location('/qux?' + urlencode({'foo': 'bar&baz'}))

It also works fine if some query params are already present::

    browser.location('/qux?quack=duck', params={'foo': 'bar&baz'})

Will do::

    GET /qux?quack=duck&foo=bar%26baz

Have multiple pages on the same URL
-----------------------------------

Define a ``is_here`` attribute in all :class:`weboob.browser.page.Page` class which have the same URL.
The ``is_here`` attr must be a string XPath.
If the XPath is found in the document, the Page will be matched, else other Pages will be checked::

    # in browser.py

    class MyBrowser(PagesBrowser):
        page_a = URL('/foo', PageA)
        page_b = URL('/foo', PageB)

    # in pages.py

    class PageA(HTMLPage):
        is_here = '//div[text()="List of As"]'

    class PageB(HTMLPage):
        is_here = '//div[text()="Here are the Bs"]'

If an XPath is not enough, `is_here` can be a method returning a bool::

    class PageA(HTMLPage):
        def is_here(self):
            return self.doc.xpath('//div[text()="List of As"]')

Have a page which is sometimes a ``LoggedPage``, sometimes isn't
----------------------------------------------------------------

:class:`weboob.browser.pages.LoggedPage` just defines ``logged = True`` while other pages define ``logged = False`` by default.
To make this attribute variable, use a ``@property`` method returning a ``bool``::

    class HomePage(HTMLPage):
        @property
        def logged(self):
            return self.doc.xpath('//a[contains(@href,"logout")]')

Skip items in a ``ListElement``/``ItemElement``
-----------------------------------------------

There are multiple ways to skip elements::

    class MyPage(HTMLPage):
        @method
        class iter_something(ListElement):
            item_xpath = '//ul/li'

            class item(ItemElement):
                klass = SomeClass

                # condition is called before obj_* parsing takes place
                def condition(self):
                    return 'foo' not in self.el.attrib['class']
                    # this is a basic example, we could have done
                    # item_xpath = '//ul/li[not(has-class("foo"))]'

                def obj_foo(self):
                    value = CleanText('.')(self)
                    if 'forbidden' in value:
                        raise SkipItem()
                    return value

                obj_bar = CleanDecimal(Attr('.', 'number'))

                # validate is called after obj_* parsing is done
                def validate(self, obj):
                    return obj.bar != 42

Fix invalid HTML that prevents lxml to be parsed
------------------------------------------------

When the document must be fixed before being parsed, :meth:`weboob.browser.pages.Page.build_doc` can be overridden::

    class MyPage(HTMLPage):
        def build_doc(self, content):
            content = content.replace(b'\x00', b'') # when the doc erroneously contains null bytes
            return super(MyPage, self).build_doc(content)

Follow HTML ``<meta>`` redirects
--------------------------------

Some sites do not use HTTP 3xx redirect codes but HTML ``<meta>`` refreshing. HTMLPage can handle it if enabled::

    class RedirectPage(HTMLPage):
        REFRESH_MAX = 0

Automatically follow a link on a page
-------------------------------------

Some sites do not even do that and may use Javascript to follow a link. The ``on_load`` method is called for each ``location``::

    class PortalPage(HTMLPage):
        def on_load(self):
            self.browser.location(Link('//a[@id="target"]')(self.doc))
