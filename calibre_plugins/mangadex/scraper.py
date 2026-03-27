from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

'''
MangaDex API client.

Uses the public MangaDex API v5 (https://api.mangadex.org/docs/).
No authentication required for reading public manga data.
'''

import json

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
    from urllib.parse import quote_plus
except ImportError:
    from urllib2 import Request, urlopen, URLError, HTTPError
    from urllib import quote_plus

API_BASE = 'https://api.mangadex.org'

USER_AGENT = 'CalibrePlugin/1.0'

# Cover art URL template: https://uploads.mangadex.org/covers/{manga_id}/{filename}
COVER_URL_TMPL = 'https://uploads.mangadex.org/covers/%s/%s'

# MangaDex original language codes to Calibre ISO 639-2 codes
_MD_LANG_MAP = {
    'ja': 'jpn',
    'ko': 'kor',
    'zh': 'zho',
    'zh-hk': 'zho',
    'en': 'eng',
    'fr': 'fra',
    'de': 'deu',
    'es': 'spa',
    'es-la': 'spa',
    'vi': 'vie',
    'th': 'tha',
    'id': 'ind',
    'tl': 'tgl',
    'ru': 'rus',
    'pt-br': 'por',
    'pt': 'por',
    'it': 'ita',
    'pl': 'pol',
    'tr': 'tur',
}


def _api_get(path, log=None):
    """Make a GET request to the MangaDex API and return parsed JSON."""
    url = API_BASE + path
    if log:
        log('API: ' + url)

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    }

    try:
        req = Request(url, headers=headers)
        response = urlopen(req, timeout=30)
        raw = response.read()
        return json.loads(raw)
    except HTTPError as e:
        if log:
            log('HTTP error %d: %s' % (e.code, url))
        return None
    except (URLError, Exception) as e:
        if log:
            log('Error fetching %s: %s' % (url, e))
        return None


def _pick_localized(obj, preferred='en'):
    """Pick a value from a {locale: text} dict, preferring English."""
    if not obj or not isinstance(obj, dict):
        return None
    if preferred in obj:
        return obj[preferred]
    # Fall back to first available
    for val in obj.values():
        if val:
            return val
    return None


def fetch_md_metadata(manga_id, log=None):
    """
    Fetch metadata for a manga from MangaDex API.

    manga_id: the UUID string (e.g. '4c1e7dd6-66d6-405d-911d-c8092072d179')

    Returns a dict with parsed fields, or None on failure.
    Keys: title, authors, artists, description, genres, tags, cover_url,
          status, year, content_rating, original_language, alt_titles.
    """
    resp = _api_get(
        '/manga/%s?includes[]=author&includes[]=artist&includes[]=cover_art' % manga_id,
        log=log)

    if not resp or resp.get('result') != 'ok':
        return None

    data = resp.get('data', {})
    attrs = data.get('attributes', {})
    rels = data.get('relationships', [])

    result = {}

    # Title
    result['title'] = _pick_localized(attrs.get('title'))
    if log:
        log('  title: ' + str(result['title']))

    # Alt titles
    alt_titles = []
    for alt in (attrs.get('altTitles') or []):
        for val in alt.values():
            if val and val != result['title']:
                alt_titles.append(val)
    result['alt_titles'] = alt_titles

    # Description
    result['description'] = _pick_localized(attrs.get('description'))
    if log:
        log('  description: %d chars' % len(result['description'] or ''))

    # Tags — split into genres (group=genre) and themes/format (group=theme/format)
    genres = []
    tags = []
    for tag in (attrs.get('tags') or []):
        tag_name = _pick_localized(tag.get('attributes', {}).get('name'))
        tag_group = tag.get('attributes', {}).get('group', '')
        if tag_name:
            if tag_group == 'genre':
                genres.append(tag_name)
            else:
                tags.append(tag_name)
    result['genres'] = genres
    result['tags'] = tags
    if log:
        log('  genres: ' + str(genres))
        log('  tags: ' + str(tags))

    # Authors and Artists from relationships
    authors = []
    artists = []
    for rel in rels:
        rel_type = rel.get('type', '')
        name = (rel.get('attributes') or {}).get('name', '')
        if not name:
            continue
        if rel_type == 'author':
            authors.append(name)
        elif rel_type == 'artist':
            artists.append(name)
    result['authors'] = authors
    result['artists'] = artists
    if log:
        log('  authors: ' + str(authors))
        log('  artists: ' + str(artists))

    # Cover art
    cover_url = None
    for rel in rels:
        if rel.get('type') == 'cover_art':
            filename = (rel.get('attributes') or {}).get('fileName', '')
            if filename:
                cover_url = COVER_URL_TMPL % (manga_id, filename)
                break
    result['cover_url'] = cover_url

    # Status, year, content rating, original language
    result['status'] = attrs.get('status')
    result['year'] = str(attrs.get('year') or '')
    result['content_rating'] = attrs.get('contentRating')
    result['original_language'] = attrs.get('originalLanguage')

    # Links (external site links stored on the manga)
    result['links'] = attrs.get('links') or {}

    return result


def md_lang_to_calibre(md_lang):
    """Convert a MangaDex language code to a Calibre ISO 639-2 code."""
    if not md_lang:
        return None
    return _MD_LANG_MAP.get(md_lang.lower())


def search_md_series(query, log=None):
    """
    Search MangaDex for manga matching the query.

    Returns a list of dicts: [{title, manga_id, url, genres, year, status}, ...]
    """
    resp = _api_get(
        '/manga?title=%s&includes[]=cover_art&limit=15&order[relevance]=desc'
        % quote_plus(query),
        log=log)

    if not resp or resp.get('result') != 'ok':
        return []

    results = []
    for item in (resp.get('data') or []):
        attrs = item.get('attributes', {})
        manga_id = item.get('id', '')

        title = _pick_localized(attrs.get('title'))
        if not title:
            continue

        genres = []
        for tag in (attrs.get('tags') or []):
            tag_name = _pick_localized(tag.get('attributes', {}).get('name'))
            if tag_name and tag.get('attributes', {}).get('group') == 'genre':
                genres.append(tag_name)

        results.append({
            'title': title,
            'manga_id': manga_id,
            'url': 'https://mangadex.org/title/%s' % manga_id,
            'genres': ', '.join(genres),
            'year': str(attrs.get('year') or ''),
            'status': attrs.get('status') or '',
        })

    return results
