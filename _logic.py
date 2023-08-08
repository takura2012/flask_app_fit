# Создайте структуру данных, чтобы хранить информацию об упражнениях, мышцах и нагрузке.
# Загрузите данные из вашей базы данных в эту структуру
import random, config
from _models import Exercise, Muscle, Training, ExerciseMuscle
from typing import List
from sqlalchemy import or_


# from main import app
#
# app.config.from_object('config')


# функция вернет список объектов Exercise сумма difficulty у которых будет не превышать max_effort по жадному алгоритму (начиная с больших)

def count_muscles(exercises: Exercise = []):
    id_list = []
    muscles_percent = {}
    pc_mus = {}

    for ex in exercises:
        id_list.append(ex.exercise_id)

    for exercise_muscle in ExerciseMuscle.query.all():
        if exercise_muscle.exercise_id in id_list:
            muscle_id = exercise_muscle.muscle_id
            muscles_percent[muscle_id] = muscles_percent.get(muscle_id, 0) + exercise_muscle.percent

    # print(muscles_percent)
    lp = 100
    for mu, pc in muscles_percent.items():
        lp += 1
        pc = str(lp) + '-' + str(pc)
        pc_mus[pc] = Muscle.query.get(mu)
        # print(f'{pc_mus[pc].muscle_name:<45}: {pc} %')
    # sorted_keys = sorted(pc_mus.keys())
    # sorted_pc_mus = {key: pc_mus[key] for key in sorted_keys}

    return pc_mus


def create_exercises_set(exercises: List[Exercise], max_effort):
    random_exercises = []
    sorted_exercises = sorted(exercises, key=lambda exercise: exercise.difficulty, reverse=True)
    random_exercises = sorted_exercises[1:]
    # random.shuffle(random_exercises)
    random_exercises.insert(0, sorted_exercises[0])

    current_sum = 0
    result = []
    final = []

    for ex in random_exercises:
        if current_sum + ex.difficulty <= max_effort:
            result.append(ex)
            current_sum += ex.difficulty
    final = result[:3]
    return final


def select_exercises(target_list=['Ноги'], efforts=90, excluded=[], filters=[['1'], ['2'], ['3'], ['4'], ['5'], ['6'], ['7'],[8], [9]]):
    selected_exercises = []

    for target in target_list:

        target_exercises = Exercise.query.filter(
            Exercise.target == target,
            # or_(*[Exercise.filters.contains(f) for f in filters])
        ).all()

        # print(f'filters: {filters}')
        # for ex in target_exercises:
            # print(f'{ex.name}: {ex.filters}')

        exercises = [ex for ex in target_exercises if ex.exercise_id not in excluded]

        if exercises:
            targeted_exercises = create_exercises_set(exercises, efforts)
            selected_exercises += targeted_exercises

    return selected_exercises


def convert_dict_to_list(target_days, groups=config.GROUPS):
    list_with_empty = [[], [], [], [], [], [], []]
    # перебираем словарь targets_dict = 'fullbody':'1,2,3', ...
    for key, positions in target_days.items():
        poslist = [pos for pos in positions.split(',')]  # из строки делаем список разделяя по запятой '1,2,3'
        for pos in poslist:
            del list_with_empty[int(pos) - 1]
            list_with_empty.insert(int(pos) - 1,
                                   groups[key])  # вставляем элемент groups[key] в список list_with_empty на pos
    # удаляю пустые подсписки
    group_json = [sub for sub in list_with_empty if sub]

    return group_json


def filtering(object_filters, filter_lists):
    result = all(any(filter in object_filters for filter in filter_list) for filter_list in filter_lists)
    return result
