# 🔭 PortWatch

**Network port & service monitor** — мониторинг хостов/портов по расписанию, уведомления в Telegram и Email, история uptime в SQLite.

Идеально для домашних серверов, NAS (QNAP), VPN и self-hosted сервисов.

---

## ✨ Возможности

- **TCP-проверки** — любой порт (SSH, VPN, Plex, базы данных...)
- **HTTP/HTTPS-проверки** — GET-запрос с проверкой статус-кода
- **Telegram-уведомления** — мгновенный алерт при падении и восстановлении
- **Email-уведомления** — SMTP с TLS/SSL (Gmail, Yandex, кастомный сервер)
- **История uptime** — SQLite, хранение всех проверок, аггрегированная статистика
- **CLI** — команды `run`, `check`, `stats`
- **Python API** — встраивание в любой проект, callback `on_result`
- **Динамическое управление** — добавление/удаление хостов без перезапуска
- **Context manager** — `with PortWatch(...) as pw:`
- **QNAP Container Station** — готовый docker-compose YAML

---

## 📦 Установка

```bash
# Базовая установка (без YAML-конфигов)
pip install .

# С поддержкой YAML-конфигов
pip install ".[yaml]"

# Для разработки (тесты)
pip install ".[dev]"
```

**Требования:** Python ≥ 3.10, стандартная библиотека (нет внешних зависимостей для TCP/HTTP).

---

## 🚀 Быстрый старт

### Python API

```python
from portwatch import PortWatch, Host, TelegramNotifier

hosts = [
    Host(name="NAS SSH",     host="192.168.1.10", port=22),
    Host(name="VPN Server",  host="10.8.0.1",     port=1194),
    Host(name="Web App",     host="192.168.1.20", port=80,  protocol="http"),
    Host(name="Plex",        host="192.168.1.10", port=32400),
]

tg = TelegramNotifier(token="BOT_TOKEN", chat_id="CHAT_ID")

with PortWatch(hosts=hosts, interval=60, notifiers=[tg]) as pw:
    input("PortWatch запущен. Нажмите Enter для остановки...\n")
```

### CLI

```bash
# Скопировать пример конфига
cp portwatch.example.yaml portwatch.yaml
# Отредактировать: добавить хосты и токен Telegram

# Запустить непрерывный мониторинг
portwatch run -c portwatch.yaml

# Разовая проверка всех хостов
portwatch check -c portwatch.yaml

# Статистика uptime
portwatch stats -c portwatch.yaml
```

---

## ⚙️ Конфигурация (YAML)

```yaml
interval: 60           # секунды между проверками
db_path: portwatch.db  # путь к SQLite базе

hosts:
  - name: "Home NAS (SSH)"
    host: "192.168.1.10"
    port: 22
    protocol: tcp        # tcp | http | https
    timeout: 5
    tags: [nas, ssh]

  - name: "Home Web Server"
    host: "192.168.1.20"
    port: 80
    protocol: http
    http_url: "http://192.168.1.20/health"
    http_expected_status: 200

notifications:
  telegram:
    enabled: true
    token: "123456:ABC-DEF..."
    chat_id: "-100123456789"
    notify_on_recovery: true

  email:
    enabled: false
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    username: "you@gmail.com"
    password: "app-password"
    recipients: ["admin@example.com"]
```

---

## 🐳 QNAP Container Station

Поместите папку проекта в `/share/Container/portwatch/` на NAS и создайте приложение через `examples/container_station.yaml`:

```yaml
version: "3.8"
services:
  portwatch:
    image: python:3.11-slim
    container_name: portwatch
    restart: unless-stopped
    working_dir: /app
    volumes:
      - ./:/app
      - portwatch_data:/app/data
    environment:
      - TZ=Asia/Almaty
    command: >
      bash -c "pip install --quiet pyyaml &&
               python -m portwatch.cli run -c /app/portwatch.yaml"
volumes:
  portwatch_data:
```

> ⚡ Образ `python:3.11-slim` — ~60 МБ RAM. Подходит для QNAP с 4 ГБ.

---

## 📊 API Reference

### `Host`

| Параметр | Тип | Описание |
|---|---|---|
| `name` | str | Уникальное имя хоста |
| `host` | str | IP-адрес или hostname |
| `port` | int | Порт (1–65535) |
| `protocol` | str | `tcp`, `http`, `https` |
| `timeout` | float | Таймаут в секундах (default 5.0) |
| `http_url` | str | URL для HTTP-проверки (опционально) |
| `http_expected_status` | int | Ожидаемый HTTP статус (default 200) |
| `tags` | list | Метки для группировки |

### `PortWatch`

| Метод | Описание |
|---|---|
| `start()` | Запуск фонового мониторинга |
| `stop()` | Остановка мониторинга |
| `check_now()` | Разовая синхронная проверка всех хостов |
| `get_stats(name)` | Статистика uptime по имени хоста |
| `get_all_stats()` | Статистика по всем хостам |
| `get_recent(name, limit)` | Последние N результатов проверок |
| `add_host(host)` | Добавить хост на лету |
| `remove_host(name)` | Удалить хост по имени |

---

## 🧪 Тесты

```bash
# Запуск всех тестов
pytest tests/ -v

# С покрытием кода
pip install pytest-cov
pytest tests/ --cov=portwatch --cov-report=term-missing
```

**55 тестов** покрывают: модели, TCP/HTTP чекеры, SQLite историю, нотификаторы, планировщик, оркестратор.

---

## 📂 Структура проекта

```
portwatch/
├── portwatch/
│   ├── __init__.py      # Публичный API
│   ├── models.py        # Host, CheckResult, UptimeRecord
│   ├── checker.py       # TCP и HTTP/HTTPS проверки
│   ├── history.py       # SQLite хранилище
│   ├── notifiers.py     # Telegram + Email
│   ├── scheduler.py     # Фоновый планировщик
│   ├── monitor.py       # Главный оркестратор
│   ├── config.py        # Загрузка YAML/JSON конфига
│   └── cli.py           # CLI интерфейс
├── tests/               # 55 тестов
├── examples/            # Примеры использования
├── portwatch.example.yaml
├── setup.py
├── pyproject.toml
└── LICENSE              # MIT
```

---

## 📄 License

MIT License — см. [LICENSE](LICENSE).
