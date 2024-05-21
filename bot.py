import logging
from telegram import Bot, Update, ParseMode, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import pytz

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for conversation
(CHANNEL, NAME, TITLE, DESCRIPTION, COUPON, OFFER_PRICE, OLD_PRICE, LINK, IMAGE, SCHEDULE, CONFIRM, PUBLISH_NOW) = range(12)

# Dictionary to store publication data
publication_data = {}
scheduled_jobs = {}

# Create scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Hola! En qué canal deseas publicar? (Introduce el ID del canal)')
    return CHANNEL

def channel(update: Update, context: CallbackContext) -> int:
    publication_data['channel'] = update.message.text
    update.message.reply_text('Nombre de la tienda:')
    return NAME

def name(update: Update, context: CallbackContext) -> int:
    publication_data['name'] = update.message.text
    update.message.reply_text('Título:')
    return TITLE

def title(update: Update, context: CallbackContext) -> int:
    publication_data['title'] = update.message.text
    update.message.reply_text('Descripción:')
    return DESCRIPTION

def description(update: Update, context: CallbackContext) -> int:
    publication_data['description'] = update.message.text
    update.message.reply_text('Cupón descuento:')
    return COUPON

def coupon(update: Update, context: CallbackContext) -> int:
    publication_data['coupon'] = update.message.text
    update.message.reply_text('Precio de oferta:')
    return OFFER_PRICE

def offer_price(update: Update, context: CallbackContext) -> int:
    publication_data['offer_price'] = update.message.text
    update.message.reply_text('Precio anterior:')
    return OLD_PRICE

def old_price(update: Update, context: CallbackContext) -> int:
    publication_data['old_price'] = update.message.text
    update.message.reply_text('Link de la publicación:')
    return LINK

def link(update: Update, context: CallbackContext) -> int:
    publication_data['link'] = update.message.text
    update.message.reply_text('Imagen de la publicación (URL o sube un archivo de imagen):')
    return IMAGE

def image(update: Update, context: CallbackContext) -> int:
    if update.message.photo:
        publication_data['image'] = update.message.photo[-1].file_id
        publication_data['image_type'] = 'file_id'
    else:
        publication_data['image'] = update.message.text
        publication_data['image_type'] = 'url'
    update.message.reply_text('¿Cuándo deseas programar la publicación? (Formato: AAAA-MM-DD HH:MM o escribe "ahora" para publicar inmediatamente)')
    return SCHEDULE

def schedule(update: Update, context: CallbackContext) -> int:
    publication_data['schedule'] = update.message.text
    if publication_data['schedule'].lower() == 'ahora':
        preview_text = create_preview(publication_data)
        if publication_data['image_type'] == 'file_id':
            context.bot.send_photo(chat_id=update.message.chat_id, photo=publication_data['image'], caption=preview_text, parse_mode=ParseMode.HTML)
        else:
            context.bot.send_photo(chat_id=update.message.chat_id, photo=publication_data['image'], caption=preview_text, parse_mode=ParseMode.HTML)
        update.message.reply_text('¿Confirmas la publicación? (Sí/No)')
        return PUBLISH_NOW
    else:
        try:
            schedule_time = datetime.strptime(publication_data['schedule'], '%Y-%m-%d %H:%M')
            schedule_time = pytz.timezone('UTC').localize(schedule_time)
            publication_data['schedule_time'] = schedule_time
            preview_text = create_preview(publication_data)
            if publication_data['image_type'] == 'file_id':
                context.bot.send_photo(chat_id=update.message.chat_id, photo=publication_data['image'], caption=preview_text, parse_mode=ParseMode.HTML)
            else:
                context.bot.send_photo(chat_id=update.message.chat_id, photo=publication_data['image'], caption=preview_text, parse_mode=ParseMode.HTML)
            update.message.reply_text('¿Confirmas la publicación? (Sí/No)')
            return CONFIRM
        except ValueError:
            update.message.reply_text('Formato de fecha/hora incorrecto. Por favor usa AAAA-MM-DD HH:MM.')
            return SCHEDULE

def confirm(update: Update, context: CallbackContext) -> int:
    if update.message.text.lower() == 'sí':
        job = scheduler.add_job(send_message, DateTrigger(run_date=publication_data['schedule_time']), [context])
        scheduled_jobs[job.id] = publication_data.copy()
        update.message.reply_text('Publicación programada!')
        return ConversationHandler.END
    else:
        update.message.reply_text('Operación cancelada.')
        return ConversationHandler.END

def publish_now(update: Update, context: CallbackContext) -> int:
    if update.message.text.lower() == 'sí':
        send_message_now(context)
        update.message.reply_text('Publicación realizada!')
        return ConversationHandler.END
    else:
        update.message.reply_text('Operación cancelada.')
        return ConversationHandler.END

def send_message_now(context: CallbackContext) -> None:
    bot: Bot = context.bot
    channel_id = publication_data['channel']
    message = create_preview(publication_data)
    if publication_data['image_type'] == 'file_id':
        bot.send_photo(chat_id=channel_id, photo=publication_data['image'], caption=message, parse_mode=ParseMode.HTML)
    else:
        bot.send_photo(chat_id=channel_id, photo=publication_data['image'], caption=message, parse_mode=ParseMode.HTML)

def create_preview(data: dict) -> str:
    return (
        f"<b><a href='{data['link']}'>{data['name']}</a></b>\n\n"
        f"<b>{data['title']}</b>\n\n"
        f"{data['description']}\n\n"
        f"<b>➡️CUPÓN: {data['coupon']}</b>\n\n"
        f"<b>✅OFERTA: <i>{data['offer_price']}</i></b>\n\n"
        f"<b>❌ANTES: <s>{data['old_price']}</s></b>\n\n"
        f"{data['link']}"
    )

def list_scheduled(update: Update, context: CallbackContext) -> None:
    if scheduled_jobs:
        for job_id, job_data in scheduled_jobs.items():
            schedule_time = job_data['schedule']
            preview_text = (
                f"Publicación programada para {schedule_time}\n"
                f"Canal: {job_data['channel']}\n"
                f"Nombre: {job_data['name']}\n"
                f"Título: {job_data['title']}\n"
                f"Descripción: {job_data['description']}\n"
                f"Cupón: {job_data['coupon']}\n"
                f"Precio oferta: {job_data['offer_price']}\n"
                f"Precio anterior: {job_data['old_price']}\n"
                f"Link: {job_data['link']}\n"
                f"Imagen: {job_data['image']}"
            )
            update.message.reply_text(preview_text)
    else:
        update.message.reply_text("No hay publicaciones programadas.")

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

def main():
    updater = Updater("7189244415:AAEpS6rLPhWT5GaSSwNoCJ2bLWVla9CdYj8", use_context=True)
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
            IMAGE: [MessageHandler(Filters.photo | Filters.text & ~Filters.command, image)],
            SCHEDULE: [MessageHandler(Filters.text & ~Filters.command, schedule)],
            CONFIRM: [MessageHandler(Filters.text & ~Filters.command, confirm)],
            PUBLISH_NOW: [MessageHandler(Filters.text & ~Filters.command, publish_now)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('list', list_scheduled))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
