from tinydb import TinyDB, Query
from datetime import datetime
import os

class AnimeDatabase:
    def __init__(self, db_path='anime.db'):
        self.db = TinyDB(db_path)
        self.Anime = Query()

    def add_anime(self, title, description, poster_path, screenshots_paths, tags=None):
        anime_entry = {
            'title': title,
            'description': description,
            'poster_path': poster_path,
            'screenshots_paths': screenshots_paths,
            'tags': tags or [],
            'added_date': datetime.now().isoformat()
        }
        self.db.insert(anime_entry)

    def get_anime_by_title(self, title):
        return self.db.search(self.Anime.title == title)

    def search_anime(self, query):
        query = query.lower()
        return [
            anime for anime in self.db.all()
            if query in anime['title'].lower() or 
               query in anime['description'].lower() or
               any(query in tag.lower() for tag in anime.get('tags', []))
        ]

    def get_all_anime(self, sort_by='title', reverse=False):
        animes = self.db.all()
        if sort_by == 'title':
            animes.sort(key=lambda x: x['title'].lower(), reverse=reverse)
        elif sort_by == 'date':
            animes.sort(key=lambda x: x.get('added_date', ''), reverse=reverse)
        return animes

    def get_all_tags(self):
        tags = set()
        for anime in self.db.all():
            tags.update(anime.get('tags', []))
        return sorted(list(tags))

    def get_anime_by_tag(self, tag):
        return self.db.search(self.Anime.tags.any([tag]))

    def update_anime(self, title, new_data):
        if 'tags' not in new_data:
            new_data['tags'] = []
        self.db.update(new_data, self.Anime.title == title)

    def delete_anime(self, title):
        self.db.remove(self.Anime.title == title)

    def _make_relative_path(self, abs_path):
        """Convert absolute path to relative path (relative to exe/script location)"""
        if not abs_path:
            return ''
        try:
            abs_path = os.path.abspath(abs_path)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Try to make relative
            rel_path = os.path.relpath(abs_path, base_dir)
            # If path goes outside base_dir (starts with ..), return original absolute path
            if rel_path.startswith('..'):
                return abs_path
            return rel_path
        except Exception:
            return abs_path

    def export_to_json(self):
        """Export anime data with relative paths"""
        animes = self.db.all()
        result = []
        for anime in animes:
            export_item = anime.copy()
            # Convert poster path to relative
            if export_item.get('poster_path'):
                export_item['poster_path'] = self._make_relative_path(export_item['poster_path'])
            # Convert screenshot paths to relative
            if export_item.get('screenshots_paths'):
                export_item['screenshots_paths'] = [
                    self._make_relative_path(p) for p in export_item['screenshots_paths']
                ]
            result.append(export_item)
        return result

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

            # Convert relative paths to absolute (relative to exe/script location)
            poster_path = entry.get('poster_path', '')
            if poster_path and not os.path.isabs(poster_path):
                poster_path = os.path.join(base_dir, poster_path)
            entry['poster_path'] = poster_path

            screenshots_paths = entry.get('screenshots_paths', [])
            abs_screenshots = []
            for p in screenshots_paths:
                if p and not os.path.isabs(p):
                    p = os.path.join(base_dir, p)
                abs_screenshots.append(p)
            entry['screenshots_paths'] = abs_screenshots

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