import asyncio
from typing import Any, Type
import os

import aiofiles
import aiofiles.os
import aioschedule
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup
from aiogram.utils import executor
from aiogram.utils.exceptions import RetryAfter, BotBlocked
from loguru import logger

from PIL import Image, ImageFont, ImageDraw
from concurrent.futures import ThreadPoolExecutor

from . import dp
from .bot_content import features
from .bot_content.errors import Errors
from .bot_infra.callbacks import game_cb, questions_cb
from .bot_infra.filters import CreatorFilter, NonRegistrationFilter, RegistrationFilter
from .bot_infra.states import UserForm, UserFormData, InterviewQuestion, UserInterviewData
from .bot_lib.aiogram_overloads import DbDispatcher
from .bot_lib.bot_feature import Feature, InlineButton, TgUser, Question
from .bot_lib.utils import bot_edit_callback_message, bot_safe_send_message, bot_safe_send_photo
from .config import settings
from .db_infra import db, setup_db

# filters binding
dp.filters_factory.bind(CreatorFilter)
dp.filters_factory.bind(RegistrationFilter)
dp.filters_factory.bind(NonRegistrationFilter)


# -------------------------------------------- BASE HANDLERS ----------------------------------------------------------
@dp.message_handler(lambda message: features.ping_ftr.find_triggers(message))
async def ping(msg: types.Message) -> None:
    await bot_safe_send_message(dp, msg.from_user.id, features.ping_ftr.text)  # type: ignore[arg-type]


