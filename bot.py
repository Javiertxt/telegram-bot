import logging
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from telegram.ext.dispatcher import run_async
from telegram.utils.request import Request
import os
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta

# Definir constantes para los estados de la conversación
CHANNEL, NAME, TITLE, DESCRIPTION, COUPON, OFFER_PRICE, OLD_PRICE, LINK, IMAGE, SCHEDULE, CONFIRM, PUBLISH_NOW = range(12)

# Configurar el logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear el diccionario para almacenar los trabajos programados
scheduled_jobs = {}

# Inicializar el scheduler
scheduler = BackgroundScheduler(timezone="Europe/Madrid")
scheduler.start()

# Obtener el token del bot desde las variables de entorno
TOKEN = os.getenv("7189244415:AAEpS6rLPhWT5GaSSwNoCJ2bLWVla9CdYj8")

# Crear el bot y el updater
request = Request(con_pool_size=8)
bot = Bot(token=TOKEN, request=request)
updater = Updater(bot=bot, use_context=True)

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('¡Hola! Vamos a crear una publicación. ¿En qué canal quieres publicarla?')
    return CHANNEL

def channel(update: Update, context: CallbackContext) -> int:
    context.user_data['channel'] = update.message.text
    update.message.reply_text('Nombre de la tienda:')
    return NAME

def name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text('Título:')
    return TITLE

def title(update: Update, context: CallbackContext) -> int:
    context.user_data['title'] = update.message.text
    update.message.reply_text('Descripción:')
    return DESCRIPTION

def description(update: Update, context: CallbackContext) -> int:
    context.user_data['description'] = update.message.text
    update.message.reply_text('Cupón descuento:')
    return COUPON

def coupon(update: Update, context: CallbackContext) -> int:
    context.user_data['coupon'] = update.message.text
    update.message.reply_text('Precio de oferta:')
    return OFFER_PRICE

def offer_price(update: Update, context: CallbackContext) -> int:
    context.user_data['offer_price'] = update.message.text
    update.message.reply_text('Precio anterior:')
    return OLD_PRICE

def old_price(update: Update, context: CallbackContext) -> int:
    context.user_data['old_price'] = update.message.text
    update.message.reply_text('Link de la publicación:')
    return LINK

def link(update: Update, context: CallbackContext) -> int:
    context.user_data['link'] = update.message.text
    update.message.reply_text('Imagen de la publicación (puedes enviar una URL o un archivo de imagen):')
    return IMAGE

def image(update: Update, context: CallbackContext) -> int:
    if update.message.photo:
        context.user_data['image'] = update.message.photo[-1].file_id
    else:
        context.user_data['image'] = update.message.text
    update.message.reply_text('¿Quieres publicar ahora o programar la publicación? (responde con "ahora" o "programar")\nFecha y hora actual: {}'.format(datetime.now(pytz.timezone("Europe/Madrid")).strftime('%Y-%m-%d %H:%M:%S')))
    return SCHEDULE

def schedule(update: Update, context: CallbackContext) -> int:
    response = update.message.text.lower()
    if response == "ahora":
        return publish_now(update, context)
    elif response == "programar":
        update.message.reply_text('Introduce la fecha y hora de la publicación (formato: YYYY-MM-DD HH:MM):')
        return CONFIRM
    else:
        update.message.reply_text('Respuesta no válida. Responde con "ahora" o "programar".')
        return SCHEDULE

def publish_now(update: Update, context: CallbackContext) -> int:
    send_publication(context.user_data)
    update.message.reply_text('Publicación realizada.')
    return ConversationHandler.END

def confirm(update: Update, context: CallbackContext) -> int:
    try:
        schedule_time = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        schedule_time = pytz.timezone("Europe/Madrid").localize(schedule_time)
        job_id = str(len(scheduled_jobs) + 1)
        scheduler.add_job(send_publication, DateTrigger(run_date=schedule_time), [context.user_data], id=job_id)
        scheduled_jobs[job_id] = context.user_data
        update.message.reply_text('Publicación programada para: {}'.format(schedule_time.strftime('%Y-%m-%d %H:%M:%S')))
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text('Fecha y hora no válidas. Por favor, introduce en el formato correcto: YYYY-MM-DD HH:MM.')
        return CONFIRM

