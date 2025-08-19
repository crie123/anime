"""
Utility helpers for thumbnails.
Creates a thumbnails/ directory in the project root and generates small versions of images.
"""
import os
import hashlib
import time

THUMBS_DIR = os.path.join(os.getcwd(), 'thumbnails')
# directory to keep local copies of original source images (so sources are available locally)
COPIES_DIR = os.path.join(os.getcwd(), 'copies')
LOG_PATH = os.path.join(os.getcwd(), 'deletion.log')

def ensure_thumbs_dir():
    try:
        os.makedirs(THUMBS_DIR, exist_ok=True)
    except Exception:
        pass

def ensure_copies_dir():
    try:
        os.makedirs(COPIES_DIR, exist_ok=True)
    except Exception:
        pass

def _log_delete(msg):
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as lf:
            lf.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass

def _safe_name(path):
    # create a stable filename based on absolute path
    h = hashlib.sha1(os.path.abspath(path).encode('utf-8')).hexdigest()
    base = os.path.splitext(os.path.basename(path))[0]
    return f"thumb_{base}_{h}.jpg"

def _safe_copy_name(path):
    # generates a stable filename for a copied original, preserve extension
    h = hashlib.sha1(os.path.abspath(path).encode('utf-8')).hexdigest()
    base = os.path.basename(path)
    name, ext = os.path.splitext(base)
    return f"copy_{name}_{h}{ext}"

def get_thumbnail_path(src_path):
    ensure_thumbs_dir()
    name = _safe_name(src_path)
    return os.path.join(THUMBS_DIR, name)

def get_copy_path(src_path):
    ensure_copies_dir()
    name = _safe_copy_name(src_path)
    return os.path.join(COPIES_DIR, name)

def create_copy(src_path, copy_path=None):
    """Create a local copy of src_path in the copies directory and return the copy path."""
    ensure_copies_dir()
    try:
        import shutil
    except Exception:
        raise
    if not src_path:
        return ''
    if not os.path.exists(src_path):
        return ''
    if not copy_path:
        copy_path = get_copy_path(src_path)
    try:
        if os.path.exists(copy_path):
            return copy_path
        shutil.copy2(src_path, copy_path)
        return copy_path
    except Exception:
        return ''

def copy_source_to_local(src_path):
    """Convenience function: returns local copy path for src_path, creates it if missing."""
    try:
        if not src_path:
            return ''
        # if already inside copies dir, return as-is
        try:
            if os.path.commonpath([os.path.abspath(src_path), os.path.abspath(COPIES_DIR)]) == os.path.abspath(COPIES_DIR):
                return src_path
        except Exception:
            pass
        return create_copy(src_path, None)
    except Exception:
        return ''

def create_thumbnail(src_path, thumb_path, size=(320, 320)):
    """Create thumbnail using Pillow if available; returns thumb_path on success else raises."""
    ensure_thumbs_dir()
    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError('Pillow is required for creating thumbnails') from e

    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source not found: {src_path}")

    try:
        with Image.open(src_path) as im:
            im.thumbnail(size)
            # convert to RGB and save as JPEG for consistent thumbnails
            if im.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', im.size, (0, 0, 0))
                bg.paste(im, mask=im.split()[-1])
                bg.save(thumb_path, 'JPEG', quality=85)
            else:
                im.convert('RGB').save(thumb_path, 'JPEG', quality=85)
        return thumb_path
    except Exception as e:
        raise

def delete_thumbnail(src_path):
    """Delete thumbnail file(s) corresponding to src_path if they exist.

    Attempts to remove thumbnails for the provided path and for the copy path derived
    from it. Also scans thumbnails/ for files containing the basename token and removes them.
    Returns True if any file was removed.
    """
    try:
        if not src_path:
            _log_delete(f"delete_thumbnail called with empty src_path")
            return False
        abs_src = os.path.abspath(src_path)
        removed = False
        _log_delete(f"delete_thumbnail start for: {abs_src}")
        # candidate exact thumb for source
        try:
            thumb = get_thumbnail_path(abs_src)
            _log_delete(f"checking exact thumb: {thumb}")
            if os.path.exists(thumb):
                try:
                    os.remove(thumb)
                    removed = True
                    _log_delete(f"removed exact thumb: {thumb}")
                except Exception as e:
                    _log_delete(f"failed remove exact thumb: {thumb} -> {e}")
        except Exception as e:
            _log_delete(f"error computing exact thumb: {e}")

        # candidate thumb for the copy path derived from source
        try:
            copy_path = get_copy_path(abs_src)
            thumb_copy = get_thumbnail_path(copy_path)
            _log_delete(f"checking copy thumb: {thumb_copy}")
            if os.path.exists(thumb_copy):
                try:
                    os.remove(thumb_copy)
                    removed = True
                    _log_delete(f"removed copy thumb: {thumb_copy}")
                except Exception as e:
                    _log_delete(f"failed remove copy thumb: {thumb_copy} -> {e}")
        except Exception as e:
            copy_path = None
            _log_delete(f"error computing copy thumb: {e}")

        # Defensive: remove any thumbnail files containing basename tokens
        try:
            base_tokens = set()
            base_tokens.add(os.path.splitext(os.path.basename(abs_src))[0])
            if copy_path:
                base_tokens.add(os.path.splitext(os.path.basename(copy_path))[0])
            if os.path.isdir(THUMBS_DIR):
                for fn in os.listdir(THUMBS_DIR):
                    fn_lower = fn.lower()
                    for token in base_tokens:
                        if token and token.lower() in fn_lower:
                            fp = os.path.join(THUMBS_DIR, fn)
                            try:
                                os.remove(fp)
                                removed = True
                                _log_delete(f"removed token-matched thumb: {fp} (token={token})")
                            except Exception as e:
                                _log_delete(f"failed remove token-matched thumb: {fp} -> {e}")
                            break
        except Exception as e:
            _log_delete(f"error scanning thumbnails dir: {e}")

        _log_delete(f"delete_thumbnail finished for: {abs_src}, removed={removed}")
        return removed
    except Exception as e:
        _log_delete(f"delete_thumbnail unexpected error for {src_path}: {e}")
        return False

