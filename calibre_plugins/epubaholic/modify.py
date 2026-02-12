from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import json

import six
import os, time, traceback, re

from calibre import CurrentDir, guess_type
from calibre.ebooks.chardet import strip_encoding_declarations
from calibre.ebooks.conversion.plumber import OptionValues
from calibre.ebooks.metadata.opf2 import OPF
from calibre.ebooks.metadata.meta import set_metadata
from calibre.ebooks.oeb.base import XPath
from calibre.customize.ui import apply_null_metadata
from calibre.libunzip import extract as zipextract
from calibre.ptempfile import TemporaryDirectory

from calibre_plugins.epubaholic.container import ExtendedContainer, OPF_NS
from calibre_plugins.epubaholic.covers import CoverUpdater
from calibre_plugins.epubaholic.css import CSSUpdater
from calibre_plugins.epubaholic.jacket import (remove_legacy_jackets, remove_all_jackets,
                                                add_replace_jacket)
from calibre_plugins.epubaholic.margins import MarginsUpdater
# make a chapter importer
# make a text replacer

ITUNES_FILES = ['iTunesMetadata.plist', 'iTunesArtwork']
BOOKMARKS_FILES = ['META-INF/calibre_bookmarks.txt']
OS_FILES = ['.DS_Store', 'thumbs.db']
ALL_ARTIFACTS = ITUNES_FILES + BOOKMARKS_FILES + OS_FILES

class TAG:
    content = ''    #actual content
    pair = 0        #tag pair
    e_type = 0      #1=OPEN 2=CLOSE 3=CONTAINED 4=TEXT OR CR/LF 9=REMOVE-EMPTY-SPAN

def modify_epub(log, title, epub_path, calibre_opf_path, cover_path, options):
    start_time = time.time()
    modifier = BookModifier(log)
    result = modifier.process_book(title, epub_path, calibre_opf_path, cover_path, options)
    
    if isinstance(result, tuple):
        new_book_path, custom_metadata = result
    else:
        new_book_path, custom_metadata = result, {}
    
    if new_book_path:
        log('epub updated in %.2f seconds'%(time.time() - start_time))
        if custom_metadata:
            return (new_book_path, custom_metadata)
        else:
            return new_book_path
    else:
        log('epub not changed after %.2f seconds'%(time.time() - start_time))
        return new_book_path


