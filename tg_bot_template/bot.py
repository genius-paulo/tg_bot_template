import asyncio
import aioschedule
from aiogram.dispatcher.filters.state import StatesGroup
from typing import Type
from loguru import logger

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor

from tg_bot_template import dp
from tg_bot_template.bot_lib.bot_feature import Feature, InlineButton, TgUser
from tg_bot_template.bot_content.errors import Errors
from tg_bot_template.bot_infra.callbacks import game_cb
from tg_bot_template.bot_infra.states import UserForm, UserFormData
from tg_bot_template.bot_content import features
from tg_bot_template.bot_lib.db_dispatcher import DbDispatcher
from tg_bot_template.config import settings
from tg_bot_template.db_infra import db, setup_db
from tg_bot_template.bot_infra.filters import RegistrationFilter, NonRegistrationFilter, CreatorFilter
from tg_bot_template.bot_lib.utils import bot_safe_send_message, bot_safe_send_photo, bot_edit_callback_message

# filters binding
dp.filters_factory.bind(CreatorFilter)
dp.filters_factory.bind(RegistrationFilter)
dp.filters_factory.bind(NonRegistrationFilter)


# -------------------------------------------- BASE HANDLERS ----------------------------------------------------------
@dp.message_handler(lambda message: features.ping_ftr.find_triggers(message))
async def ping(msg: types.Message):
    await bot_safe_send_message(dp, msg.from_user.id, features.ping_ftr.text)


