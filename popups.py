from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
import os
import json
import threading
import functools

from utils import regen_copies_for_paths, get_copy_path, regen_thumbnails_for_paths, copy_source_to_local, get_thumbnail_path, create_thumbnail, ensure_thumbs_dir, delete_thumbnail, delete_copy
from localization import tr

class FileChooserPopup(Popup):
    def __init__(self, callback, multiple=False, save_mode=False, filters=None, owner=None, initial_path=None, **kwargs):
        # KV provides the layout (ids: filechooser, filename_input, select_btn, cancel_btn, drives_layout)
        super(FileChooserPopup, self).__init__(**kwargs)
        self.title = tr('Choose File')
        self.size_hint = (0.9, 0.9)
        self.callback = callback
        self.save_mode = save_mode
        self.owner = owner
        self._initial_path = initial_path
        self._filters = filters
        self._multiple = multiple
        # apply settings once kv ids exist
        Clock.schedule_once(self._apply_initial)

    def _apply_initial(self, dt):
        try:
            if self._filters is not None and hasattr(self.ids, 'filechooser'):
                try:
                    self.ids.filechooser.filters = self._filters
                except Exception:
                    pass
            if self._initial_path and hasattr(self.ids, 'filechooser') and os.path.isdir(self._initial_path):
                try:
                    self.ids.filechooser.path = self._initial_path
                except Exception:
                    pass
            if hasattr(self.ids, 'filechooser'):
                try:
                    self.ids.filechooser.multiselect = self._multiple
                except Exception:
                    pass
            # hide filename input if not save_mode
            if hasattr(self.ids, 'filename_input'):
                try:
                    self.ids.filename_input.opacity = 1 if self.save_mode else 0
                    self.ids.filename_input.disabled = not self.save_mode
                except Exception:
                    pass
        except Exception:
            pass

    def _select_file(self, *args):
        try:
            if self.save_mode:
                filename = getattr(self.ids.get('filename_input'), 'text', '') if hasattr(self, 'ids') else ''
                filename = self.ids.filename_input.text if 'filename_input' in self.ids else filename
                sel = list(self.ids.filechooser.selection) if 'filechooser' in self.ids else []
                if sel:
                    selected = sel[0]
                    if os.path.isdir(selected):
                        path = os.path.join(selected, filename) if filename else selected
                    else:
                        path = os.path.join(os.path.dirname(selected), filename) if filename else selected
                else:
                    if filename:
                        path = os.path.join(self.ids.filechooser.path, filename)
                    else:
                        return
                try:
                    self.callback([path])
                except Exception:
                    pass
                try:
                    dir_to_save = os.path.dirname(path)
                    if self.owner and hasattr(self.owner, 'update_last_dir'):
                        self.owner.update_last_dir(dir_to_save)
                except Exception:
                    pass
            else:
                if self.ids.filechooser.multiselect:
                    selected = list(self.ids.filechooser.selection)
                    if selected:
                        try:
                            self.callback(selected)
                        except Exception:
                            pass
                        try:
                            dir_to_save = os.path.dirname(selected[0]) if selected else self.ids.filechooser.path
                            if self.owner and hasattr(self.owner, 'update_last_dir'):
                                self.owner.update_last_dir(dir_to_save)
                        except Exception:
                            pass
                else:
                    selected = list(self.ids.filechooser.selection)
                    if not selected:
                        return
                    selected = selected[0]
                    try:
                        self.callback([selected])
                    except Exception:
                        pass
                    try:
                        dir_to_save = os.path.dirname(selected)
                        if self.owner and hasattr(self.owner, 'update_last_dir'):
                            self.owner.update_last_dir(dir_to_save)
                    except Exception:
                        pass
            self.dismiss()
        except Exception:
            pass