class BookModifier(object):

    def __init__(self, log):
        self.log = log
        self._debug_file_path = None
    
    def _debug_log(self, message, book_title=None):
        """Log debug messages to the book-specific folder for future debugging"""
        if book_title:
            try:
                import datetime
                # Clean title for folder name (same as in _import_chapters)
                clean_title = re.sub(r'[\\/:*?"<>|]', '', book_title)
                debug_path = os.path.join('R:/epub-manipulator/added-chapters', clean_title)
                
                # Add date and time to filename
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = os.path.join(debug_path, f'epubaholic_debug_{timestamp}.log')
                
                with open(debug_file, 'a') as f:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{current_time}] {message}\n")
            except:
                pass

    def process_book(self, title, epub_path, calibre_opf_path, cover_path, options):
        self.log('  Modifying: ', epub_path)
        try:
            self._restore_metadata_from_opf(calibre_opf_path, cover_path)
            self._setup_user_options()

            # If the user is updating metadata, we need to do this as a separate
            # step at the start, because it takes a stream object as input so is
            # run before we have written any container changes to disk below.
            is_metadata_updated = False
            if options['update_metadata']:
                is_metadata_updated = self._update_metadata_and_cover(epub_path)

            # Extract the epub into a temp directory
            with TemporaryDirectory('_modify-epub') as tdir:
                with CurrentDir(tdir):
                    zipextract(epub_path, tdir)

                    # Use our own simplified wrapper around an epub that will
                    # preserve the file structure and css
                    container = ExtendedContainer(tdir, self.log)
                    is_modified = self._process_book(container, options)
                    if is_modified:
                        container.write(epub_path)
                        
                        # If chapters were imported, update both metadata and OPF
                        if options['import_chapters'] and hasattr(self, '_pending_lastimport_value'):
                            self.log('\tUpdating metadata after chapter import')
                            
                            # Update metadata for Calibre database
                            with open(epub_path, 'r+b') as f:
                                with apply_null_metadata:
                                    set_metadata(f, self.mi, stream_type='epub')
                            is_metadata_updated = True
                            
                            # Update OPF file directly to preserve custom columns
                            try:
                                with TemporaryDirectory('_update-opf') as temp_dir:
                                    with CurrentDir(temp_dir):
                                        zipextract(epub_path, temp_dir)
                                        temp_container = ExtendedContainer(temp_dir, self.log)
                                        if hasattr(self, '_pending_lastimport_debug_file'):
                                            debug_file = self._pending_lastimport_debug_file
                                        else:
                                            debug_file = None
                                        success = self._update_opf_custom_column(temp_container, '#lastimport', self._pending_lastimport_value, debug_file)
                                        if success:
                                            temp_container.write(epub_path)
                            except Exception as e:
                                self.log('\t  Failed to update OPF:', str(e))

            # Only return path to the epub if we have changed it
            if is_metadata_updated or is_modified:
                # Check if we have custom metadata updates to return
                if hasattr(self, '_custom_metadata_updates'):
                    return (epub_path, self._custom_metadata_updates)
                else:
                    return epub_path
        except:
            self.log.exception('%s - ERROR: %s' % (title, traceback.format_exc()))
        finally:
            if calibre_opf_path and os.path.exists(calibre_opf_path):
                os.remove(calibre_opf_path)
            if cover_path and os.path.exists(cover_path):
                os.remove(cover_path)

    def _restore_metadata_from_opf(self, calibre_opf_path, cover_path):
        """
        Create a mi object from our copy of the latest Calibre metadata
        stored in an OPF, so that we can perform functions that update
        the book metadata, such as generating a new jacket.
        """
        if calibre_opf_path and os.path.exists(calibre_opf_path):
            with open(calibre_opf_path, 'r') as f:
                calibre_opf = OPF(f, os.path.dirname(calibre_opf_path))
            self.mi = calibre_opf.to_book_metadata()

        # Store our link to a copy of the book cover, so that we can perform
        # functions such as replacing the cover image.
        self.cover_path = cover_path

    def _update_metadata_and_cover(self, epub_path):
        self.log('\tUpdating metadata and cover')
        # Populate our mi object with the cover data
        if self.cover_path:
            if os.access(self.cover_path, os.R_OK):
                fmt = self.cover_path.rpartition('.')[-1]
                data = open(self.cover_path, 'rb').read()
                self.mi.cover_data = (fmt, data)
        with open(epub_path, 'r+b') as f:
            with apply_null_metadata:
                set_metadata(f, self.mi, stream_type='epub')
        return True # Going to "assume" it did something

    def _process_book(self, container, options):
        is_changed = False
        apply_changes_to_imports = options['appy_replacements_to_imports']

        # META OPTIONS
        # update_metadata performed earlier
        if options['remove_calibre_bookmarks']:
            is_changed |= self._remove_files_if_exist(container, BOOKMARKS_FILES)
        if options['add_unmanifested_files']:
            is_changed |= self._process_unmanifested_files(container, add=True)

        # Imports if selected to be included in other changes
        if options['import_chapters'] and apply_changes_to_imports:
            is_changed |= self._import_chapters(container)
        
        # HTML AND CSS CHANGES
        if options['inline_styles_to_tags']:
            is_changed |= self._inline_styles_to_tags(container)
        if options['strip_leftover_styles']:
            is_changed |= self._strip_leftover_styles(container)
        if options['strip_spans']:
            # Do after other html changes because there may be more spans with no attributes
            is_changed |= self._strip_spans(container)
            
        # TEXT REPLACEMENTS
        if options['consistent_ellipsis']:
            is_changed |= self._consistent_ellipsis(container)
        if options['capitalize_paragraphs']:
            is_changed |= self._capitalize_paragraphs(container)
        if options['smarten_punctuation']:
            is_changed |= self._smarten_punctuation(container)
        if options['normalize_names']:
            is_changed |= self._normalize_names(container)
        if options['female-to-male']:
            is_changed |= self._female_to_male(container)

        # Imports if selected to not be included in other changes
        if options['import_chapters'] and not apply_changes_to_imports:
            is_changed |= self._import_chapters(container)

        return is_changed

    def _get_search_terms(self, container):
        self.log('\tLooking for search terms in the manifest')
        if not container.opf_name:
            self.log('\t  No opf manifest found')
            return []
        search_data = ''

        # EPUB 3
        metadata = container.opf.xpath('//opf:metadata', namespaces={'opf': OPF_NS})[0]
        for child in metadata:
            if child.get('property') == 'calibre:user_metadata':
                custom_metadata = ''.join(child.itertext())
                search_data = json.loads(custom_metadata)['#searchterm']['#value#']
                break

        # Try EPUB 2 if search_data is still empty
        if search_data == '':
            meta_item = container.get_meta_content_item('calibre:user_metadata:#searchterm')
            if meta_item is not None:
                search_data = json.loads(meta_item.get('content'))['#value#']
                self.log('\t  Metadata found in EPUB 2 format ', search_data)

        if search_data == '':
            return None

        return search_data.split(',')

    def _set_lastimport(self, container, chapter_num, debug_path=None):
        self.log('\tSetting lastimport column to:', chapter_num)
        
        if hasattr(self, 'mi') and self.mi:
            lastimport_value = str(chapter_num)
            
            # Set in metadata object for Calibre database
            try:
                self.mi.set('#lastimport', lastimport_value)
                user_metadata = self.mi.get_user_metadata('#lastimport', make_copy=True)
                if user_metadata:
                    user_metadata['#value#'] = lastimport_value
                    self.mi.set_user_metadata('#lastimport', user_metadata)
            except Exception as e:
                self.log('\t  Error setting metadata:', str(e))
                return False
            
            # Store for OPF update and action layer
            self._pending_lastimport_value = lastimport_value
            
            if not hasattr(self, '_custom_metadata_updates'):
                self._custom_metadata_updates = {}
            self._custom_metadata_updates['#lastimport'] = lastimport_value
            
            self.log('\t  Set lastimport to %s' % lastimport_value)
            return True
        else:
            self.log('\t  No metadata object available')
            return False

    def _update_opf_custom_column(self, container, column_name, value, debug_file=None):
        """Update custom column value directly in the OPF file while preserving ALL custom metadata"""
        if not container.opf_name:
            return False

        import json
        
        # Get the metadata section
        metadata = container.opf.xpath('//opf:metadata', namespaces={'opf': OPF_NS})[0]
        
        # Collect ALL custom metadata from ALL calibre:user_metadata elements
        all_custom_metadata = {}
        elements_to_remove = []
        
        for child in metadata:
            if child.get('property') == 'calibre:user_metadata':
                try:
                    custom_metadata = ''.join(child.itertext())
                    parsed_metadata = json.loads(custom_metadata)
                    all_custom_metadata.update(parsed_metadata)
                    elements_to_remove.append(child)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Update our target column
        if column_name not in all_custom_metadata:
            return False
            
        all_custom_metadata[column_name]['#value#'] = value
        
        # Remove old elements and create new consolidated element
        for element in elements_to_remove:
            metadata.remove(element)
        
        if all_custom_metadata:
            from lxml import etree
            meta_elem = etree.SubElement(metadata, '{%s}meta' % OPF_NS)
            meta_elem.set('property', 'calibre:user_metadata')
            meta_elem.text = json.dumps(all_custom_metadata)
            meta_elem.tail = '\n    '
            
            container.set(container.opf_name, container.opf)
            return True
        
        return False

    def _process_search_term(self, term, all_files, existing_matches=None):
        """
        Process a single search term against all files and return matching files

        Args:
            term: The search term to process
            all_files: List of all filenames to check against
            existing_matches: Optional list of already matched files

        Returns:
            List of filenames that match the search term
        """
        matching_files = [] if existing_matches is None else existing_matches.copy()
        term = term.strip()
        if term == "":
            return matching_files

        self.log('  Searching for chapters: ', term)

        if '+' in term:  # Inclusion rule (AND)
            # Split the term into parts that must all be present
            include_parts = [part.strip().lower() for part in term.split('+')]

            for filename in all_files:
                filename_lower = filename.lower()
                # All parts must be present for this to match
                if all(part in filename_lower for part in include_parts):
                    if filename not in matching_files:
                        matching_files.append(filename)

        elif '!' in term:  # Exclusion rule (NOT)
            # Split into main term and exclusion term
            parts = term.split('!')
            main_term = parts[0].strip().lower()
            exclude_term = parts[1].strip().lower()

            for filename in all_files:
                filename_lower = filename.lower()
                # Main term must be present, exclusion term must not be present
                if main_term in filename_lower and exclude_term not in filename_lower:
                    if filename not in matching_files:
                        matching_files.append(filename)

        else:  # Basic term (simple match)
            term_lower = term.lower()
            for filename in all_files:
                if term_lower in filename.lower():
                    if filename not in matching_files:
                        matching_files.append(filename)

        return matching_files

    def _move_chapter_files(self, chapter_files, source_path, target_path):
        self.log('Moving chapter files to new location:', target_path)
        os.makedirs(target_path, exist_ok=True)
        for ch_file in chapter_files:
            new_ch_file = ch_file
            # if the file already exists in the target path, add a 1 to the filename
            while os.path.exists(os.path.join(target_path, new_ch_file)):
                new_ch_file = new_ch_file + '_1'
            os.rename(os.path.join(source_path, ch_file), os.path.join(target_path, new_ch_file))

    def _import_chapters(self, container):
        import random
        search_terms = self._get_search_terms(container)
        if not search_terms:
            self.log('No search term found in calibre metadata')
            return False

        self.log('\tLooking for chapters to import')
        chapters_path = 'R:/epub-manipulator/new-chapters'

        # Get all files in the directory
        all_files = [f for f in os.listdir(chapters_path)]

        # Process each search term individually
        chapter_files = []
        for term in search_terms:
            chapter_files = self._process_search_term(term, all_files, chapter_files)

        if not chapter_files:
            self.log('No chapter files found')
            return False

        def get_chapter_number(filename):
            digits = ''.join(c for c in filename if c.isdigit())
            return int(digits) if digits else 0  # Return 0 if no digits found

        # Sort files numerically so auto_2 comes before auto_10
        chapter_files.sort(key=get_chapter_number)

        for ch_file in chapter_files:
            chapter_num = get_chapter_number(ch_file)
            chapter_id = f'auto_{chapter_num}'

            # Generate random suffix once
            random.seed(random.randint(0, 999))
            suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
            chapter_id = f'{chapter_id}_{suffix}'

            # Generate file paths and references once
            file_path = f'EPUB/text/{chapter_id}.html'
            file_name = os.path.relpath(file_path, container.root).replace(os.sep, '/')
            chapter_href = container.name_to_href(file_name)

            # Generate unique IDs if needed
            chapter_id, chapter_href = container.generate_unique(id=chapter_id, href=chapter_href)

            # Update file path with potentially modified ID
            file_path = f'EPUB/text/{chapter_id}.html'

            # Read and write file content
            with open(os.path.join(chapters_path, ch_file), 'r', encoding='utf8') as f:
                file_content = f.read()
            with open(file_path, 'wb') as f:
                f.write(file_content.encode('utf-8'))

            # Add references to container
            container.add_to_manifest(chapter_id, chapter_href, 'application/xhtml+xml')
            container.add_to_spine(chapter_id)
            container.add_to_toc(chapter_id, chapter_href)
            container.add_to_nav(chapter_id, chapter_href)

        title = container.get_book_title()
        # remove illegal characters from title
        title = re.sub(r'[\\/:*?"<>|]', '', title)
        new_chapters_path = os.path.join('R:/epub-manipulator/added-chapters', title)
        self._move_chapter_files(chapter_files, chapters_path, new_chapters_path)
        
        # Set the lastimport column with the last (highest) chapter number
        if chapter_files:
            # Extract digit groups separated by dots for display (e.g., "v1c14" → "1.14")
            digit_groups = re.findall(r'\d+', chapter_files[-1])
            display_num = '.'.join(digit_groups) if digit_groups else '0'
            # Pass the new_chapters_path for debug logging
            self._set_lastimport(container, display_num, new_chapters_path)
        
        return True

    def _remove_files_if_exist(self, container, files):
        '''
        Helper function to remove items from manifest whose filename is
        in the set of 'files'
        '''
        dirtied = False
        self.log('\tLooking for files to remove:', files)
        files = [f.lower() for f in files]
        for name in list(container.name_path_map.keys()):
            found = False
            if name.lower() in files:
                found = True
            if not found:
                for f in files:
                    if name.lower().endswith('/'+f):
                        found = True
                        break
            if found:
                self.log('\t  Found file to remove:', name)
                container.delete_from_manifest(name)
                dirtied = True
        return dirtied

    def _remove_unused_images(self, container):
        self.log('\tLooking for unused images')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot remove unused images from DRM encrypted book')
            return False

        dirtied = container.remove_unused_images(container.get_image_names())
        return dirtied

    def _remove_missing_files(self, container):
        self.log('\tLooking for redundant entries in manifest')
        missing_files = set(container.mime_map.keys()) - set(container.name_path_map.keys())
        dirtied = False
        for name in missing_files:
            self.log('\t  Found entry to remove:', name)
            container.delete_from_manifest(name)
            dirtied = True
        if dirtied:
            container.set(container.opf_name, container.opf)
        return dirtied

    def _process_unmanifested_files(self, container, add=False):
        self.log('\tLooking for unmanifested files')
        all_artifacts = [f.lower() for f in ALL_ARTIFACTS]
        dirtied = False
        for name in list(container.manifest_worthy_names()):
            # Special exclusion for bookmarks, plist files and other OS artifacts
            known_artifact = False
            if name.lower() in all_artifacts:
                known_artifact = True
            if not known_artifact:
                for a in all_artifacts:
                    if name.lower().endswith('/'+a):
                        known_artifact = True
                        break
            if known_artifact:
                continue

            item = container.get_manifest_item_for_name(name)
            if item is None:
                if add:
                    self.log('\t  Found file to to add:', name)
                    ext = os.path.splitext(name)[1]
                    mt = None   # Let the mime-type be guessed from the extension
                    if ext.lower().startswith('.htm'):
                        # If this is really an xhtml file, need to explicitly declare it
                        raw = container.get_raw(name)
                        if raw.find('xmlns="http://www.w3.org/1999/xhtml"') != -1:
                            mt = guess_type('a.xhtml')[0]
                            self.log('\t Switching mimetype to:', mt)
                    container.add_name_to_manifest(name, mt)
                else:
                    self.log('\t  Found file to to remove:', name)
                    container.delete_name(name)
                dirtied = True
        if dirtied:
            container.set(container.opf_name, container.opf)
        return dirtied


    def _smarten_punctuation(self, container):
        from calibre.ebooks.conversion.preprocess import smarten_punctuation
        dirtied = False
        self.log('\tApplying smarten punctuation')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot smarten punctuation in DRM encrypted book')
            return False

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html = smarten_punctuation(html, container.log)
            if html != new_html:
                dirtied = True
                new_html = strip_encoding_declarations(new_html)
                container.set(name, new_html)
                self.log('\t  Smartened punctuation in:', name)
        return dirtied


    def _strip_spans(self, container):
        dirtied = False
        self.log('\tStripping spans')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot strip spans in DRM encrypted book')
            return False

        def strip_span_for_page(html_text):
            HTML_ENTITY = []

            html_text = re.sub(r'<(\S+)([^/>]*?) style="display: ?none;"([^/>]*?)></\1>', r'', html_text)
            html_text = re.sub(r'<(\S+)([^/>]*?)></\1>', r'<\1\2/>', html_text)
            html_text = re.sub(r'<([^>]*?)(\s+?)/>', r'<\1/>', html_text)
            html_text = re.sub(r'</(b|h)r>', r'', html_text)
            html_text = re.sub(r'<(b|h)r([^/>]*?)/?>', r'<\1r\2/>', html_text)
            html_text = re.sub(r'<(b|i|u|a|em|strong|span|big|small)/>', r'', html_text)
            html_text = re.sub(r'<\?dp([^>]*?)\?>\n?', r'', html_text)

            entities = re.split(r'(<.+?>)', html_text)

            total = 0
            for entity in entities:
                if entity:
                    entity = container.decode(entity)
                    total += 1
                    this_entity = TAG()
                    this_entity.content = entity
                    if entity == u'<span>':
                        this_entity.e_type = 9
                    elif entity[-2:] == u'/>':
                        this_entity.e_type = 3
                    elif entity[0] != u'<':
                        this_entity.e_type = 4
                    elif entity[:2] == u'</':
                        this_entity.e_type = 2
                    else:
                        this_entity.e_type = 1
                    HTML_ENTITY.append(this_entity)

            pos = -1
            PAIR = 0
            while pos < total-1:
                pos+=1
                if HTML_ENTITY[pos].e_type == 2:
                    PAIR += 1
                    HTML_ENTITY[pos].pair = PAIR
                    pair_pos = pos
                    while True:
                        pair_pos += -1
                        if pair_pos<0 : break
                        e_type = HTML_ENTITY[pair_pos].e_type
                        if e_type == 1 or e_type==9:
                            if HTML_ENTITY[pair_pos].pair == 0:
                                HTML_ENTITY[pair_pos].pair = PAIR
                                if e_type == 9: HTML_ENTITY[pos].e_type = 9
                                break

            output = []
            for entry in HTML_ENTITY:
                if entry.e_type < 9:
                    output.append(entry.content)

            out_text = ''.join(output)
            return out_text

        for name in container.get_html_names():
            orig_html = container.get_raw(name)
            html = orig_html
            new_html = strip_span_for_page(html)
            while html != new_html:
                dirtied = True
                html = new_html
                new_html = strip_span_for_page(html)
            if orig_html != new_html:
                container.set(name, new_html)
                self.log('\t  Stripped spans in:', name)
        return dirtied

    def _setup_user_options(self):
        """
        Initialise the self.opts which is required for passing to some of the
        tasks within this plugin that are utilising calibre pipeline code or
        are wanting to look up the user's default values
        """
        def get_user_margins():
            default_margins = {
                'margin_right' : 5.0,
                  'margin_top' : 5.0,
                 'margin_left' : 5.0,
               'margin_bottom' : 5.0,
                        }
            prefs_margins = {}

            from calibre.ebooks.conversion.config import load_defaults
            ps = load_defaults('page_setup')
            if 'margin_top' in ps:
                prefs_margins = ps
            else:
                prefs_margins = default_margins

            for s, v in six.iteritems(prefs_margins):
                setattr(self.opts, s, v)

        def get_epub_output_options():
            default_values = {
                'preserve_cover_aspect_ratio' : False,
                'no_svg_cover' : False
                        }
            prefs_options = {}

            from calibre.ebooks.conversion.config import load_defaults
            ps = load_defaults('epub_output')
            if 'preserve_cover_aspect_ratio' in ps:
                prefs_options = ps
            else:
                prefs_options = default_values

            for s, v in six.iteritems(prefs_options):
                setattr(self.opts, s, v)

        self.opts = OptionValues()
        get_user_margins()
        get_epub_output_options()
        self.opts.output_profile = self._get_output_profile()
        self.opts.dest = self.opts.output_profile

    def _get_output_profile(self):
        from calibre.ebooks.conversion.config import load_defaults
        from calibre.customize.ui import output_profiles
        ps = load_defaults('page_setup')
        output_profile_name = 'default'
        if 'output_profile' in ps:
            output_profile_name = ps['output_profile']
        for x in output_profiles():
            if x.short_name == output_profile_name:
                return x
        self.log.warn('Output Profile %s is no longer available, using default'%output_profile_name)
        for x in output_profiles():
            if x.short_name == 'default':
                return x

    def _inline_styles_to_tags(self, container):
        dirtied = False
        self.log('\tConverting inline styles to semantic tags')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot convert inline styles in DRM encrypted book')
            return False

        # Define patterns to convert inline styles to semantic tags
        style_to_tag_patterns = [
            # Convert font-style: italic/oblique to <i> tags
            {
                'find_style': re.compile(r'(<[^>]*)\s+style="([^"]*?)font-style\s*:\s*(italic|oblique)\s*;?([^"]*?)"([^>]*>)(.*?)(</[^>]+>)', re.IGNORECASE | re.DOTALL),
                'tag': 'i'
            },
            # Convert font-weight: bold/700+ to <b> tags  
            {
                'find_style': re.compile(r'(<[^>]*)\s+style="([^"]*?)font-weight\s*:\s*(bold|[7-9]\d\d)\s*;?([^"]*?)"([^>]*>)(.*?)(</[^>]+>)', re.IGNORECASE | re.DOTALL),
                'tag': 'b'
            },
            # Convert text-decoration: underline to <u> tags
            {
                'find_style': re.compile(r'(<[^>]*)\s+style="([^"]*?)text-decoration\s*:\s*underline\s*;?([^"]*?)"([^>]*>)(.*?)(</[^>]+>)', re.IGNORECASE | re.DOTALL),
                'tag': 'u'
            },
            # Convert text-decoration: line-through to <s> tags
            {
                'find_style': re.compile(r'(<[^>]*)\s+style="([^"]*?)text-decoration\s*:\s*line-through\s*;?([^"]*?)"([^>]*>)(.*?)(</[^>]+>)', re.IGNORECASE | re.DOTALL),
                'tag': 's'
            }
        ]

        def process_style_match(match, tag_name):
            opening_tag_start = match.group(1)
            style_before = match.group(2)
            style_after = match.group(4) if len(match.groups()) >= 4 else ""
            opening_tag_end = match.group(5) if len(match.groups()) >= 5 else match.group(3)
            content = match.group(6) if len(match.groups()) >= 6 else match.group(4)
            closing_tag = match.group(7) if len(match.groups()) >= 7 else match.group(5)
            
            # Reconstruct style attribute without the converted style
            remaining_style = (style_before + style_after).strip()
            remaining_style = re.sub(r';\s*;', ';', remaining_style)  # Clean up double semicolons
            remaining_style = remaining_style.strip(';').strip()
            
            # Build the new opening tag
            if remaining_style:
                new_opening_tag = f'{opening_tag_start} style="{remaining_style}"{opening_tag_end}'
            else:
                new_opening_tag = f'{opening_tag_start}{opening_tag_end}'
            
            # Wrap content in semantic tag
            return f'{new_opening_tag}<{tag_name}>{content}</{tag_name}>{closing_tag}'

        # Pattern to remove non-semantic font-weight styles
        remove_normal_weight = re.compile(r'font-weight\s*:\s*(normal|[1-4]\d\d)\s*;?', re.IGNORECASE)

        for name in container.get_html_names():
            html = container.get_raw(name)
            original_html = html
            replacement_count = 0
            
            # Apply each style-to-tag conversion
            for pattern_info in style_to_tag_patterns:
                pattern = pattern_info['find_style']
                tag = pattern_info['tag']
                
                matches = list(pattern.finditer(html))
                if matches:
                    replacement_count += len(matches)
                    # Process matches in reverse order to avoid position shifts
                    for match in reversed(matches):
                        replacement = process_style_match(match, tag)
                        html = html[:match.start()] + replacement + html[match.end():]
            
            # Remove non-semantic font-weight styles
            new_html, weight_removals = remove_normal_weight.subn('', html)
            if weight_removals > 0:
                replacement_count += weight_removals
                html = new_html
            
            if replacement_count > 0:
                dirtied = True
                html = strip_encoding_declarations(html)
                container.set(name, html)
                self.log('\t  Converted %d inline styles to tags in: %s' % (replacement_count, name))
        
        return dirtied

    def _strip_leftover_styles(self, container):
        dirtied = False
        self.log('\tStripping leftover styles')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot strip leftover styles in DRM encrypted book')
            return False

        from calibre_plugins.epubaholic.text_replacement_utils import apply_replacements_to_content
        from calibre_plugins.epubaholic.pattern_definitions import get_patterns

        # Get the strip style patterns
        all_patterns = get_patterns()
        strip_patterns = all_patterns.get('strip-style', [])

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html, replacement_count = apply_replacements_to_content(html, strip_patterns)
            
            if replacement_count > 0:
                dirtied = True
                new_html = strip_encoding_declarations(new_html)
                container.set(name, new_html)
                self.log('\t  Stripped %d leftover styles in: %s' % (replacement_count, name))
        
        return dirtied

    def _consistent_ellipsis(self, container):
        dirtied = False
        self.log('\tApplying consistent ellipsis')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot apply consistent ellipsis in DRM encrypted book')
            return False

        from calibre_plugins.epubaholic.text_replacement_utils import apply_replacements_to_content
        from calibre_plugins.epubaholic.pattern_definitions import get_patterns

        # Get the consistent ellipsis patterns
        all_patterns = get_patterns()
        ellipsis_patterns = all_patterns.get('consistent-ellipsis', [])

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html, replacement_count = apply_replacements_to_content(html, ellipsis_patterns)
            
            if replacement_count > 0:
                dirtied = True
                new_html = strip_encoding_declarations(new_html)
                container.set(name, new_html)
                self.log('\t  Applied %d ellipsis replacements in: %s' % (replacement_count, name))
        
        return dirtied

    def _capitalize_paragraphs(self, container):
        dirtied = False
        self.log('\tCapitalizing first letter of paragraphs')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot capitalize paragraphs in DRM encrypted book')
            return False

        from calibre_plugins.epubaholic.text_replacement_utils import apply_replacements_to_content

        # Define the capitalization pattern based on capitalize_start_of_tags_patterns
        capitalize_patterns = [{
            "regex": r"<p([^>]*)>([\"“'‘]?)(\\.{3}|…)?([a-z])",
            "replace": r"<p\1>\2\3\4",
            "transform": "uppercase",
            "transform_group": 4
        }]

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html, replacement_count = apply_replacements_to_content(html, capitalize_patterns)
            
            if replacement_count > 0:
                dirtied = True
                new_html = strip_encoding_declarations(new_html)
                container.set(name, new_html)
                self.log('\t  Capitalized %d paragraphs in: %s' % (replacement_count, name))
        
        return dirtied

    def _normalize_names(self, container):
        pass

    def _female_to_male(self, container):
        dirtied = False
        self.log('\tConverting female pronouns to male')
        if container.is_drm_encrypted():
            self.log('ERROR - cannot convert female to male in DRM encrypted book')
            return False

        from calibre_plugins.epubaholic.text_replacement_utils import apply_replacements_to_content
        from calibre_plugins.epubaholic.pattern_definitions import get_patterns

        # Get the female to male conversion patterns
        all_patterns = get_patterns()
        conversion_patterns = all_patterns.get('female-to-male', [])

        for name in container.get_html_names():
            html = container.get_raw(name)
            new_html, replacement_count = apply_replacements_to_content(html, conversion_patterns)
            
            if replacement_count > 0:
                dirtied = True
                new_html = strip_encoding_declarations(new_html)
                container.set(name, new_html)
                self.log('\t  Made %d female-to-male conversions in: %s' % (replacement_count, name))
        
        return dirtied
