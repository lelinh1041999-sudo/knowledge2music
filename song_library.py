"""File-backed audio library and recoverable deletion for Streamlit sessions."""

from datetime import datetime
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory, mkdtemp
from threading import Lock


SONGS = Path("saved_songs")
TRASH = SONGS / ".trash"
AUDIO_MIMES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac", ".ogg": "audio/ogg"}
_library_lock = Lock()


def _is_song(path):
    return path.suffix.lower() in AUDIO_MIMES and not path.is_symlink() and path.is_file()


def saved_songs():
    with _library_lock:
        if not SONGS.is_dir():
            return []
        return sorted((path for path in SONGS.iterdir() if _is_song(path)), reverse=True)


def trashed_songs():
    with _library_lock:
        if not TRASH.is_dir():
            return []
        return sorted(
            (path for folder in TRASH.iterdir() if folder.is_dir() and not folder.is_symlink()
             for path in folder.iterdir() if _is_song(path)),
            reverse=True,
        )


def _available_path(name):
    original = destination = SONGS / name
    index = 2
    while destination.exists() or destination.is_symlink():
        destination = original.with_stem(f"{original.stem} ({index})")
        index += 1
    return destination


def save_song(name, audio):
    # Normalize upload names on both Windows and Linux.
    name = PureWindowsPath(name).name
    if Path(name).suffix.lower() not in AUDIO_MIMES or ":" in name:
        raise ValueError("Unsupported audio filename")
    with _library_lock:
        SONGS.mkdir(exist_ok=True)
        with TemporaryDirectory(prefix=".saving-", dir=SONGS) as folder:
            temporary = Path(folder) / "audio"
            temporary.write_bytes(audio)
            return temporary.rename(_available_path(name))


def move_to_trash(song):
    with _library_lock:
        if song.parent != SONGS or not _is_song(song):
            raise FileNotFoundError(song.name)
        TRASH.mkdir(exist_ok=True)
        # Each entry keeps its original filename, even after repeated deletions.
        entry = mkdtemp(prefix=datetime.now().strftime("%Y%m%d_%H%M%S_%f_"), dir=TRASH)
        folder = TRASH / Path(entry).name
        try:
            return song.rename(folder / song.name)
        except OSError:
            _remove_empty_folder(folder)
            raise


def _require_trashed_song(song):
    if song.parent.parent != TRASH or song.parent.is_symlink() or not _is_song(song):
        raise FileNotFoundError(song.name)


def restore_song(song):
    with _library_lock:
        _require_trashed_song(song)
        restored = song.rename(_available_path(song.name))
        _remove_empty_folder(song.parent)
        return restored


def delete_song_permanently(song):
    with _library_lock:
        _require_trashed_song(song)
        song.unlink()
        _remove_empty_folder(song.parent)


def _remove_empty_folder(folder):
    try:
        folder.rmdir()
    except OSError:
        pass
