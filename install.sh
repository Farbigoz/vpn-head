#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  vpn-head — установка дирижёра одной командой.
#
#  На чистом сервере (рекомендуется Debian 13; поддерживаются Debian 12,
#  Ubuntu 22.04+):
#    curl -fsSL <URL-ЭТОГО-ФАЙЛА> | bash
#  или из клона репозитория:
#    ./install.sh
#
#  Что произойдёт:
#    1. Установятся git, python3, Ansible.
#    2. Репозиторий будет склонирован в /opt/vpn-head (если нужно).
#    3. Интерактивно создастся ваш инвентарь (без секретов).
#    4. Развернётся дирижёр: Semaphore (Web UI), Uptime Kuma, 3x-ui master.
#    5. В терминал будут выведены все доступы (и сохранены в файл 600).
#
#  Дальше всё делается из Web UI Semaphore — см. docs/admin-ux.md.
# ════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_URL="${VPN_HEAD_REPO:-https://github.com/Farbigoz/vpn-head.git}"
INSTALL_DIR="${VPN_HEAD_DIR:-/opt/vpn-head}"

echo "══ vpn-head: установка дирижёра ══"

# --- 0. Права ---
if [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null; then
  echo "Нужен root или sudo."; exit 1
fi
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

# --- 1. Зависимости ---
echo "==> Пакеты: git, python3, pip"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq git python3 python3-venv python3-pip

# --- 2. Репозиторий ---
if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "==> Клонирую репозиторий в $INSTALL_DIR"
  $SUDO git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# --- 3. Окружение и Ansible ---
./scripts/bootstrap.sh

# --- 4. Инвентарь (один раз; ноды можно добавить позже через Web UI) ---
if [ ! -f .deployment-name ]; then
  ./scripts/new-deployment.sh --conductor-only
else
  NAME="$(cat .deployment-name)"
  echo "==> Инвентарь уже создан: $NAME"
fi
NAME="$(cat .deployment-name)"

# --- 5. Секреты ---
VAULT="ansible/inventories/$NAME/group_vars/all/vault.yml"
if [ ! -f "$VAULT" ]; then
  echo
  echo "==> Создайте vault с секретами (откроется редактор; шаблон:"
  echo "    ansible/inventories/example/group_vars/all/vault.example.yml)"
  read -rp "Нажмите Enter, чтобы открыть редактор vault..." _
  ansible-vault create "$VAULT"
fi

# --- 6. Дирижёр ---
echo "==> Разворачиваю дирижёр (Docker, Semaphore, Uptime Kuma, 3x-ui master)"
cd ansible
ansible-playbook -i "inventories/$NAME" playbooks/00-setup-conductor.yml -c local

cat <<EOF

══ Установка завершена ══
Доступы выведены выше и сохранены на сервере:
  $(grep -m1 credentials_file inventories/$NAME/group_vars/conductor.yml | awk '{print $2}' || echo '/root/.vpn-head/credentials.txt')

Дальше — Web UI Semaphore (добавление нод, все сценарии — кнопками):
  ssh -L 3000:127.0.0.1:3000 -L 3001:127.0.0.1:3001 root@<этот-сервер>
  затем открыть http://127.0.0.1:3000

Документация: $INSTALL_DIR/docs/admin-ux.md
EOF
