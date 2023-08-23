# Создайте структуру данных, чтобы хранить информацию об упражнениях, мышцах и нагрузке.
# Загрузите данные из вашей базы данных в эту структуру
import random, config
from _models import Exercise, Muscle, Training, ExerciseMuscle, TrainingExercise, Plan, UserTraining, UserTrainingExercise, Plan_Trainings
from typing import List
from sqlalchemy import or_
from main import db


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


def get_training_connections(train_id):   # te_info = [te, sets, repetitions] (te- Exercise)

    train = Training.query.get(train_id)
    te_info_list = []

    # exercise_list = train.exercises  # Упражнения будут в порядке, в котором они находятся в базе

    # print(f'_logic: train.exercises= {exercise_list}')

    for te in train.exercises:  # для каждого упражнения te из цикла по training.exercises (класса Training)
        training_exercise = TrainingExercise.query.filter_by(training_id=train.training_id,
                                                             exercise_id=te.exercise_id).first()
        # выбираем по фильтру объекты связей TrainingExercise по training_id и exercise_id
        if training_exercise:  # и выбираем связанные сеты повторы и веса (которые 0 по умолчанию)
            sets = training_exercise.sets
            repetitions = training_exercise.repetitions

            te_info = [te, sets, repetitions]
            te_info_list.append(te_info)

    return te_info_list


def generate_unique_plan_name(base_name):
    name = base_name
    counter = 1

    while Plan.query.filter_by(name=name).first():
        name = f"{base_name}({counter})"
        counter += 1

    return name


def generate_unique_train_name(base_name):
    name = base_name
    counter = 1

    while Training.query.filter_by(name=name).first():
        name = f"{base_name}({counter})"
        counter += 1

    return name


def assign_plan_to_user(user, plan_id):
    # беру все связи план-тренировка для этого плана
    plan_trainings = Plan_Trainings.query.filter_by(plan_id=plan_id).all()
    # цикл по этим связям
    for plan_train in plan_trainings:
        # создаю связь user_training для пользователя с флагом assigned=True
        user_training = UserTraining(user_id=user.id,
                                     training_id=plan_train.training_id,
                                     assigned=True
                                     )
        db.session.add(user_training)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return e

    # беру из базы новосозданные user_trainings для этого юзера с флагом assigned=True
    user_trainings = UserTraining.query.filter_by(user_id=user.id, assigned=True).all()

    # далее создаю связи user_train_exercises , беру сеты и повторы с training_exercise
    user_train_exercises = []
    for user_training in user_trainings:
        train = Training.query.get(user_training.training_id)
        exercises = train.exercises
        for exercise in exercises:
            training_exercise = TrainingExercise.query.filter_by(training_id=train.training_id, exercise_id=exercise.exercise_id).first()
            user_train_exercise = UserTrainingExercise(user_training_id=user_training.id,
                                                        exercise_id=exercise.exercise_id,
                                                        sets=training_exercise.sets,
                                                        repetitions = training_exercise.repetitions,
                                                        weight = 0
                                                        )
            user_train_exercises.append(user_train_exercise)

        db.session.add_all(user_train_exercises)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return e


    return True


def del_current_user_plan(user):

    user_trainings = UserTraining.query.filter_by(user_id=user.id, assigned=True, completed=False).all()
    for user_training in user_trainings:
        db.session.delete(user_training)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return e

    return True


def get_user_trains(user):

    trains = UserTraining.query.filter_by(user_id=user.id).all()

    return trains


def get_user_assigned_train(user):

    user_training = UserTraining.query.filter_by(user_id=user.id, assigned=True).first()
    if not user_training:
        return None

    train = Training.query.filter_by(training_id=user_training.training_id).first()

    return train