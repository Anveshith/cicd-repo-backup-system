import os
import subprocess
import json
import pytest

BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")
GPG_PASSPHRASE = os.environ.get("GPG_PASSPHRASE", "")


def get_latest_backup():
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".gpg")],
        reverse=True
    )
    assert files, f"No .gpg backup files found in {BACKUP_DIR}"
    return os.path.join(BACKUP_DIR, files[0])


class TestBackupExists:
    def test_backup_file_created(self):
        path = get_latest_backup()
        assert os.path.isfile(path)

    def test_backup_size_is_reasonable(self):
        path = get_latest_backup()
        size = os.path.getsize(path)
        assert size > 512, f"Backup too small ({size} bytes)"

    def test_manifest_exists(self):
        manifest = os.path.join(BACKUP_DIR, "manifest.json")
        assert os.path.isfile(manifest)

    def test_manifest_is_valid_json(self):
        manifest = os.path.join(BACKUP_DIR, "manifest.json")
        with open(manifest) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_manifest_has_required_fields(self):
        manifest = os.path.join(BACKUP_DIR, "manifest.json")
        with open(manifest) as f:
            data = json.load(f)
        latest = data[-1]
        for field in ["file", "repo", "timestamp", "size_bytes"]:
            assert field in latest


class TestBackupIntegrity:
    def test_file_is_valid_gpg_encrypted(self):
        path = get_latest_backup()
        result = subprocess.run(
            ["gpg", "--list-packets", "--batch", path],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "encrypted" in result.stdout.lower()

    def test_decrypt_succeeds(self, tmp_path):
        path = get_latest_backup()
        out = tmp_path / "decrypted.tar.gz"
        result = subprocess.run(
            ["gpg", "--batch", "--yes",
             "--passphrase", GPG_PASSPHRASE,
             "--output", str(out),
             "--decrypt", path],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert out.exists()

    def test_decrypted_is_valid_tar(self, tmp_path):
        path = get_latest_backup()
        out = tmp_path / "decrypted.tar.gz"
        subprocess.run(
            ["gpg", "--batch", "--yes",
             "--passphrase", GPG_PASSPHRASE,
             "--output", str(out), "--decrypt", path],
            check=True, capture_output=True
        )
        result = subprocess.run(
            ["tar", "-tzf", str(out)],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert ".git" in result.stdout

    def test_restore_produces_git_repo(self, tmp_path):
        path = get_latest_backup()
        out = tmp_path / "decrypted.tar.gz"
        subprocess.run(
            ["gpg", "--batch", "--yes",
             "--passphrase", GPG_PASSPHRASE,
             "--output", str(out), "--decrypt", path],
            check=True, capture_output=True
        )
        subprocess.run(
            ["tar", "-xzf", str(out), "-C", str(tmp_path)],
            check=True, capture_output=True
        )
        git_dirs = list(tmp_path.glob("*.git"))
        assert git_dirs
        result = subprocess.run(
            ["git", "-C", str(git_dirs[0]), "log", "--oneline", "-3"],
            capture_output=True, text=True
        )
        assert result.returncode == 0