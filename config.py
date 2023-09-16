DEBUG = True
SECRET_KEY = 'some_ha5sh_#_keyidkK'
SQLALCHEMY_DATABASE_URI = 'sqlite:///fitness.db'
SESSION_TYPE = 'filesystem'
RESERVED_NAMES = ['admin', 'administrator', 'админ', 'администратор', 'old']

ACCOUNT_TYPES_EN = {
    'user': 'Standart account',
    'paid_user': 'Paid account',
    'premium': 'Premium account',
    'admin': 'admin'
}

ACCOUNT_COLORS = {
    'user': '#202050',
    'paid_user': '#32CD32',
    'premium': '#4169E1',
    'admin': '#DC143C'
}

ACCOUNT_TYPES_RU = {
    'user': 'Обычный аккаунт',
    'paid_user': 'Оплаченный аккаунт',
    'premium': 'Премиум аккаунт',
    'admin': 'Администратор'
}

TRAINING_LEVELS = {
    '1': 'Не занимался ранее',
    '2': 'Легкие тренировки/восстановление',
    '3': 'Регулярные средние тренировки',
    '4': 'Регулярные силовые тренировки'
                   }

BMI = {
    16: 'Выраженный дефицит массы тела',
    19: 'Недостаточная (дефицит) масса тела',
    25: 'Норма',
    30: 'Избыточная масса тела (предожирение)',
    35: 'Ожирение 1 степени',
    40: 'Ожирение 2 степени',
    100: 'Ожирение 3 степени'
}

TARGETS = ['Разминка', 'Пресс', 'Ноги', 'Спина', 'Грудь', 'Ягодицы', 'Бицепс', 'Трицепс', 'Плечи', 'Кардио']

NO_WEIGHT_TARGETS = ['Разминка', 'Пресс', 'Кардио']

FILTERS_LOCATION = {
    '1': 'В зале',
    '2': 'Дома',
    '3': 'Спортплощадка'
            }

FILTERS_SEX = {
    '4': 'Для мужчин',
    '5': 'Для женщин'
}

FILTERS_INVENTORY = {
    '6': 'Без инвентаря',
    '7': 'С инвентарем'
}

FILTERS_TYPE = {
    '8': 'Силовые',
    '9': 'Разминка',
    '10': 'Кардио'
}

FILTERS_LEVEL = {
    '11': 'Для начинающих'
}

FILTER_TARGETS = ['Все']+TARGETS

FILTER_LIST = [FILTERS_LOCATION, FILTERS_SEX, FILTERS_INVENTORY, FILTERS_TYPE, FILTERS_LEVEL]

GROUPS = {
        'fullbody': ['Разминка', 'Ноги', 'Спина', 'Грудь'],
        'cardio': ['Кардио'],
        'warming':['Разминка'],
        'split1': ['Разминка', 'Ноги', 'Плечи'],
        'split2': ['Разминка', 'Грудь', 'Трицепс'],
        'split3': ['Разминка', 'Спина', 'Бицепс'],
        'split4': ['Разминка', 'Плечи'],
        'split7': ['Разминка', 'Бицепс', 'Трицепс','Плечи'],
        'split2_1': ['Разминка', 'Ноги', 'Плечи', 'Бицепс'],
        'split2_2': ['Разминка', 'Спина', 'Грудь', 'Трицепс'],
        'Legs':['Ноги'],
        'legs_glutes': ['Ноги', 'Ягодицы']
          }
