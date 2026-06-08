"""Telegram bot entrypoint using python-telegram-bot ConversationHandler."""

from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .contracts import ContractError, build_search_request, normalize_country, normalize_state
from .messages import render_response
from .scraper_client import run_scraper


ESPERANDO_PAIS, ESPERANDO_ESTADO = range(2)

LOGGER = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Pais da busca? Envie BR.")
    return ESPERANDO_PAIS


async def receber_pais(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text or ""
    try:
        country = normalize_country(text)
    except ContractError as exc:
        await update.effective_message.reply_text(str(exc))
        return ESPERANDO_PAIS

    context.user_data["country"] = country
    await update.effective_message.reply_text("Estado? Envie a sigla. Ex.: PB")
    return ESPERANDO_ESTADO


async def receber_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text or ""
    try:
        state = normalize_state(text)
        search_request = build_search_request(str(context.user_data["country"]), state)
    except (ContractError, KeyError) as exc:
        await update.effective_message.reply_text(str(exc))
        return ESPERANDO_ESTADO

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        response = await run_scraper(search_request)
    except Exception:
        LOGGER.exception("Scraper integration failed")
        response = {
            "request_id": search_request["request_id"],
            "status": "error",
            "country": search_request["country"],
            "state": search_request["state"],
            "applied_filters": {
                "keywords": search_request["keywords"],
                "sources": search_request["sources"],
                "limit": search_request["limit"],
                "page": search_request["page"],
                "sort": search_request["sort"],
                "include_closed": search_request["include_closed"],
            },
            "summary": {
                "total_found": 0,
                "total_returned": 0,
                "partial_failures": 1,
            },
            "items": [],
            "warnings": ["Tente novamente mais tarde."],
        }

    for message in render_response(response):
        await update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

    context.user_data.clear()
    await update.effective_message.reply_text("Nova busca: /buscar")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Busca cancelada.")
    return ConversationHandler.END


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("buscar", start)],
        states={
            ESPERANDO_PAIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_pais)],
            ESPERANDO_ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_estado)],
        },
        fallbacks=[CommandHandler("cancelar", cancel), CommandHandler("cancel", cancel)],
    )
    application.add_handler(conversation)
    return application


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nao configurado.")

    build_application(token).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
