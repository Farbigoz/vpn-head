# Changelog

Формат: [SemVer](https://semver.org/lang/ru/). Версия инструмента (этот файл)
и версии компонентов (`xui_version` и др. в group_vars) независимы.

## [0.2.0] — 2026-11-06

Web UI как основной путь, установка одной строкой:

- `install.sh` — установка дирижёра одной командой (`curl | bash`);
  в конце выводит все доступы в терминал и сохраняет их в файл 600.
- `00-setup-conductor` + роли `docker`, `conductor_stack`, `xui_master`:
  Semaphore, Uptime Kuma, 3x-ui master на дирижёре.
- `00-add-node` — добавление ноды из Web UI (survey) или CLI;
  инвентарь перестроен на формат `nodes.d/<нода>.yml` (файл на ноду).
- Сценарий «смена IP на том же VPS»: процедура в
  `docs/node-replacement.md` + шаблон «Сменить IP ноды» в Semaphore.
- `scripts/conductor-seed.py` — засев проекта и шаблонов задач
  в Semaphore (черновик, VERIFY).
- Рекомендуемая ОС — Debian 13 (поддерживаются Debian 12, Ubuntu 22.04+).
- `docs/admin-ux.md` переписан под Web UI-first сценарий.

## [0.1.0] — 2026-11-06

Первый каркас:

- роли `common` (SSH/UFW/Fail2ban, MOTD) и `xui_node` (3x-ui 2.6.1);
- плейбуки `01-prepare-node` (реализован), `02-join-node`,
  `03-validate-node`, `04-switch-dns` (заготовки с TODO/VERIFY);
- скрипты `bootstrap.sh`, `new-deployment.sh`, `gen-client-config.py`,
  `show-access.py`, `self-update.sh`;
- режимы клиентов `pinned` / `failover`;
- документация в `docs/`: архитектура, требования, безопасность,
  замена ноды, клиентские режимы, восстановление, обновление инструмента.
