from dataclasses import dataclass

from aiogram.dispatcher.filters.state import State, StatesGroup


@dataclass
class UserFormData:
    name: str
    info: str
    photo: str


class UserForm(StatesGroup):  # type: ignore[misc]
    name = State()
    info = State()
    photo = State()


class InterviewQuestion(StatesGroup):  # type: ignore[misc]
    question = State()
    description = State()

@dataclass
class UserInterviewData:
    answer: str