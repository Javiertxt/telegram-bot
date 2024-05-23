import os
import logging
from datetime import datetime
from pytz import timezone
from telegram import Bot, Update, ParseMode, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import requests

# Configurar el logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Configurar el token del bot
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)

# Definir constantes para las etapas de la conversación
CHANNEL, NAME, TITLE, DESCRIPTION, COUPON, DISCOUNT_PRICE, ORIGINAL_PRICE, LINK, IMAGE, CONFIRMATION = range(10)

# Crear un programador
scheduler = BackgroundScheduler(timezone=timezone('Europe/Madrid'))
scheduler.start()

# Función para iniciar el bot
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Hola! Te ayudaré a programar publicaciones. ¿En qué canal deseas publicar?')
    return CHANNEL

# Función para obtener el canal
def get_channel(update: Update, context: CallbackContext):
    context.user_data['channel'] = update.message.text
    update.message.reply_text('Por favor, proporciona el nombre de la tienda.')
    return NAME

# Función para obtener el nombre de la tienda
def get_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    update.message.reply_text('Por favor, proporciona el título de la publicación.')
    return TITLE

# Función para obtener el título
def get_title(update: Update, context: CallbackContext):
    context.user_data['title'] = update.message.text
    update.message.reply_text('Por favor, proporciona la descripción de la publicación.')
    return DESCRIPTION

# Función para obtener la descripción
def get_description(update: Update, context: CallbackContext):
    context.user_data['description'] = update.message.text
    update.message.reply_text('Por favor, proporciona el cupón de descuento.')
    return COUPON

# Función para obtener el cupón de descuento
def get_coupon(update: Update, context: CallbackContext):
    context.user_data['coupon'] = update.message.text
    update.message.reply_text('Por favor, proporciona el precio de oferta.')
    return DISCOUNT_PRICE

# Función para obtener el precio de oferta
def get_discount_price(update: Update, context: CallbackContext):
    context.user_data['discount_price'] = update.message.text
    update.message.reply_text('Por favor, proporciona el precio anterior.')
    return ORIGINAL_PRICE

# Función para obtener el precio anterior
def get_original_price(update: Update, context: CallbackContext):
    context.user_data['original_price'] = update.message.text
    update.message.reply_text('Por favor, proporciona el enlace de la publicación.')
    return LINK

# Función para obtener el enlace de la publicación
def get_link(update: Update, context: CallbackContext):
    context.user_data['link'] = update.message.text
    update.message.reply_text('Por favor, proporciona la imagen de la publicación (puede ser una URL o un archivo de imagen).')
    return IMAGE

# Función para obtener la imagen de la publicación
def get_image(update: Update, context: CallbackContext):
    if update.message.photo:
        # Si es un archivo de imagen
        photo_file = update.message.photo[-1].get_file()
        context.user_data['image'] = photo_file.file_id
        context.user_data['image_type'] = 'file'
    else:
        # Si es una URL
        context.user_data['image'] = update.message.text
        context.user_data['image_type'] = 'url'
    
    # Mostrar la previsualización de la publicación
    preview_message = (
        f"<b><a href='{context.user_data['link']}'>{context.user_data['name']}</a></b>\n\n"
        f"<b>{context.user_data['title']}</b>\n\n"
        f"{context.user_data['description']}\n\n"
        f"<b>➡️CUPÓN: {context.user_data['coupon']}</b>\n\n"
        f"<b>✅OFERTA: {context.user_data['discount_price']}</b>\n\n"
        f"<b>❌ANTES: <s>{context.user_data['original_price']}</s></b>\n\n"
        f"{context.user_data['link']}"
    )
    
    update.message.reply_text(preview_message, parse_mode=ParseMode.HTML)
    
    # Enviar la imagen si es una URL
    if context.user_data['image_type'] == 'url':
        update.message.reply_photo(context.user_data['image'])

    update.message.reply_text('¿Confirmas la publicación? (Sí/No)')
    return CONFIRMATION

