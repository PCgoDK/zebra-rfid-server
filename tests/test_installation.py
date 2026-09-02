from pathlib import Path


def test_installation_grants_service_group_access_to_config_directory() -> None:
    install_script = Path("install.sh").read_text(encoding="utf-8")

    assert 'install -d -m 0750 -o root -g "$service_user" "$config_dir"' in install_script


def test_installation_opens_api_and_reader_input_firewall_ports() -> None:
    install_script = Path("install.sh").read_text(encoding="utf-8")

    assert "ufw allow 8080/tcp" in install_script
    assert "ufw allow 5084/tcp" in install_script


def test_github_bootstrap_clones_then_installs_to_opt() -> None:
    bootstrap_script = Path("install-from-github.sh").read_text(encoding="utf-8")

    assert "https://github.com/PCgoDK/zebra-rfid-server.git" in bootstrap_script
    assert 'git clone --depth 1 --branch "$branch" "$repository_url" "$source_dir"' in bootstrap_script
    assert 'bash "$source_dir/install.sh"' in bootstrap_script


def test_backup_grants_postgres_write_access_before_running_pg_dump() -> None:
    backup_script = Path("backup.sh").read_text(encoding="utf-8")

    assert 'install -d -m 0770 -o zebra-rfid-server -g postgres "$backup_dir"' in backup_script
    assert 'sudo -u postgres pg_dump' in backup_script