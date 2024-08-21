import peewee


class Users(peewee.Model):  # type: ignore[misc]
    id = peewee.PrimaryKeyField(null=False)
    social_id = peewee.BigIntegerField(null=False)
    username = peewee.CharField(max_length=50)
    registration_date = peewee.DateTimeField(null=True)
    taps = peewee.BigIntegerField(default=0)
    questions = peewee.BigIntegerField(default=0)
    right_answers = peewee.BigIntegerField(default=0)
    name = peewee.TextField(null=True)
    info = peewee.TextField(null=True)
    photo = peewee.TextField(null=True)


class Questions(peewee.Model):  # type: ignore[misc]
    id = peewee.PrimaryKeyField(null=False)
    question = peewee.TextField(null=True)
    answer1 = peewee.TextField(null=True)
    answer2 = peewee.TextField(null=True)
    answer3 = peewee.TextField(null=True)
    right_answer = peewee.TextField(null=True)