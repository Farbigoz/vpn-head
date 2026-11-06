#!/usr/bin/env bash
# Подготовка локального окружения: Python venv + Ansible + коллекции.
# Секреты не запрашивает и не создаёт. Запуск из корня репозитория:
#   ./scripts/bootstrap.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Python venv (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Установка Ansible"
pip install --quiet --upgrade pip
pip install --quiet ansible

echo "==> Коллекции Ansible (ansible/requirements.yml)"
ansible-galaxy collection install -r ansible/requirements.yml

echo "==> Проверка"
ansible --version | head -1

if [ ! -f "${HOME}/.vpn-head-vault-pass" ]; then
  cat <<'EOF'

Далее создайте файл с паролем Ansible Vault (НЕ в репозитории):
  echo 'ваш-надёжный-пароль' > ~/.vpn-head-vault-pass
  chmod 600 ~/.vpn-head-vault-pass

Затем создайте инвентарь: ./scripts/new-deployment.sh
и vault-файл: ansible-vault create ansible/inventories/<имя>/group_vars/all/vault.yml
(шаблон содержимого: ansible/inventories/example/group_vars/vault.example.yml)
EOF
fi

echo "==> Готово."
