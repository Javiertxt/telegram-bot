import os
import logging
from telegram import Update, ParseMode, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from pytz import timezone
import datetime

# Configurar el logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8443"))
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")

# Configuración del bot
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
scheduler = BackgroundScheduler(timezone="Europe/Madrid")

# Estados para la conversación
ASK_CHANNEL, ASK_STORE_NAME, ASK_TITLE, ASK_DESCRIPTION, ASK_COUPON, ASK_OFFER_PRICE, ASK_OLD_PRICE, ASK_URL, ASK_IMAGE, ASK_CONFIRMATION, ASK_SCHEDULE = range(11)

def start(update: Update, context: CallbackContext):
    context.user_data['publication_data'] = {}
    update.message.reply_text('Bienvenido al bot de publicaciones. ¿En qué canal deseas publicar?')
    return ASK_CHANNEL

def ask_channel(update: Update, context: CallbackContext):
    channel = update.message.text
    context.user_data['publication_data']['channel'] = channel
    update.message.reply_text('Por favor, ingresa el nombre de la tienda.')
    return ASK_STORE_NAME

def ask_store_name(update: Update, context: CallbackContext):
    store_name = update.message.text
    context.user_data['publication_data']['store_name'] = store_name
    update.message.reply_text('Por favor, ingresa el título de la publicación.')
    return ASK_TITLE

def ask_title(update: Update, context: CallbackContext):
    title = update.message.text
    context.user_data['publication_data']['title'] = title
    update.message.reply_text('Por favor, ingresa la descripción de la publicación.')
    return ASK_DESCRIPTION

def ask_description(update: Update, context: CallbackContext):
    description = update.message.text
    context.user_data['publication_data']['description'] = description
    update.message.reply_text('Por favor, ingresa el cupón de descuento.')
    return ASK_COUPON

def ask_coupon(update: Update, context: CallbackContext):
    coupon = update.message.text
    context.user_data['publication_data']['coupon'] = coupon
    update.message.reply_text('Por favor, ingresa el precio de oferta.')
    return ASK_OFFER_PRICE

def ask_offer_price(update: Update, context: CallbackContext):
    offer_price = update.message.text
    context.user_data['publication_data']['offer_price'] = offer_price
    update.message.reply_text('Por favor, ingresa el precio anterior.')
    return ASK_OLD_PRICE

def ask_old_price(update: Update, context: CallbackContext):
    old_price = update.message.text
    context.user_data['publication_data']['old_price'] = old_price
    update.message.reply_text('Por favor, ingresa el enlace de la publicación.')
    return ASK_URL

def ask_url(update: Update, context: CallbackContext):
    url = update.message.text
    context.user_data['publication_data']['url'] = url
    update.message.reply_text('Por favor, envía la imagen de la publicación o el enlace de la imagen.')
    return ASK_IMAGE

def ask_image(update: Update, context: CallbackContext):
    if update.message.photo:
        photo_file = update.message.photo[-1].get_file()
        context.user_data['publication_data']['image'] = photo_file.file_id
    else:
        context.user_data['publication_data']['image'] = update.message.text
    update.message.reply_text('¿Confirmas la publicación? (Sí/No)')
    preview_publication(update, context)
    return ASK_CONFIRMATION

def preview_publication(update: Update, context: CallbackContext):
    publication_data = context.user_data['publication_data']
    message = (
        f"<b><a href='{publication_data['url']}'>{publication_data['store_name']}</a></b>\n\n"
        f"<b>{publication_data['title']}</b>\n\n"
        f"{publication_data['description']}\n\n"
        f"<b>➡️CUPÓN: {publication_data['coupon']}</b>\n\n"
        f"<b>✅OFERTA: {publication_data['offer_price']}</b>\n\n"
        f"<b>❌ANTES: <s>{publication_data['old_price']}</s></b>\n\n"
        f"{publication_data['url']}\n"
    )

    if publication_data.get('image'):
        if publication_data['image'].startswith('http'):
            context.bot.send_photo(chat_id=update.message.chat_id, photo=publication_data['image'], caption=message, parse_mode=ParseMode.HTML)
        else:
            context.bot.send_photo(chat_id=update.message.chat_id, photo=publication_data['image'], caption=message, parse_mode=ParseMode.HTML)

