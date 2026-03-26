from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

'''
Fetches and parses a mangaupdates.com series page.

Selectors use data-cy attributes which are stable test identifiers.
If the site redesigns, these may need updating.
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

# XPath expressions for MU series page fields.
# Most use the stable data-cy attributes on info-box content divs.
_XP = {
    'title':              './/span[contains(@class,"releasestitle")]',
    'cover_img':          './/meta[@property="og:image"]',
    'description':        './/div[@data-cy="info-box-description"]',
    'genres':             './/div[@data-cy="info-box-genres"]/span/a',
    'categories':         './/div[@data-cy="info-box-categories"]//ul//li/a',
    'authors':            './/div[@data-cy="info-box-authors"]//a',
    'artists':            './/div[@data-cy="info-box-artists"]//a',
    'type':               './/div[@data-cy="info-box-type"]',
    'status':             './/div[@data-cy="info-box-status"]',
    'year':               './/div[@data-cy="info-box-year"]',
    'original_publisher': './/div[@data-cy="info-box-original_publisher"]//a',
    'english_publisher':  './/div[@data-cy="info-box-english_publisher"]//a',
    'assoc_names':        './/div[@data-cy="info-box-associated"]/div',
    'licensed':           './/div[@data-cy="info-box-licensed"]',
    'related_series':     './/div[@data-cy="info-box-related_series"]//a',
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


def fetch_mu_metadata(url, user_agent=None, log=None):
    """
    Fetch and parse a mangaupdates.com series page.

    Returns a dict with the parsed fields, or None on failure.
    Keys: title, authors, artists, description, genres, categories,
          cover_url, type, status, year, original_publisher,
          english_publisher, assoc_names, licensed.
    """
    def _log(msg):
        if log:
            log(msg)

    if not HAS_LXML:
        _log('ERROR: lxml is not available — cannot parse MangaUpdates page')
        return None

    _log('Fetching: ' + url)

    headers = {
        'User-Agent': user_agent or USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'identity',
        'DNT': '1',
    }

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

    # Description: find the mu_markdown div inside the description box
    try:
        desc_box = root.xpath(_XP['description'])
        if desc_box:
            md_divs = desc_box[0].xpath('.//div[contains(@class,"mu_markdown")]')
            if md_divs:
                result['description'] = _inner_html(md_divs[0])
            else:
                result['description'] = _inner_html(desc_box[0])
        else:
            result['description'] = None
    except Exception:
        result['description'] = None
    _log('  description: %s chars' % (len(result['description'] or '')))

    # Genres: links inside <span> wrappers (excludes the "Search for series" link)
    result['genres'] = _xpath_text(root, _XP['genres'], multi=True)
    _log('  genres: ' + str(result['genres']))

    # Categories: tag cloud links
    result['categories'] = _xpath_text(root, _XP['categories'], multi=True)
    _log('  categories: ' + str(result['categories']))

    result['authors'] = _xpath_text(root, _XP['authors'], multi=True)
    _log('  authors: ' + str(result['authors']))

    result['artists'] = _xpath_text(root, _XP['artists'], multi=True)
    _log('  artists: ' + str(result['artists']))

    result['type'] = _xpath_text(root, _XP['type'])

    # Status: first paragraph of the status div
    try:
        status_els = root.xpath(_XP['status'])
        if status_els:
            first_p = status_els[0].xpath('.//p')
            if first_p:
                result['status'] = first_p[0].text_content().strip()
            else:
                raw_text = status_els[0].text_content().strip()
                result['status'] = raw_text.splitlines()[0].strip() if raw_text else None
        else:
            result['status'] = None
    except Exception:
        result['status'] = None

    result['year'] = _xpath_text(root, _XP['year'])
    result['original_publisher'] = _xpath_text(root, _XP['original_publisher'], multi=True)
    result['english_publisher'] = _xpath_text(root, _XP['english_publisher'], multi=True)
    result['licensed'] = _xpath_text(root, _XP['licensed'])

    # Associated names: each alternate name is in its own <div>
    result['assoc_names'] = _xpath_text(root, _XP['assoc_names'], multi=True)
    _log('  assoc_names: ' + str(result['assoc_names']))

    return result
