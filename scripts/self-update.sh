#!/usr/bin/env bash
# Обновление инструмента vpn-head до последней версии из git.
#
# Принцип: код живёт в git, ваши данные (inventories/*, clients/,
# backups/, reports/, .venv) gitignore'нуты и при обновлении
# НЕ затрагиваются.
#
# Запуск из корня репозитория: ./scripts/self-update.sh [тег]
set -euo pipefail

cd "$(dirname "$0")/.."

[ -d .git ] || { echo "Это не git-клон репозитория — обновляйте вручную."; exit 1; }

CURRENT="$(cat VERSION 2>/dev/null || echo 'unknown')"
echo "==> Текущая версия: $CURRENT"

echo "==> Получаю обновления"
git fetch --tags --quiet

LATEST="${1:-$(git tag --sort=-v:refname | head -1)}"
[ -n "$LATEST" ] || { echo "Тегов релизов не найдено."; exit 1; }
[ "$LATEST" != "$CURRENT" ] || { echo "Уже последняя версия ($CURRENT)."; exit 0; }

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Есть незакоммиченные изменения в отслеживаемых файлах —"
  echo "закоммитьте или отложите их (git stash), затем повторите."
  exit 1
fi

echo "==> Изменения $CURRENT -> $LATEST:"
git log --oneline "v${CURRENT}..${LATEST}" 2>/dev/null | head -20 || true

echo "==> Переключаюсь на $LATEST"
git checkout --quiet "$LATEST"

if ! git diff --quiet "$CURRENT" "$LATEST" -- ansible/requirements.yml 2>/dev/null; then
  echo "==> Изменились зависимости — перезапускаю bootstrap"
  ./scripts/bootstrap.sh
fi

cat <<EOF

Готово: версия $(cat VERSION).

Дальше:
  - прочитайте CHANGELOG.md (секция $LATEST);
  - плейбуки идемпотентны: при необходимости примените изменения ролей
    повторным прогоном 01-prepare-node на нужных нодах;
  - откат: git checkout v$CURRENT
EOF
