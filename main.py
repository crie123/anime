import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.spinner import Spinner
from kivy.uix.carousel import Carousel
from kivy.uix.modalview import ModalView
from kivy.uix.image import AsyncImage
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as CoreImage
from kivy.graphics import Color, Rectangle
from kivy.properties import ObjectProperty, BooleanProperty, ListProperty, StringProperty
from kivy.uix.filechooser import FileChooserListView
from database import AnimeDatabase
from kivy.clock import Clock
from kivy.uix.widget import Widget
from localization import set_language, tr
import json
import ctypes
import os
import threading
import functools
from utils import get_thumbnail_path, create_thumbnail, ensure_thumbs_dir, delete_thumbnail, regen_thumbnails_for_paths, copy_source_to_local, delete_copy, regen_copies_for_paths, get_copy_path
# popups moved to separate module
from popups import FileChooserPopup, AddAnimePopup, EditAnimePopup, ExportPopup, ImportPopup, TagFilterPopup

# Set a slightly larger default window size (preserve proportion) and keep borderless
Window.size = (1600, 960)
Window.borderless = True

user32 = ctypes.windll.user32

class DraggableTitleBar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hwnd = user32.GetForegroundWindow()
        self._drag = False
        self._click_x = 0
        self._click_y = 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            self._click_x = pt.x
            self._click_y = pt.y
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            self._win_x = rect.left
            self._win_y = rect.top
            self._drag = True
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._drag:
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            dx = pt.x - self._click_x
            dy = pt.y - self._click_y
            user32.MoveWindow(self.hwnd, self._win_x + dx, self._win_y + dy, Window.width, Window.height, True)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self._drag = False
        return super().on_touch_up(touch)


class DetailPopup(ModalView):
    """Large resizable popup for detailed slideshow / info of a single anime."""
    def __init__(self, anime_data, main_screen, **kwargs):
        super(DetailPopup, self).__init__(**kwargs)
        self.size_hint = (0.9, 0.9)
        self.auto_dismiss = True
        self.anime = anime_data
        self.main_screen = main_screen

        # build content via kv rule; populate ids after kv applied
        Clock.schedule_once(self._populate_kv, 0)

    def _populate_kv(self, dt):
        try:
            # title
            if hasattr(self.ids, 'detail_title'):
                self.ids.detail_title.text = self.anime.get('title', '')
            # poster
            poster_src = self.anime.get('poster_path', '')
            poster_thumb = get_thumbnail_path(poster_src) if poster_src else ''
            if poster_src and os.path.exists(poster_thumb):
                self.ids.detail_poster.source = poster_thumb
                self.ids.detail_poster.opacity = 1
                self.ids.detail_poster._full_source = poster_src
            elif poster_src and os.path.exists(poster_src):
                self.ids.detail_poster.source = poster_src
                self.ids.detail_poster._full_source = poster_src
                self.ids.detail_poster.opacity = 1
            else:
                # hide poster area
                self.ids.detail_poster.source = ''
                self.ids.detail_poster.opacity = 0

            # carousel (screenshots)
            carousel = self.ids.detail_carousel
            carousel.clear_widgets()
            for src in self.anime.get('screenshots_paths', []):
                try:
                    thumb = get_thumbnail_path(src) if src else ''
                    img_src = thumb if thumb and os.path.exists(thumb) else (src or '')
                    from kivy.uix.image import AsyncImage
                    img = AsyncImage(source=img_src, allow_stretch=True, keep_ratio=True)
                    img._full_source = src
                    # open original on touch
                    def _open_full(inst, touch):
                        if inst.collide_point(*touch.pos):
                            path = getattr(inst, '_full_source', None)
                            if path and os.path.exists(path):
                                try:
                                    os.startfile(path)
                                except Exception:
                                    pass
                    img.bind(on_touch_down=_open_full)
                    carousel.add_widget(img)
                except Exception:
                    continue

            # tags and description
            if hasattr(self.ids, 'detail_tags'):
                self.ids.detail_tags.text = ', '.join(self.anime.get('tags', []))
            if hasattr(self.ids, 'detail_description'):
                self.ids.detail_description.text = self.anime.get('description', '')
        except Exception:
            pass

    def on_edit(self):
        try:
            self.dismiss()
            self.main_screen.edit_anime(None)
        except Exception:
            pass

    def on_delete(self):
        try:
            self.dismiss()
            self.main_screen.delete_anime(None)
        except Exception:
            pass


