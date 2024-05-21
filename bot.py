import logging
from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define states for conversation
(CHANNEL, NAME, TITLE, DESCRIPTION, COUPON, OFFER_PRICE, OLD_PRICE, LINK, IMAGE, SCHEDULE) = range(10)

# Dictionary to store publication data
publication_data = {}

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
    update.message.reply_text('Imagen de la publicación:')
    return IMAGE

def image(update: Update, context: CallbackContext) -> int:
    publication_data['image'] = update.message.text
    update.message.reply_text('¿Cuándo deseas programar la publicación? (Formato: AAAA-MM-DD HH:MM)')
    return SCHEDULE

def schedule(update: Update, context: CallbackContext) -> int:
    publication_data['schedule'] = update.message.text
    try:
        # Schedule the message
        schedule_time = datetime.strptime(publication_data['schedule'], '%Y-%m-%d %H:%M')
        scheduler.add_job(send_message, DateTrigger(run_date=schedule_time), [context])
        update.message.reply_text('Publicación programada!')
    except ValueError:
        update.message.reply_text('Formato de fecha/hora incorrecto. Por favor usa AAAA-MM-DD HH:MM.')
        return SCHEDULE
    return ConversationHandler.END

def send_message(context: CallbackContext) -> None:
    bot: Bot = context.bot
    channel_id = publication_data['channel']
    message = (
        f"<b><a href='{publication_data['link']}'>{publication_data['name']}</a></b>\n\n"
        f"<b>{publication_data['title']}</b>\n\n"
        f"{publication_data['description']}\n\n"
        f"<b>{publication_data['coupon']}</b>\n\n"
        f"<b><i>{publication_data['offer_price']}</i></b>\n\n"
        f"<s>{publication_data['old_price']}</s>\n\n"
        f"{publication_data['link']}"
    )
    bot.send_message(chat_id=channel_id, text=message, parse_mode=ParseMode.HTML)
    bot.send_photo(chat_id=channel_id, photo=publication_data['image'])

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
            IMAGE: [MessageHandler(Filters.text & ~Filters.command, image)],
            SCHEDULE: [MessageHandler(Filters.text & ~Filters.command, schedule)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