def ask_confirmation(update: Update, context: CallbackContext):
    confirmation = update.message.text.lower()
    if confirmation in ['sí', 'si']:
        update.message.reply_text('¿Deseas publicar ahora o programar la publicación? (Ahora/Programar)')
        return ASK_SCHEDULE
    else:
        update.message.reply_text('Operación cancelada.')
        return ConversationHandler.END

def ask_schedule(update: Update, context: CallbackContext):
    schedule_choice = update.message.text.lower()
    if schedule_choice == 'ahora':
        post_publication(context)
        update.message.reply_text('Publicación realizada con éxito.')
        return ConversationHandler.END
    elif schedule_choice == 'programar':
        now = datetime.datetime.now(timezone('Europe/Madrid'))
        update.message.reply_text(f'Por favor, ingresa la fecha y hora de la publicación en el formato DD/MM/YYYY HH:MM (Hora actual: {now.strftime("%d/%m/%Y %H:%M")}).')
        return ASK_SCHEDULE
    else:
        update.message.reply_text('Opción no válida. Operación cancelada.')
        return ConversationHandler.END

def schedule(update: Update, context: CallbackContext):
    schedule_time = update.message.text
    try:
        schedule_time = datetime.datetime.strptime(schedule_time, "%d/%m/%Y %H:%M")
        schedule_time = timezone('Europe/Madrid').localize(schedule_time)
        job = scheduler.add_job(post_publication, DateTrigger(run_date=schedule_time), [context])
        job_id = str(job.id)
        scheduled_jobs[job_id] = context.user_data['publication_data'].copy()
        update.message.reply_text(f'Publicación programada para {schedule_time}.')
    except ValueError:
        update.message.reply_text('Formato de fecha y hora no válido. Operación cancelada.')
    return ConversationHandler.END

def post_publication(context: CallbackContext):
    publication_data = context.job.context.user_data['publication_data']
    message = (
        f"<b><a href='{publication_data['url']}'>{publication_data['store_name']}</a></b>\n\n"
        f"<b>{publication_data['title']}</b>\n\n"
        f"{publication_data['description']}\n\n"
        f"<b>➡️CUPÓN: {publication_data['coupon']}</b>\n\n"
        f"<b>✅OFERTA: {publication_data['offer_price']}</b>\n\n"
        f"<b>❌ANTES: <s>{publication_data['old_price']}</s></b>\n\n"
        f"{publication_data['url']}\n"
    )
    chat_id = publication_data['channel']
    if publication_data.get('image'):
        if publication_data['image'].startswith('http'):
            context.bot.send_photo(chat_id=chat_id, photo=publication_data['image'], caption=message, parse_mode=ParseMode.HTML)
        else:
            context.bot.send_photo(chat_id=chat_id, photo=publication_data['image'], caption=message, parse_mode=ParseMode.HTML)
    else:
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

# Definir el manejador de conversación
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        ASK_CHANNEL: [MessageHandler(Filters.text & ~Filters.command, ask_channel)],
        ASK_STORE_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_store_name)],
        ASK_TITLE: [MessageHandler(Filters.text & ~Filters.command, ask_title)],
        ASK_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, ask_description)],
        ASK_COUPON: [MessageHandler(Filters.text & ~Filters.command, ask_coupon)],
        ASK_OFFER_PRICE: [MessageHandler(Filters.text & ~Filters.command, ask_offer_price)],
        ASK_OLD_PRICE: [MessageHandler(Filters.text & ~Filters.command, ask_old_price)],
        ASK_URL: [MessageHandler(Filters.text & ~Filters.command, ask_url)],
        ASK_IMAGE: [MessageHandler(Filters.photo | Filters.text & ~Filters.command, ask_image)],
        ASK_CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, ask_confirmation)],
        ASK_SCHEDULE: [MessageHandler(Filters.text & ~Filters.command, ask_schedule)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

dispatcher.add_handler(conv_handler)

if __name__ == '__main__':
    scheduler.start()
    updater.start_polling()
    updater.idle()
