# TODO declare __all__
# TODO support logging

import urlparse
from datetime import datetime, timedelta

from .cookies import Cookie, Cookies, strip_spaces_and_quotes, Definitions


def valid_domain(domain):
    """
    Like cookies.valid_domain, but allows leading periods.
    Because it is *very* common and useful for us.
    """
    domain.encode('ascii')
    if domain and domain[0] == '.':
        domain = domain[1:]
    if domain and domain[0] in '"':
        return False
    if Definitions.DOMAIN_RE.match(domain):
        return True
    return False


def parse_domain(value):
    """
    Like cookies.parse_domain, but allows leading periods.
    Because it is *very* common and useful for us.
    """
    value = strip_spaces_and_quotes(value)
    if value:
        assert valid_domain(value)
    return value

# this is ok because we are using our own copy of the lib
# TODO push a better way upstream
Cookie.attribute_parsers['domain'] = parse_domain
Cookie.attribute_validators['domain'] = valid_domain


class CookieJar(object):
    """
    Manage Cookies like a real browser, with security and privacy in mind.
    """

    ACCEPT_DOMAINS = []
    """
    Domains where to accept cookies, even when we should not.
    Add a "." before a domain to accept subdomains.
    If True, accept all cookies (a bit insecure).
    ACCEPT_DOMAINS has higher priority over REJECT_DOMAINS.

    Disabling third-party cookies on most browsers acts like [], enabling them
    acts like True. Since it is a very common browser option, we use the most
    secure and privacy-aware method by default.
    """

    REJECT_DOMAINS = []
    """
    Domains where to reject cookies, even when we should not.
    Add a "." before a domain to reject subdomains.
    If True, reject all cookies.
    REJECT_DOMAINS has lower priority over ACCEPT_DOMAINS.
    """

    SECURE_DOMAINS = True
    """
    When we get a cookie through an secure connection, mark it as secure
    (not to be sent on insecure channels) if the server did not tell us to.
    If True, do it automatically for all domains. Alternatively, you can put
    a list of domains, like ACCEPT_DOMAINS or REJECT_DOMAINS.
    If False, never do it (but still accept secure cookies as they are).

    NoScript for Firefox does this, either by automated guesses or forced from a list.
    """

    INSECURE_MATCHING = True
    """
    Do sloppy matching to mimic what browsers do.
    This is only for setting cookies; it should be relatively safe in Weboob.
    """

    def __init__(self):
        self.cookies = dict()

    def _domain_match(self, pattern, domain):
        """
        Checks a domain matches a domain pattern.
        Patterns can be either the exact domain, or a wildcard (starting with a dot).

        example.com matches example.com only
        .example.com matches *.example.com (but not example.com)

        :param pattern: str
        :param domain: str
        :rytpe: bool
        """
        if pattern.startswith('.'):
            return domain.endswith(pattern)
        return domain == pattern

    def _domain_match_list(self, patterns, domain):
        """
        Checks domains match, from a list of patters.
        If the list of patterns is True, it always matches.

        :param pattern: list or True
        :param domain: str
        :rytpe: bool
        """
        if patterns is True:
            return True
        for pattern in patterns:
            if self._domain_match(pattern, domain):
                return True
        return False

    def _can_set(self, cookie, url):
        """
        Checks an URL can set a particular cookie.
        See ACCEPT_DOMAINS, REJECT_DOMAINS to set exceptions.

        The cookie must have a domain already set, you can
        use _normalize_cookie() for that.

        :param cookie: The cookie the server set
        :type cookie: Cookie
        :param url: URL of the response
        :type url: str

        :rtype: bool
        """
        url = urlparse.urlparse(url)
        domain = url.hostname

        # Accept/reject overrides
        if self._domain_match_list(self.ACCEPT_DOMAINS, domain):
            return True
        if self._domain_match_list(self.REJECT_DOMAINS, domain):
            return False

        # check path
        if not url.path.startswith(cookie.path):
            return False

        # check domain (secure & simple)
        if cookie.domain.startswith('.'):
            if cookie.domain.endswith(domain) or '.%s' % domain == cookie.domain:
                return True
        elif domain == cookie.domain:
            return True

        # whatever.example.com should be able to set .example.com
        # Unbelievably stupid, but widely used.
        #
        # Our method is not ideal, as it isn't very secure for some TLDs.
        # A solution could be to use tldextract.
        if self.INSECURE_MATCHING:
            if domain.split('.')[-2:] == cookie.domain.split('.')[-2:]:
                return True

        return False

    def _normalize_cookie(self, cookie, url, now=None):
        """
        Update a cookie we got from the response.
        The goal is to have data relevant for use in future requests.
        * Sets domain if there is not one.
        * Sets path if there is not one.
        * Set Expires from Max-Age. We need the expires to have an absolute expiration date.
        * Force the Secure flag if required. (see SECURE_DOMAINS)

        :type cookie: :class:`cookies.Cookie`
        :type url: str
        :type now: datetime
        """
        url = urlparse.urlparse(url)
        if cookie.domain is None:
            cookie.domain = url.hostname
        if cookie.path is None:
            cookie.path = '/'
        if cookie.max_age is not None:
            if now is None:
                now = datetime.now()
            cookie.expires = now + timedelta(seconds=cookie.max_age)
        if url.scheme == 'https' \
        and self._match_domain_list(self.SECURE_DOMAINS, cookie.domain):
            cookie.secure = True

    def from_response(self, response):
        """
        Import cookies from the response.

        :type response: responses.Response
        """
        if 'Set-Cookie' in response.headers:
            cs = Cookies.from_response(response.headers['Set-Cookie'], True)
            for c in cs.itervalues():
                self._normalize_cookie(c, response.url)
                if self._can_set(c, response.url):
                    self.set(c)

    def for_request(self, url, now=None):
        """
        Get a key/value dictionnary of cookies for a given request URL.

        :type url: str
        :type now: datetime
        :rtype: dict
        """
        url = urlparse.urlparse(url)
        if now is None:
            now = datetime.now()
        # we want insecure cookies in https too!
        secure = None if url.scheme == 'https' else False

        cdict = dict()
        # get sorted cookies
        cookies = self.all(domain=url.hostname, path=url.path, secure=secure)
        for cookie in cookies:
            # only use session cookies and cookies with future expirations
            if cookie.expires is None or cookie.expires > now:
            # update only if not set, since first cookies are "better"
                cdict.setdefault(cookie.name, cookie.value)
        return cdict

    def flush(self, now=None, session=False):
        """
        Remove expired cookies. If session is True, also remove all session cookies.

        :type now: datetime
        :type session: bool
        """
        # we need a list copy since we remove from the iterable
        for cookie in list(self.iter()):
            # remove session cookies if requested
            if cookie.expires is None and session:
                self.remove(cookie)
            # remove non-session cookies if expired before now
            if cookie.expires is not None and cookie.expires < now:
                self.remove(cookie)

    def set(self, cookie):
        """
        Add or replace a Cookie in the jar.
        This is for normalized and checked cookies, no validation is done.
        Use from_response() to import cookies from a python-requests response.

        :type cookie: cookies.Cookie
        """
        # cookies are unique by domain, path and of course name
        assert len(cookie.domain)
        assert len(cookie.path)
        assert len(cookie.name)
        self.cookies.setdefault(cookie.domain, {}). \
                setdefault(cookie.path, {})[cookie.name] = cookie

    def iter(self, name=None, domain=None, path=None, secure=None):
        """
        Iterate matching cookies.
        You can restrict by name, domain, path or security.

        :type name: str
        :type domain: str
        :type path: str
        :type secure: bool

        :rtype: iter[:class:`cookies.Cookie`]
        """
        for cdomain, cpaths in self.cookies.iteritems():
            # domain matches (all domains if None)
            if domain is None or self._domain_match(cdomain, domain):
                for cpath, cnames in cpaths.iteritems():
                    # path matches (all if None)
                    if path is None or path.startswith(cpath):
                        for cname, cookie in cnames.iteritems():
                            # only wanted name (all if None)
                            if name is None or name == cname:
                                # wanted security (all if None)
                                # cookie.secure can be "None" if not secure!
                                if secure is None \
                                or (secure is False and not cookie.secure) \
                                or (secure is True and cookie.secure):
                                    yield cookie

    def all(self, name=None, domain=None, path=None, secure=None):
        """
        Like iter(), but sorts the cookies, from most precise to less precise.

        :rtype: list[:class:`cookies.Cookie`]
        """
        cookies = list(self.iter(name, domain, path, secure))

        # slowly compare all cookies
        # XXX one of the worst things I've ever written
        COOKIE1 = 1
        COOKIE2 = -1

        def ccmp(cookie1, cookie2):
            # most precise matching domain
            if domain and cookie1.domain != cookie2.domain:
                if cookie1.domain == domain:
                    return COOKIE1
                if cookie2.domain == domain:
                    return COOKIE2
            if len(cookie1.domain) > len(cookie2.domain):
                return COOKIE1
            if len(cookie2.domain) > len(cookie1.domain):
                return COOKIE2
            # most precise matching path
            if len(cookie1.path) > len(cookie2.path):
                return COOKIE1
            if len(cookie2.path) > len(cookie1.path):
                return COOKIE2
            # most secure
            if cookie1.secure and not cookie2.secure:
                return COOKIE1
            if cookie2.secure and not cookie1.secure:
                return COOKIE2
            return 0

        return sorted(cookies, cmp=ccmp, reverse=True)

    def get(self, name=None, domain=None, path=None, secure=None):
        """
        Return the best cookie from all().
        Useful for changing the value or deleting a cookie.

        name, domain, path and secure are the same as iter().

        :rtype: :class:`cookies.Cookie` or None
        """
        cookies = self.all(name, domain, path, secure)
        try:
            return cookies[0]
        except IndexError:
            pass

    def remove(self, cookie):
        """
        Remove a cookie. The cookie argument must have the same domain, path and name.
        Return False if not present, True if just removed.

        :type cookie: :class:`cookies.Cookie`
        :rtype: bool
        """
        # cookies are unique by domain, path and of course name
        assert len(cookie.domain)
        assert len(cookie.path)
        assert len(cookie.name)
        d = self.cookies.get(cookie.domain, {}).get(cookie.path)
        if cookie.name in d:
            del d[cookie.name]
            return True
        return False

    def clear(self):
        """
        Remove all cookies.
        """
        self.cookies.clear()
