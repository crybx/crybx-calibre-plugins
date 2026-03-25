from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

'''
Fetches and parses a novelupdates.com series page.

XPath selectors target NU's known HTML structure and may need adjustment
if the site changes. Enable debug logging to see what was/wasn't found.

Cloudflare: novelupdates.com uses Cloudflare. Standard requests with a
browser-like User-Agent often work. If blocked, provide a cf_clearance cookie
value in the plugin config (Preferences → Plugins → NovelUpdates).
'''

import re

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
except ImportError:
    from urllib2 import Request, urlopen, URLError, HTTPError

try:
    from lxml import html as lxml_html
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/120.0.0.0 Safari/537.36')

# XPath expressions for NU series page fields.
_XP = {
    'title':              './/div[contains(@class,"seriestitlenu")]',
    'cover_img':          './/meta[@property="og:image"]',
    'description':        './/div[@id="editdescription"]',
    'genres':             './/div[@id="seriesgenre"]//a[contains(@class,"genre")]',
    'tags':               './/div[@id="showtags"]//a[contains(@class,"genre")]',
    'authors':            './/div[@id="showauthors"]//a',
    'type':               './/div[@id="showtype"]//a',
    'status':             './/div[@id="editstatus"]',
    'language':           './/div[@id="showlang"]//a',
    'year':               './/div[@id="edityear"]',
    'original_publisher': './/div[@id="showopublisher"]//a',
    'english_publisher':  './/div[@id="showepublisher"]//a',
    'assoc_names':        './/div[@id="editassociated"]',
}


def _xpath_text(root, xpath, multi=False):
    """Evaluate XPath and return stripped text content of matched element(s)."""
    try:
        elements = root.xpath(xpath)
    except Exception:
        return [] if multi else None
    if not elements:
        return [] if multi else None
    if multi:
        return [e.text_content().strip() for e in elements if e.text_content().strip()]
    return elements[0].text_content().strip() or None


def _xpath_attr(root, xpath, attr):
    """Evaluate XPath and return an attribute value from the first match."""
    try:
        elements = root.xpath(xpath)
    except Exception:
        return None
    if not elements:
        return None
    return elements[0].get(attr, '').strip() or None


def _inner_html(element):
    """Return inner HTML of an lxml element as a string."""
    import lxml.etree as etree
    parts = [element.text or '']
    for child in element:
        parts.append(etree.tostring(child, encoding='unicode'))
    return ''.join(parts).strip()


def fetch_nu_metadata(url, cf_cookie=None, user_agent=None, log=None):
    """
    Fetch and parse a novelupdates.com series page.

    Returns a dict with the parsed fields, or None on failure.
    Keys: title, authors, description, genres, tags, cover_url,
          type, status, language, year, original_publisher,
          english_publisher, assoc_names.
    """
    def _log(msg):
        if log:
            log(msg)

    if not HAS_LXML:
        _log('ERROR: lxml is not available — cannot parse NovelUpdates page')
        return None

    _log('Fetching: ' + url)

    headers = {
        'User-Agent': user_agent or USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity',
        'DNT': '1',
    }

    if cf_cookie:
        headers['Cookie'] = 'cf_clearance=' + cf_cookie

    try:
        req = Request(url, headers=headers)
        response = urlopen(req, timeout=30)
        raw = response.read()

        # Handle compression regardless of what we requested
        content_encoding = response.info().get('Content-Encoding', '')
        if content_encoding == 'gzip' or (raw[:2] == b'\x1f\x8b'):
            import gzip, io
            try:
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            except Exception as e:
                _log('  gzip decompress failed: ' + str(e))
        elif content_encoding == 'br':
            try:
                import brotli
                raw = brotli.decompress(raw)
            except Exception as e:
                _log('  brotli decompress failed (brotli not installed?): ' + str(e))

        _log('  response: %d bytes, encoding=%r, first 200 chars: %r' % (
            len(raw), content_encoding, raw[:200]))

    except HTTPError as e:
        _log('HTTP error %d fetching %s' % (e.code, url))
        if e.code == 403:
            _log('  → 403 Forbidden: Cloudflare may be blocking the request. '
                 'Try setting a cf_clearance cookie in the plugin config.')
        return None
    except URLError as e:
        _log('URL error fetching %s: %s' % (url, e))
        return None
    except Exception as e:
        _log('Error fetching %s: %s' % (url, e))
        return None

    try:
        root = lxml_html.fromstring(raw)
    except Exception as e:
        _log('Failed to parse HTML: ' + str(e))
        return None

    result = {}

    result['title'] = _xpath_text(root, _XP['title'])
    _log('  title: ' + str(result['title']))

    result['cover_url'] = _xpath_attr(root, _XP['cover_img'], 'content')
    _log('  cover_url: ' + str(result['cover_url']))

    # Description: preserve HTML for calibre's comments field
    try:
        desc_els = root.xpath(_XP['description'])
        if desc_els:
            result['description'] = _inner_html(desc_els[0])
        else:
            result['description'] = None
    except Exception:
        result['description'] = None
    _log('  description: %s chars' % (len(result['description'] or '')))

    result['genres'] = _xpath_text(root, _XP['genres'], multi=True)
    _log('  genres: ' + str(result['genres']))

    result['tags'] = _xpath_text(root, _XP['tags'], multi=True)
    _log('  tags: ' + str(result['tags']))

    result['authors'] = _xpath_text(root, _XP['authors'], multi=True)
    _log('  authors: ' + str(result['authors']))

    result['type'] = _xpath_text(root, _XP['type'])
    status_raw = _xpath_text(root, _XP['status'])
    result['status'] = status_raw.splitlines()[0].strip() if status_raw else None
    result['language'] = _xpath_text(root, _XP['language'])
    result['year'] = _xpath_text(root, _XP['year'])
    result['original_publisher'] = _xpath_text(root, _XP['original_publisher'])
    result['english_publisher'] = _xpath_text(root, _XP['english_publisher'])

    # Associated names: NU uses <br> between entries ("One entry per line")
    # text_content() drops <br> tags so we must walk the element manually
    assoc_els = root.xpath(_XP['assoc_names'])
    if assoc_els:
        el = assoc_els[0]
        parts = [el.text or '']
        for child in el:
            tag = getattr(child, 'tag', '') or ''
            if isinstance(tag, str) and tag.lower().lstrip('{').split('}')[-1] == 'br':
                parts.append('\n')
            else:
                parts.append(child.text_content())
            if child.tail:
                parts.append(child.tail)
        full = ''.join(parts)
        result['assoc_names'] = [n.strip() for n in re.split(r'[\n,/]+', full) if n.strip()]
    else:
        result['assoc_names'] = []

    return result