def _try_remove(path, retries=3, delay=0.05):
    """Try to remove a file, making it writable and retrying if necessary. Returns True if removed."""
    try:
        if not os.path.exists(path):
            return True
    except Exception:
        pass
    for attempt in range(retries):
        try:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    try:
                        os.chmod(path, 0o666)
                    except Exception:
                        pass
                    try:
                        os.remove(path)
                    except Exception as e:
                        _log_delete(f"_try_remove attempt {attempt} failed for {path}: {e}")
                if not os.path.exists(path):
                    return True
        except Exception as e:
            _log_delete(f"_try_remove unexpected error for {path}: {e}")
        time.sleep(delay)
    # final check
    try:
        return not os.path.exists(path)
    except Exception:
        return False

def delete_copy(src_path):
    """Delete the local copied original corresponding to src_path (or delete src_path if it is already a copy path).

    Deterministic matching: compute core basename from src_path, then for each file in COPIES_DIR
    strip leading 'copy_' prefixes and trailing hash segments to get its core name; if core names match
    (fuzzy, alnum compare), remove the file. Also attempt direct removal of exact computed copy path.
    Returns True if any file removed.
    """
    try:
        if not src_path:
            _log_delete(f"delete_copy called with empty src_path")
            return False
        abs_src = os.path.abspath(src_path)
        abs_copies = os.path.abspath(COPIES_DIR)
        removed_any = False
        _log_delete(f"delete_copy start for: {abs_src}")

        # If src is already inside copies dir, try to remove it directly
        try:
            norm_src = os.path.normcase(abs_src)
            norm_copies = os.path.normcase(abs_copies)
            if norm_src == norm_copies or norm_src.startswith(norm_copies + os.sep):
                if os.path.exists(abs_src):
                    try:
                        _try_remove(abs_src)
                        _log_delete(f"removed direct copy: {abs_src}")
                        return True
                    except Exception as e:
                        _log_delete(f"failed remove direct copy: {abs_src} -> {e}")
        except Exception as e:
            _log_delete(f"error checking if src inside copies: {e}")

        # Try exact computed copy path
        try:
            cp = get_copy_path(abs_src)
            if os.path.exists(cp):
                try:
                    _try_remove(cp)
                    _log_delete(f"removed computed copy: {cp}")
                    removed_any = True
                except Exception as e:
                    _log_delete(f"failed remove computed copy: {cp} -> {e}")
        except Exception as e:
            _log_delete(f"error computing/trying computed copy path: {e}")

        # Build normalized token for original
        try:
            import re
            def _normalize_name(s):
                # keep only alphanumerics
                return re.sub(r'[^0-9a-z]', '', s.lower())

            orig_base = os.path.splitext(os.path.basename(abs_src))[0]
            # strip leading copy_ prefixes if any
            ob = orig_base
            while ob.startswith('copy_'):
                ob = ob[len('copy_'):]
            orig_core = _normalize_name(ob)
            _log_delete(f"orig_core='{orig_core}' (from {orig_base})")

            # scan copies dir and match
            if os.path.isdir(COPIES_DIR):
                for fn in os.listdir(COPIES_DIR):
                    fp = os.path.join(COPIES_DIR, fn)
                    try:
                        fn_base = os.path.splitext(fn)[0]
                        # strip leading copy_ prefixes
                        fb = fn_base
                        while fb.startswith('copy_'):
                            fb = fb[len('copy_'):]
                        # remove trailing underscore-separated hash-like segments
                        parts = fb.split('_')
                        # drop trailing parts that look like hex hashes (length >=6 and hex)
                        def looks_like_hash(x):
                            if len(x) < 6:
                                return False
                            try:
                                int(x, 16)
                                return True
                            except Exception:
                                return False
                        while parts and looks_like_hash(parts[-1]):
                            parts = parts[:-1]
                        fb_core = '_'.join(parts)
                        fn_normal = _normalize_name(fb_core)
                        if not fn_normal:
                            continue
                        # fuzzy match: either contains the other
                        if orig_core in fn_normal or fn_normal in orig_core:
                            try:
                                _try_remove(fp)
                                removed_any = True
                                _log_delete(f"removed matched copy file: {fp} (matched '{fn_normal}' vs '{orig_core}')")
                            except Exception as e:
                                _log_delete(f"failed remove matched copy: {fp} -> {e}")
                    except Exception as e:
                        _log_delete(f"error processing copy file '{fn}': {e}")
        except Exception as e:
            _log_delete(f"error scanning copies dir for deterministic matches: {e}")

        _log_delete(f"delete_copy finished for: {abs_src}, removed_any={removed_any}")
        return removed_any
    except Exception as e:
        _log_delete(f"delete_copy unexpected error for {src_path}: {e}")
        return False

