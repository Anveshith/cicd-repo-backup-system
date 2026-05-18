"""Pytest configuration and fixtures."""
import os
import subprocess
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_gpg_env():
    """Initialize GPG environment for tests."""
    gpg_home = "/tmp/gpg"
    os.makedirs(gpg_home, mode=0o700, exist_ok=True)
    
    # Create GPG directory structure
    for subdir in ["private-keys-v1.d", "crls.d"]:
        os.makedirs(os.path.join(gpg_home, subdir), mode=0o700, exist_ok=True)
    
    yield