# Función para confirmar la publicación
def confirm(update: Update, context: CallbackContext):
    user_response = update.message.text.lower()
    if user_response == 'sí' or user_response == 'si':
        update.message.reply_text('¿Deseas publicar ahora o programar la publicación? (Escribe "ahora" o "programar")')
    else:
        update.message.reply_text('Operación cancelada.')
        return ConversationHandler.END

    return None

# Función para decidir si publicar ahora o programar
def publish_or_schedule(update: Update, context: CallbackContext):
    user_response = update.message.text.lower()
    if user_response == 'ahora':
        publish_message(update, context)
    elif user_response == 'programar':
        current_time = datetime.now(timezone('Europe/Madrid')).strftime('%Y-%m-%d %H:%M:%S')
        update.message.reply_text(f'Por favor, proporciona la fecha y hora de la publicación (formato: YYYY-MM-DD HH:MM). Hora actual: {current_time}')
        return SCHEDULE_TIME
    else:
        update.message.reply_text('Respuesta no reconocida. Por favor, escribe "ahora" o "programar".')
        return None

# Función para obtener la hora de la publicación
def get_schedule_time(update: Update, context: CallbackContext):
    schedule_time = update.message.text
    schedule_datetime = datetime.strptime(schedule_time, '%Y-%m-%d %H:%M')
    context.user_data['schedule_time'] = schedule_datetime
    update.message.reply_text('Publicación programada.')

    # Programar el mensaje
    scheduler.add_job(publish_message, DateTrigger(run_date=schedule_datetime, timezone=timezone('Europe/Madrid')), [update, context])
    return ConversationHandler.END

# Función para publicar el mensaje
def publish_message(update: Update, context: CallbackContext):
    channel = context.user_data['channel']
    message = (
        f"<b><a href='{context.user_data['link']}'>{context.user_data['name']}</a></b>\n\n"
        f"<b>{context.user_data['title']}</b>\n\n"
        f"{context.user_data['description']}\n\n"
        f"<b>➡️CUPÓN: {context.user_data['coupon']}</b>\n\n"
        f"<b>✅OFERTA: {context.user_data['discount_price']}</b>\n\n"
        f"<b>❌ANTES: <s>{context.user_data['original_price']}</s></b>\n\n"
        f"{context.user_data['link']}"
    )
    
    if context.user_data['image_type'] == 'file':
        bot.send_photo(chat_id=channel, photo=context.user_data['image'], caption=message, parse_mode=ParseMode.HTML)
    else:
        bot.send_message(chat_id=channel, text=message, parse_mode=ParseMode.HTML)

    if context.user_data['image_type'] == 'url':
        bot.send_photo(chat_id=channel, photo=context.user_data['image'])

# Configurar el manejador de la conversación
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CHANNEL: [MessageHandler(Filters.text & ~Filters.command, get_channel)],
        NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
        TITLE: [MessageHandler(Filters.text & ~Filters.command, get_title)],
        DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, get_description)],
        COUPON: [MessageHandler(Filters.text & ~Filters.command, get_coupon)],
        DISCOUNT_PRICE: [MessageHandler(Filters.text & ~Filters.command, get_discount_price)],
        ORIGINAL_PRICE: [MessageHandler(Filters.text & ~Filters.command, get_original_price)],
        LINK: [MessageHandler(Filters.text & ~Filters.command, get_link)],
        IMAGE: [MessageHandler(Filters.text & ~Filters.command, get_image)],
        CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirm)],
        PUBLISH_OR_SCHEDULE: [MessageHandler(Filters.text & ~Filters.command, publish_or_schedule)],
        SCHEDULE_TIME: [MessageHandler(Filters.text & ~Filters.command, get_schedule_time)],
    },
    fallbacks=[]
)

# Configurar el updater y el dispatcher
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Añadir el manejador de la conversación al dispatcher
dispatcher.add_handler(conv_handler)

# Iniciar el bot
updater.start_polling()
updater.idle()
