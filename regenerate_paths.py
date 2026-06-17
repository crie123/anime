"""
A script for regenerating paths in the database when changing the location of the application.
Takes the file name from the saved path and searches for it in copies/ next to the exe/script.

Usage:
python regenerate_paths.py
"""

import os
import sys
from database import AnimeDatabase


def _remap_path(stored_path, copies_dir):
    """
    Turns any saved path (absolute old or relative)
    into an actual relative path of the type copies\<filename>.

    Logic:
    1. We take the file name from stored_path.
    2. Check if there is such a file in copies_dir.
    3. If there is, we return the relative path copies\<filename>.
    4. If not, we return the stored_path unchanged (the file was not found).
    """
    if not stored_path:
        return stored_path

    filename = os.path.basename(stored_path)
    if not filename:
        return stored_path

    candidate = os.path.join(copies_dir, filename)
    if os.path.exists(candidate):
        # Возвращаем относительный путь: copies/<filename>
        return os.path.join('copies', filename)

    # Файл не найден в copies/ — оставляем как есть (предупредим пользователя)
    return None


def regenerate_paths(db_path='anime.db'):
    """Regenerate all paths in the database to point to copies/ next to exe/script."""
    print("Regenerating paths in the database...")

    db = AnimeDatabase(db_path)
    animes = db.db.all()

    if not animes:
        print("Database is empty, nothing to update.")
        return 0

    base_dir = db._get_base_dir()
    copies_dir = os.path.join(base_dir, 'copies')

    if not os.path.isdir(copies_dir):
        print(f"Error: copies/ directory not found at expected location: {copies_dir}")
        print("Make sure to create a copies/ folder next to the exe/script and place the anime files there before running this script.")
        return 1

    updated_count = 0
    not_found = []
    errors = []

    for idx, anime in enumerate(animes, 1):
        title = anime.get('title', f'Anime #{idx}')
        try:
            # --- poster ---
            poster_stored = anime.get('poster_path', '')
            rel_poster = _remap_path(poster_stored, copies_dir)
            if rel_poster is None:
                not_found.append(f"{title} [poster]: {poster_stored}")
                rel_poster = poster_stored  # leave as-is if not found, don't break the entry

            # --- screenshots ---
            rel_screenshots = []
            for sc in anime.get('screenshots_paths', []):
                if sc:
                    remapped = _remap_path(sc, copies_dir)
                    if remapped is None:
                        not_found.append(f"{title} [screenshot]: {sc}")
                        rel_screenshots.append(sc)
                    else:
                        rel_screenshots.append(remapped)
                else:
                    rel_screenshots.append('')

            db.db.update({
                'poster_path': rel_poster,
                'screenshots_paths': rel_screenshots
            }, db.Anime.title == title)

            updated_count += 1
            print(f"  [{idx}/{len(animes)}] ✓ {title}")

        except Exception as e:
            errors.append(f"{title}: {str(e)}")
            print(f"  [{idx}/{len(animes)}] ✗ {title} - Error: {e}")

    print(f"\nResult:")
    print(f"  Updated: {updated_count}/{len(animes)}")

    if not_found:
        print(f"\n  Not found in copies/: {len(not_found)}")
        for nf in not_found:
            print(f"    - {nf}")

    if errors:
        print(f"\n  Errors: {len(errors)}")
        for err in errors:
            print(f"    - {err}")

    if not not_found and not errors:
        print("\nAll paths were successfully updated to point to copies/.")
        return 0
    else:
        print("\nPart of the paths were not updated due to missing files or errors. Please review the above report.")
        return 1


if __name__ == '__main__':
    exit_code = regenerate_paths()
    sys.exit(exit_code)