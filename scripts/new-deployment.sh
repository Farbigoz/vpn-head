#!/usr/bin/env bash
# Создание собственного инвентаря из шаблона example/.
# Запрашивает только НЕсекретные параметры. Секреты — через ansible-vault.
#
# Запуск: ./scripts/new-deployment.sh [--conductor-only]
#   --conductor-only  ноды не спрашивать (добавите их позже через Web UI)
set -euo pipefail

cd "$(dirname "$0")/.."
INV_DIR="ansible/inventories"
CONDUCTOR_ONLY="${1:-}"

read -rp "Имя развёртывания (латиница, без пробелов, напр. myvpn): " NAME
[ -n "$NAME" ] || { echo "Имя не задано"; exit 1; }
[ ! -e "$INV_DIR/$NAME" ] || { echo "Инвентарь $INV_DIR/$NAME уже существует"; exit 1; }

read -rp "Доменная зона у REG.RU (напр. vpn.example.com): " DOMAIN
read -rp "IP дирижёра (этот сервер; VPS или homelab): " CONDUCTOR_IP

cp -r "$INV_DIR/example" "$INV_DIR/$NAME"

# Дирижёр в hosts.yml
sed -i \
  -e "s|ansible_host: 198.51.100.10.*|ansible_host: $CONDUCTOR_IP|" \
  -e "s|conductor_ip: 198.51.100.10.*|conductor_ip: $CONDUCTOR_IP|" \
  "$INV_DIR/$NAME/hosts.yml"

# Домен в group_vars/all/vars.yml
sed -i "s|infra_domain: \"vpn.example.com\"|infra_domain: \"$DOMAIN\"|" \
  "$INV_DIR/$NAME/group_vars/all/vars.yml"

# Пример vault не копируем — оставляем как референс в example/
rm -f "$INV_DIR/$NAME/group_vars/all/vault.example.yml"

# Ноды: шаблонные удаляем; свои можно вписать сейчас или добавить
# позже через Web UI (шаблон «Добавить ноду»)
rm -f "$INV_DIR/$NAME/nodes.d"/n*.yml

if [ "$CONDUCTOR_ONLY" != "--conductor-only" ]; then
  read -rp "Добавить ноды сейчас? [y/N]: " ADD_NODES
  if [ "$ADD_NODES" = "y" ] || [ "$ADD_NODES" = "Y" ]; then
    for N in 1 2; do
      read -rp "Имя ноды (напр. n$N, пусто — пропустить): " NODE_NAME
      [ -n "$NODE_NAME" ] || continue
      read -rp "  IP $NODE_NAME: " NODE_IP
      read -rp "  FQDN $NODE_NAME (напр. $NODE_NAME.$DOMAIN): " NODE_FQDN
      cat > "$INV_DIR/$NAME/nodes.d/$NODE_NAME.yml" <<EOF
---
vpn_nodes:
  hosts:
    $NODE_NAME:
      ansible_host: $NODE_IP
      ansible_user: root
      node_fqdn: $NODE_FQDN
EOF
      echo "  -> $INV_DIR/$NAME/nodes.d/$NODE_NAME.yml"
    done
  fi
fi

echo "$NAME" > .deployment-name

cat <<EOF

Готово: $INV_DIR/$NAME/

Следующие шаги:
  1. Создайте vault с секретами (шаблон: $INV_DIR/example/group_vars/all/vault.example.yml):
       ansible-vault create $INV_DIR/$NAME/group_vars/all/vault.yml
  2. Дирижёр:        ansible-playbook -i $INV_DIR/$NAME playbooks/00-setup-conductor.yml
  3. Новая нода:     через Web UI Semaphore (шаблон «Добавить ноду»)
                     или ansible-playbook -i $INV_DIR/$NAME playbooks/00-add-node.yml \
                        -e "inventory_name=$NAME node_name=n1 node_ip=<IP> node_fqdn=<FQDN>"
EOF
