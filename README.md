# 🌐 NetMon Box

Автономный сервис для инвентаризации и мониторинга лабораторной сети без внешних зависимостей и сторонних API.

## 📋 Описание

NetMon Box - это REST-приложение на Python + FastAPI, которое предоставляет:

- **Регистрация сетевых устройств** с IP-адресами, описаниями и тегами
- **Автоматический мониторинг** - каждую минуту пингует зарегистрированные узлы
- **Prometheus метрики** - экспорт метрик доступности и задержки
- **Веб-интерфейс** - простой UI для управления устройствами
- **Grafana дашборды** - визуализация метрик мониторинга

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │   Prometheus    │
│   (Port 8000)   │◄──►│   (Port 5432)   │    │   (Port 9090)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ping Service  │    │   CRUD Ops      │    │   Grafana       │
│   (Async)       │    │   (SQLAlchemy)  │    │   (Port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Компоненты

- **FastAPI** - REST API сервер
- **SQLAlchemy** - ORM для работы с базой данных
- **PostgreSQL** - реляционная база данных
- **Prometheus** - сбор и хранение метрик
- **Grafana** - визуализация метрик
- **Docker Compose** - оркестрация контейнеров

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Git

### Запуск

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd netmon-box
```

2. **Запустите приложение:**
```bash
docker-compose up -d
```

3. **Откройте в браузере:**
- **NetMon Box UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 📊 API Endpoints

### Управление устройствами

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/devices` | Список всех активных устройств |
| `POST` | `/devices` | Регистрация нового устройства |
| `GET` | `/devices/{id}` | Информация об устройстве |
| `PUT` | `/devices/{id}` | Обновление устройства |
| `DELETE` | `/devices/{id}` | Деактивация устройства |

### Мониторинг

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/devices/{id}/ping` | Принудительный ping устройства |
| `GET` | `/devices/{id}/ping-history` | История ping результатов |

### Системные

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/metrics` | Prometheus метрики |
| `GET` | `/health` | Проверка состояния |
| `GET` | `/docs` | Swagger UI документация |

## 📈 Prometheus метрики

Приложение экспортирует следующие метрики:

- `netmon_ping_requests_total` - общее количество ping запросов
- `netmon_ping_response_time_seconds` - время отклика в секундах
- `netmon_device_availability` - доступность устройства (0/1)
- `netmon_packet_loss_percentage` - процент потери пакетов

## 🗄️ Схема базы данных

### Таблица `devices`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER | Первичный ключ |
| `ip_address` | VARCHAR | IP-адрес устройства |
| `description` | VARCHAR | Описание устройства |
| `tags` | VARCHAR | Теги (через запятую) |
| `snmp_community` | VARCHAR | SNMP community строка |
| `created_at` | TIMESTAMP | Дата создания |
| `is_active` | BOOLEAN | Активность устройства |

### Таблица `ping_results`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER | Первичный ключ |
| `device_id` | INTEGER | Внешний ключ к devices |
| `timestamp` | TIMESTAMP | Время ping |
| `is_alive` | BOOLEAN | Доступность |
| `response_time` | FLOAT | Время отклика (мс) |
| `packet_loss` | FLOAT | Потеря пакетов (%) |
| `error_message` | VARCHAR | Сообщение об ошибке |

## 🧪 Тестирование

### Запуск тестов

```bash
# Unit тесты
pytest tests/test_ping_service.py -v

# Интеграционные тесты
pytest tests/test_integration.py -v

# Все тесты с покрытием
pytest tests/ -v --cov=app --cov-report=html
```

### Типы тестов

- **Unit тесты** - тестирование отдельных компонентов (ping сервис)
- **Интеграционные тесты** - тестирование полного цикла работы API
- **CI/CD тесты** - автоматические тесты в GitHub Actions

## 🔧 Разработка

### Локальная разработка

1. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

2. **Настройте базу данных:**
```bash
# Создайте .env файл с переменными окружения
DATABASE_URL=postgresql://user:password@localhost:5432/netmon
```

3. **Запустите приложение:**
```bash
uvicorn app.main:app --reload
```

### Структура проекта

```
netmon-box/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── models.py            # SQLAlchemy модели
│   ├── schemas.py           # Pydantic схемы
│   ├── crud.py              # CRUD операции
│   ├── database.py          # Настройки БД
│   ├── ping_service.py      # Ping сервис
│   ├── monitor_service.py   # Сервис мониторинга
│   └── metrics.py           # Prometheus метрики
├── tests/
│   ├── test_ping_service.py # Unit тесты
│   └── test_integration.py  # Интеграционные тесты
├── docker-compose.yml       # Docker Compose конфигурация
├── Dockerfile              # Docker образ
├── requirements.txt        # Python зависимости
└── README.md              # Документация
```

## 🚀 CI/CD Pipeline

GitHub Actions автоматически выполняет:

1. **Linting** - проверка кода (flake8, black, isort)
2. **Unit тесты** - тестирование компонентов
3. **Сборка образа** - создание Docker образа
4. **Интеграционные тесты** - тестирование в Docker Compose
5. **Публикация** - загрузка образа в GitHub Container Registry

## 📝 Примеры использования

### Регистрация устройства

```bash
curl -X POST "http://localhost:8000/devices" \
     -H "Content-Type: application/json" \
     -d '{
       "ip_address": "192.168.1.1",
       "description": "Router",
       "tags": ["gateway", "router"],
       "snmp_community": "public"
     }'
```

### Принудительный ping

```bash
curl -X POST "http://localhost:8000/devices/1/ping"
```

### Получение метрик

```bash
curl "http://localhost:8000/metrics"
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs app`
2. Убедитесь, что все сервисы запущены: `docker-compose ps`
3. Проверьте состояние: `curl http://localhost:8000/health`
4. Создайте Issue в репозитории
