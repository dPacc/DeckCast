import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.transfer.file_manager import FileManager


@pytest.fixture
def data_dir():
    d = tempfile.mkdtemp(prefix="deckcast_fm_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def fm(data_dir):
    return FileManager(data_dir)


class TestFolderCRUD:
    def test_get_folders_empty(self, fm):
        assert fm.get_folders() == []

    def test_create_folder(self, fm):
        folder = fm.create_folder("My Folder")
        assert "id" in folder
        assert folder["name"] == "My Folder"
        assert len(fm.get_folders()) == 1

    def test_create_folder_strips_whitespace(self, fm):
        folder = fm.create_folder("  Spaced  ")
        assert folder["name"] == "Spaced"

    def test_rename_folder(self, fm):
        folder = fm.create_folder("Original")
        result = fm.rename_folder(folder["id"], "Renamed")
        assert result["name"] == "Renamed"
        assert fm.get_folders()[0]["name"] == "Renamed"

    def test_rename_nonexistent_folder(self, fm):
        result = fm.rename_folder("nonexistent", "Name")
        assert result == {}

    def test_delete_folder(self, fm):
        folder = fm.create_folder("ToDelete")
        assert fm.delete_folder(folder["id"]) is True
        assert fm.get_folders() == []

    def test_delete_nonexistent_folder(self, fm):
        assert fm.delete_folder("nonexistent") is False

    def test_multiple_folders(self, fm):
        fm.create_folder("Folder A")
        fm.create_folder("Folder B")
        fm.create_folder("Folder C")
        assert len(fm.get_folders()) == 3


class TestClipAssignment:
    def test_assign_clips_to_folder(self, fm):
        folder = fm.create_folder("Games")
        ok = fm.assign_clips(folder["id"], ["clip_1", "clip_2"])
        assert ok is True

    def test_assign_to_nonexistent_folder(self, fm):
        assert fm.assign_clips("nonexistent", ["clip_1"]) is False

    def test_remove_clips_from_folder(self, fm):
        folder = fm.create_folder("Games")
        fm.assign_clips(folder["id"], ["clip_1", "clip_2", "clip_3"])
        ok = fm.remove_clips(folder["id"], ["clip_2"])
        assert ok is True
        folders = fm.get_folders()
        assert "clip_2" not in folders[0].get("clips", [])
        assert "clip_1" in folders[0].get("clips", [])

    def test_reassign_moves_between_folders(self, fm):
        f1 = fm.create_folder("Folder A")
        f2 = fm.create_folder("Folder B")
        fm.assign_clips(f1["id"], ["clip_1"])
        fm.assign_clips(f2["id"], ["clip_1"])
        assert fm.get_folder_for_clip("clip_1") == f2["id"]

    def test_get_folder_for_unassigned_clip(self, fm):
        assert fm.get_folder_for_clip("unassigned") is None

    def test_get_folder_for_assigned_clip(self, fm):
        folder = fm.create_folder("Assigned")
        fm.assign_clips(folder["id"], ["clip_x"])
        assert fm.get_folder_for_clip("clip_x") == folder["id"]


class TestRenames:
    def test_get_display_name_default(self, fm):
        assert fm.get_display_name("clip_1", "default.mp4") == "default.mp4"

    def test_rename_clip(self, fm):
        ok = fm.rename_clip("clip_1", "My Cool Clip")
        assert ok is True
        assert fm.get_display_name("clip_1", "default.mp4") == "My Cool Clip"

    def test_rename_clip_empty_fails(self, fm):
        assert fm.rename_clip("clip_1", "   ") is False

    def test_rename_persists(self, fm, data_dir):
        fm.rename_clip("clip_1", "Saved Name")
        fm2 = FileManager(data_dir)
        assert fm2.get_display_name("clip_1", "fallback") == "Saved Name"


class TestDelete:
    def test_delete_file(self, fm, data_dir):
        test_file = data_dir / "test_clip.mp4"
        test_file.write_bytes(b"\x00" * 100)
        ok = fm.delete_clip(str(test_file), "test_clip")
        assert ok is True
        assert not test_file.exists()

    def test_delete_directory(self, fm, data_dir):
        clip_dir = data_dir / "clip_12345"
        clip_dir.mkdir()
        (clip_dir / "session.mpd").write_text("<MPD/>")
        (clip_dir / "chunk.m4s").write_bytes(b"\x00" * 50)
        ok = fm.delete_clip(str(clip_dir), "clip_12345")
        assert ok is True
        assert not clip_dir.exists()

    def test_delete_removes_rename(self, fm, data_dir):
        fm.rename_clip("clip_del", "Named Clip")
        assert fm.get_display_name("clip_del", "default") == "Named Clip"
        test_file = data_dir / "clip_del.mp4"
        test_file.write_bytes(b"\x00")
        fm.delete_clip(str(test_file), "clip_del")
        assert fm.get_display_name("clip_del", "default") == "default"

    def test_delete_removes_from_folders(self, fm, data_dir):
        folder = fm.create_folder("F1")
        fm.assign_clips(folder["id"], ["clip_rm"])
        test_file = data_dir / "clip_rm.mp4"
        test_file.write_bytes(b"\x00")
        fm.delete_clip(str(test_file), "clip_rm")
        assert fm.get_folder_for_clip("clip_rm") is None


class TestClientSecrets:
    def test_save_valid_installed(self, fm):
        data = {"installed": {"client_id": "abc", "client_secret": "xyz", "auth_uri": "", "token_uri": ""}}
        assert fm.save_client_secrets(data) is True
        assert fm.has_client_secrets() is True

    def test_save_valid_web(self, fm):
        data = {"web": {"client_id": "abc", "client_secret": "xyz"}}
        assert fm.save_client_secrets(data) is True
        assert fm.has_client_secrets() is True

    def test_save_missing_keys(self, fm):
        assert fm.save_client_secrets({"installed": {"client_id": "abc"}}) is False

    def test_save_wrong_structure(self, fm):
        assert fm.save_client_secrets({"other_key": {}}) is False

    def test_has_client_secrets_empty(self, fm):
        assert fm.has_client_secrets() is False

    def test_save_sets_permissions(self, fm, data_dir):
        data = {"installed": {"client_id": "a", "client_secret": "b"}}
        fm.save_client_secrets(data)
        secrets_path = data_dir / "client_secrets.json"
        assert secrets_path.exists()
        mode = oct(secrets_path.stat().st_mode & 0o777)
        assert mode == "0o600"


class TestPersistence:
    def test_folders_persist(self, data_dir):
        fm1 = FileManager(data_dir)
        fm1.create_folder("Persistent")
        fm2 = FileManager(data_dir)
        assert len(fm2.get_folders()) == 1
        assert fm2.get_folders()[0]["name"] == "Persistent"

    def test_corrupt_json_uses_default(self, data_dir):
        (data_dir / "folders.json").write_text("not valid json")
        fm = FileManager(data_dir)
        assert fm.get_folders() == []


class TestSanitiseFilename:
    def test_removes_slashes(self):
        assert "/" not in FileManager._sanitise_filename("a/b/c")
        assert "\\" not in FileManager._sanitise_filename("a\\b\\c")

    def test_removes_special_chars(self):
        result = FileManager._sanitise_filename('file:name<>"|')
        for ch in (':', '<', '>', '"', '|'):
            assert ch not in result

    def test_strips_dots(self):
        result = FileManager._sanitise_filename("...hidden...")
        assert not result.startswith(".")
        assert not result.endswith(".")