class AnimeCard(ButtonBehavior, BoxLayout):
    def __init__(self, anime_data, main_screen, **kwargs):
        super(AnimeCard, self).__init__(**kwargs)
        self.anime_data = anime_data
        self.main_screen = main_screen
        # ensure kv-built ids are populated next frame
        Clock.schedule_once(self._populate_from_data, 0)
        # bind a unified handler that supports selection mode
        self.bind(on_press=self.on_card_click)
        # double-click support
        self._last_click = 0.0
        self._double_click_interval = 0.35

    def _populate_from_data(self, dt):
        try:
            # set title and tags
            if 'title_label' in self.ids:
                self.ids.title_label.text = self.anime_data.get('title', '')
            if 'tags_label' in self.ids:
                tags_text = ', '.join(self.anime_data.get('tags', [])) if self.anime_data.get('tags') else ''
                self.ids.tags_label.text = tags_text
            # poster thumbnail handling
            poster_src = self.anime_data.get('poster_path', '')
            thumb = get_thumbnail_path(poster_src) if poster_src else ''
            if poster_src and os.path.exists(thumb):
                if 'poster' in self.ids:
                    self.ids.poster.source = thumb
                    self.ids.poster.opacity = 1
                    self.ids.poster._full_source = poster_src
            elif poster_src:
                # placeholder until thumbnail created
                if 'poster' in self.ids:
                    self.ids.poster.source = ''
                    self.ids.poster.opacity = 0
                    self.ids.poster._full_source = poster_src
                # spawn background thumbnail creation
                def make_thumb():
                    try:
                        ensure_thumbs_dir()
                        local_src = copy_source_to_local(poster_src) or poster_src
                        create_thumbnail(local_src, thumb)
                        def set_thumb(dt):
                            try:
                                if 'poster' in self.ids:
                                    self.ids.poster.source = thumb
                                    self.ids.poster.opacity = 1
                            except Exception:
                                pass
                        Clock.schedule_once(set_thumb, 0)
                    except Exception:
                        pass
                threading.Thread(target=make_thumb, daemon=True).start()
            else:
                if 'poster' in self.ids:
                    self.ids.poster.source = ''
                    self.ids.poster.opacity = 0
        except Exception:
            pass

    def on_card_click(self, instance):
        # double-click detection
        import time
        now = time.time()
        if now - getattr(self, '_last_click', 0) <= self._double_click_interval:
            try:
                self.main_screen.open_detail_popup(self.anime_data)
            except Exception:
                pass
            self._last_click = 0
            return
        self._last_click = now

        if getattr(self.main_screen, 'multi_select_mode', False):
            self.main_screen.toggle_card_selection(self)
        else:
            # show details in side panel (not popup)
            try:
                self.main_screen.show_anime_details(self.anime_data)
            except Exception:
                pass

    def set_selected(self, sel=True):
        # visual feedback for selection
        self.selected = sel
        try:
            self.opacity = 0.6 if sel else 1
        except Exception:
            pass

