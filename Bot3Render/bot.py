"""
Telegram bot for receiving forwarded threat messages
Parses messages and sends them to the database
"""
import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from parser import parse_threat_message
from database import db

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot statistics
bot_stats = {
    'messages_received': 0,
    'threats_parsed': 0,
    'threats_added': 0,
    'duplicates': 0
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """
🚨 **Aerial Threat Tracking Bot** 🚨

This bot monitors forwarded messages from threat reporting channels.

**Commands:**
/start - Show this message
/stats - Show bot statistics
/help - Show help information

**How to use:**
1. Forward messages from threat reporting channels to this bot
2. Bot will automatically parse and track threats
3. View live map at your web interface

⚠️ Forward messages containing threat information (drones, missiles, aircraft)
    """
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 **Help Information**

**Supported message formats:**
• "Drone heading to [City]"
• "Missile detected near [City]"
• "Shahed moving [direction]"
• "[Threat type] towards [City]"

**Supported threat types:**
🛩️ Drones (UAV, Shahed, Geran, БПЛА)
🚀 Missiles (Калібр, Іскандер, Кінжал)
✈️ Aircraft (Літак, Bomber, Fighter)

**Supported cities:**
Kyiv, Kharkiv, Odesa, Dnipro, Lviv, and 25+ more Ukrainian cities

**Languages:**
Both English and Ukrainian messages are supported

Forward any relevant messages and the bot will automatically extract threat information.
    """
    await update.message.reply_text(help_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    db_stats = db.get_statistics()
    
    stats_text = f"""
📊 **Bot Statistics**

**Messages:**
• Received: {bot_stats['messages_received']}
• Parsed: {bot_stats['threats_parsed']}
• Added: {bot_stats['threats_added']}
• Duplicates: {bot_stats['duplicates']}

**Database:**
• Total threats: {db_stats['total_threats']}
• Active (last hour): {db_stats['active_threats']}
• Cities tracked: {db_stats['cities_tracked']}

**Threat Types:**
"""
    
    for threat_type, count in db_stats['threat_types'].items():
        stats_text += f"• {threat_type.capitalize()}: {count}\n"
    
    await update.message.reply_text(stats_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages (forwarded or direct)"""
    message = update.message
    
    if not message or not message.text:
        return
    
    bot_stats['messages_received'] += 1
    
    # Extract source channel if forwarded
    source_channel = None
    if message.forward_from_chat:
        source_channel = message.forward_from_chat.title or message.forward_from_chat.username
    elif message.forward_from:
        source_channel = message.forward_from.username or "Private User"
    
    # Parse the message
    text = message.text
    parsed_threat = parse_threat_message(text, source_channel)
    
    if not parsed_threat:
        # Not a threat message, ignore
        logger.info(f"Non-threat message: {text[:50]}...")
        return
    
    bot_stats['threats_parsed'] += 1
    
    # Add to database
    added = db.add_threat(parsed_threat)
    
    if added:
        bot_stats['threats_added'] += 1
        
        # Send confirmation
        response = f"""
✅ **Threat Logged**

Type: {parsed_threat['threat_type'].upper()}
City: {parsed_threat.get('city', 'Unknown')}
Direction: {parsed_threat.get('direction', 'N/A')}
Source: {source_channel or 'Direct message'}

The threat has been added to the live map.
        """
        await message.reply_text(response)
        
        logger.info(f"Added threat: {parsed_threat['threat_type']} near {parsed_threat.get('city', 'Unknown')}")
    else:
        bot_stats['duplicates'] += 1
        await message.reply_text("ℹ️ This threat has already been reported (duplicate)")
        logger.info(f"Duplicate threat rejected")


async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Specifically handle forwarded messages"""
    # Same as handle_message, but we know it's forwarded
    await handle_message(update, context)


def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")


def run_bot():
    """Initialize and run the Telegram bot"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        logger.error("Bot will not start. Please set TELEGRAM_BOT_TOKEN in Replit Secrets")
        return
    
    try:
        # Create application
        application = Application.builder().token(token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        # Add message handlers
        # Handle forwarded messages
        application.add_handler(
            MessageHandler(filters.FORWARDED & filters.TEXT, handle_forwarded)
        )
        
        # Handle all text messages (including non-forwarded)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Starting Telegram bot...")
        logger.info("Bot is ready to receive messages")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")


if __name__ == "__main__":
    run_bot()
