from pathlib import Path


def test_installation_grants_service_group_access_to_config_directory() -> None:
    install_script = Path("install.sh").read_text(encoding="utf-8")

    assert 'install -d -m 0750 -o root -g "$service_user" "$config_dir"' in install_script