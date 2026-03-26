from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

'''
Common language resolution utilities shared across metadata plugins.

Provides alias-based matching of ISO 639 language codes against custom
column permitted values, supporting ISO codes, common abbreviations,
full language names, and country names.
'''

# Common aliases for matching language codes against custom column values.
LANG_ALIASES = {
    'jpn': ['jpn', 'japanese', 'jp', 'ja', 'japan'],
    'kor': ['kor', 'korean', 'kr', 'ko', 'korea'],
    'zho': ['zho', 'chinese', 'cn', 'zh', 'china', 'chi'],
    'eng': ['eng', 'english', 'en'],
    'fra': ['fra', 'french', 'fr'],
    'deu': ['deu', 'german', 'de'],
    'spa': ['spa', 'spanish', 'es'],
    'vie': ['vie', 'vietnamese', 'vi'],
    'tha': ['tha', 'thai', 'th'],
    'ind': ['ind', 'indonesian', 'id'],
    'tgl': ['tgl', 'tagalog', 'tl'],
    'rus': ['rus', 'russian', 'ru'],
}


def resolve_lang_for_column(db, col, lang_code):
    '''Match a language code to a custom column value.

    For enumerated columns, finds the permitted value that matches the
    language (by alias). For free-text columns, returns the human-readable
    language name. Returns None if no match is found for enum columns.
    '''
    if not lang_code or not col:
        return None
    aliases = LANG_ALIASES.get(lang_code, [lang_code])
    aliases_lower = [a.lower() for a in aliases]

    try:
        db_api = db.new_api if hasattr(db, 'new_api') else db
        fm = db_api.field_metadata.get(col, {})
        permitted = fm.get('display', {}).get('enum_values', [])
    except Exception:
        permitted = []

    if permitted:
        for pv in permitted:
            if pv.lower() in aliases_lower:
                return pv
        return None
    else:
        from calibre.utils.localization import calibre_langcode_to_name
        return calibre_langcode_to_name(lang_code)
