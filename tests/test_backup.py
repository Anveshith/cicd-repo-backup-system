import os
import subprocess
import json
import pytest

BACKUP_DIR = os.environ.get("BACKUP_DIR", "/backups")
GPG_PASSPHRASE = os.environ.get("GPG_PASSPHRASE", "")


def get_latest_backup():
    """Find the most recent .gpg backup file."""
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".gpg")],
        reverse=True
    )
    assert files, f"No .gpg backup files found in {BACKUP_DIR}"
    return os.path.join(BACKUP_DIR, files[0])


def get_gpg_env():
    """Get environment variables for GPG commands, disabling agent in CI."""
    env = os.environ.copy()
    # Disable GPG agent in non-interactive environments (CI/CD)
    env["GNUPGHOME"] = "/tmp/gpg"
    os.makedirs(env["GNUPGHOME"], exist_ok=True)
    env["GPG_TTY"] = os.ttyname(0) if os.isatty(0) else ""
    return env


class TestBackupExists:
    def test_backup_file_created(self):
        path = get_latest_backup()
        assert os.path.isfile(path), f"Backup file not found: {path}"

    def test_backup_size_is_reasonable(self):
        path = get_latest_backup()
        size = os.path.getsize(path)
        assert size > 512, f"Backup too small ({size} bytes) — likely empty"

    def test_manifest_exists(self):
        manifest = os.path.join(BACKUP_DIR, "manifest.json")
        assert os.path.isfile(manifest), "manifest.json not created"

    def test_manifest_is_valid_json(self):
        manifest = os.path.join(BACKUP_DIR, "manifest.json")
        with open(manifest) as f:
            data = json.load(f)
        assert isinstance(data, list), "Manifest should be a JSON array"
        assert len(data) > 0, "Manifest is empty"

    def test_manifest_has_required_fields(self):
        manifest = os.path.join(BACKUP_DIR, "manifest.json")
        with open(manifest) as f:
            data = json.load(f)
        latest = data[-1]
        for field in ["file", "repo", "timestamp", "size_bytes"]:
            assert field in latest, f"Missing field '{field}' in manifest"


class TestBackupIntegrity:
    def test_file_is_valid_gpg_encrypted(self):
        path = get_latest_backup()
        result = subprocess.run(
            ["gpg", "--list-packets", "--batch", path],
            capture_output=True, text=True, env=get_gpg_env()
        )
        assert result.returncode == 0, f"gpg failed: {result.stderr}"
        assert "encrypted" in result.stdout.lower(), "File doesn't appear GPG-encrypted"

    def test_decrypt_succeeds(self, tmp_path):
        path = get_latest_backup()
        out = tmp_path / "decrypted.tar.gz"
        result = subprocess.run(
            ["gpg", "--batch", "--yes",
             "--passphrase", GPG_PASSPHRASE,
             "--output", str(out),
             "--decrypt", path],
            capture_output=True, text=True, env=get_gpg_env()
        )
        assert result.returncode == 0, f"Decryption failed: {result.stderr}"
        assert out.exists(), "Decrypted file not created"
        assert out.stat().st_size > 0, "Decrypted file is empty"

    def test_decrypted_is_valid_tar(self, tmp_path):
        path = get_latest_backup()
        out = tmp_path / "decrypted.tar.gz"
        subprocess.run(
            ["gpg", "--batch", "--yes",
             "--passphrase", GPG_PASSPHRASE,
             "--output", str(out), "--decrypt", path],
            check=True, capture_output=True, env=get_gpg_env()
        )
        result = subprocess.run(
            ["tar", "-tzf", str(out)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "tar listing failed — archive may be corrupt"
        assert ".git" in result.stdout, "No .git directory found in archive"

    def test_restore_produces_git_repo(self, tmp_path):
        path = get_latest_backup()
        out = tmp_path / "decrypted.tar.gz"
        subprocess.run(
            ["gpg", "--batch", "--yes",
             "--passphrase", GPG_PASSPHRASE,
             "--output", str(out), "--decrypt", path],
            check=True, capture_output=True, env=get_gpg_env()
        )
        subprocess.run(
            ["tar", "-xzf", str(out), "-C", str(tmp_path)],
            check=True, capture_output=True
        )
        git_dirs = list(tmp_path.glob("*.git"))
        assert git_dirs, "No bare .git repo found after restore"
        result = subprocess.run(
            ["git", "-C", str(git_dirs[0]), "log", "--oneline", "-3"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "git log failed — repo may be corrupt"
