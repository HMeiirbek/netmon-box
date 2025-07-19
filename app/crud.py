from . import models, schemas
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

# ============================================================================
# CRUD ОПЕРАЦИИ ДЛЯ УСТРОЙСТВ
# ============================================================================


def create_device(db: Session, device: schemas.DeviceCreate):
    """
    Создание нового устройства в базе данных

    Args:
        db: Сессия базы данных
        device: Данные устройства для создания

    Returns:
        Созданное устройство
    """
    db_device = models.Device(
        ip_address=str(device.ip_address),
        description=device.description,
        tags=",".join(device.tags) if device.tags else "",
        snmp_community=device.snmp_community,
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def get_device(db: Session, device_id: int):
    """Получение устройства по ID"""
    return (
        db.query(models.Device).filter(models.Device.id == device_id).first()
    )


def get_device_by_ip(db: Session, ip_address: str):
    """Получение устройства по IP-адресу"""
    return (
        db.query(models.Device)
        .filter(models.Device.ip_address == ip_address)
        .first()
    )


def get_devices(
    db: Session, skip: int = 0, limit: int = 100, active_only: bool = True
):
    """
    Получение списка устройств с пагинацией

    Args:
        db: Сессия базы данных
        skip: Количество записей для пропуска
        limit: Максимальное количество записей
        active_only: Только активные устройства

    Returns:
        Список устройств
    """
    query = db.query(models.Device)
    if active_only:
        query = query.filter(models.Device.is_active.is_(True))
    return query.offset(skip).limit(limit).all()


def update_device(
    db: Session, device_id: int, device_update: schemas.DeviceUpdate
):
    """
    Обновление информации об устройстве

    Args:
        db: Сессия базы данных
        device_id: ID устройства
        device_update: Данные для обновления

    Returns:
        Обновленное устройство или None
    """
    db_device = get_device(db, device_id)
    if not db_device:
        return None

    update_data = device_update.dict(exclude_unset=True)

    # Обрабатываем список тегов
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = ",".join(update_data["tags"])

    for field, value in update_data.items():
        setattr(db_device, field, value)

    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(db: Session, device_id: int):
    """
    Мягкое удаление устройства (деактивация)

    Args:
        db: Сессия базы данных
        device_id: ID устройства

    Returns:
        True если успешно, False если устройство не найдено
    """
    db_device = get_device(db, device_id)
    if not db_device:
        return False

    # Мягкое удаление - помечаем как неактивное
    db_device.is_active = False
    db.commit()
    return True


# ============================================================================
# CRUD ОПЕРАЦИИ ДЛЯ РЕЗУЛЬТАТОВ PING
# ============================================================================


def create_ping_result(db: Session, ping_result: schemas.PingResultCreate):
    """
    Создание записи результата ping

    Args:
        db: Сессия базы данных
        ping_result: Данные результата ping

    Returns:
        Созданная запись результата ping
    """
    db_ping_result = models.PingResult(
        device_id=ping_result.device_id,
        is_alive=ping_result.is_alive,
        response_time=ping_result.response_time,
        packet_loss=ping_result.packet_loss,
        error_message=ping_result.error_message,
    )
    db.add(db_ping_result)
    db.commit()
    db.refresh(db_ping_result)
    return db_ping_result


def get_device_ping_results(db: Session, device_id: int, limit: int = 100):
    """
    Получение истории результатов ping для устройства

    Args:
        db: Сессия базы данных
        device_id: ID устройства
        limit: Максимальное количество записей

    Returns:
        Список результатов ping, отсортированный по времени (новые сначала)
    """
    return (
        db.query(models.PingResult)
        .filter(models.PingResult.device_id == device_id)
        .order_by(desc(models.PingResult.timestamp))
        .limit(limit)
        .all()
    )


def get_last_ping_result(db: Session, device_id: int):
    """Получение последнего результата ping для устройства"""
    return (
        db.query(models.PingResult)
        .filter(models.PingResult.device_id == device_id)
        .order_by(desc(models.PingResult.timestamp))
        .first()
    )


def get_device_availability(db: Session, device_id: int, hours: int = 24):
    """
    Вычисление процента доступности устройства за последние N часов

    Args:
        db: Сессия базы данных
        device_id: ID устройства
        hours: Количество часов для расчета

    Returns:
        Процент доступности (0.0 - 100.0)
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    # Общее количество ping за период
    total_pings = (
        db.query(func.count(models.PingResult.id))
        .filter(models.PingResult.device_id == device_id)
        .filter(models.PingResult.timestamp >= since)
        .scalar()
    )

    if total_pings == 0:
        return 0.0

    # Количество успешных ping за период
    successful_pings = (
        db.query(func.count(models.PingResult.id))
        .filter(models.PingResult.device_id == device_id)
        .filter(models.PingResult.timestamp >= since)
        .filter(models.PingResult.is_alive.is_(True))
        .scalar()
    )

    return (successful_pings / total_pings) * 100


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def get_devices_with_status(db: Session, skip: int = 0, limit: int = 100):
    """
    Получение устройств с их последним статусом ping и процентом доступности

    Args:
        db: Сессия базы данных
        skip: Количество записей для пропуска
        limit: Максимальное количество записей

    Returns:
        Список устройств с дополнительной информацией о статусе
    """
    devices = get_devices(db, skip, limit, active_only=True)
    result = []

    for device in devices:
        last_ping = get_last_ping_result(db, device.id)
        availability = get_device_availability(db, device.id)

        device_data = {
            "id": device.id,
            "ip_address": device.ip_address,
            "description": device.description,
            "tags": device.tags.split(",") if device.tags else [],
            "snmp_community": device.snmp_community,
            "created_at": device.created_at,
            "is_active": device.is_active,
            "last_ping": _convert_ping_result_to_dict(last_ping),
            "availability_percentage": availability,
        }
        result.append(device_data)

    return result


def _convert_ping_result_to_dict(ping_result: models.PingResult):
    """
    Преобразование модели PingResult в словарь

    Args:
        ping_result: Модель результата ping

    Returns:
        Словарь с данными результата ping или None
    """
    if ping_result is None:
        return None
    return {
        "id": ping_result.id,
        "device_id": ping_result.device_id,
        "timestamp": ping_result.timestamp,
        "is_alive": ping_result.is_alive,
        "response_time": ping_result.response_time,
        "packet_loss": ping_result.packet_loss,
        "error_message": ping_result.error_message,
    }


def _convert_device_to_dict(device: models.Device):
    """
    Преобразование модели Device в словарь с правильной обработкой тегов

    Args:
        device: Модель устройства

    Returns:
        Словарь с данными устройства
    """
    return {
        "id": device.id,
        "ip_address": device.ip_address,
        "description": device.description,
        "tags": device.tags.split(",") if device.tags else [],
        "snmp_community": device.snmp_community,
        "created_at": device.created_at,
        "is_active": device.is_active,
    }
