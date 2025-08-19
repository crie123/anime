from tinydb import TinyDB, Query
from datetime import datetime

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

    def export_to_json(self):
        return self.db.all()

    def import_from_json(self, data):
        """
        Import a list of anime entries from JSON-like data.
        Validates each entry and inserts only valid ones.
        Returns a report dict: { 'imported': int, 'skipped': int, 'errors': [str, ...] }
        """
        if not isinstance(data, list):
            raise ValueError('Data must be a list of anime entries')

        required_keys = {'title', 'description', 'poster_path', 'screenshots_paths', 'tags'}
        valid_entries = []
        errors = []

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