# Повседневная работа администратора (UX)

## Главный принцип

Установка — одна строка (`install.sh`). Всё остальное — в **Web UI
Semaphore** на дирижёре: добавление нод, вся цепочка сценариев, запуски
с полями ввода (survey). Терминал и файлы остаются доступны для опытных.

## Доступ к Web UI

По умолчанию интерфейсы слушают только `127.0.0.1` дирижёра:

```bash
ssh -L 3000:127.0.0.1:3000 -L 3001:127.0.0.1:3001 root@<дирижёр>
# Semaphore:  http://127.0.0.1:3000
# Uptime Kuma: http://127.0.0.1:3001
```

Логин/пароль Semaphore выводятся в конце установки и лежат в
`/root/.vpn-head/credentials.txt` (права 600). Хотите открыть UI снаружи
для конкретных IP — впишите их в `conductor_ui_allowed_from`
(`group_vars/conductor.yml`) и перезапустите `00-setup-conductor`.

## Типовые операции

### Добавить новую ноду — через Web UI

1. Создайте VPS и A-запись для его FQDN в REG.RU.
2. Semaphore → Tasks → workflow **«Новая нода»** → Run.
3. Введите поля: имя (`n3`), IP, FQDN.
4. Workflow сам выполнит цепочку: добавление в инвентарь
   (`00-add-node`) → `01-prepare-node` → `02-join-node` →
   `03-validate-node`. На каждом шаге виден лог.
5. Переключение DNS (`04-switch-dns`) — отдельный шаблон, всегда
   с ручным подтверждением.

Существующие ноды при этом не затрагиваются (везде `--limit <нода>`).

То же самое из терминала (путь «для прошаренных»):

```bash
cd /opt/vpn-head/ansible
ansible-playbook -i inventories/<имя> playbooks/00-add-node.yml \
  -e "inventory_name=<имя> node_name=n3 node_ip=<IP> node_fqdn=n3.<зона>"
ansible-playbook -i inventories/<имя> playbooks/01-prepare-node.yml --limit n3
```

Инвентарь — это файлы `inventories/<имя>/<нода>.yml`
(один файл на ноду): их можно править руками, UI и CLI не конфликтуют.

### Посмотреть доступы

- **Коротко:** `ssh root@<дирижёр> 'cat /root/.vpn-head/credentials.txt'`
- **Сводка по всей инфраструктуре (с локального ПК):**
  `./scripts/show-access.py --inventory <имя>`
- **Карточка ноды:** `reports/<нода>.yml` (создаётся после `01`).
- **На самой ноде:** MOTD при входе по SSH.

### Добавить клиента

1. Клиент создаётся в master-панели 3x-ui → UUID.
2. Запись в `clients/clients.json` (`mode: pinned|failover`).
3. `./scripts/gen-client-config.py` → готовые ссылки/конфиги
   в `clients/output/<клиент>/`.

### Мониторинг

Uptime Kuma (`:3001`): мониторы на каждую ноду по всем портам профилей,
оповещения о падении/восстановлении (Telegram и др. — настраивается
в UI Kuma). Автоматической смены DNS по сигналу мониторинга **нет** —
только уведомление вам.

### Сменить IP ноды (тот же VPS, новый IP от хостера)

1. Сделайте новый IP постоянным в ОС (netplan/interfaces — см.
   `docs/node-replacement.md`, раздел «Смена IP на том же VPS»).
2. Обновите `ansible_host` в `inventories/<имя>/<нода>.yml`.
3. В Semaphore запустите шаблон **«Сменить IP ноды»** — та же защита,
   что у переключения DNS (проверка старого IP + подтверждение).

### Обновить инструмент

```bash
./scripts/self-update.sh
```

См. `docs/upgrading.md`.

## Диагностика ноды изнутри

```bash
ssh deploy@<нода>            # MOTD покажет порты и путь панели
sudo x-ui status             # состояние панели/ядра
sudo journalctl -u x-ui -f   # логи
sudo fail2ban-client status sshd
```