def send_publication(data: dict) -> None:
    channel = data['channel']
    name = f"*{data['name']}*"
    title = f"*{data['title']}*"
    description = data['description']
    coupon = f"*➡️CUPÓN: {data['coupon']}*"
    offer_price = f"*✅OFERTA: {data['offer_price']}*"
    old_price = f"*❌ANTES: {data['old_price']}*"
    link = data['link']
    image = data['image']

    message = f"{name}\n{title}\n{description}\n{coupon}\n{offer_price}\n~{old_price}~\n{link}"

    if image.startswith('http'):
        bot.send_message(chat_id=channel, text=message, parse_mode='Markdown')
        bot.send_photo(chat_id=channel, photo=image)
    else:
        bot.send_message(chat_id=channel, text=message, parse_mode='Markdown')
        bot.send_photo(chat_id=channel, photo=image)

def list_scheduled(update: Update, context: CallbackContext) -> None:
    if scheduled_jobs:
        message = "Publicaciones programadas:\n"
        for job_id, data in scheduled_jobs.items():
            message += f"ID: {job_id}, Fecha/Hora: {scheduler.get_job(job_id).next_run_time}, Canal: {data['channel']}, Título: {data['title']}\n"
        update.message.reply_text(message)
    else:
        update.message.reply_text("No hay publicaciones programadas.")

def edit_scheduled(update: Update, context: CallbackContext) -> int:
    job_id = update.message.text.split()[1]
    if job_id in scheduled_jobs:
        context.user_data['job_id'] = job_id
        context.user_data.update(scheduled_jobs[job_id])
        update.message.reply_text("¿Qué campo quieres editar? (Canal, Nombre, Título, Descripción, Cupón, Precio oferta, Precio anterior, Link, Imagen, Fecha/Hora)")
        return 1
    else:
        update.message.reply_text("ID de publicación no encontrado.")
        return ConversationHandler.END

def delete_scheduled(update: Update, context: CallbackContext) -> None:
    job_id = update.message.text.split()[1]
    if job_id in scheduled_jobs:
        scheduler.remove_job(job_id)
        del scheduled_jobs[job_id]
        update.message.reply_text(f"Publicación ID: {job_id} eliminada.")
    else:
        update.message.reply_text("ID de publicación no encontrado.")

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

def main() -> None:
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHANNEL: [MessageHandler(Filters.text & ~Filters.command, channel)],
            NAME: [MessageHandler(Filters.text & ~Filters.command, name)],
            TITLE: [MessageHandler(Filters.text & ~Filters.command, title)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, description)],
            COUPON: [MessageHandler(Filters.text & ~Filters.command, coupon)],
            OFFER_PRICE: [MessageHandler(Filters.text & ~Filters.command, offer_price)],
            OLD_PRICE: [MessageHandler(Filters.text & ~Filters.command, old_price)],
            LINK: [MessageHandler(Filters.text & ~Filters.command, link)],
            IMAGE: [MessageHandler(Filters.text & ~Filters.command, image)],
            SCHEDULE: [MessageHandler(Filters.text & ~Filters.command, schedule)],
            CONFIRM: [MessageHandler(Filters.text & ~Filters.command, confirm)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('list', list_scheduled))
    dp.add_handler(CommandHandler('edit', edit_scheduled))
    dp.add_handler(CommandHandler('delete', delete_scheduled))

    updater.start_webhook(listen="0.0.0.0",
                          port=int(os.environ.get("PORT", 8443)),
                          url_path=TOKEN)
    updater.bot.setWebhook(f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")

    updater.idle()

if __name__ == '__main__':
    main()