class AnimeApp(App):
    is_dark_theme = BooleanProperty(True)
    primary_color = ListProperty([0.2, 0.6, 0.9, 1])
    secondary_color = ListProperty([0.15, 0.15, 0.15, 1])
    accent_color = ListProperty([0.9, 0.3, 0.3, 1])
    text_color = ListProperty([0.9, 0.9, 0.9, 1])
    bg_color = ListProperty([0.1, 0.1, 0.1, 1])
    input_bg_color = ListProperty([0.2, 0.2, 0.2, 1])
    current_language = StringProperty('en')
    
    # Translatable strings as properties
    str_add = StringProperty('Add')
    str_edit = StringProperty('Edit')
    str_delete = StringProperty('Delete')
    str_import = StringProperty('Import')
    str_export = StringProperty('Export')
    str_search = StringProperty('Search anime...')
    str_tags = StringProperty('Tags')
    str_sort = StringProperty('Sort')
    str_select_anime = StringProperty('Select Anime')
    str_a_z = StringProperty('A-Z')
    str_z_a = StringProperty('Z-A')
    str_date_added = StringProperty('Date Added')
    str_all = StringProperty('All')
    str_select_an_anime = StringProperty('Select an anime')
    str_delete_anime = StringProperty('Delete Anime')
    str_add_new_anime = StringProperty('Add New Anime')
    str_edit_anime = StringProperty('Edit Anime')
    str_title = StringProperty('Title:')
    str_poster = StringProperty('Poster:')
    str_screenshots = StringProperty('Screenshots:')
    str_description = StringProperty('Description:')
    str_browse = StringProperty('Browse')
    str_tags_label = StringProperty('Tags:')
    str_enter_anime_title = StringProperty('Enter anime title')
    str_enter_poster_path = StringProperty('Enter poster path')
    str_enter_screenshot_paths = StringProperty('Enter screenshot paths (comma separated)')
    str_enter_anime_description = StringProperty('Enter anime description')
    str_enter_tags_input = StringProperty('Enter tags (comma separated)')
    str_save = StringProperty('Save')
    str_cancel = StringProperty('Cancel')

    # Additional strings for popups and messages
    str_export_to_json = StringProperty('Export to JSON')
    str_import_from_json = StringProperty('Import from JSON')
    str_confirm_delete = StringProperty('Confirm Delete')
    str_filter_by_tags = StringProperty('Filter by tags')
    str_apply = StringProperty('Apply')
    str_ok = StringProperty('OK')
    str_yes = StringProperty('Yes')
    str_no = StringProperty('No')
    str_close = StringProperty('Close')
    str_importing = StringProperty('Importing...')
    str_exported_to = StringProperty('Exported to {}')
    str_import_successful = StringProperty('Import Successful')
    str_import_failed = StringProperty('Import Failed')
    str_export_successful = StringProperty('Export Successful')
    str_export_failed = StringProperty('Export Failed')
    str_validation_error = StringProperty('Validation Error')
    str_title_required = StringProperty('Title is required')
    
    # Additional dynamic labels
    str_no_anime_available = StringProperty('No anime available')
    str_bulk_delete = StringProperty('Bulk Delete')
    str_bulk_edit = StringProperty('Bulk Edit')
    str_delete_items = StringProperty('Delete items?')
    str_no_items_selected = StringProperty('No items selected')
    str_enter_tags = StringProperty('Enter tags (comma separated) to set for selected items')
    str_bulk_edit_tags = StringProperty('Bulk Edit Tags')
    
    # Delete button
    str_delete_button = StringProperty('Delete Anime')

    def build(self):
        self.db = AnimeDatabase()
        # Initialize all translatable strings
        self._update_strings()
        return MainScreen(db=self.db)

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        try:
            if self.is_dark_theme:
                # Switch to light theme
                self.is_dark_theme = False
                self.secondary_color = [0.95, 0.95, 0.95, 1]  # Light gray
                self.text_color = [0.1, 0.1, 0.1, 1]  # Dark text
                self.bg_color = [0.98, 0.98, 0.98, 1]  # Very light gray
                self.input_bg_color = [0.9, 0.9, 0.9, 1]  # Slightly darker light
            else:
                # Switch to dark theme
                self.is_dark_theme = True
                self.secondary_color = [0.15, 0.15, 0.15, 1]  # Dark Gray
                self.text_color = [0.9, 0.9, 0.9, 1]  # Light text
                self.bg_color = [0.1, 0.1, 0.1, 1]  # Very Dark Gray
                self.input_bg_color = [0.2, 0.2, 0.2, 1]  # Slightly lighter dark
            
            # Save theme preference to settings
            if hasattr(self.root, 'settings'):
                self.root.settings['theme'] = 'light' if not self.is_dark_theme else 'dark'
                self.root.save_settings()
        except Exception as e:
            pass

    def toggle_language(self):
        """Toggle between English and Russian"""
        try:
            if self.current_language == 'en':
                self.current_language = 'ru'
                set_language('ru')
            else:
                self.current_language = 'en'
                set_language('en')
            
            # Update all translatable strings
            self._update_strings()
            
            # Save language preference to settings
            if hasattr(self.root, 'settings'):
                self.root.settings['language'] = self.current_language
                self.root.save_settings()
        except Exception as e:
            pass

    def _update_strings(self):
        """Update all UI strings based on current language"""
        try:
            self.str_add = tr('add')
            self.str_edit = tr('edit')
            self.str_delete = tr('delete')
            self.str_import = tr('import')
            self.str_export = tr('export')
            self.str_search = tr('search')
            self.str_tags = tr('tags')
            self.str_sort = tr('sort')
            self.str_select_anime = tr('select_anime')
            self.str_a_z = tr('a_z')
            self.str_z_a = tr('z_a')
            self.str_date_added = tr('date_added')
            self.str_all = tr('all')
            self.str_select_an_anime = tr('select_an_anime')
            self.str_delete_anime = tr('delete_anime')
            self.str_add_new_anime = tr('add_new_anime')
            self.str_edit_anime = tr('edit_anime')
            self.str_title = tr('title')
            self.str_poster = tr('poster')
            self.str_screenshots = tr('screenshots')
            self.str_description = tr('description')
            self.str_browse = tr('browse')
            self.str_tags_label = tr('tags_label')
            self.str_enter_anime_title = tr('enter_anime_title')
            self.str_enter_poster_path = tr('enter_poster_path')
            self.str_enter_screenshot_paths = tr('enter_screenshot_paths')
            self.str_enter_anime_description = tr('enter_anime_description')
            self.str_enter_tags_input = tr('enter_tags_input')
            self.str_save = tr('save')
            self.str_cancel = tr('cancel')
            # Additional strings for popups
            self.str_export_to_json = tr('export_to_json')
            self.str_import_from_json = tr('import_from_json')
            self.str_confirm_delete = tr('confirm_delete')
            self.str_filter_by_tags = tr('filter_by_tags')
            self.str_apply = tr('apply')
            self.str_ok = tr('ok')
            self.str_yes = tr('yes')
            self.str_no = tr('no')
            self.str_close = tr('close')
            self.str_importing = tr('importing')
            self.str_import_successful = tr('import_successful')
            self.str_import_failed = tr('import_failed')
            self.str_export_successful = tr('export_successful')
            self.str_export_failed = tr('export_failed')
            self.str_validation_error = tr('validation_error')
            self.str_title_required = tr('title_required')
            # Additional dynamic labels
            self.str_no_anime_available = tr('no_anime_available')
            self.str_bulk_delete = tr('bulk_delete')
            self.str_bulk_edit = tr('bulk_edit')
            self.str_delete_items = tr('delete_items')
            self.str_no_items_selected = tr('no_items_selected')
            self.str_enter_tags = tr('enter_tags')
            self.str_bulk_edit_tags = tr('bulk_edit_tags')
            self.str_delete_button = tr('delete_anime')
        except Exception as e:
            pass

