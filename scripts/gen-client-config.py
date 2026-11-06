#!/usr/bin/env python3
"""
Генератор клиентских конфигов vpn-head.

Вход: clients/clients.json (НЕ коммитится; пример — clients/clients.example.json).
Выход: clients/output/<клиент>/ — vless-ссылки и/или xray JSON-конфиг.

Режимы клиента (поле "mode"):
  pinned   — жёстко одна нода (preferred_node). Отказоустойчивости нет:
             нода упала — связи нет, переключение вручную. Подходит тем,
             кому важна конкретная страна выхода.
  failover — Xray JSON с observatory + balancer: автоматическое
             переключение между VLESS-нодами. Текущее соединение при отказе
             всё равно разорвётся, но новое поднимется через живую ноду.

Скрипт зависит только от стандартной библиотеки Python 3.8+.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote


def build_vless_link(client_uuid: str, node: dict, dep: dict, name: str) -> str:
    """Собрать vless:// ссылку для VLESS+TCP+REALITY+Vision."""
    r = dep["reality"]
    params = (
        f"security=reality&encryption=none"
        f"&pbk={quote(r['public_key'])}&fp={quote(r.get('fingerprint', 'chrome'))}"
        f"&sni={quote(r['sni'])}&sid={quote(r['short_id'])}"
        f"&flow=xtls-rprx-vision&type=tcp"
    )
    return (
        f"vless://{client_uuid}@{node['fqdn']}:{node['vless_port']}"
        f"?{params}#{quote(name)}"
    )


def build_outbound(client_uuid: str, node: dict, dep: dict) -> dict:
    """Xray outbound для VLESS+TCP+REALITY+Vision на одну ноду."""
    r = dep["reality"]
    return {
        "tag": f"proxy-{node['name']}",
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": node["fqdn"],
                "port": node["vless_port"],
                "users": [{
                    "id": client_uuid,
                    "encryption": "none",
                    "flow": "xtls-rprx-vision",
                }],
            }],
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "serverName": r["sni"],
                "publicKey": r["public_key"],
                "shortId": r["short_id"],
                "fingerprint": r.get("fingerprint", "chrome"),
            },
        },
    }


def build_failover_config(client_uuid: str, nodes: list, dep: dict) -> dict:
    """Xray JSON с observatory + balancer между всеми нодами."""
    outbounds = [build_outbound(client_uuid, n, dep) for n in nodes]
    outbounds.append({"tag": "direct", "protocol": "freedom"})
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": 10808,
            "protocol": "socks",
            "settings": {"udp": True},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
        }],
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "balancers": [{
                "tag": "proxy",
                "selector": ["proxy-"],
                "strategy": {"type": "leastPing"},
            }],
            "rules": [{
                "type": "field",
                "network": "tcp,udp",
                "balancerTag": "proxy",
            }],
        },
        "observatory": {
            "subjectSelector": ["proxy-"],
            "probeURL": "https://www.gstatic.com/generate_204",
            "probeInterval": "1m",
            "enableConcurrency": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Генератор клиентских конфигов vpn-head")
    ap.add_argument("--config", default="clients/clients.json",
                    help="путь к описанию клиентов (по умолчанию clients/clients.json)")
    ap.add_argument("--out", default="clients/output",
                    help="каталог для результатов")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Нет файла {cfg_path}. Скопируйте clients/clients.example.json "
              f"и заполните своими данными.", file=sys.stderr)
        return 1

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    dep = cfg["deployment"]
    nodes = {n["name"]: n for n in dep["nodes"]}
    out_root = Path(args.out)

    for client in cfg["clients"]:
        mode = client.get("mode", "pinned")
        cdir = out_root / client["name"]
        cdir.mkdir(parents=True, exist_ok=True)

        if mode == "pinned":
            node = nodes[client["preferred_node"]]
            link = build_vless_link(client["uuid"], node, dep,
                                    f"{dep['domain']}-{node['name']}-{client['name']}")
            (cdir / f"vless-{node['name']}.txt").write_text(link + "\n", encoding="utf-8")
            # Резервные профили остальных нод — для ручного переключения
            for n in dep["nodes"]:
                if n["name"] == node["name"]:
                    continue
                l = build_vless_link(client["uuid"], n, dep,
                                     f"{dep['domain']}-{n['name']}-{client['name']}-manual")
                (cdir / f"vless-{n['name']}-manual.txt").write_text(l + "\n", encoding="utf-8")
            print(f"[pinned]   {client['name']}: основной {node['fqdn']}, "
                  f"резервные ссылки для ручного переключения приложены")

        elif mode == "failover":
            conf = build_failover_config(client["uuid"], dep["nodes"], dep)
            (cdir / "xray-failover.json").write_text(
                json.dumps(conf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"[failover] {client['name']}: xray-failover.json "
                  f"({len(dep['nodes'])} нод, leastPing + observatory)")

        else:
            print(f"[ошибка]   {client['name']}: неизвестный mode '{mode}'", file=sys.stderr)
            return 2

    print(f"\nГотово. Результаты в {out_root}/ (каталог не коммитится).")
    print("Замечание: Hysteria2 и AWG распространяются отдельными профилями —")
    print("единого автоматического failover между всеми протоколами нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
