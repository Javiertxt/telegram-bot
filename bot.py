import os
import logging
import pytz
from telegram import Bot, Update, ParseMode
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater, CallbackContext, ConversationHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime

# Configurar el logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener el token del bot de las variables de entorno
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv('PORT', '8443'))

# Crear el bot
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Definir estados para la conversación
TITLE, URL, COUPON, OFFER_PRICE, OLD_PRICE, SCHEDULE_TIME, CONFIRMATION = range(7)

# Almacenar publicaciones programadas
scheduled_posts = []

# Inicializar el scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Manejar el comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("¡Bienvenido! Por favor, envíame el título de la publicación.")
    return TITLE

# Manejar el título
def get_title(update: Update, context: CallbackContext):
    context.user_data['title'] = update.message.text
    update.message.reply_text("Perfecto. Ahora envíame la URL de la publicación.")
    return URL

# Manejar la URL
def get_url(update: Update, context: CallbackContext):
    context.user_data['url'] = update.message.text
    update.message.reply_text("Genial. Ahora envíame el cupón de descuento (si no hay, escribe 'N/A').")
    return COUPON

# Manejar el cupón
def get_coupon(update: Update, context: CallbackContext):
    context.user_data['coupon'] = update.message.text
    update.message.reply_text("Entendido. Ahora envíame el precio de oferta.")
    return OFFER_PRICE

# Manejar el precio de oferta
def get_offer_price(update: Update, context: CallbackContext):
    context.user_data['offer_price'] = update.message.text
    update.message.reply_text("Gracias. Ahora envíame el precio anterior.")
    return OLD_PRICE

# Manejar el precio anterior
def get_old_price(update: Update, context: CallbackContext):
    context.user_data['old_price'] = update.message.text
    update.message.reply_text("¿Quieres publicar esto ahora o programarlo para más tarde? (Escribe 'ahora' o 'programar')")
    return SCHEDULE_TIME

# Manejar la programación
def schedule_time(update: Update, context: CallbackContext):
    choice = update.message.text.lower()
    if choice == 'ahora':
        # Publicar inmediatamente
        send_message(context)
        update.message.reply_text("La publicación ha sido realizada.")
        return ConversationHandler.END
    elif choice == 'programar':
        update.message.reply_text("Por favor, envíame la fecha y hora de publicación (formato: YYYY-MM-DD HH:MM).")
        return CONFIRMATION
    else:
        update.message.reply_text("Opción no válida. Por favor, escribe 'ahora' o 'programar'.")
        return SCHEDULE_TIME

# Manejar la confirmación
def confirmation(update: Update, context: CallbackContext):
    schedule_time_str = update.message.text
    try:
        schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%d %H:%M")
        schedule_time = pytz.timezone('Europe/Madrid').localize(schedule_time)

        # Añadir la tarea programada
        scheduler.add_job(send_message, DateTrigger(run_date=schedule_time), [context])
        update.message.reply_text(f"La publicación ha sido programada para {schedule_time_str}.")
        
        # Almacenar la publicación programada
        scheduled_posts.append((context.user_data.copy(), schedule_time))
        
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("Formato de fecha y hora no válido. Por favor, usa el formato: YYYY-MM-DD HH:MM.")
        return CONFIRMATION

# Enviar el mensaje
def send_message(context: CallbackContext):
    user_data = context.job.context.user_data
    message = f"<b>{user_data['title']}</b>\n\n"
    message += f"{user_data['url']}\n\n"
    if user_data['coupon'] != 'N/A':
        message += f"➡️<b>CUPÓN:</b> {user_data['coupon']}\n\n"
    message += f"✅<b>OFERTA:</b> {user_data['offer_price']}\n\n"
    message += f"❌<b>ANTES:</b> <s>{user_data['old_price']}</s>"

    context.bot.send_message(chat_id=context.job.context.chat_id, text=message, parse_mode=ParseMode.HTML)

# Manejar errores
def error(update: Update, context: CallbackContext):
    logger.warning(f"Update {update} caused error {context.error}")

# Configurar el manejador de conversaciones
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        TITLE: [MessageHandler(Filters.text & ~Filters.command, get_title)],
        URL: [MessageHandler(Filters.text & ~Filters.command, get_url)],
        COUPON: [MessageHandler(Filters.text & ~Filters.command, get_coupon)],
        OFFER_PRICE: [MessageHandler(Filters.text & ~Filters.command, get_offer_price)],
        OLD_PRICE: [MessageHandler(Filters.text & ~Filters.command, get_old_price)],
        SCHEDULE_TIME: [MessageHandler(Filters.text & ~Filters.command, schedule_time)],
        CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmation)],
    },
    fallbacks=[CommandHandler('start', start)]
)

dispatcher.add_handler(conv_handler)
dispatcher.add_error_handler(error)

# Iniciar el bot con Webhook en Heroku
if __name__ == '__main__':
    HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN)
    updater.bot.set_webhook(f"https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN}")

    updater.idle()



