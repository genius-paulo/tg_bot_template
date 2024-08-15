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


# Get question from db
async def get_question(*, question_gl_obj: Question) -> Question | None:
    try:
        # Get db object of question
        question_db_obj = await _get_conn().get(Questions, id=question_gl_obj.id)
        # Assign fields from db object to global object
        question_gl_obj.question = question_db_obj.question
        question_gl_obj.answer1 = question_db_obj.answer1
        question_gl_obj.answer2 = question_db_obj.answer2
        question_gl_obj.answer3 = question_db_obj.answer3
        question_gl_obj.right_answer = question_db_obj.right_answer
        return question_gl_obj
    except Exception:
        return None


# Get list of question ids
async def get_random_question_ids() -> list | None:
    # Get all question id from db
    questions_ids = list(await _get_conn().execute(Questions.select().order_by(Questions.id.desc())))
    # Get list with 10 int ids
    ten_random_questions_ids = list(map(int, (map(str, random.sample(questions_ids, k=10)))))
    return ten_random_questions_ids


# Update answers and questions in db user
async def incr_user_questions(*, tg_user: TgUser, right_answers: int, all_questions: int) -> tuple[int, int]:
    user = await get_user(tg_user=tg_user)
    if user is not None:
        user.right_answers += right_answers
        user.questions += all_questions
        await _get_conn().update(user)
        logger.info(f"User's right answers: {user.right_answers}, all of questions: {user.questions}")
    return user.questions, user.right_answers
