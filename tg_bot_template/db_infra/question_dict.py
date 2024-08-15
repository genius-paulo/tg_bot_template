question_dict = {'question1':
                     {'question': 'Откуда растут корни у названия Python?',
                      'answer1': 'От названия змеи',
                      'answer2': 'Из названия сериала',
                      'answer3': 'У названия нет предыстории',
                      'right_answer': 'Из названия сериала'},
                 'question2':
                     {'question': 'Для чего используется функция setattr() в объекте?',
                      'answer1': 'Доступ к атрибуту',
                      'answer2': 'Проверка наличия атрибута',
                      'answer3': 'Установка значения атрибута',
                      'right_answer': 'Установка значения атрибута'},
                 'question3':
                     {
                         'question': 'Какой метод вызывается при использовании оператора in для проверки наличия '
                                     'элемента в пользовательском классе?',
                         'answer1': '__contains__',
                         'answer2': '__hasitem__',
                         'answer3': '__getitem__',
                         'right_answer': '__contains__'},
                 'question4':
                     {
                         'question': 'Какой оператор позволяет «перепрыгнуть» оставшиеся выражения в цикле и перейти '
                                     'к следующей итерации?',
                         'answer1': 'pass',
                         'answer2': 'else',
                         'answer3': 'continue',
                         'right_answer': 'continue'},
                 'question5':
                     {'question': 'Какой модуль Python поддерживает регулярные выражения?',
                      'answer1': 're',
                      'answer2': 'regex',
                      'answer3': 'pyregex',
                      'right_answer': 're'},
                 'question6':
                     {
                         'question': 'Чем можно заменить комментарий в теле функции, чтобы использовать минимум кода '
                                     'и избежать ошибок?',
                         'answer1': 'Заменить комментарий на docstring',
                         'answer2': 'Заменить комментарий на троеточие',
                         'answer3': 'Оба варианта подходят',
                         'right_answer': 'Оба варианта подходят'},
                 'question7':
                     {'question': 'Какой из следующих операторов имеет наименьший приоритет?',
                      'answer1': '**',
                      'answer2': '+',
                      'answer3': 'and',
                      'right_answer': 'and'},
                 'question8':
                     {'question': 'Какое из следующих преобразований типов данных невозможно в Python?',
                      'answer1': 'True в строку',
                      'answer2': '[1, 2, 3] в кортеж',
                      'answer3': '[1, 2, 3] в целое число',
                      'right_answer': '[1, 2, 3] в целое число'},
                 'question9':
                     {'question': 'Какое ключевое слово используется вместо return при создании генераторов?',
                      'answer1': 'generate',
                      'answer2': 'yield',
                      'answer3': 'iterate',
                      'right_answer': 'yield'},
                 'question10':
                     {'question': 'Что делает функция complex() в Python?',
                      'answer1': 'Возводит число в степень',
                      'answer2': 'Находит общий делитель',
                      'answer3': 'Создаёт комплексное число',
                      'right_answer': 'Создаёт комплексное число'},
                 'question11':
                     {'question': 'Что из перечисленного ниже является недопустимым именем переменной в Python?',
                      'answer1': 'yield',
                      'answer2': 'true',
                      'answer3': '_a_b',
                      'right_answer': 'yield'},
                 'question12':
                     {
                         'question': 'Какое исключение будет выброшено, если попытаться изменить кортеж после его '
                                     'создания?',
                         'answer1': 'ValueError',
                         'answer2': 'TypeError',
                         'answer3': 'AttributeError',
                         'right_answer': 'TypeError'},
                 'question13':
                     {
                         'question': 'Имеется кортеж вида T = (4, 2, 3). Какая из операций приведёт к тому, что имя T '
                                     'будет ссылаться на кортеж (1, 2, 3)',
                         'answer1': 'T[0] = 1',
                         'answer2': 'T = (1) + T[1:]',
                         'answer3': 'T = (1,) + T[1:]',
                         'right_answer': 'T = (1,) + T[1:]'},
                 'question14':
                     {
                         'question': 'Нужно собрать и вывести все уникальные слова из строки текста. Какой из типов '
                                     'данных подходит лучше всего?',
                         'answer1': 'кортеж (tuple)',
                         'answer2': 'список (list)',
                         'answer3': 'множество (set)',
                         'right_answer': 'множество (set)'},
                 'question15':
                     {
                         'question': 'Как вывести список методов и атрибутов объекта x?',
                         'answer1': 'help(x)',
                         'answer2': 'info(x)',
                         'answer3': 'dir(x)',
                         'right_answer': 'dir(x)'},
                 'question16':
                     {
                         'question': 'Какая из перечисленных инструкций выполнится быстрее всего, если n = 10**6?',
                         'answer1': 'a = list(i for i in range(n))',
                         'answer2': 'a = [i for i in range(n)]',
                         'answer3': 'a = (i for i in range(n))',
                         'right_answer': 'a = (i for i in range(n))'},
                 'question17':
                     {
                         'question': 'С помощью Python нужно записать данные в файл, но только в том случае, '
                                     'если файла ещё нет. Какой режим указать в инструкции open()?',
                         'answer1': 'x',
                         'answer2': 'w',
                         'answer3': 'r',
                         'right_answer': 'x'},
                 'question18':
                     {
                         'question': 'Что делает следующий код? def a(b, c, d): pass',
                         'answer1': 'Определяет пустой класс',
                         'answer2': 'Инициализирует список',
                         'answer3': 'Определяет пустую функцию',
                         'right_answer': 'Определяет пустую функцию'},
                 'question19':
                     {
                         'question': 'Что выведет следующий фрагмент кода? x = 4.5 y = 2 print(x // y)',
                         'answer1': '2.0',
                         'answer2': '2.25',
                         'answer3': '9.0',
                         'right_answer': '2.0'},
                 'question20':
                     {
                         'question': 'Какое ключевое слово используется для определения функции в Python?',
                         'answer1': 'func',
                         'answer2': 'define',
                         'answer3': 'def',
                         'right_answer': 'def'}}