class AddAnimePopup(BoxLayout):
    # KV describes the layout and provides ids used below
    def __init__(self, db, main_screen, **kwargs):
        super(AddAnimePopup, self).__init__(**kwargs)
        self.db = db
        self.main_screen = main_screen

    def select_poster(self, instance):
        initial = self.main_screen.settings.get('last_dir') if hasattr(self.main_screen, 'settings') else None
        file_chooser = FileChooserPopup(callback=self._on_poster_selected, filters=['*.png', '*.jpg', '*.jpeg', '*.gif'], owner=self.main_screen, initial_path=initial)
        file_chooser.open()

    def _on_poster_selected(self, paths):
        if paths:
            try:
                self.ids.poster_input.text = paths[0]
            except Exception:
                pass

    def select_screenshots(self, instance):
        initial = self.main_screen.settings.get('last_dir') if hasattr(self.main_screen, 'settings') else None
        file_chooser = FileChooserPopup(callback=self._on_screenshot_selected, multiple=True, filters=['*.png', '*.jpg', '*.jpeg', '*.gif'], owner=self.main_screen, initial_path=initial)
        file_chooser.open()

    def _on_screenshot_selected(self, paths):
        if paths:
            try:
                self.ids.screenshots_input.text = ', '.join(paths)
            except Exception:
                pass

    def _on_dropfile(self, window, filepath):
        try:
            fp = filepath.decode('utf-8') if isinstance(filepath, (bytes, bytearray)) else str(filepath)
        except Exception:
            fp = str(filepath)
        try:
            if not self.ids.poster_input.text:
                self.ids.poster_input.text = fp
            else:
                current = [s.strip() for s in self.ids.screenshots_input.text.split(',') if s.strip()]
                current.append(fp)
                self.ids.screenshots_input.text = ', '.join(current)
        except Exception:
            pass

    def _spawn_regen_thumbs(self, poster, screenshots):
        def do_regen():
            try:
                paths = []
                if poster:
                    paths.append(poster)
                paths.extend([p for p in screenshots if p])
                try:
                    regen_copies_for_paths(paths)
                except Exception:
                    pass
                copy_paths = [get_copy_path(p) for p in paths if p]
                regen_thumbnails_for_paths(copy_paths)
            except Exception:
                pass
        threading.Thread(target=do_regen, daemon=True).start()

    def save_anime(self, instance):
        title = self.ids.title_input.text.strip()
        description = self.ids.description_input.text
        poster_path = self.ids.poster_input.text
        screenshots_paths = [s.strip() for s in self.ids.screenshots_input.text.split(',') if s.strip()]
        tags = [t.strip() for t in self.ids.tags_input.text.split(',') if t.strip()]
        if not title:
            self.main_screen.show_message(tr('Validation Error'), tr('Title is required'))
            return

        try:
            copied_poster = copy_source_to_local(poster_path) if poster_path else ''
            copied_screens = []
            for p in screenshots_paths:
                cp = copy_source_to_local(p) or p
                copied_screens.append(cp)
        except Exception:
            copied_poster = poster_path
            copied_screens = screenshots_paths

        self.db.add_anime(
            title=title,
            description=description,
            poster_path=copied_poster,
            screenshots_paths=copied_screens,
            tags=tags
        )
        try:
            self._spawn_regen_thumbs(copied_poster, copied_screens)
        except Exception:
            pass
        if hasattr(self, 'popup'):
            self.popup.dismiss()
            self.main_screen.refresh_content()
            self.main_screen.show_message(tr('Added'), tr(f"Anime '{title}' added"))

    def close_popup(self, instance=None):
        if hasattr(self, 'popup'):
            self.popup.dismiss()

