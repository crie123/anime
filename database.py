from tinydb import TinyDB, Query
from datetime import datetime
import os
import sys

class AnimeDatabase:
    def __init__(self, db_path='anime.db'):
        self.db = TinyDB(db_path)
        self.Anime = Query()

    def add_anime(self, title, description, poster_path, screenshots_paths, tags=None):
        # Convert paths to relative before saving
        rel_poster = self._make_relative_path(poster_path) if poster_path else ''
        rel_screenshots = [self._make_relative_path(p) if p else '' for p in screenshots_paths]
        
        anime_entry = {
            'title': title,
            'description': description,
            'poster_path': rel_poster,
            'screenshots_paths': rel_screenshots,
            'tags': tags or [],
            'added_date': datetime.now().isoformat()
        }
        self.db.insert(anime_entry)

    def get_anime_by_title(self, title):
        results = self.db.search(self.Anime.title == title)
        return [self._convert_anime_paths(r) for r in results]

    def search_anime(self, query):
        query = query.lower()
        results = [
            anime for anime in self.db.all()
            if query in anime['title'].lower() or 
               query in anime['description'].lower() or
               any(query in tag.lower() for tag in anime.get('tags', []))
        ]
        return [self._convert_anime_paths(r) for r in results]

    def get_all_anime(self, sort_by='title', reverse=False):
        animes = self.db.all()
        if sort_by == 'title':
            animes.sort(key=lambda x: x['title'].lower(), reverse=reverse)
        elif sort_by == 'date':
            animes.sort(key=lambda x: x.get('added_date', ''), reverse=reverse)
        return [self._convert_anime_paths(a) for a in animes]

    def get_all_tags(self):
        tags = set()
        for anime in self.db.all():
            tags.update(anime.get('tags', []))
        return sorted(list(tags))

    def get_anime_by_tag(self, tag):
        results = self.db.search(self.Anime.tags.any([tag]))
        return [self._convert_anime_paths(r) for r in results]

    def update_anime(self, title, new_data):
        if 'tags' not in new_data:
            new_data['tags'] = []
        # Convert paths to relative if they are present
        data_to_update = new_data.copy()
        if 'poster_path' in data_to_update:
            data_to_update['poster_path'] = self._make_relative_path(data_to_update['poster_path'])
        if 'screenshots_paths' in data_to_update:
            data_to_update['screenshots_paths'] = [
                self._make_relative_path(p) if p else '' for p in data_to_update['screenshots_paths']
            ]
        self.db.update(data_to_update, self.Anime.title == title)

    def delete_anime(self, title):
        self.db.remove(self.Anime.title == title)

    def _get_base_dir(self):
        """Get the base directory of the application (handles both exe and script execution)"""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running from PyInstaller exe
            return os.path.dirname(sys.executable)
        else:
            # Running as a script
            return os.path.dirname(os.path.abspath(__file__))

    def _make_relative_path(self, abs_path):
        """Convert absolute path to relative path (relative to exe/script location)"""
        if not abs_path:
            return ''
        try:
            base_dir = self._get_base_dir()
            # Resolve relative paths against base_dir (not cwd) to avoid temp-folder expansion
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(base_dir, abs_path)
            abs_path = os.path.normpath(abs_path)
            # Try to make relative
            rel_path = os.path.relpath(abs_path, base_dir)
            # If path goes outside base_dir (starts with ..), return original absolute path
            if rel_path.startswith('..'):
                return abs_path
            return rel_path
        except Exception:
            return abs_path

    def _make_absolute_path(self, path):
        """Convert relative path to absolute path (relative to exe/script location), or return as-is if already absolute"""
        if not path:
            return ''
        try:
            # If already absolute, return as-is
            if os.path.isabs(path):
                return path
            # Otherwise, make it absolute relative to script location
            base_dir = self._get_base_dir()
            return os.path.join(base_dir, path)
        except Exception:
            return path

    def _convert_anime_paths(self, anime):
        """Convert stored relative paths to absolute paths in anime entry"""
        if not anime:
            return anime
        anime_copy = anime.copy()
        if anime_copy.get('poster_path'):
            anime_copy['poster_path'] = self._make_absolute_path(anime_copy['poster_path'])
        if anime_copy.get('screenshots_paths'):
            anime_copy['screenshots_paths'] = [
                self._make_absolute_path(p) if p else '' for p in anime_copy['screenshots_paths']
            ]
        return anime_copy

    def export_to_json(self):
        """Export anime data with relative paths (already stored as relative in DB)"""
        animes = self.db.all()
        # Paths are already relative in the database, just return as-is
        return animes

    def import_from_json(self, data):
        """
        Import a list of anime entries from JSON-like data.
        Converts relative paths to absolute paths (relative to exe/script location).
        Validates each entry and inserts only valid ones.
        Returns a report dict: { 'imported': int, 'skipped': int, 'errors': [str, ...] }
        """
        if not isinstance(data, list):
            raise ValueError('Data must be a list of anime entries')

        required_keys = {'title', 'description', 'poster_path', 'screenshots_paths', 'tags'}
        valid_entries = []
        errors = []
        base_dir = os.path.dirname(os.path.abspath(__file__))

        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                errors.append(f'Item {idx}: not an object')
                continue
            missing = required_keys - set(entry.keys())
            if missing:
                errors.append(f"Item {idx}: missing keys {', '.join(sorted(missing))}")
                continue
            # Validate types
            if not isinstance(entry.get('title'), str) or not entry.get('title').strip():
                errors.append(f'Item {idx}: invalid title')
                continue
            if not isinstance(entry.get('description'), str):
                errors.append(f'Item {idx}: invalid description')
                continue
            if not isinstance(entry.get('poster_path'), str):
                errors.append(f'Item {idx}: invalid poster_path')
                continue
            if not isinstance(entry.get('screenshots_paths'), list) or not all(isinstance(p, str) for p in entry.get('screenshots_paths')):
                errors.append(f'Item {idx}: invalid screenshots_paths (must be list of strings)')
                continue
            if not isinstance(entry.get('tags'), list) or not all(isinstance(t, str) for t in entry.get('tags')):
                errors.append(f'Item {idx}: invalid tags (must be list of strings)')
                continue

            # Paths in JSON can be relative or absolute - normalize them to relative for DB storage
            poster_path = entry.get('poster_path', '')
            # If it's absolute, convert to relative; if already relative, keep as-is
            if poster_path:
                if os.path.isabs(poster_path):
                    poster_path = self._make_relative_path(poster_path)
            entry['poster_path'] = poster_path

            screenshots_paths = entry.get('screenshots_paths', [])
            rel_screenshots = []
            for p in screenshots_paths:
                if p:
                    if os.path.isabs(p):
                        p = self._make_relative_path(p)
                rel_screenshots.append(p)
            entry['screenshots_paths'] = rel_screenshots

            # Ensure added_date exists
            if 'added_date' not in entry or not isinstance(entry.get('added_date'), str):
                entry['added_date'] = datetime.now().isoformat()

            valid_entries.append(entry)

        # If there are valid entries, replace DB content with them (truncate then insert)
        imported = 0
        if valid_entries:
            self.db.truncate()
            self.db.insert_multiple(valid_entries)
            imported = len(valid_entries)

        skipped = len(data) - imported
        return {
            'imported': imported,
            'skipped': skipped,
            'errors': errors
        }