def regen_thumbnails_for_paths(paths, size=(320, 320)):
    """Generate thumbnails for a list of source image paths. Returns dict with results."""
    results = {'created': [], 'failed': []}
    ensure_thumbs_dir()
    for p in paths:
        try:
            if not p or not os.path.exists(p):
                results['failed'].append((p, 'missing'))
                continue
            thumb = get_thumbnail_path(p)
            # if already exists skip
            if os.path.exists(thumb):
                results['created'].append(thumb)
                continue
            try:
                create_thumbnail(p, thumb, size=size)
                results['created'].append(thumb)
            except Exception as e:
                results['failed'].append((p, str(e)))
        except Exception as e:
            results['failed'].append((p, str(e)))
    return results

def regen_copies_for_paths(paths):
    """Copy originals to local copies directory for the given list of paths. Returns dict with results."""
    results = {'copied': [], 'failed': []}
    ensure_copies_dir()
    import shutil
    for p in paths:
        try:
            if not p or not os.path.exists(p):
                results['failed'].append((p, 'missing'))
                continue
            # If path is already a copy inside COPIES_DIR, treat it as already copied and skip
            try:
                abs_p = os.path.abspath(p)
                abs_copies = os.path.abspath(COPIES_DIR)
                if os.path.commonpath([abs_p, abs_copies]) == abs_copies:
                    # already inside copies dir
                    results['copied'].append(abs_p)
                    continue
            except Exception:
                # if any error determining commonpath, fall back to normal behavior
                pass

            cp = get_copy_path(p)
            if os.path.exists(cp):
                results['copied'].append(cp)
                continue
            shutil.copy2(p, cp)
            results['copied'].append(cp)
        except Exception as e:
            results['failed'].append((p, str(e)))
    return results

def cleanup_unreferenced_copies(referenced_paths):
    """Remove files in COPIES_DIR that are not present in referenced_paths.

    referenced_paths: iterable of paths (absolute or relative) that should be kept.
    Returns a dict {'removed': [paths], 'kept': [paths], 'failed': [ (path, err) ]}
    """
    res = {'removed': [], 'kept': [], 'failed': []}
    try:
        ensure_copies_dir()
        # Build set of absolute paths to keep
        keep = set()
        for p in (referenced_paths or []):
            try:
                if not p:
                    continue
                ap = os.path.abspath(p)
                # if p is not in copies dir but corresponds to original, also include its computed copy path
                if os.path.commonpath([ap, os.path.abspath(COPIES_DIR)]) != os.path.abspath(COPIES_DIR):
                    try:
                        cp = get_copy_path(ap)
                        keep.add(os.path.abspath(cp))
                    except Exception:
                        pass
                keep.add(ap)
            except Exception:
                continue
        # iterate copies dir and remove files not in keep
        if os.path.isdir(COPIES_DIR):
            for fn in os.listdir(COPIES_DIR):
                fp = os.path.abspath(os.path.join(COPIES_DIR, fn))
                try:
                    if fp in keep:
                        res['kept'].append(fp)
                        continue
                    # not referenced: attempt remove
                    ok = _try_remove(fp)
                    if ok:
                        res['removed'].append(fp)
                        _log_delete(f"cleanup removed: {fp}")
                    else:
                        res['failed'].append((fp, 'remove_failed'))
                        _log_delete(f"cleanup failed to remove: {fp}")
                except Exception as e:
                    res['failed'].append((fp, str(e)))
                    _log_delete(f"cleanup exception for {fp}: {e}")
    except Exception as e:
        _log_delete(f"cleanup_unreferenced_copies unexpected error: {e}")
    return res