@dp.message_handler(lambda message: features.creator_ftr.find_triggers(message), creator=True)
async def creator_filter_check(msg: types.Message):
    await msg.answer(features.creator_ftr.text, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(Text(equals=features.cancel_ftr.triggers, ignore_case=True), state="*")
async def cancel_command(msg: types.Message, state: FSMContext):
    await msg.answer(features.cancel_ftr.text)
    if await state.get_state() is not None:
        await state.finish()
    await main_menu(from_user_id=msg.from_user.id)


@dp.callback_query_handler(Text(equals=features.cancel_ftr.triggers, ignore_case=True), state="*")
async def cancel_callback(callback: types.CallbackQuery, state: FSMContext):
    await bot_edit_callback_message(dp, callback, features.cancel_ftr.text)
    if await state.get_state() is not None:
        await state.finish()
    await main_menu(from_user_id=callback.from_user.id)


@dp.callback_query_handler(game_cb.filter(action=features.start_ftr.callback_action), registered=True)
@dp.message_handler(Text(equals=features.start_ftr.triggers, ignore_case=True), registered=True)
async def start(msg: types.Message | types.CallbackQuery):
    await main_menu(from_user_id=msg.from_user.id)
    if isinstance(msg, types.CallbackQuery):
        await msg.answer()


@dp.message_handler(Text(equals=features.help_ftr.triggers, ignore_case=True), registered=True)
async def help_feature(msg: types.Message):
    await msg.answer(features.help_ftr.text, reply_markup=features.empty.kb)


async def main_menu(*, from_user_id: int):
    text = f"{features.start_ftr.text}\n\n{features.start_ftr.menu.text}"
    await bot_safe_send_message(dp, from_user_id, text, reply_markup=features.start_ftr.kb)


# -------------------------------------------- PROFILE HANDLERS -------------------------------------------------------
@dp.message_handler(Text(equals=features.set_user_info.triggers, ignore_case=True), registered=True)
async def set_name(msg: types.Message):
    await msg.answer(features.set_user_info.text, reply_markup=features.cancel_ftr.kb)
    await UserForm.name.set()


@dp.message_handler(content_types=["text", "caption"], state=UserForm.name)
async def add_form_name(msg: types.Message, state: FSMContext):
    await fill_form(msg=msg, feature=features.set_user_name, form=UserForm, state=state)


@dp.message_handler(content_types=["text", "caption"], state=UserForm.info)
async def add_form_info(msg: types.Message, state: FSMContext):
    await fill_form(msg=msg, feature=features.set_user_about, form=UserForm, state=state)


async def fill_form(*, msg: types.Message, feature: Feature, form: Type[StatesGroup], state: FSMContext):
    async with state.proxy() as data:
        data[feature.data_key] = msg.caption or msg.text
    await form.next()
    await msg.answer(feature.text, reply_markup=features.cancel_ftr.kb)


@dp.message_handler(content_types=["photo"], state=UserForm.photo)
async def add_form_photo(msg: types.Message, state: FSMContext):
    async with state.proxy() as data:
        user_form_data = UserFormData(
            name=data[features.set_user_name.data_key],
            info=data[features.set_user_about.data_key],
            photo=msg.photo[-1].file_id
        )
        tg_user = TgUser(tg_id=msg.from_user.id, username=msg.from_user.username)
        await db.update_user_info(tg_user=tg_user, user_form_data=user_form_data)
    await state.finish()
    await msg.answer(features.set_user_info.text2, reply_markup=features.set_user_info.kb)


@dp.message_handler(content_types=["any"], state=UserForm.name)
async def error_form_name(msg: types.Message):
    await msg.answer(Errors.text_form, reply_markup=features.cancel_ftr.kb)


@dp.message_handler(content_types=["any"], state=UserForm.info)
async def error_form_info(msg: types.Message):
    await msg.answer(Errors.text_form, reply_markup=features.cancel_ftr.kb)


@dp.message_handler(content_types=["any"], state=UserForm.photo)
async def error_form_photo(msg: types.Message):
    await msg.answer(Errors.photo_form, reply_markup=features.cancel_ftr.kb)


# -------------------------------------------- GAME HANDLERS ----------------------------------------------------------
@dp.message_handler(Text(equals=features.rating_ftr.triggers, ignore_case=True), registered=True)
async def rating(msg: types.Message):
    user = await db.get_user(tg_user=TgUser(tg_id=msg.from_user.id, username=msg.from_user.username))
    all_users = await db.get_all_users()
    total_taps = sum([i.taps for i in all_users])
    text = features.rating_ftr.text.format(user_taps=user.taps, total_taps=total_taps)
    await msg.answer(text, reply_markup=features.rating_ftr.kb)
    if all_users and (best_user := all_users[0]).taps > 0:
        # best_user = all_users[0]
        text = features.rating_ftr.text2.format(name=best_user.name, username=best_user.username, info=best_user.info)
        await msg.answer(text, reply_markup=features.rating_ftr.kb)
        await bot_safe_send_photo(dp, msg.from_user.id, best_user.photo, reply_markup=features.rating_ftr.kb)


@dp.message_handler(Text(equals=features.press_button_ftr.triggers, ignore_case=True), registered=True)
async def send_press_button(msg: types.Message):
    text, keyboard = await update_button_tap(taps=0)
    await msg.answer(text, reply_markup=Feature.create_tg_inline_kb(keyboard))


@dp.callback_query_handler(game_cb.filter(action=features.press_button_ftr.callback_action), registered=True)
async def count_button_tap(callback: types.CallbackQuery, callback_data: dict):
    current_taps = int(callback_data["taps"])
    new_taps = current_taps + 1
    await db.incr_user_taps(tg_user=TgUser(tg_id=callback.from_user.id, username=callback.from_user.username))
    text, keyboard = await update_button_tap(taps=new_taps)
    await bot_edit_callback_message(dp, callback, text, reply_markup=Feature.create_tg_inline_kb(keyboard))


async def update_button_tap(*, taps: int) -> tuple[str, list[list[InlineButton]]]:
    text = features.press_button_ftr.text.format(last_session=taps)
    keyboard = [
        [InlineButton(text=features.press_button_ftr.button,
                      callback_data=game_cb.new(action=features.press_button_ftr.callback_action, taps=taps))],
        [InlineButton(text=features.start_ftr.button,
                      callback_data=game_cb.new(action=features.start_ftr.callback_action, taps=taps))],
    ]
    return text, keyboard


# -------------------------------------------- SERVICE HANDLERS -------------------------------------------------------
@dp.message_handler(content_types=["any"], not_registered=True)
async def registration(msg: types.Message):
    if settings.register_passphrase is not None:
        if msg.text.lower() != settings.register_passphrase:
            return await msg.answer(Errors.please_register, reply_markup=features.empty.kb)
        if not msg.from_user.username:
            return await msg.answer(Errors.register_failed, reply_markup=features.empty.kb)
    # user registration
    await db.create_user(tg_user=TgUser(tg_id=msg.from_user.id, username=msg.from_user.username))
    await msg.answer(features.register_ftr.text)
    await main_menu(from_user_id=msg.from_user.id)


@dp.message_handler(content_types=["any"], registered=True)
async def handle_wrong_text_msg(msg: types.Message):
    await msg.answer(Errors.text)


# ---------------------------------------- SCHEDULED FEATURES ---------------------------------------
async def healthcheck():
    logger.info(features.ping_ftr.text2)
    if settings.creator_id is not None:
        await bot_safe_send_message(dp, int(settings.creator_id), features.ping_ftr.text2)


# -------------------------------------------- BOT SETUP --------------------------------------------
async def bot_scheduler():
    logger.info("Scheduler is up")
    aioschedule.every().day.at(settings.schedule_healthcheck).do(healthcheck)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dispatcher: DbDispatcher):
    logger.info("Bot is up")
    await bot_safe_send_message(dp, settings.creator_id, "Bot is up")

    # bot commands setup
    cmds = Feature.commands_to_set
    bot_commands = [types.BotCommand(ftr.slashed_command, ftr.slashed_command_descr) for ftr in cmds]
    await dispatcher.bot.set_my_commands(bot_commands)

    # scheduler startup
    asyncio.create_task(bot_scheduler())

    # register handlers
    # dispatcher.register_message_handler(cancel_handler, commands=['cancel'], state="*")


async def on_shutdown(dispatcher: DbDispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == "__main__":
    dp.set_db_conn(conn=setup_db(settings))
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
