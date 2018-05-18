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

    browser.location('/quux', json={'foo': 'bar'})

Will do::

    POST /quux
    Content-Type: application/json

    {"foo": "bar"}

Equivalent to::

    browser.location('/quux', data=json.dumps({'foo': 'bar'}), headers={'Content-Type': 'application/json'})


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

Parse data from an HTML table
-----------------------------

This example code isn't very semantic and could fail silently if columns are changed::

    class MyPage(HTMLPage):
        @method
        class iter_stuff(ListElement):
            item_xpath = '//table/tr[pos() > 1]' # data rows

            class item(ItemElement):
                klass = Stuff

                obj_id = CleanText('./td[1]')
                obj_foo = CleanText('./td[2]')

It can be improved by using the column labels::

    class MyPage(HTMLPage):
        @method
        class iter_stuff(ListElement):
            head_xpath = '//table/tr/th' # where to look for column titles

            # these are the column titles from the site
            col_id = 'Identifier'  # Exact match
            col_foo = re.compile(r'^Foo value for today \(.*\)')  # regexp for finer matching
            col_bar = ['Bar', 'Barr']  # Multiple exact matches

            item_xpath = '//table/tr[pos() > 1]' # data rows

            class item(ItemElement):
                klass = Stuff

                obj_id = CleanText(TableCell('id'))
                obj_foo = CleanText(TableCell('foo'))

Handle multiple tables with similar headers
-------------------------------------------

Sometimes, you might encounter a page with multiple tables to parse. The columns are titled the same, but they aren't at the same column index.
So, it's required to restart :class:`weboob.browser.elements.TableElement` column processing for each table. It's possible to encapsulate elements in other elements::

    class MultiPage(HTMLPage):
        @method
        class iter_stuff(ListElement):
            item_xpath = '//table'

            class one_table(TableElement):
                head_xpath = './thead/tr/th'
                item_xpath = './tbody/tr'

                col_foo = 'Foo'

                class item(ItemElement):
                    obj_foo = CleanText(TableCell('foo'))

Handle pagination
-----------------

For a simple case where there's a "Next" link in the page::

    class MyPage(HTMLPage):
        @pagination
        @method
        class iter_stuff(ListElement):
            next_page = AbsoluteLink('//a[text()="Next"]', default=None)
            # when it evaluates to None, pagination stops

            item_xpath = '//ul/li'

            class item(ItemElement):
                klass = SomeClass
                obj_text = CleanText('.')

Handle pagination with POST
---------------------------

When going to next page requires making a ``POST``::

    class MyPage(JsonPage):
        @pagination
        @method
        class iter_stuff(ListElement):
            def next_page(self):
                if self.doc.get('next_page_params'):
                    return requests.Request('POST', self.page.url, data=self.doc.get('next_page_params'))

            item_xpath = 'items'

            class item(ItemElement):
                klass = SomeClass
                obj_text = Dict('text')

Handle HTTP errors
------------------

HTTP errors raise exceptions that can be caught::

    class MyBrowser(PagesBrowser):
        def do_stuff(self):
            try:
                self.location('/')
            except HTTPNotFound: # in case of 404
                pass
            except ClientError as e: # in case of 4xx
                # for all these exceptions, the response attribute is set
                self.logger.warning('failed with code %d', e.response.status_code)
                pass
            except ServerError: # in case of 5xx
                raise
            except HTTPError: # other cases
                raise

Parse an object from multiple pages
-----------------------------------

Sometimes, object info is spread across multiple pages::

    class Page1(HTMLPage):
        @method
        class get_stuff(ItemElement):
            klass = Stuff

            obj_foo = CleanText('//h1')

    class Page2(HTMLPage):
        @method
        class fill_stuff(ItemElement):
            klass = Stuff
            # if we're sure we'll always go on Page1 first, we can omit previous line

            obj_bar = CleanText('//a[@class="bar"]')

Since the pages contain different attributes, info can be merged easily::

    def get_stuff(self):
        self.page1.go()
        stuff = self.page.get_stuff()  # get a Stuff object with foo set

        self.page2.go()
        self.page.fill_stuff(obj=stuff)  # fill existing Stuff object's bar

        return stuff  # foo and bar are set

This can also be useful for implementing ``fillobj``.

Unfortunately, this doesn't work when multiple objects are parsed (for example, in a ``ListElement``).
In this case, manual merging is required, and linking objects from each page.

Use ``ItemElement`` with non-scalar attributes
----------------------------------------------

Some ``BaseObject`` subclasses have fields of other ``BaseObject`` types, for example::

    class Foo(BaseObject):
        name = StringField('name')

    class Bar(BaseObject):
        simple = StringField('simple')
        foo = Field('foo', Foo)
        multiple = Field('multiple foo objects', list)

They may still be parsed with ``ItemElement``::

    class item(ItemElement):
        klass = Bar

        obj_simple = Attr('span', 'class')

        class obj_foo(ItemElement):
            klass = Foo

            obj_name = CleanText('span')

This also works for ``ListElement``::

    class item(ItemElement):
        klass = Bar

        class obj_multiple(ListElement):
            item_xpath = './/li'

            class item(ItemElement):
                klass = Foo

                obj_name = CleanText('.')
