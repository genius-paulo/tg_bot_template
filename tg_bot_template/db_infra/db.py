from datetime import datetime

from aiocache import cached
from aiocache.serializers import PickleSerializer
from loguru import logger
from peewee_async import Manager

from tg_bot_template import dp
from tg_bot_template.bot_infra.states import UserFormData, UserInterviewData
from tg_bot_template.bot_lib.bot_feature import TgUser, Question
from tg_bot_template.db_infra.models import Users, Questions

import random


def _get_conn() -> Manager:
    return dp.get_db_conn()


async def check_user_registered(*, tg_user: TgUser) -> bool:
    return bool(await get_user_for_filters(tg_user=tg_user))


@cached(ttl=0.2, serializer=PickleSerializer())
async def get_user_for_filters(*, tg_user: TgUser) -> Users | None:
    return await get_user(tg_user=tg_user)


async def get_user(*, tg_user: TgUser) -> Users | None:
    try:
        user = await _get_conn().get(Users, social_id=tg_user.tg_id)
    except Exception:
        return None
    else:
        user.username = tg_user.username
        return user  # type: ignore[no-any-return]


async def create_user(*, tg_user: TgUser) -> None:
    await _get_conn().create(
        Users, social_id=tg_user.tg_id, username=tg_user.username, registration_date=datetime.now()  # noqa: DTZ005
    )
    logger.info(f"New user[{tg_user.username}] registered")


async def update_user_info(*, tg_user: TgUser, user_form_data: UserFormData) -> None:
    user = await get_user(tg_user=tg_user)
    if user is not None:
        user.name = user_form_data.name
        user.info = user_form_data.info
        user.photo = user_form_data.photo
        await _get_conn().update(user)


async def incr_user_taps(*, tg_user: TgUser) -> None:
    user = await get_user(tg_user=tg_user)
    if user is not None:
        user.taps += 1
        await _get_conn().update(user)


async def get_all_users() -> list[Users]:
    return list(await _get_conn().execute(Users.select().order_by(Users.taps.desc())))

#Функция для получения вопроса из базы
async def get_question(*, question_gl_obj: Question) -> Questions | None:
    try:
        # Получаю объект вопроса из бд
        question_db_obj = await _get_conn().get(Questions, id = question_gl_obj.id)
        # Присваиваю глобальному объекту поля из объекта бд
        question_gl_obj.question = question_db_obj.question
        question_gl_obj.answer1 = question_db_obj.answer1
        question_gl_obj.answer2 = question_db_obj.answer2
        question_gl_obj.answer3 = question_db_obj.answer3
        question_gl_obj.right_answer = question_db_obj.right_answer
        return question_gl_obj
    except Exception:
        return None

# Функция для получения рандомного номера вопроса из всех существующих
async def get_random_question_id() -> int | None:
    # Получить количетсво вопросов из бд
    questions_ids = list(await _get_conn().execute(Questions.select().order_by(Questions.id.desc())))
    question_id = int(str(random.choice(questions_ids)))
    # TODO: сейчас возвращаем объект, надо int
    logger.info(f"Get random ID of question: {question_id}")
    return question_id

# Функция для обновления количества вопросов у пользователя
async def incr_user_questions(*, tg_user: TgUser, answer: str) -> int:
    user = await get_user(tg_user=tg_user)
    # Если ответил верно, добавляем верный ответ и вопрос, неверно — только вопрос
    if user is not None:
        if answer == "correct":
            user.right_answers += 1
            user.questions += 1
        else:
            user.questions += 1
        await _get_conn().update(user)
        logger.info(f"Верных ответов у пользователя: {user.right_answers}, всего вопросов: {user.questions}")
    return user.questions, user.right_answers