class EditAnimePopup(BoxLayout):
    def __init__(self, db, main_screen, **kwargs):
        super(EditAnimePopup, self).__init__(**kwargs)
        self.db = db
        self.main_screen = main_screen
        self.current_title = ''
        # populate after kv applied
        Clock.schedule_once(self._populate_delayed, 0)

    def _populate_delayed(self, dt):
        try:
            self.current_title = self.main_screen.ids.current_title.text
            if self.current_title and self.current_title != tr('Select an anime'):
                current_anime = self.db.get_anime_by_title(self.current_title)
                if current_anime:
                    anime = current_anime[0]
                    self.ids.title_input.text = anime['title']
                    self.ids.description_input.text = anime['description']
                    self.ids.poster_input.text = anime['poster_path']
                    self.ids.screenshots_input.text = ', '.join(anime['screenshots_paths'])
                    self.ids.tags_input.text = ', '.join(anime.get('tags', []))
                    self._original_poster = anime.get('poster_path', '')
                    self._original_screenshots = list(anime.get('screenshots_paths', []))
        except Exception:
            pass

    def select_poster(self, instance):
        initial = self.main_screen.settings.get('last_dir') if hasattr(self.main_screen, 'settings') else None
        file_chooser = FileChooserPopup(callback=self._on_poster_selected, filters=['*.png', '*.jpg', '*.jpeg', '*.gif'], owner=self.main_screen, initial_path=initial)
        file_chooser.open()

    def _on_poster_selected(self, paths):
        if paths:
            try:
                self.ids.poster_input.text = paths[0]
            except Exception:
                pass

    def select_screenshots(self, instance):
        initial = self.main_screen.settings.get('last_dir') if hasattr(self.main_screen, 'settings') else None
        file_chooser = FileChooserPopup(callback=self._on_screenshot_selected, multiple=True, filters=['*.png', '*.jpg', '*.jpeg', '*.gif'], owner=self.main_screen, initial_path=initial)
        file_chooser.open()

    def _on_screenshot_selected(self, paths):
        if paths:
            try:
                self.ids.screenshots_input.text = ', '.join(paths)
            except Exception:
                pass

    def _on_dropfile(self, window, filepath):
        try:
            fp = filepath.decode('utf-8') if isinstance(filepath, (bytes, bytearray)) else str(filepath)
        except Exception:
            fp = str(filepath)
        try:
            if not self.ids.poster_input.text:
                self.ids.poster_input.text = fp
            else:
                current = [s.strip() for s in self.ids.screenshots_input.text.split(',') if s.strip()]
                current.append(fp)
                self.ids.screenshots_input.text = ', '.join(current)
        except Exception:
            pass

    def _spawn_regen_thumbs(self, poster, screenshots):
        def do_regen():
            try:
                paths = []
                if poster:
                    paths.append(poster)
                paths.extend([p for p in screenshots if p])
                try:
                    regen_copies_for_paths(paths)
                except Exception:
                    pass
                copy_paths = [get_copy_path(p) for p in paths if p]
                regen_thumbnails_for_paths(copy_paths)
            except Exception:
                pass
        threading.Thread(target=do_regen, daemon=True).start()

    def save_anime(self, instance):
        title = self.ids.title_input.text.strip()
        description = self.ids.description_input.text
        poster_path = self.ids.poster_input.text
        screenshots_paths = [s.strip() for s in self.ids.screenshots_input.text.split(',') if s.strip()]
        tags = [t.strip() for t in self.ids.tags_input.text.split(',') if t.strip()]
        if not title:
            self.main_screen.show_message(tr('Validation Error'), tr('Title is required'))
            return

        try:
            new_poster_copy = copy_source_to_local(poster_path) if poster_path else ''
            new_screens_copies = []
            for p in screenshots_paths:
                cp = copy_source_to_local(p) or p
                new_screens_copies.append(cp)
        except Exception:
            new_poster_copy = poster_path
            new_screens_copies = screenshots_paths

        try:
            old_p = getattr(self, '_original_poster', '')
            if old_p and old_p != new_poster_copy:
                try:
                    delete_thumbnail(old_p)
                except Exception:
                    pass
                try:
                    delete_copy(old_p)
                except Exception:
                    pass
            old_ss = set(getattr(self, '_original_screenshots', []) or [])
            new_ss = set(new_screens_copies)
            for removed in (old_ss - new_ss):
                try:
                    delete_thumbnail(removed)
                except Exception:
                    pass
                try:
                    delete_copy(removed)
                except Exception:
                    pass
        except Exception:
            pass

        self.db.update_anime(self.current_title, {
            'title': title,
            'description': description,
            'poster_path': new_poster_copy,
            'screenshots_paths': new_screens_copies,
            'tags': tags
        })
        try:
            self._spawn_regen_thumbs(new_poster_copy, new_screens_copies)
        except Exception:
            pass
        if hasattr(self, 'popup'):
            self.popup.dismiss()
        try:
            self.main_screen.refresh_content()
            self.main_screen.show_message(tr('Updated'), tr(f"Anime '{title}' updated"))
        except Exception:
            pass

    def close_popup(self, instance=None):
        if hasattr(self, 'popup'):
            self.popup.dismiss()

class ExportPopup(BoxLayout):
    def __init__(self, db, owner=None, **kwargs):
        super(ExportPopup, self).__init__(**kwargs)
        self.db = db
        self.owner = owner
        # Apply binding after kv applied
        Clock.schedule_once(self._apply_binding, 0)

    def _apply_binding(self, dt):
        try:
            from kivy.app import App
            app = App.get_running_app()
            # Bind button texts to update dynamically
            if hasattr(self.ids, 'export_button'):
                def update_export(*args):
                    self.ids.export_button.text = app.str_export_to_json
                app.bind(str_export_to_json=update_export)
            if hasattr(self.ids, 'close_button'):
                def update_close(*args):
                    self.ids.close_button.text = app.str_close
                app.bind(str_close=update_close)
        except Exception:
            pass

    def export_json(self, instance):
        initial = self.owner.settings.get('last_dir') if self.owner and hasattr(self.owner, 'settings') else None
        file_chooser = FileChooserPopup(callback=self._save_json, save_mode=True, filters=['*.json'], owner=self.owner, initial_path=initial)
        file_chooser.open()

    def _save_json(self, paths):
        if paths:
            path = paths[0]
            if not path.endswith('.json'):
                path += '.json'
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.db.export_to_json(), f, ensure_ascii=False, indent=2)
                try:
                    with open('export_log.txt', 'a', encoding='utf-8') as lf:
                        lf.write(tr(f"Exported {len(self.db.export_to_json())} records to {path}\n"))
                except Exception:
                    pass
                self._show_result(tr('Export Successful'), tr(f'Exported to {path}'))
            except Exception as e:
                self._show_result(tr('Export Failed'), str(e))
        if hasattr(self, 'popup'):
            self.popup.dismiss()

    def _show_result(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=message))
        btn = Button(text=tr('OK'), size_hint_y=None, height=40)
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.5, 0.3))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def close_popup(self, instance=None):
        if hasattr(self, 'popup'):
            self.popup.dismiss()

