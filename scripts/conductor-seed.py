#!/usr/bin/env python3
"""
Засев Semaphore: проект vpn-head, окружение, инвентарь, репозиторий,
ключ vault, шаблоны задач (00–04, «Сменить IP ноды»).
После этого всё делается кнопками в Web UI.

Запуск на дирижёре после 00-setup-conductor:
  SEMAPHORE_ADMIN_PASSWORD='...' ./scripts/conductor-seed.py --inventory <имя>

Пароль можно не задавать в env — скрипт прочитает его из
/root/.vpn-head/credentials.txt на дирижёре.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = Path("/root/.vpn-head/credentials.txt")


def read_admin_password() -> str:
    """Пароль администратора Semaphore из env или credentials-файла дирижёра."""
    pw = os.environ.get("SEMAPHORE_ADMIN_PASSWORD")
    if pw:
        return pw
    if CREDENTIALS_FILE.exists():
        m = re.search(r"пароль:\s*(\S+)", CREDENTIALS_FILE.read_text())
        if m:
            return m.group(1)
    raise SystemExit("Не найден пароль Semaphore: задайте SEMAPHORE_ADMIN_PASSWORD "
                     "или запустите на дирижёре (читается credentials.txt)")


class Semaphore:
    def __init__(self, base: str):
        self.base = base.rstrip("/") + "/api"
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar()))
        self.token = None

    def _req(self, method: str, path: str, body=None, raw=False):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            with self.opener.open(req, timeout=30) as resp:
                data = resp.read().decode()
                return data if raw else (json.loads(data) if data else {})
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            raise SystemExit(f"API {method} {path} -> HTTP {e.code}: {detail}")

    def login(self, user: str, password: str):
        self._req("POST", "/auth/login", {"auth": user, "password": password})
        # Сессионная cookie недостаточна для API-вызовов — создаём API-токен
        token = self._req("POST", "/user/tokens", {})
        self.token = token.get("id") or token.get("token") or token
        if not isinstance(self.token, str):
            raise SystemExit(f"Неожиданный ответ /user/tokens: {token}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Засев проекта vpn-head в Semaphore")
    ap.add_argument("--inventory", required=True, help="имя инвентаря")
    ap.add_argument("--semaphore", default="http://127.0.0.1:3000")
    args = ap.parse_args()

    user = os.environ.get("SEMAPHORE_ADMIN", "admin")
    sem = Semaphore(args.semaphore)
    sem.login(user, read_admin_password())
    print("· Вход выполнен, API-токен создан")

    # Проект (идемпотентно: ищем существующий)
    projects = sem._req("GET", "/projects")
    project = next((p for p in projects if p.get("name") == "vpn-head"), None)
    if not project:
        project = sem._req("POST", "/projects", {"name": "vpn-head"})
    pid = project["id"]
    print(f"· Проект vpn-head: id={pid}")

    def find_or_create(kind: str, name: str, body: dict):
        items = sem._req("GET", f"/project/{pid}/{kind}")
        found = next((i for i in items if i.get("name") == name), None)
        if found:
            return found
        return sem._req("POST", f"/project/{pid}/{kind}", body)

    # Пустое окружение (обязательно для шаблонов в Semaphore v2.10+)
    env = find_or_create("environment", "default",
                         {"name": "default", "json": "{}", "project_id": pid})
    print(f"· Окружение default: id={env['id']}")

    # Ключ: пароль Ansible Vault (из env VAULT_PASSWORD или /root/.vault-pass)
    vault_pass = os.environ.get("VAULT_PASSWORD", "")
    vp_file = Path("/root/.vault-pass")
    if not vault_pass and vp_file.exists():
        vault_pass = vp_file.read_text().strip()
    vault_key = find_or_create("keys", "ansible-vault", {
        "name": "ansible-vault", "type": "login_password",
        "project_id": pid,
        "login_password": {"login": "", "password": vault_pass},
    })
    print(f"· Ключ ansible-vault: id={vault_key['id']}")

    # Репозиторий — локальный клон на дирижёре
    # (смонтирован в контейнер Semaphore как /repo, см. compose.yml)
    repo = find_or_create("repositories", "vpn-head", {
        "name": "vpn-head", "project_id": pid,
        "git_url": "file:///repo", "git_branch": "main",
        "ssh_key_id": vault_key["id"],
    })
    print(f"· Репозиторий: id={repo['id']}")

    # Инвентарь — каталог внутри репозитория
    inv = find_or_create("inventory", args.inventory, {
        "name": args.inventory, "project_id": pid, "type": "file",
        "inventory": f"ansible/inventories/{args.inventory}",
        "repository_id": repo["id"], "ssh_key_id": vault_key["id"],
    })
    print(f"· Инвентарь {args.inventory}: id={inv['id']}")

    templates = [
        # (имя, плейбук, survey-поля)
        ("Добавить ноду", "ansible/playbooks/00-add-node.yml",
         ["inventory_name", "node_name", "node_ip", "node_fqdn"]),
        ("01 Подготовить ноду", "ansible/playbooks/01-prepare-node.yml", ["limit"]),
        ("02 Подключить ноду к master", "ansible/playbooks/02-join-node.yml", ["limit"]),
        ("03 Проверить ноду (canary)", "ansible/playbooks/03-validate-node.yml",
         ["limit", "node_ip"]),
        ("04 Переключить DNS", "ansible/playbooks/04-switch-dns.yml",
         ["node_fqdn", "expected_old_ip", "new_ip"]),
        ("Сменить IP ноды", "ansible/playbooks/04-switch-dns.yml",
         ["node_fqdn", "expected_old_ip", "new_ip"]),
    ]
    for name, playbook, survey in templates:
        tpl = find_or_create("templates", name, {
            "name": name, "project_id": pid, "playbook": playbook,
            "inventory_id": inv["id"], "repository_id": repo["id"],
            "environment_id": env["id"],
            "vaults": [{"vault_key_id": vault_key["id"], "type": "password",
                        "name": "ansible-vault"}],
            "survey_vars": [
                {"name": s, "title": s, "type": "string", "required": True}
                for s in survey],
        })
        print(f"· Шаблон «{name}»: id={tpl_id}" if (tpl_id := tpl.get('id')) else f"· Шаблон «{name}»")

    # TODO(VERIFY): workflow «Новая нода» (связка шаблонов add → 01 → 02 → 03)
    # реализовать через Workflow API Semaphore после проверки схемы.

    print("\nГотово. Откройте Web UI — проект vpn-head с шаблонами на месте.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
