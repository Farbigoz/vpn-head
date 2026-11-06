#!/usr/bin/env python3
"""
Засев Semaphore: проект vpn-head, инвентарь, ключ, шаблоны задач (01–04,
«Добавить ноду») и workflow «Новая нода». После этого всё делается
кнопками в Web UI.

Запуск на дирижёре после 00-setup-conductor:
  ./scripts/conductor-seed.py --inventory <имя> [--semaphore http://127.0.0.1:3000]

СТАТУС: черновик. Точные эндпоинты/схемы Semaphore API сверить с версией
{{ semaphore_version }} (docs: https://docs.semaphoreui.com) — помечено VERIFY.
"""

import argparse
import json
import os
import sys
import urllib.request
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def api(base: str, token: str, method: str, path: str, body=None):
    req = urllib.request.Request(
        base.rstrip("/") + "/api" + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def login(base: str, user: str, password: str) -> str:
    """VERIFY: эндпоинт аутентификации (/auth/login) и формат токена."""
    req = urllib.request.Request(
        base.rstrip("/") + "/api/auth/login",
        method="POST",
        data=json.dumps({"auth": user, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        for cookie in resp.headers.get_all("Set-Cookie", []):
            if cookie.startswith("semaphore="):
                return cookie.split("=", 1)[1].split(";", 1)[0]
    raise RuntimeError("Не удалось получить сессию Semaphore")


def main() -> int:
    ap = argparse.ArgumentParser(description="Засев проекта vpn-head в Semaphore")
    ap.add_argument("--inventory", required=True, help="имя инвентаря")
    ap.add_argument("--semaphore", default="http://127.0.0.1:3000")
    args = ap.parse_args()

    user = os.environ.get("SEMAPHORE_ADMIN", "admin")
    password = os.environ.get("SEMAPHORE_ADMIN_PASSWORD") or getpass("Пароль Semaphore: ")

    token = login(args.semaphore, user, password)

    # VERIFY: схемы полей project/inventory/repository/template в API вашей версии.
    project = api(args.semaphore, token, "POST", "/projects",
                  {"name": "vpn-head"})
    pid = project["id"]

    api(args.semaphore, token, "POST", f"/project/{pid}/keys",
        {"name": "local ssh", "type": "none"})

    # Репозиторий — локальный клон на дирижёре (/opt/vpn-head).
    repo = api(args.semaphore, token, "POST", f"/project/{pid}/repositories",
               {"name": "vpn-head", "git_url": f"file://{ROOT}", "git_branch": "main"})
    rid = repo["id"]

    inv = api(args.semaphore, token, "POST", f"/project/{pid}/inventory",
              {"name": args.inventory, "type": "file",
               "inventory": f"ansible/inventories/{args.inventory}",
               "repository_id": rid})
    iid = inv["id"]

    templates = [
        # (имя, плейбук, survey-поля)
        ("Добавить ноду", "playbooks/00-add-node.yml",
         ["inventory_name", "node_name", "node_ip", "node_fqdn"]),
        ("01 Подготовить ноду", "playbooks/01-prepare-node.yml", ["limit"]),
        ("02 Подключить ноду к master", "playbooks/02-join-node.yml", ["limit"]),
        ("03 Проверить ноду (canary)", "playbooks/03-validate-node.yml", ["limit", "node_ip"]),
        ("04 Переключить DNS", "playbooks/04-switch-dns.yml",
         ["node_fqdn", "expected_old_ip", "new_ip"]),
        ("Сменить IP ноды", "playbooks/04-switch-dns.yml",
         ["node_fqdn", "expected_old_ip", "new_ip"]),
    ]
    for name, playbook, survey in templates:
        api(args.semaphore, token, "POST", f"/project/{pid}/templates",
            {"name": name, "playbook": playbook, "inventory_id": iid,
             "repository_id": rid, "survey_vars": [
                 {"name": s, "title": s, "type": "string", "required": True}
                 for s in survey]})

    # TODO(VERIFY): workflow «Новая нода» — связать шаблоны
    # «Добавить ноду» → 01 → 02 → 03 (Workflow API Semaphore).

    print("Готово. Откройте Web UI — шаблоны задач на месте.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