class MainScreen(Screen):
    def __init__(self, db, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.db = db
        self.anime_titles = [anime['title'] for anime in self.db.get_all_anime()]
        self.current_sort = 'title'
        self.sort_reverse = False
        self.current_tag = None
        self.current_tags = []
        self.multi_select_mode = False
        self.selected_cards = set()
        self.settings_path = os.path.join(os.getcwd(), 'settings.json')
        self.settings = {}
        self.load_settings()
        # Apply settings after kv ids exist
        Clock.schedule_once(lambda dt: self.apply_settings(), 0)
        Clock.schedule_once(lambda dt: self.load_anime_cards(), 0)
        # start watching window position/size to persist into settings
        Clock.schedule_once(lambda dt: self._start_window_watch(), 0.5)

    def load_settings(self):
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            else:
                self.settings = {}
            # apply to memory
            self.current_sort = self.settings.get('sort', 'title')
            self.sort_reverse = self.settings.get('sort_reverse', False)
            self.current_tag = self.settings.get('selected_tag', None)
            self.current_tags = self.settings.get('selected_tags', []) or []
            # load language preference
            language = self.settings.get('language', 'en')
            if language in ['en', 'ru']:
                set_language(language)
                # ...existing code...
        except Exception:
            self.settings = {}

    def save_settings(self):
        try:
            self.settings['sort'] = self.current_sort
            self.settings['sort_reverse'] = self.sort_reverse
            self.settings['selected_tag'] = self.current_tag
            self.settings['selected_tags'] = self.current_tags
            # write last known window geometry
            try:
                self.settings['window_size'] = list(Window.size)
            except Exception:
                pass
            try:
                # use Window.left/Window.top when available
                self.settings['window_pos'] = [int(getattr(Window, 'left', 0)), int(getattr(Window, 'top', 0))]
            except Exception:
                pass
            # last_dir may be set by update_last_dir
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def apply_settings(self):
        # set spinner texts according to settings without triggering actions
        try:
            # sort spinner
            if self.current_sort == 'title' and not self.sort_reverse:
                self.ids.sort_spinner.text = tr('a_z')
            elif self.current_sort == 'title' and self.sort_reverse:
                self.ids.sort_spinner.text = tr('z_a')
            elif self.current_sort == 'date':
                self.ids.sort_spinner.text = tr('date_added')
            # tag spinner
            if self.current_tag:
                self.ids.tag_filter.text = self.current_tag
            # multi-tag button text update
            if self.current_tags:
                self.ids.tag_multi_btn.text = ', '.join(self.current_tags[:3]) + (',...' if len(self.current_tags) > 3 else '')
            else:
                self.ids.tag_multi_btn.text = tr('tags')
        except Exception:
            pass
        # apply saved window geometry if exists
        try:
            ws = self.settings.get('window_size')
            wp = self.settings.get('window_pos')
            if ws and isinstance(ws, (list, tuple)) and len(ws) == 2:
                try:
                    Window.size = tuple(ws)
                except Exception:
                    pass
            if wp and isinstance(wp, (list, tuple)) and len(wp) == 2:
                try:
                    # Kivy may expose Window.left/top via position
                    Window.left, Window.top = int(wp[0]), int(wp[1])
                except Exception:
                    try:
                        # fallback: Window.position
                        Window.position = (int(wp[0]), int(wp[1]))
                    except Exception:
                        pass
        except Exception:
            pass

    def update_last_dir(self, path):
        # path should be a directory
        try:
            if path and os.path.isdir(path):
                self.settings['last_dir'] = path
                self.save_settings()
        except Exception:
            pass

    def show_message(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=message))
        btn = Button(text='OK', size_hint_y=None, height=40)
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.5, 0.3))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def load_anime_cards(self, search_query='', tag_filter=None):
        grid_layout = self.ids.grid_layout
        grid_layout.clear_widgets()

        # Get anime with current sort settings
        animes = self.db.get_all_anime(sort_by=self.current_sort, reverse=self.sort_reverse)

        # Apply search filter (filter the already-sorted list so sorting is preserved)
        if search_query:
            q = search_query.lower()
            animes = [a for a in animes if q in a.get('title','').lower() or q in a.get('description','').lower() or any(q in t.lower() for t in a.get('tags', []))]

        # Apply tag filter (filter the current list)
        # tag_filter may be a single tag or a list of tags
        if tag_filter:
            if isinstance(tag_filter, (list, tuple)) and tag_filter:
                # match if anime has any of the selected tags (OR)
                animes = [a for a in animes if any(t in a.get('tags', []) for t in tag_filter)]
            else:
                animes = [a for a in animes if tag_filter in a.get('tags', [])]

        # Create cards normally
        for anime in animes:
            card = AnimeCard(anime, self)
            grid_layout.add_widget(card)

        # Update tag spinner values
        all_tags = self.db.get_all_tags()
        self.ids.tag_filter.values = ['All'] + all_tags

        # Update anime selector spinner values without force-resetting the user's selection
        anime_titles = [a['title'] for a in self.db.get_all_anime()]
        values = ['Select Anime'] + anime_titles if anime_titles else ['No anime available']
        self.ids.anime_spinner.values = values
        if self.ids.anime_spinner.text not in values:
            # reset only if current selection disappeared
            self.ids.anime_spinner.text = values[0]

    def open_tag_filter(self, instance):
        tags = self.db.get_all_tags()
        content = TagFilterPopup(owner=self, tags=tags, selected=self.current_tags)
        popup = Popup(title='Filter by tags', content=content, size_hint=(0.5, 0.6))
        content.popup = popup
        popup.open()

    def enter_multi_select(self, instance=None):
        self.multi_select_mode = not self.multi_select_mode
        self.selected_cards.clear()
        # reset all card visuals
        try:
            for child in self.ids.grid_layout.children:
                if hasattr(child, 'set_selected'):
                    child.set_selected(False)
        except Exception:
            pass

    def toggle_card_selection(self, card):
        if card in self.selected_cards:
            self.selected_cards.remove(card)
            card.set_selected(False)
        else:
            self.selected_cards.add(card)
            card.set_selected(True)

    def bulk_delete(self, instance=None):
        if not self.selected_cards:
            from kivy.app import App
            app = App.get_running_app()
            self.show_message(app.str_bulk_delete, app.str_no_items_selected)
            return
        titles = [c.anime_data.get('title') for c in list(self.selected_cards)]
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        from kivy.app import App
        app = App.get_running_app()
        
        # Create label with binding to update dynamically
        msg_label = Label(text=f'{app.str_delete_items}: {len(titles)}')
        def update_msg(*args):
            msg_label.text = f'{app.str_delete_items}: {len(titles)}'
        app.bind(str_delete_items=update_msg)
        content.add_widget(msg_label)
        
        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok = Button(text=app.str_yes)
        cancel = Button(text=app.str_no)
        
        # Bind button texts to update dynamically
        def update_ok_text(*args):
            ok.text = app.str_yes
        def update_cancel_text(*args):
            cancel.text = app.str_no
        app.bind(str_yes=update_ok_text)
        app.bind(str_no=update_cancel_text)
        
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(btns)
        popup = Popup(title=app.str_bulk_delete, content=content, size_hint=(0.4, 0.3))
        
        # Bind popup title to update dynamically
        def update_title(*args):
            popup.title = app.str_bulk_delete
        app.bind(str_bulk_delete=update_title)

        def do_delete(inst):
            for t in titles:
                try:
                    recs = self.db.get_anime_by_title(t)
                    if recs:
                        rec = recs[0]
                        try:
                            delete_thumbnail(rec.get('poster_path', ''))
                        except Exception:
                            pass
                        try:
                            delete_copy(rec.get('poster_path', ''))
                        except Exception:
                            pass
                        for sp in rec.get('screenshots_paths', []):
                            try:
                                delete_thumbnail(sp)
                            except Exception:
                                pass
                            try:
                                delete_copy(sp)
                            except Exception:
                                pass
                    self.db.delete_anime(t)
                except Exception:
                    pass
            popup.dismiss()
            self.multi_select_mode = False
            self.selected_cards.clear()
            self.refresh_content()

        ok.bind(on_release=do_delete)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def bulk_edit(self, instance=None):
        if not self.selected_cards:
            from kivy.app import App
            app = App.get_running_app()
            self.show_message(app.str_bulk_edit, app.str_no_items_selected)
            return
        from kivy.app import App
        app = App.get_running_app()
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Create label with binding to update dynamically
        label = Label(text=app.str_enter_tags)
        def update_label(*args):
            label.text = app.str_enter_tags
        app.bind(str_enter_tags=update_label)
        content.add_widget(label)
        
        from kivy.uix.textinput import TextInput
        ti = TextInput(multiline=False)
        content.add_widget(ti)
        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok = Button(text=app.str_apply)
        cancel = Button(text=app.str_cancel)
        
        # Bind button texts to update dynamically
        def update_ok_text(*args):
            ok.text = app.str_apply
        def update_cancel_text(*args):
            cancel.text = app.str_cancel
        app.bind(str_apply=update_ok_text)
        app.bind(str_cancel=update_cancel_text)
        
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(btns)
        popup = Popup(title=app.str_bulk_edit_tags, content=content, size_hint=(0.5, 0.3))
        
        # Bind popup title to update dynamically
        def update_title(*args):
            popup.title = app.str_bulk_edit_tags
        app.bind(str_bulk_edit_tags=update_title)

        def apply_tags(inst):
            tags = [t.strip() for t in ti.text.split(',') if t.strip()]
            for c in list(self.selected_cards):
                try:
                    self.db.update_anime(c.anime_data.get('title'), {'tags': tags})
                except Exception:
                    pass
            popup.dismiss()
            self.multi_select_mode = False
            self.selected_cards.clear()
            self.refresh_content()

        ok.bind(on_release=apply_tags)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def bulk_export(self, instance=None):
        if not self.selected_cards:
            self.show_message('Bulk Export', 'No items selected')
            return
        # prepare data
        data = [c.anime_data for c in list(self.selected_cards)]
        def save_callback(paths):
            if paths:
                path = paths[0]
                if not path.endswith('.json'):
                    path += '.json'
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    self.show_message('Export Successful', f'Exported {len(data)} items to {path}')
                except Exception as e:
                    self.show_message('Export Failed', str(e))
        initial = self.settings.get('last_dir') if hasattr(self, 'settings') else None
        fc = FileChooserPopup(callback=save_callback, save_mode=True, filters=['*.json'], owner=self, initial_path=initial)
        fc.open()

    def show_anime_details(self, anime_data):
        # use empty source for transparent poster placeholder in details; keep full poster
        source = anime_data.get('poster_path', '')
        self.ids.current_poster.source = source
        self.ids.current_poster.opacity = 1 if source else 0
        self.ids.current_title.text = anime_data.get('title', '')
        self.ids.current_description.text = anime_data.get('description', '')
        # show tags in details
        self.ids.current_tags.text = ', '.join(anime_data.get('tags', [])) if anime_data.get('tags') else ''
        carousel = self.ids.screenshots_carousel
        carousel.clear_widgets()
        # show thumbnails in carousel for faster load; generate missing thumbs in background
        for screenshot in anime_data.get('screenshots_paths', []):
            try:
                thumb = get_thumbnail_path(screenshot) if screenshot else ''
                if screenshot and os.path.exists(thumb):
                    img = Image(source=thumb, allow_stretch=True, keep_ratio=True)
                    img._full_source = screenshot
                    carousel.add_widget(img)
                elif screenshot:
                    # placeholder until thumbnail is created
                    img = Image(source='', allow_stretch=True, keep_ratio=True)
                    img.opacity = 0
                    img._full_source = screenshot
                    carousel.add_widget(img)
                    # create thumbnail in background
                    def make_thumb_local(src, widget):
                        try:
                            ensure_thumbs_dir()
                            create_thumbnail(src, get_thumbnail_path(src))
                            def set_thumb(dt):
                                try:
                                    widget.source = get_thumbnail_path(src)
                                    widget.opacity = 1
                                except Exception:
                                    pass
                            Clock.schedule_once(set_thumb, 0)
                        except Exception:
                            # fallback to showing original image
                            def set_orig(dt):
                                try:
                                    widget.source = src
                                    widget.opacity = 1
                                except Exception:
                                    pass
                            Clock.schedule_once(set_orig, 0)
                    threading.Thread(target=functools.partial(make_thumb_local, screenshot, img), daemon=True).start()
                else:
                    # empty entry
                    img = Image(source='', allow_stretch=True, keep_ratio=True)
                    img.opacity = 0
                    carousel.add_widget(img)
            except Exception:
                try:
                    img = Image(source=screenshot, allow_stretch=True, keep_ratio=True)
                    carousel.add_widget(img)
                except Exception:
                    pass

    def on_spinner_select(self, spinner, text):
        # If a real anime is selected show details, otherwise clear details and use transparent poster
        if (text and text not in ('Select Anime', 'No anime available')):
            anime = self.db.get_anime_by_title(text)
            if anime:
                self.show_anime_details(anime[0])
                return
        # Clear details for non-selection or missing item
        try:
            self.ids.current_poster.source = ''
            self.ids.current_poster.opacity = 0
            self.ids.current_title.text = 'Select an anime'
            self.ids.current_description.text = ''
            self.ids.current_tags.text = ''
            self.ids.screenshots_carousel.clear_widgets()
        except Exception:
            pass

    def add_anime(self, instance):
        content = AddAnimePopup(self.db, self)
        popup = Popup(title='Add Anime', content=content, size_hint=(0.8, 0.8))
        content.popup = popup
        popup.open()
        # bind drag & drop to popup lifecycle
        try:
            Window.bind(on_dropfile=content._on_dropfile)
            popup.bind(on_dismiss=lambda *a: Window.unbind(on_dropfile=content._on_dropfile))
        except Exception:
            pass

    def edit_anime(self, instance):
        selected_title = self.ids.current_title.text
        if selected_title and selected_title != 'Select an anime':
            content = EditAnimePopup(self.db, self)
            popup = Popup(title='Edit Anime', content=content, size_hint=(0.8, 0.8))
            content.popup = popup
            popup.open()
            try:
                Window.bind(on_dropfile=content._on_dropfile)
                popup.bind(on_dismiss=lambda *a: Window.unbind(on_dropfile=content._on_dropfile))
            except Exception:
                pass
        else:
            # Could add a notification here that no anime is selected
            pass

    def delete_anime(self, instance):
        selected_title = self.ids.current_title.text
        if selected_title and selected_title != tr('select_an_anime'):
            # show confirmation popup
            content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            content.add_widget(Label(text=f"{tr('delete_title', selected_title)}"))
            btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
            btn_yes = Button(text=tr('yes'))
            btn_no = Button(text=tr('no'))
            btns.add_widget(btn_yes)
            btns.add_widget(btn_no)
            content.add_widget(btns)
            popup = Popup(title=tr('confirm_delete'), content=content, size_hint=(0.4, 0.3))

            def do_delete(instance):
                # delete thumbnails for this anime (poster + screenshots)
                try:
                    recs = self.db.get_anime_by_title(selected_title)
                    if recs:
                        rec = recs[0]
                        try:
                            delete_thumbnail(rec.get('poster_path', ''))
                        except Exception:
                            pass
                        try:
                            delete_copy(rec.get('poster_path', ''))
                        except Exception:
                            pass
                        for sp in rec.get('screenshots_paths', []):
                            try:
                                delete_thumbnail(sp)
                            except Exception:
                                pass
                            try:
                                delete_copy(sp)
                            except Exception:
                                pass
                except Exception:
                    pass
                self.db.delete_anime(selected_title)
                popup.dismiss()
                self.refresh_content()

            btn_yes.bind(on_release=do_delete)
            btn_no.bind(on_release=popup.dismiss)
            popup.open()

    def refresh_content(self):
        self.load_anime_cards()
        # Reset the details panel
        self.ids.current_poster.source = ''
        self.ids.current_poster.opacity = 0
        self.ids.current_title.text = 'Select an anime'
        self.ids.current_description.text = ''
        self.ids.current_tags.text = ''
        self.ids.screenshots_carousel.clear_widgets()

    def on_search_text(self, instance, value):
        self.load_anime_cards(search_query=value, tag_filter=self.current_tags)  

    def on_sort_select(self, spinner, text):
        if text == 'A-Z':
            self.current_sort = 'title'
            self.sort_reverse = False
        elif text == 'Z-A':
            self.current_sort = 'title'
            self.sort_reverse = True
        elif text == 'Date Added':
            self.current_sort = 'date'
            self.sort_reverse = True
        self.load_anime_cards(search_query=self.ids.search_input.text, tag_filter=self.current_tags)

    def on_tag_select(self, spinner, text):
        self.current_tag = None if text == 'All' else text
        self.load_anime_cards(search_query=self.ids.search_input.text, tag_filter=self.current_tag)

    def export_data(self, instance):
        content = ExportPopup(self.db, owner=self)
        popup = Popup(title='Export Data', content=content, size_hint=(0.4, 0.3))
        content.popup = popup
        popup.open()

    def import_data(self, instance):
        content = ImportPopup(self.db, self)
        popup = Popup(title='Import Data', content=content, size_hint=(0.4, 0.3))
        content.popup = popup
        popup.open()

    def _start_window_watch(self):
        # track window geometry and persist on change (polling for portability)
        try:
            self._last_win_size = list(Window.size)
            self._last_win_pos = [int(getattr(Window, 'left', 0)), int(getattr(Window, 'top', 0))]
        except Exception:
            self._last_win_size = [0, 0]
            self._last_win_pos = [0, 0]
        # poll every second
        self._win_watch_ev = Clock.schedule_interval(self._poll_window_geom, 1.0)

    def _stop_window_watch(self):
        try:
            if hasattr(self, '_win_watch_ev') and self._win_watch_ev:
                self._win_watch_ev.cancel()
        except Exception:
            pass

    def _poll_window_geom(self, dt):
        changed = False
        try:
            cur_size = list(Window.size)
            cur_pos = [int(getattr(Window, 'left', 0)), int(getattr(Window, 'top', 0))]
            if cur_size != getattr(self, '_last_win_size', None):
                self._last_win_size = cur_size
                self.settings['window_size'] = cur_size
                changed = True
            if cur_pos != getattr(self, '_last_win_pos', None):
                self._last_win_pos = cur_pos
                self.settings['window_pos'] = cur_pos
                changed = True
            if changed:
                # write settings quickly
                try:
                    with open(self.settings_path, 'w', encoding='utf-8') as f:
                        json.dump(self.settings, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        except Exception:
            pass

    def open_detail_popup(self, anime_data):
        try:
            dp = DetailPopup(anime_data, main_screen=self)
            dp.open()
        except Exception:
            pass

if __name__ == '__main__':
    # Ensure settings saved on exit; bind stop handler
    app = AnimeApp()
    try:
        app.run()
    finally:
        # attempt to save settings (if main screen exists)
        try:
            ms = app.root
            if hasattr(ms, 'save_settings'):
                ms.save_settings()
            if hasattr(ms, '_stop_window_watch'):
                ms._stop_window_watch()
        except Exception:
            pass

