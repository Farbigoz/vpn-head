# Безопасность и секреты

## Жёсткие правила

- Никаких реальных паролей, токенов, приватных ключей и клиентских конфигов
  в git. `.gitignore` исключает: реальные инвентари, `clients/clients.json`,
  `clients/output/`, `backups/`, файлы `vault-password*`.
- Секреты — только в Ansible Vault (`group_vars/all/vault.yml`)
  и/или секретах Semaphore. Шаблон содержимого:
  `ansible/inventories/example/group_vars/vault.example.yml`.
- SSH по паролю на нодах отключается только после проверки входа по ключу
  (`hardening_disable_password_auth: false` → проверка → `true`).
- База master 3x-ui целиком на ноды не копируется — только штатный
  multi-node/API-механизм.
- Изменения на действующих серверах — только после показа плана и
  подтверждения владельца.
- Production DNS не меняется автоматически по сигналу мониторинга.
- Скрипты смены DNS проверяют ожидаемый старый IP и идемпотентны.
- Секреты REG.RU хранятся только на дирижёре / в Vault.

## Перечень секретов для Vault

| Ключ | Назначение |
|---|---|
| `vault_admin_ssh_public_keys` | Публичные ключи админов (строго говоря не секрет, но удобно держать вместе) |
| `vault_regru_username`, `vault_regru_password` | REG.RU API: DNS-01 для acme.sh и `04-switch-dns` |
| `vault_xui_node_user`, `vault_xui_node_password` | Учётные данные панелей нод |
| `vault_hysteria2_password` | Пароль(и) Hysteria2 |

REALITY private key, short ID и AWG-ключи генерируются на нодах и попадают
в резервные копии `backups/` (локально, не в git). При замене ноды они
восстанавливаются из бэкапа — см. `docs/restore.md`.

## Пароль Vault

```bash
echo 'ваш-надёжный-пароль' > ~/.vpn-head-vault-pass
chmod 600 ~/.vpn-head-vault-pass
export ANSIBLE_VAULT_PASSWORD_FILE=~/.vpn-head-vault-pass
```

Файл с паролем хранится вне репозитория и нигде не коммитится.

## Если сервер скомпрометирован

Ключи переносить нельзя: при замене ноды генерируются новые UUID клиентов,
REALITY-ключи, пароли Hysteria2 и AWG-ключи, а клиентам выдаются новые
конфиги. Поэтому «замена без перенастройки клиентов» действует только для
некомпрометированного сервера.
