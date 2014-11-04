#!/usr/bin/env python
"""
web.py - Web Facilities
Author: Sean B. Palmer, inamidst.com
About: http://inamidst.com/phenny/
"""

import re, urllib, urllib2
import hashlib
import time
from htmlentitydefs import name2codepoint


class Grab(urllib.URLopener):
    def __init__(self, *args):
        self.version = 'Mozilla/5.0 (Phenny)'
        urllib.URLopener.__init__(self, *args)

    def http_error_default(self, url, fp, errcode, errmsg, headers):
        return urllib.addinfourl(fp, [headers, errcode], "http:" + url)
urllib._urlopener = Grab()


def get(uri):
    if not uri.startswith('http'):
        return
    request = urllib2.Request(uri, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0"})
    u = urllib2.urlopen(request)
    bytes = u.read()
    u.close()
    return bytes


def head(uri):
    if not uri.startswith('http'):
        return
    u = urllib2.urlopen(uri)
    info = u.info()
    u.close()
    return info


def post(uri, query):
    return post_with_url(uri, query)[0]


def post_with_url(uri, query):
    """Post, and get both the bytes and the redirected url in a tuple"""
    if not uri.startswith('http'):
        return
    data = urllib.urlencode(query)
    u = urllib2.urlopen(uri, data)
    furl = u.geturl()
    bytes = u.read()
    u.close()
    return (bytes, furl)

r_entity = re.compile(r'&([^;\s]+);')


def entity(match):
    value = match.group(1).lower()
    if value.startswith('#x'):
        return unichr(int(value[2:], 16))
    elif value.startswith('#'):
        return unichr(int(value[1:]))
    elif name2codepoint.has_key(value):
        return unichr(name2codepoint[value])
    return '[' + value + ']'


def decode(html):
    return r_entity.sub(entity, html)

r_string = re.compile(r'("(\\.|[^"\\])*")')
r_json = re.compile(r'^[,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t]+$')
env = {'__builtins__': None, 'null': None, 'true': True, 'false': False}


def json(text):
    """Evaluate JSON text safely (we hope)."""
    if r_json.match(r_string.sub('', text)):
        text = r_string.sub(lambda m: 'u' + m.group(1), text)
        return eval(text.strip(' \t\r\n'), env, {})
    raise ValueError('Input must be serialised JSON.')


def dpaste(phenny, text):
    if not hasattr(phenny, 'dpaste_cache'):
        phenny.dpaste_cache = {}
    DAY = 1000 * 60 * 60 * 24
    if isinstance(text, unicode):
        text = text.encode("utf-8")
    text_hash = hashlib.md5(text).hexdigest()
    if text_hash in phenny.dpaste_cache:
        # Ensure it's up to date.
        url, expire_time = phenny.dpaste_cache[text_hash]
        if expire_time < time.time():
            if get(url + ".txt") == text_hash:
                return url
            phenny.notice("Cache miss!")
        del phenny.dpaste_cache[text_hash]
    data = urllib.urlencode({"content": text})
    request = urllib2.Request("http://dpaste.com/api/v2/", data)
    response = urllib2.urlopen(request)
    url = response.geturl()
    phenny.dpaste_cache[text_hash] = (url, time.time() + DAY * 6)
    return url
