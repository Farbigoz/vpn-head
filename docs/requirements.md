# Требования

## Локальный ПК владельца

- Linux, macOS или Windows + WSL2 (скрипты рассчитаны на bash).
- Python 3.8+ (скрипт `bootstrap.sh` сам ставит Ansible в `.venv`).
- Git.

## Дирижёр (VPS или homelab — по выбору)

- 1 CPU / 1 GB RAM достаточно (трафик через него не идёт).
- ОС: **Debian 13 — рекомендуется**; поддерживаются Debian 12 и Ubuntu 22.04+.
- Статический IP или стабильный DNS-адрес — ноды открывают ему доступ
  к панелям через UFW (`conductor_ip` в инвентаре).
- Место под резервные копии (`backup_dir`, по умолчанию `/srv/vpn-head/backups`).

## VPN-ноды

- Минимум 2 VPS у **разных хостеров** (иначе теряется смысл отказоустойчивости).
- ОС: **Debian 13 «Trixie» — рекомендуется** (актуальный stable, поддержка
  до 2030, ядро 6.12 LTS). Поддерживаются также Debian 12 (oldstable,
  LTS до 2028) и Ubuntu 22.04+/24.04+ — плейбуки проверяют семейство
  `Debian`. CentOS/RHEL/Alpine не поддерживаются.
- Выделенный IPv4. При выдаче нового IP взамен заблокированного сначала
  проверьте его доступность из целевых регионов — см. `docs/node-replacement.md`.

## Домен и DNS

- Домен, обслуживаемый у REG.RU, с доступом к API
  (логин/пароль REG.RU — в Vault, см. `docs/security.md`).
- A-записи `n1.<зона>`, `n2.<зона>` и canary-поддомены `canary-n1.<зона>` и т.д.

## Версии (зафиксированы, обновлять осознанно)

| Компонент | Версия | Где задана |
|---|---|---|
| 3x-ui | 2.6.1 | `group_vars/all/vars.yml` → `xui_version` |

Перед первым применением сверьте `xui_version` с актуальным стабильным
релизом: https://github.com/MHSanaei/3x-ui/releases

## Клиентские платформы

- Android, iOS/iPadOS, Windows, macOS, Linux.
- VLESS (pinned) — любой клиент, принимающий `vless://` ссылку
  (v2rayNG, Streisand/Shadowrocket, Nekoray и т.п.).
- VLESS (failover) — клиент на ядре Xray с поддержкой JSON-конфига,
  observatory и balancer.
- AWG 3.1 — AmneziaVPN / AmneziaWG с импортом `.conf`.
- Hysteria2 — клиент с поддержкой Hysteria2, отдельный профиль на ноду.
