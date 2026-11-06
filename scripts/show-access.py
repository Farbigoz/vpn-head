#!/usr/bin/env python3
"""
Показать сводку доступов к инфраструктуре: ноды, панели, порты,
учётные данные из Vault.

Запуск из корня репозитория (в активированном .venv):
  ./scripts/show-access.py --inventory <имя>

Источники: ansible-inventory (не-секреты) + ansible-vault view (секреты).
Скрипт только читает — ничего не меняет.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT / "ansible", **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description="Сводка доступов vpn-head")
    ap.add_argument("--inventory",
                    default=os.environ.get("VPN_HEAD_INVENTORY", "example"),
                    help="имя инвентаря в ansible/inventories/")
    args = ap.parse_args()

    inv_dir = ROOT / "ansible" / "inventories" / args.inventory
    if not inv_dir.is_dir():
        print(f"Инвентарь не найден: {inv_dir}", file=sys.stderr)
        return 1

    # --- Инвентарь (не-секреты) ---
    r = sh(["ansible-inventory", "-i", str(inv_dir), "--list"])
    if r.returncode != 0:
        print("Ошибка ansible-inventory:\n" + r.stderr, file=sys.stderr)
        return 1
    inv = json.loads(r.stdout)

    try:
        import yaml
    except ImportError:
        print("Нужен PyYAML — активируйте .venv (./scripts/bootstrap.sh).", file=sys.stderr)
        return 1

    allvars = {}
    gv = inv_dir / "group_vars" / "all" / "vars.yml"
    if gv.exists():
        allvars = yaml.safe_load(gv.read_text(encoding="utf-8")) or {}

    panel_port = allvars.get("xui_panel_port", 2053)
    panel_path = allvars.get("xui_panel_path", "changeme-panel")
    ports = {k: allvars.get(k) for k in
             ("vless_tcp_port", "xhttp_port", "hysteria2_port", "awg_port")}

    print("=" * 64)
    print(f"Инфраструктура: {args.inventory}   (зона: {allvars.get('infra_domain', '?')})")
    print("=" * 64)

    for group, title in (("conductor", "ДИРИЖЁР"), ("vpn_nodes", "НОДЫ")):
        hosts = inv.get(group, {}).get("hosts", [])
        if not hosts:
            continue
        print(f"\n## {title}")
        for h in hosts:
            hv = inv.get("_meta", {}).get("hostvars", {}).get(h, {})
            fqdn = hv.get("node_fqdn", "-")
            print(f"  {h}: {hv.get('ansible_host', '?')}  fqdn={fqdn}")
            if group == "vpn_nodes":
                print(f"    панель:  http://{fqdn}:{panel_port}/{panel_path}/  "
                      f"(только для дирижёра)")
                print(f"    профили: VLESS tcp/{ports['vless_tcp_port']} · "
                      f"XHTTP tcp/{ports['xhttp_port']} · "
                      f"Hysteria2 udp/{ports['hysteria2_port']} · "
                      f"AWG udp/{ports['awg_port']}")
                report = ROOT / "reports" / f"{h}.yml"
                if report.exists():
                    print(f"    карточка: reports/{h}.yml")

    # --- Vault (секреты) ---
    vault = inv_dir / "group_vars" / "all" / "vault.yml"
    print("\n## УЧЁТНЫЕ ДАННЫЕ")
    if not vault.exists():
        print(f"  vault.yml ещё не создан: {vault}")
        print(f"  шаблон: ansible/inventories/example/group_vars/all/vault.example.yml")
        return 0

    env = dict(os.environ)
    cmd = ["ansible-vault", "view", str(vault)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("  Не удалось прочитать vault (пароль?). "
              "Проверьте ANSIBLE_VAULT_PASSWORD_FILE.", file=sys.stderr)
        return 1

    data = yaml.safe_load(r.stdout) or {}
    labels = {
        "vault_xui_node_user": "Панель нод, логин",
        "vault_xui_node_password": "Панель нод, пароль",
        "vault_hysteria2_password": "Hysteria2, пароль",
        "vault_regru_username": "REG.RU API, логин",
        "vault_regru_password": "REG.RU API, пароль",
    }
    for key, label in labels.items():
        if key in data:
            print(f"  {label}: {data[key]}")
    keys = data.get("vault_admin_ssh_public_keys") or []
    print(f"  SSH-ключи администраторов: {len(keys)} шт.")
    print("\nГотово. Скрипт ничего не изменяет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