@dp.message_handler(lambda message: features.creator_ftr.find_triggers(message), creator=True)
async def creator_filter_check(msg: types.Message) -> None:
    await msg.answer(features.creator_ftr.text, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(Text(equals=features.cancel_ftr.triggers, ignore_case=True), state="*")
async def cancel_command(msg: types.Message, state: FSMContext) -> None:
    await msg.answer(features.cancel_ftr.text)
    if await state.get_state() is not None:
        await state.finish()
    await main_menu(from_user_id=msg.from_user.id)


@dp.callback_query_handler(Text(equals=features.cancel_ftr.triggers, ignore_case=True), state="*")
async def cancel_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    await bot_edit_callback_message(dp, callback, features.cancel_ftr.text)
    if await state.get_state() is not None:
        await state.finish()
    await main_menu(from_user_id=callback.from_user.id)


@dp.callback_query_handler(game_cb.filter(action=features.start_ftr.callback_action), registered=True)
@dp.message_handler(Text(equals=features.start_ftr.triggers, ignore_case=True), registered=True)
async def start(msg: types.Message | types.CallbackQuery) -> None:
    await main_menu(from_user_id=msg.from_user.id)
    if isinstance(msg, types.CallbackQuery):
        await msg.answer()


@dp.message_handler(Text(equals=features.help_ftr.triggers, ignore_case=True), registered=True)
async def help_feature(msg: types.Message) -> None:
    await msg.answer(features.help_ftr.text, reply_markup=features.empty.kb)


async def main_menu(*, from_user_id: int) -> None:
    text = f"{features.start_ftr.text}\n\n{features.start_ftr.menu.text}"  # type: ignore[union-attr]
    await bot_safe_send_message(dp, from_user_id, text, reply_markup=features.start_ftr.kb)


# -------------------------------------------- PROFILE HANDLERS -------------------------------------------------------
@dp.message_handler(Text(equals=features.set_user_info.triggers, ignore_case=True), registered=True)
async def set_name(msg: types.Message) -> None:
    await msg.answer(features.set_user_info.text, reply_markup=features.cancel_ftr.kb)
    await UserForm.name.set()


@dp.message_handler(content_types=["text", "caption"], state=UserForm.name)
async def add_form_name(msg: types.Message, state: FSMContext) -> None:
    await fill_form(msg=msg, feature=features.set_user_name, form=UserForm, state=state)


@dp.message_handler(content_types=["text", "caption"], state=UserForm.info)
async def add_form_info(msg: types.Message, state: FSMContext) -> None:
    await fill_form(msg=msg, feature=features.set_user_about, form=UserForm, state=state)


async def fill_form(*, msg: types.Message, feature: Feature, form: Type[StatesGroup], state: FSMContext) -> None:
    async with state.proxy() as data:
        data[feature.data_key] = msg.caption or msg.text
    await form.next()
    await msg.answer(feature.text, reply_markup=features.cancel_ftr.kb)


@dp.message_handler(content_types=["photo"], state=UserForm.photo)
async def add_form_photo(msg: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        user_form_data = UserFormData(
            name=data[features.set_user_name.data_key],
            info=data[features.set_user_about.data_key],
            photo=msg.photo[-1].file_id,
        )
        tg_user = TgUser(tg_id=msg.from_user.id, username=msg.from_user.username)
        await db.update_user_info(tg_user=tg_user, user_form_data=user_form_data)
    await state.finish()
    await msg.answer(features.set_user_info.text2, reply_markup=features.set_user_info.kb)


@dp.message_handler(content_types=["any"], state=UserForm.name)
async def error_form_name(msg: types.Message) -> None:
    await msg.answer(Errors.text_form, reply_markup=features.cancel_ftr.kb)


@dp.message_handler(content_types=["any"], state=UserForm.info)
async def error_form_info(msg: types.Message) -> None:
    await msg.answer(Errors.text_form, reply_markup=features.cancel_ftr.kb)


@dp.message_handler(content_types=["any"], state=UserForm.photo)
async def error_form_photo(msg: types.Message) -> None:
    await msg.answer(Errors.photo_form, reply_markup=features.cancel_ftr.kb)


# -------------------------------------------- GAME HANDLERS ----------------------------------------------------------
@dp.message_handler(Text(equals=features.rating_ftr.triggers, ignore_case=True), registered=True)
async def rating(msg: types.Message) -> None:
    user = await db.get_user(tg_user=TgUser(tg_id=msg.from_user.id, username=msg.from_user.username))
    all_users = await db.get_all_users()
    total_taps = sum([i.taps for i in all_users])
    text = features.rating_ftr.text.format(user_taps=user.taps, total_taps=total_taps)  # type: ignore[union-attr]
    await msg.answer(text, reply_markup=features.rating_ftr.kb)
    if all_users and (best_user := all_users[0]).taps > 0:
        text = features.rating_ftr.text2.format(  # type: ignore[union-attr]
            name=best_user.name, username=best_user.username, info=best_user.info
        )
        await msg.answer(text, reply_markup=features.rating_ftr.kb)
        await bot_safe_send_photo(dp, msg.from_user.id, best_user.photo, reply_markup=features.rating_ftr.kb)


@dp.message_handler(Text(equals=features.press_button_ftr.triggers, ignore_case=True), registered=True)
async def send_press_button(msg: types.Message) -> None:
    text, keyboard = await update_button_tap(taps=0)
    await msg.answer(text, reply_markup=Feature.create_tg_inline_kb(keyboard))


@dp.callback_query_handler(game_cb.filter(action=features.press_button_ftr.callback_action), registered=True)
async def count_button_tap(callback: types.CallbackQuery, callback_data: dict[Any, Any]) -> None:
    current_taps = int(callback_data["taps"])
    new_taps = current_taps + 1
    await db.incr_user_taps(tg_user=TgUser(tg_id=callback.from_user.id, username=callback.from_user.username))
    text, keyboard = await update_button_tap(taps=new_taps)
    await bot_edit_callback_message(dp, callback, text, reply_markup=Feature.create_tg_inline_kb(keyboard))


async def update_button_tap(*, taps: int) -> tuple[str, list[list[InlineButton]]]:
    text = features.press_button_ftr.text.format(last_session=taps)  # type: ignore[union-attr]
    keyboard = [
        [
            InlineButton(
                text=features.press_button_ftr.button,
                callback_data=game_cb.new(action=features.press_button_ftr.callback_action, taps=taps),
            )
        ],
        [
            InlineButton(
                text=features.start_ftr.button,
                callback_data=game_cb.new(action=features.start_ftr.callback_action, taps=taps),
            )
        ],
    ]
    return text, keyboard


# ------------------------------------------ QUESTIONS HANDLERS --------------------------------------------------------
@dp.message_handler(Text(equals=features.question_ftr.triggers, ignore_case=True), registered=True)
async def start_quiz(msg: types.Message | types.CallbackQuery, state: FSMContext) -> None:
    # Check state
    current_state = await state.get_state()
    logger.info(f"Current state: {current_state}")
    if current_state == InterviewQuestion.send_question or current_state == InterviewQuestion.check_answer:
        logger.info(f"User wants quiz, but he has quiz already: {current_state}")
    else:
        # Set and check state
        await state.set_state(InterviewQuestion.start_quiz)
        current_state = await state.get_state()
        logger.info(f"State changed. Current state: {current_state}")
        # Send question
        feature_txt_kb = await get_start_quiz_message()
        #  Get and set random questions ids to state.data
        question_ids = await db.get_random_question_ids()
        logger.info(f"Get 10 question ids in list: {question_ids}")
        await state.update_data(question_ids=question_ids)
        # Set number of right answers
        await state.update_data(right_answers=0)
        # Send changes to user
        await msg.answer(text=feature_txt_kb.text, reply_markup=Feature.create_tg_inline_kb(feature_txt_kb.keyboard))
        # Check state
        logger.info(f"Current state: {await state.get_state()}")
        # Set and check state
        await state.set_state(InterviewQuestion.send_question)
        logger.info(f"State changed. Current state: {await state.get_state()}")


async def get_start_quiz_message() -> Feature:
    # Create instance of Feature
    start_quiz_message = Feature()
    # Get question text
    start_quiz_message.text = "Добро пожаловать в викторину. Начнем?"
    # Define keyboard
    start_quiz_message.keyboard = [[InlineButton(text="Поехали", callback_data=questions_cb.new(action="answer", answer="Start quiz"))]]
    return start_quiz_message


@dp.callback_query_handler(
    questions_cb.filter(action=features.question_ftr.callback_action),
    registered=True,
    state=InterviewQuestion.send_question,
)
async def send_question(msg: types.CallbackQuery, state: FSMContext) -> None:
    # Check state
    logger.info(f"Current state: {await state.get_state()}")
    # Get state.data
    data = await state.get_data()
    logger.info(f"All of data: {data}")
    question_ids = data["question_ids"]
    logger.info(f"Get question_ids from data of state: {question_ids}")
    answers_data = data["right_answers"]
    logger.info(f"Get number of right answers: {answers_data}")

    # Check question_ids for emptiness
    if not question_ids:
        logger.info("question_ids is empty. Finish state")
        # Get attributes for finish_quiz. There is a fix number of 10 questions
        await finish_quiz(msg, answers_data, all_questions=10)
        await state.finish()
    else:
        # Get current question id
        current_questions_id = question_ids.pop()
        await state.update_data(question_ids=question_ids)
        logger.info(f"Get current question id: {current_questions_id}. List of question ids: {question_ids}")

        # Give all fields to question object from db object
        current_question = await db.get_question(question_gl_obj=Question(id=current_questions_id))
        # Get question text and answers in keyboard
        updated_question_message = await update_question_message(current_question=current_question)
        # Send changes to user
        await msg.message.answer(updated_question_message.text, reply_markup=Feature.create_tg_inline_kb(updated_question_message.keyboard))
        # Send message with question, delete buttons
        await msg.message.edit_reply_markup()
        # Set state
        await state.set_state(InterviewQuestion.check_answer)
        logger.info(f"State changed. Current state: {await state.get_state()}")


async def update_question_message(*, current_question: Question) -> Feature:
    updated_question_message = Feature()
    # Get question text
    updated_question_message.text = current_question.question
    # Define keyboard with answers
    updated_question_message.keyboard = []
    for current_answer in (current_question.answer1, current_question.answer2, current_question.answer3):
        if current_answer is not None:
            if current_answer == current_question.right_answer:
                answer = "correct"
            else:
                answer = "incorrect"
            updated_question_message.keyboard.append(
                [InlineButton(text=current_answer, callback_data=questions_cb.new(action="answer", answer=answer))]
            )
        else:
            pass

    # Add menu button
    updated_question_message.keyboard.append(
        [
            InlineButton(
                text=features.start_ftr.button,
                callback_data=questions_cb.new(action=features.start_ftr.callback_action, answer="None"),
            )
        ]
    )
    return updated_question_message


@dp.callback_query_handler(
    questions_cb.filter(action=features.question_ftr.callback_action),
    registered=True,
    state=InterviewQuestion.check_answer,
)
async def check_answer(callback: types.CallbackQuery, callback_data: dict, state: FSMContext) -> None:
    # Check state
    logger.info(f"Current state: {await state.get_state()}")
    data = await state.get_data()
    answers_data = data["right_answers"]
    # Send message with result
    if callback_data["answer"] == "correct":
        text = f"Верно!"
        answers_data += 1
        await state.update_data(right_answers=answers_data)
    else:
        text = f"Неверно :("
    # Get keyboard with buttons "Menu" and "Next question"
    keyboard = await update_answer_message_keyboard()
    await callback.message.answer(text, reply_markup=Feature.create_tg_inline_kb(keyboard))
    # Update message after answer the question
    await callback.message.edit_reply_markup()
    # Set state
    await state.set_state(InterviewQuestion.send_question)
    logger.info(f"State changed. Current state: {await state.get_state()}")


async def update_answer_message_keyboard() -> tuple[list[InlineButton], list[InlineButton]]:
    # Add menu button
    keyboard = (
        [
            InlineButton(
                text=features.question_ftr.button_in_question,
                callback_data=questions_cb.new(action=features.question_ftr.callback_action, answer="None"),
            )
        ],
        [
            InlineButton(
                text=features.start_ftr.button,
                callback_data=questions_cb.new(action=features.start_ftr.callback_action, answer="None"),
            )
        ],
    )
    return keyboard


async def finish_quiz(msg: types.CallbackQuery, right_answers: int, all_questions: int):
    # Update message, delete buttons
    await msg.message.edit_reply_markup()
    # Update value answers and questions to user
    user_questions, user_right_answers = await db.incr_user_questions(
        tg_user=TgUser(tg_id=msg.from_user.id, username=msg.from_user.username),
        right_answers=right_answers,
        all_questions=all_questions,
    )
    text = (
        f"Викторина завершена. Ваш результат: {right_answers}/{all_questions}."
        f"\nВсего вопросов пройдено: {user_questions}."
        f"\nВсего верных ответов: {user_right_answers}."
    )
    await msg.message.answer(text)
    logger.debug(os.path.abspath(__file__))

    # Generate picture with ThreadPoolExecutor
    logger.debug('Start generate picture with ThreadPoolExecutor')
    path_to_result_pic = await asyncio.to_thread(get_result_quiz_picture, msg, all_questions, right_answers)
    logger.debug(f'End generate picture with ThreadPoolExecutor. Path: {path_to_result_pic}')

    # Send and delete result picture
    async with aiofiles.open(path_to_result_pic, 'rb') as photo:
        await bot_safe_send_photo(dp, msg.from_user.id, photo)
    await aiofiles.os.remove(path_to_result_pic)
    logger.debug(f'File with result ({path_to_result_pic}) sent and removed.')


def get_result_quiz_picture(msg, questions: int, right_answers: int):
    path_to_result_quiz_picture = os.path.dirname(os.path.abspath(__file__)) + '/bot_content/result_pic.jpg'
    logger.debug(f'Path to picture with result of quiz: {path_to_result_quiz_picture}')
    result_quiz_picture = Image.open(path_to_result_quiz_picture)
    font = ImageFont.load_default(size=220)
    pencil = ImageDraw.Draw(result_quiz_picture)
    text = f'{right_answers}/{questions}'
    logger.debug(f'Text with result of quiz: {text}')
    pencil.text((60, 600), text, font=font, stroke_width=5, stroke_fill='purple')
    path_to_result_quiz_picture = (os.path.dirname(os.path.abspath(__file__))
                                   + '/bot_content/result_pic'
                                   + str(msg.from_user.id) + '.jpg')
    logger.debug(f'Path to save result pic: {path_to_result_quiz_picture}')
    result_quiz_picture.save(path_to_result_quiz_picture)
    return path_to_result_quiz_picture


# Tap menu button
@dp.callback_query_handler(questions_cb.filter(action=features.start_ftr.callback_action), registered=True, state="*")
async def exit_quiz(msg: types.Message | types.CallbackQuery, state: FSMContext) -> None:
    logger.info("User taps menu button. Ending the quiz, reset answers...")
    # TODO: Reset answers from data here
    await msg.message.edit_reply_markup()
    text = "Вы вышли из викторины, ответы сброшены."
    # Reset questions and answers in state.data
    await state.update_data(question_ids=None, answers_data=0)
    # Send message
    await msg.message.answer(text)
    await state.finish()
    await main_menu(from_user_id=msg.from_user.id)


# -------------------------------------------- SERVICE HANDLERS -------------------------------------------------------
@dp.message_handler(content_types=["any"], not_registered=True)
async def registration(msg: types.Message) -> types.Message | None:
    if settings.register_passphrase is not None:
        if msg.text.lower() != settings.register_passphrase:
            return await msg.answer(Errors.please_register, reply_markup=features.empty.kb)
        if not msg.from_user.username:
            return await msg.answer(Errors.register_failed, reply_markup=features.empty.kb)
    # user registration
    await db.create_user(tg_user=TgUser(tg_id=msg.from_user.id, username=msg.from_user.username))
    await msg.answer(features.register_ftr.text)
    await main_menu(from_user_id=msg.from_user.id)
    return None


@dp.message_handler(content_types=["any"], registered=True)
async def handle_wrong_text_msg(msg: types.Message) -> None:
    await asyncio.sleep(2)
    await msg.reply(Errors.text)


@dp.my_chat_member_handler()
async def handle_my_chat_member_handlers(msg: types.Message):
    logger.info(msg)  # уведомление о блокировке


@dp.errors_handler(exception=BotBlocked)
async def exception_handler(update: types.Update, exception: BotBlocked):
    # работает только для хендлеров бота, для шедулера не работает
    logger.info(update.message.from_user.id)  # уведомление о блокировке
    logger.info(exception)  # уведомление о блокировке
    return True


# ---------------------------------------- SCHEDULED FEATURES ---------------------------------------
async def healthcheck() -> None:
    logger.info(features.ping_ftr.text2)
    if settings.creator_id is not None:
        await bot_safe_send_message(dp, int(settings.creator_id), features.ping_ftr.text2)  # type: ignore[arg-type]


# -------------------------------------------- BOT SETUP --------------------------------------------
async def bot_scheduler() -> None:
    logger.info("Scheduler is up")
    aioschedule.every().day.at(settings.schedule_healthcheck).do(healthcheck)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dispatcher: DbDispatcher) -> None:
    logger.info("Bot is up")
    await bot_safe_send_message(dp, settings.creator_id, "Bot is up")

    # bot commands setup
    cmds = Feature.commands_to_set
    bot_commands = [types.BotCommand(ftr.slashed_command, ftr.slashed_command_descr) for ftr in cmds]
    await dispatcher.bot.set_my_commands(bot_commands)

    # scheduler startup
    asyncio.create_task(bot_scheduler())


async def on_shutdown(dispatcher: DbDispatcher) -> None:
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == "__main__":
    dp.set_db_conn(conn=setup_db(settings))

    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
