from telegram import Update, Bot, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import pytz
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Verificar la configuración del token
print("Valor de TELEGRAM_BOT_TOKEN:", TOKEN)

bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
scheduler = BackgroundScheduler()
scheduler.start()

# Estados del bot
TIENDA, TITULO, DESCRIPCION, CUPON, OFERTA, ANTES, LINK, IMAGEN, CONFIRMAR, CANAL, PROGRAMA = range(11)

publicaciones_programadas = []

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Bienvenido al bot de publicación. Por favor, ingresa el nombre de la tienda:")
    return TIENDA

def tienda(update: Update, context: CallbackContext) -> int:
    context.user_data['tienda'] = update.message.text
    update.message.reply_text("Título de la publicación:")
    return TITULO

def titulo(update: Update, context: CallbackContext) -> int:
    context.user_data['titulo'] = update.message.text
    update.message.reply_text("Descripción de la publicación:")
    return DESCRIPCION

def descripcion(update: Update, context: CallbackContext) -> int:
    context.user_data['descripcion'] = update.message.text
    update.message.reply_text("Cupón de descuento:")
    return CUPON

def cupon(update: Update, context: CallbackContext) -> int:
    context.user_data['cupon'] = update.message.text
    update.message.reply_text("Precio de oferta:")
    return OFERTA

def oferta(update: Update, context: CallbackContext) -> int:
    context.user_data['oferta'] = update.message.text
    update.message.reply_text("Precio anterior:")
    return ANTES

def antes(update: Update, context: CallbackContext) -> int:
    context.user_data['antes'] = update.message.text
    update.message.reply_text("Link de la publicación:")
    return LINK

def link(update: Update, context: CallbackContext) -> int:
    context.user_data['link'] = update.message.text
    update.message.reply_text("Por favor, envía la imagen de la publicación o proporciona una URL de la imagen:")
    return IMAGEN

def imagen(update: Update, context: CallbackContext) -> int:
    if update.message.photo:
        photo_file = update.message.photo[-1].get_file()
        context.user_data['imagen'] = photo_file.file_id
        context.user_data['imagen_tipo'] = 'archivo'
    elif update.message.text:
        context.user_data['imagen'] = update.message.text
        context.user_data['imagen_tipo'] = 'url'
    else:
        update.message.reply_text("Formato no reconocido. Por favor, envía una imagen o proporciona una URL de la imagen:")
        return IMAGEN

    update.message.reply_text("¿Confirmas la publicación? (Sí/No)")
    return CONFIRMAR

def confirmar(update: Update, context: CallbackContext) -> int:
    if update.message.text.lower() == 'sí':
        context.user_data['canal'] = update.message.chat_id
        update.message.reply_text("¿Deseas publicar ahora o programar la publicación? (Responde con 'Ahora' o 'Programar')")
        return PROGRAMA
    else:
        update.message.reply_text("Operación cancelada.")
        return ConversationHandler.END

def programa(update: Update, context: CallbackContext) -> int:
    if update.message.text.lower() == 'ahora':
        enviar_publicacion(context)
        update.message.reply_text("Publicación realizada con éxito.")
        return ConversationHandler.END
    elif update.message.text.lower() == 'programar':
        update.message.reply_text("Por favor, proporciona la fecha y hora (AAAA-MM-DD HH:MM) en horario español:")
        return CANAL
    else:
        update.message.reply_text("Respuesta no válida. Operación cancelada.")
        return ConversationHandler.END

def canal(update: Update, context: CallbackContext) -> int:
    try:
        schedule_time = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        schedule_time = pytz.timezone('Europe/Madrid').localize(schedule_time)
        context.user_data['schedule_time'] = schedule_time
        publicaciones_programadas.append(context.user_data.copy())
        update.message.reply_text("Publicación programada con éxito.")
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("Formato de fecha y hora no válido. Operación cancelada.")
        return ConversationHandler.END

def enviar_publicacion(context: CallbackContext):
    job = context.job
    data = job.context

    mensaje = (
        f"<b><a href='{data['link']}'>{data['tienda']}</a></b>\n\n"
        f"<b>{data['titulo']}</b>\n\n"
        f"{data['descripcion']}\n\n"
        f"<b>➡️CUPÓN: {data['cupon']}</b>\n\n"
        f"<b>✅OFERTA: <span style='color:red;'>{data['oferta']}</span></b>\n\n"
        f"<b>❌ANTES: <s>{data['antes']}</s></b>\n\n"
        f"{data['link']}"
    )

    if data['imagen_tipo'] == 'url':
        bot.send_message(
            chat_id=data['canal'],
            text=mensaje,
            parse_mode=ParseMode.HTML
        )
        bot.send_photo(
            chat_id=data['canal'],
            photo=data['imagen']
        )
    else:
        bot.send_message(
            chat_id=data['canal'],
            text=mensaje,
            parse_mode=ParseMode.HTML
        )
        bot.send_photo(
            chat_id=data['canal'],
            photo=data['imagen']
        )

def error(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    context.logger.warning('Update "%s" caused error "%s"', update, context.error)

# Añadir los handlers al dispatcher
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        TIENDA: [MessageHandler(Filters.text & ~Filters.command, tienda)],
        TITULO: [MessageHandler(Filters.text & ~Filters.command, titulo)],
        DESCRIPCION: [MessageHandler(Filters.text & ~Filters.command, descripcion)],
        CUPON: [MessageHandler(Filters.text & ~Filters.command, cupon)],
        OFERTA: [MessageHandler(Filters.text & ~Filters.command, oferta)],
        ANTES: [MessageHandler(Filters.text & ~Filters.command, antes)],
        LINK: [MessageHandler(Filters.text & ~Filters.command, link)],
        IMAGEN: [MessageHandler(Filters.photo | Filters.text & ~Filters.command, imagen)],
        CONFIRMAR: [MessageHandler(Filters.text & ~Filters.command, confirmar)],
        PROGRAMA: [MessageHandler(Filters.text & ~Filters.command, programa)],
        CANAL: [MessageHandler(Filters.text & ~Filters.command, canal)],
    },
    fallbacks=[CommandHandler('cancel', lambda update, context: update.message.reply_text('Operación cancelada.'))]
)

dispatcher.add_handler(conv_handler)
dispatcher.add_error_handler(error)

updater.start_polling()
updater.idle()
