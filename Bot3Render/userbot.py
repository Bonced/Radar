"""
Userbot для мониторинга каналов угроз с использованием Telethon
Может читать сообщения из любых каналов, где вы состоите
"""
import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from parser import parse_threat_message
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_STRING = os.getenv('TELEGRAM_SESSION_STRING', '')

# Список каналов для мониторинга (можно указать username или ID)
MONITORED_CHANNELS = os.getenv('MONITORED_CHANNELS', '').split(',')
MONITORED_CHANNELS = [ch.strip() for ch in MONITORED_CHANNELS if ch.strip()]

# Статистика
userbot_stats = {
    'messages_received': 0,
    'threats_parsed': 0,
    'threats_added': 0,
    'channels_active': 0
}


class ThreatUserbot:
    """Userbot для мониторинга каналов с угрозами"""
    
    def __init__(self):
        self.client = None
        self.monitored_channels = MONITORED_CHANNELS.copy()
        self.channel_entities = {}
        
    async def start(self):
        """Запуск userbot"""
        if not API_ID or not API_HASH:
            logger.error("❌ TELEGRAM_API_ID и TELEGRAM_API_HASH не установлены!")
            logger.error("Получите их на https://my.telegram.org/apps")
            return False
        
        # Создаем клиента
        if SESSION_STRING:
            # Используем существующую сессию
            self.client = TelegramClient(
                StringSession(SESSION_STRING),
                API_ID,
                API_HASH
            )
            logger.info("📱 Использую существующую сессию")
        else:
            # Создаем новую сессию (для первого запуска)
            self.client = TelegramClient(
                'userbot_session',
                API_ID,
                API_HASH
            )
            logger.info("📱 Создаю новую сессию (потребуется авторизация)")
        
        try:
            await self.client.start()
            
            # Получаем информацию о текущем пользователе
            me = await self.client.get_me()
            logger.info(f"✅ Авторизован как: {me.first_name} (@{me.username})")
            
            # Сохраняем session string для использования на Render
            if not SESSION_STRING:
                session_string = self.client.session.save()
                logger.info("\n" + "="*60)
                logger.info("🔑 СОХРАНИТЕ ЭТУ СТРОКУ СЕССИИ!")
                logger.info("="*60)
                logger.info(f"\n{session_string}\n")
                logger.info("="*60)
                logger.info("Добавьте в переменные окружения Render:")
                logger.info("TELEGRAM_SESSION_STRING = строка выше")
                logger.info("="*60 + "\n")
            
            # Подключаемся к каналам
            await self.setup_channels()
            
            # Регистрируем обработчик новых сообщений
            @self.client.on(events.NewMessage(chats=self.channel_entities.values()))
            async def handler(event):
                await self.handle_message(event)
            
            logger.info("✅ Userbot запущен и мониторит каналы")
            logger.info(f"📡 Активных каналов: {len(self.channel_entities)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            return False
    
    async def setup_channels(self):
        """Настройка мониторинга каналов"""
        if not self.monitored_channels:
            logger.warning("⚠️  Нет каналов для мониторинга")
            logger.info("Добавьте их в MONITORED_CHANNELS (через запятую)")
            logger.info("Пример: @channel1,@channel2,-1001234567890")
            return
        
        logger.info("\n📡 Подключение к каналам...")
        
        for channel in self.monitored_channels:
            try:
                # Получаем entity канала
                if channel.startswith('-100') or channel.isdigit():
                    # Это ID канала
                    entity = await self.client.get_entity(int(channel))
                else:
                    # Это username канала
                    entity = await self.client.get_entity(channel)
                
                self.channel_entities[channel] = entity
                
                # Получаем информацию о канале
                if hasattr(entity, 'title'):
                    logger.info(f"  ✓ {entity.title} ({channel})")
                else:
                    logger.info(f"  ✓ {channel}")
                
                userbot_stats['channels_active'] += 1
                
            except Exception as e:
                logger.error(f"  ✗ Ошибка подключения к {channel}: {e}")
        
        logger.info(f"\n✅ Подключено к {len(self.channel_entities)} каналам\n")
    
    async def handle_message(self, event):
        """Обработка нового сообщения из канала"""
        try:
            message = event.message
            
            if not message.text:
                return
            
            userbot_stats['messages_received'] += 1
            
            # Получаем информацию о канале
            channel = await event.get_chat()
            channel_name = getattr(channel, 'title', 'Unknown Channel')
            
            # Парсим сообщение
            parsed = parse_threat_message(message.text, channel_name)
            
            if not parsed:
                return  # Не сообщение об угрозе
            
            userbot_stats['threats_parsed'] += 1
            
            # Добавляем в базу данных
            added = db.add_threat(parsed)
            
            if added:
                userbot_stats['threats_added'] += 1
                logger.info(
                    f"✅ Новая угроза: {parsed['threat_type'].upper()} "
                    f"→ {parsed.get('city', 'Unknown')} "
                    f"[{channel_name}]"
                )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def run(self):
        """Запуск и поддержание работы userbot"""
        if await self.start():
            logger.info("🔄 Userbot работает... (Ctrl+C для остановки)")
            await self.client.run_until_disconnected()
        else:
            logger.error("❌ Не удалось запустить userbot")
    
    async def stop(self):
        """Остановка userbot"""
        if self.client:
            await self.client.disconnect()
            logger.info("👋 Userbot остановлен")
    
    async def list_dialogs(self):
        """Показать список всех диалогов (для поиска каналов)"""
        logger.info("\n📋 Список ваших каналов и чатов:")
        logger.info("="*60)
        
        async for dialog in self.client.iter_dialogs():
            if dialog.is_channel:
                chat_id = dialog.id
                # Преобразуем в формат для бота
                bot_format_id = f"-100{chat_id}" if chat_id > 0 else str(chat_id)
                logger.info(f"📢 {dialog.name}")
                logger.info(f"   Username: @{dialog.entity.username if dialog.entity.username else 'Нет'}")
                logger.info(f"   ID: {bot_format_id}")
                logger.info("-" * 60)


# Глобальный экземпляр userbot
userbot = ThreatUserbot()


async def initialize_userbot():
    """Инициализация и запуск userbot"""
    await userbot.run()


def run_userbot():
    """Запуск userbot (вызывается из main.py)"""
    try:
        asyncio.run(initialize_userbot())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")


async def get_session_string():
    """
    Утилита для получения session string (первый запуск)
    Запускайте локально: python userbot.py
    """
    if not API_ID or not API_HASH:
        print("❌ Установите TELEGRAM_API_ID и TELEGRAM_API_HASH")
        print("Получите их на https://my.telegram.org/apps")
        return
    
    client = TelegramClient('auth_session', API_ID, API_HASH)
    
    await client.start()
    
    me = await client.get_me()
    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username})")
    
    session_string = client.session.save()
    
    print("\n" + "="*70)
    print("🔑 ВАШ SESSION STRING (сохраните его!):")
    print("="*70)
    print(f"\n{session_string}\n")
    print("="*70)
    print("\nДобавьте эти переменные окружения на Render:")
    print("-" * 70)
    print(f"TELEGRAM_API_ID = {API_ID}")
    print(f"TELEGRAM_API_HASH = {API_HASH}")
    print(f"TELEGRAM_SESSION_STRING = {session_string}")
    print("="*70)
    
    # Показываем список каналов
    print("\n📋 Ваши каналы (для MONITORED_CHANNELS):")
    print("="*70)
    
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            username = f"@{dialog.entity.username}" if dialog.entity.username else f"{dialog.id}"
            print(f"  {dialog.name}: {username}")
    
    print("="*70)
    print("\nПример MONITORED_CHANNELS:")
    print("@channel1,@channel2,-1001234567890")
    print("="*70 + "\n")
    
    await client.disconnect()


if __name__ == "__main__":
    # Если запускается напрямую - получаем session string
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auth":
        print("🔐 Режим авторизации - получение session string\n")
        asyncio.run(get_session_string())
    else:
        print("📱 Запуск userbot для мониторинга каналов\n")
        run_userbot()
