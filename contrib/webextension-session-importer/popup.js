var makePromise;

if (navigator.userAgent.indexOf('Firefox') > -1) {
    makePromise = function() {
        var args = Array.prototype.slice.call(arguments);
        var f = args.shift();
        var self = args.shift();

        return f.apply(self, args);
    }
} else { /* In chrome, navigator is an empty object, wtf? */
    browser = chrome;

    /* chrome APIs don't return Promise objects */
    makePromise = function() {
        var args = Array.prototype.slice.call(arguments);
        var f = args.shift();
        var self = args.shift();

        return new Promise(function(resolve, reject) {
            args.push(function() {
                resolve.apply(null, arguments);
            });
            f.apply(self, args);
        });
    }
}

function loadCookies() {
    var onGetCookies = function(url, cookies) {
        var objs = cookies.map(function(cookie) {
            return {
                name: cookie.name,
                value: cookie.value,
                domain: cookie.domain,
                path: cookie.path,
                secure: cookie.secure,
                httpOnly: cookie.httpOnly,
                expirationDate: cookie.expirationDate,
                storeId: cookie.storeId
            };
        });
        var ret = {
            url: url,
            cookies: objs
        };

        document.getElementById('data').placeholder = JSON.stringify(ret, null, 2);
    };

    var onGetActive = function(tabs) {
        makePromise(browser.cookies.getAll, browser.cookies, {
            url: tabs[0].url,
            storeId: tabs[0].cookieStoreId
        }).then(function(cookies) { onGetCookies(tabs[0].url, cookies); });
    };

    makePromise(browser.tabs.query, browser.tabs, {
        active: true,
        currentWindow: true
    }).then(onGetActive);
}

function clearCookies(cookieStoreId, url) {
    return new Promise(function(resolve, reject) {
        var onGetCookie = function(cookies) {
            var promises = cookies.map(function(cookie) {
                return makePromise(browser.cookies.remove, browser.cookies, {
                    url: url,
                    name: cookie.name,
                    storeId: cookie.storeId
                });
            });
            Promise.all(promises).then(function() { resolve(); });
        };

        makePromise(browser.cookies.getAll, browser.cookies, {
            url: url,
            storeId: cookieStoreId
        }).then(onGetCookie);
    });
}

function setCookies(cookieStoreId, url, objs) {
    return new Promise(function(resolve, reject) {
        var promises = objs.map(function(obj) {
            if (obj.domain.startsWith('.')) {
                obj.url = 'https://' + obj.domain.substring(1);
            } else {
                obj.url = 'https://' + obj.domain;
            }
            obj.storeId = cookieStoreId;
            return makePromise(browser.cookies.set, browser.cookies, obj);
        });

        Promise.all(promises).then(function() { resolve(); });
    });
}

function setState() {
    var data = JSON.parse(document.getElementById('data').value);
    var objs = data.cookies;
    var url = data.url;

    var onGetActive = function(tabs) {
        clearCookies(tabs[0].cookieStoreId, url).then(function() {
            setCookies(tabs[0].cookieStoreId, url, objs).then(function() {
                makePromise(browser.tabs.update, browser.tabs, tabs[0].id, {
                    url: url
                }).then(function() {
                    window.close();
                });
            });
        });
    };

    makePromise(browser.tabs.query, browser.tabs, {
        active: true,
        currentWindow: true
    }).then(onGetActive);
}

window.addEventListener('load', loadCookies);
window.addEventListener('load', function() {
    document.getElementById('submit').addEventListener('click', setState);
});