class ImportPopup(BoxLayout):
    def __init__(self, db, main_screen, **kwargs):
        super(ImportPopup, self).__init__(**kwargs)
        self.db = db
        self.main_screen = main_screen
        # Apply binding after kv applied
        Clock.schedule_once(self._apply_binding, 0)

    def _apply_binding(self, dt):
        try:
            from kivy.app import App
            app = App.get_running_app()
            # Bind button texts to update dynamically
            if hasattr(self.ids, 'import_button'):
                def update_import(*args):
                    self.ids.import_button.text = app.str_import_from_json
                app.bind(str_import_from_json=update_import)
            if hasattr(self.ids, 'close_button'):
                def update_close(*args):
                    self.ids.close_button.text = app.str_close
                app.bind(str_close=update_close)
        except Exception:
            pass

    def import_json(self, instance):
        initial = self.main_screen.settings.get('last_dir') if hasattr(self.main_screen, 'settings') else None
        file_chooser = FileChooserPopup(callback=self._load_json, filters=['*.json'], owner=self.main_screen, initial_path=initial)
        file_chooser.open()

    def _load_json(self, paths):
        if not paths:
            if hasattr(self, 'popup'):
                self.popup.dismiss()
            return
        path = paths[0]
        progress_content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        progress_content.add_widget(Label(text=tr('Importing...')))
        prog = Popup(title=tr('Importing'), content=progress_content, size_hint=(0.4, 0.2), auto_dismiss=False)
        prog.open()

        def do_import():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError(tr('Imported JSON must be a list of anime entries'))
                report = self.db.import_from_json(data)
                def finish(dt):
                    prog.dismiss()
                    self.main_screen.refresh_content()
                    msg = tr(f"Imported: {report.get('imported', 0)}. Skipped: {report.get('skipped', 0)}.")
                    if report.get('errors'):
                        errs = report.get('errors')
                        msg += tr('\nErrors:\n') + '\n'.join(errs[:10])
                    title = tr('Import Successful') if not report.get('errors') else tr('Import Completed with errors')
                    try:
                        with open('import_log.txt', 'a', encoding='utf-8') as lf:
                            lf.write(tr(f"Imported {report.get('imported',0)} records from {path}; skipped {report.get('skipped',0)}\n"))
                    except Exception:
                        pass
                    self._show_result(title, msg)
                Clock.schedule_once(finish, 0)
            except Exception as e:
                def fail(dt):
                    prog.dismiss()
                    self._show_result(tr('Import Failed'), str(e))
                Clock.schedule_once(fail, 0)

        threading.Thread(target=do_import, daemon=True).start()
        if hasattr(self, 'popup'):
            self.popup.dismiss()

    def _show_result(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=message))
        btn = Button(text=tr('OK'), size_hint_y=None, height=40)
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.5, 0.3))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def close_popup(self, instance=None):
        if hasattr(self, 'popup'):
            self.popup.dismiss()

class TagFilterPopup(BoxLayout):
    def __init__(self, owner, tags, selected=None, **kwargs):
        super(TagFilterPopup, self).__init__(**kwargs)
        self.owner = owner
        self.tags = tags
        self.selected = selected or []
        self.checkboxes = []
        # populate tag rows after kv applied
        Clock.schedule_once(self._populate_tags, 0)

    def _populate_tags(self, dt):
        try:
            container = self.ids.get('tags_box')
            if not container:
                return
            container.clear_widgets()
            for t in self.tags:
                row = BoxLayout(size_hint_y=None, height=30)
                cb = CheckBox(active=(t in self.selected))
                row.add_widget(cb)
                row.add_widget(Label(text=t))
                container.add_widget(row)
                self.checkboxes.append((t, cb))
        except Exception:
            pass

    def apply_filters(self):
        try:
            chosen = [t for t, cb in self.checkboxes if cb.active]
            self.owner.current_tags = chosen
            if chosen:
                self.owner.ids.tag_multi_btn.text = ', '.join(chosen[:3]) + (',...' if len(chosen) > 3 else '')
            else:
                self.owner.ids.tag_multi_btn.text = tr('Tags')
            self.owner.load_anime_cards(search_query=self.owner.ids.search_input.text, tag_filter=chosen)
            self.owner.save_settings()
            if hasattr(self, 'popup'):
                self.popup.dismiss()
        except Exception:
            pass

    def close_popup(self, instance=None):
        if hasattr(self, 'popup'):
            self.popup.dismiss()
