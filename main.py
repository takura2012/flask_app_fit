from flask import Flask, render_template, url_for, request, redirect, session, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import json
import config
from _models import Exercise, Muscle, ExerciseMuscle, db, User, Plan, TrainingExercise, Training, UserTraining, UserTrainingExercise
from sqlalchemy import Column, Integer, String, ForeignKey, and_, or_
from sqlalchemy.orm import relationship
from datetime import datetime
from _logic import *
from flask_session import Session


app = Flask(__name__)
app.config.from_object('config')

db.init_app(app)
Session(app)
migrate = Migrate(app, db)

@app.route('/index', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def index():

    const_config = {}
    const_config['levels'] = config.TRAINING_LEVELS
    const_config['filter_list'] = config.FILTER_LIST
    index_dict = session.get('index_dict', {})
    if 'filter_list' not in index_dict:
        index_dict['filter_list'] = ['1','4','7','8']

    plan = None
    level = None
    selected_forday = None
    week_days = None
    times_for_train = None


    if request.method == 'POST':
        user_level = request.form.get('select_level')
        days = request.form.get('days')

        try:
            week_days = int(days)
        except:
            flash('Нужно ввести количество тренировочных дней в неделю')
            return redirect(url_for('index'))

        if week_days<1 or week_days>7:
            flash('Количество тренировочных дней в неделю должно быть от 1 до 7')
            return redirect(url_for('index'))

        index_dict['level'] = str(user_level)
        index_dict['days'] = str(week_days)
        session['index_dict'] = index_dict

        level_day = str(user_level)+'_'+str(week_days)

        plan = Plan.query.filter_by(level_day=level_day).first()
        if not plan:
            flash('Для таких параметров в базе нет шаблона тренировок')
            return redirect(url_for('index'))


        targets_list = convert_dict_to_list(plan.groups)

        max_effort = plan.strength
        level = config.TRAINING_LEVELS[plan.level_day[:1]]

        excluded = []
        selected_forday = []
        excluded_forday = []
        exercises_forday = []

        exercises = Exercise.query.all()

        for day in range(week_days):
            selected_result = select_exercises(targets_list[day], max_effort, excluded, index_dict['filter_list'])
            selected_forday.append([res for res in selected_result])
            excluded.extend(ex.exercise_id for ex in selected_forday[day] if ex.difficulty >= 50)
            excluded_forday.append([ex for ex in excluded])

        times_for_train = []
        for day in range(week_days):
            time_for_day = 0
            for ex in selected_forday[day]:
                time_for_day += ex.time_per_set
            times_for_train.append(time_for_day)

    return render_template("index.html", plan=plan, level=level, index_dict=index_dict, const_config=const_config,
                           selected_forday=selected_forday, times_for_train=times_for_train)


@app.route('/usefilter', methods=['POST'])
def usefilter():
    const_config = {}
    const_config['filter_list'] = config.FILTER_LIST

    index_dict = session.get('index_dict', {})  # беру из сессии

    if 'filter_list' not in index_dict: # если нет ключа то назначаю по умолчанию
        index_dict['filter_list'] = ['1','4','7','8']

    if request.method == 'POST':    # если принимаются данные с формы
        index_dict['filter_list'] = []
        for i in range(len(const_config['filter_list'])):
            index_dict['filter_list'].append(request.form.getlist('filters' + str(i + 1)))  # снимаю фильтрі в списки

    session['index_dict'] = index_dict

    return redirect('index')

# ------------------------------------------------LIST----------------------------------------------------------------

@app.route('/list/<string:counters>/del', methods=['POST','GET'])
def list_del(counters):
    tb = counters[:2]
    counter = counters[2:]
    exercises = Exercise.query.all()
    muscles = Muscle.query.all()
    if tb == 'ex':
        # exercise = Exercise.query.get_or_404(id)
        exercise = Exercise.query.filter_by(counter=counter).first()
        try:
            db.session.delete(exercise)
            db.session.commit()
            Exercise.update_counters()
            exercises = Exercise.query.all()
            return render_template('list.html', exercises=exercises, muscles=muscles)
        except Exception as e:
            return f'Ошибка при удалении упражнения из базы: {e}'
    else:
        # muscle = Muscle.query.get_or_404(id)
        muscle = Muscle.query.filter_by(counter=counter).first()
        try:
            db.session.delete(muscle)
            db.session.commit()
            Muscle.update_counters()
            return render_template('list.html', exercises=exercises, muscles=muscles)
        except:
            return 'Ошибка при удалении из базы'


@app.route('/list/<string:counters>/edit', methods=['POST', 'GET'])
def list_edit(counters):
    targets = config.TARGETS
    const_config = {}
    const_config['filter_list'] = config.FILTER_LIST
    index_dict = {}
    index_dict['filter_list'] = []


    tb = counters[:2]   # counters передано сюда в маршруте , вид: ex3 или mu4
    counter = counters[2:]
    exercises = Exercise.query.all()
    muscles = Muscle.query.all()
    if tb == 'ex':  # если передано ex, то работа над редактированием Упражнения
        exercise = Exercise.query.filter_by(counter=counter).first()    # counter - переданное значение счетчика, фильтрую базу по счетчику
        if exercise.filters is None:
            exercise.filters=[]
        if request.method == 'POST':    # если метод ПОСТ (то есть если мы передаем данные с формы к нам сюда на сервер, то далее обрабатываем данные формы и сохраняем в базу
            exercise.name = request.form['name']
            exercise.target = request.form['select_target']  # тут новое поле для класса
            exercise.description = request.form['description']
            exercise.difficulty = request.form['difficulty']
            exercise.time_per_set = request.form['time_per_set']

            for i in range(len(const_config['filter_list'])):
                form_list = request.form.getlist('filters' + str(i + 1))
                if any(sublist for sublist in form_list if sublist):
                    index_dict['filter_list'] += form_list

            print(index_dict['filter_list'])

            exercise.filters = index_dict['filter_list']

            percents = request.form.getlist('percents[]')   # получаю список значений полей с именем percents[]

            exercise_muscles = []
            # удаляю из связей старые по exercise_id
            ExerciseMuscle.query.filter_by(exercise_id=exercise.exercise_id).delete()


            for counter, percent in enumerate(percents, start=1):
                if percent != '':
                    muscle = Muscle.query.filter_by(counter=counter).first()    # нахожу Muscle по counter
                    # создаю объект ExerciseMuscle для exercise_id muscle_id percent
                    ExMus = ExerciseMuscle(exercise_id = exercise.exercise_id, muscle_id = muscle.muscle_id, percent = percent)
                    # добавляю его в список
                    exercise_muscles.append(ExMus)
                    print(f'Упражнение id: {ExMus.exercise_id} - {muscle.muscle_name} (id:{ExMus.muscle_id}) - на {ExMus.percent}%')

            try:
                # сливаю список объектов ExerciseMuscle в базу, которая ранее была очищена
                db.session.add_all(exercise_muscles)
                db.session.commit()
                return render_template('list.html', exercises=exercises, muscles=muscles)
            except Exception as e:
                db.session.rollback()
                return f'Ошибка при сохранения в базу данных: {e}'
        else:   # если метод не ПОСТ (а значит ГЕТ) то мы только зашли на маршрут и генерируем страницу для редактирования Упражнений, отсылая ей данные
            ex_len = len(exercises)


            # Объект Exercise получен в начале по counter
            if exercise is not None:
                muscles_in_ex = exercise.muscles  # Получение списка связанных мышц
                mus_dict = {}
                for muscle in muscles_in_ex:
                    percent = ExerciseMuscle.query.filter_by(exercise_id=exercise.exercise_id, muscle_id=muscle.muscle_id).first().percent
                    mus_dict[muscle.counter] = percent
            else:
                return "Упражнение не найдено."

            # передаем в шаблон упражнение, все мышцы, словарь {счетчик_мышцы:процент}
            return render_template('edit_ex_table.html', exercise=exercise, ex_len=ex_len, muscles=muscles,
                                   mus_dict=mus_dict, targets=targets, const_config=const_config)
    else:   # если передано не ех (а значит mu) то мы работаем над мускулами
        muscle = Muscle.query.filter_by(counter=counter).first()    # получем по счетчику, и далее по методам ПОСТ или ГЕТ
        if request.method == 'POST':    # ПОСТ- сохраняем данные полученные из формы и генерируем маршрут на список всего
            muscle.muscle_name = request.form['name']
            try:
                db.session.commit()
                return render_template('list.html', exercises=exercises, muscles=muscles)
            except:
                return 'Ошибка при сохранении в базу данных'
        else:   # ГЕТ - генерируем страницу редактирования мышцы, длина списка передается для кнопок назад-вперед
            mu_len = len(muscles)
            return render_template('edit_mus_table.html', muscle=muscle, mu_len=mu_len)


@app.route('/list', methods=['POST', 'GET'])
def list():
    exercises = Exercise.query.all()
    muscles = Muscle.query.all()
    return render_template('list.html', exercises = exercises, muscles = muscles)


@app.route('/create_exercises', methods=['POST','GET'])
def create_exercises():
    filters = []
    targets = config.TARGETS
    config_filters = config.FILTER_LIST
    if request.method == 'POST':
        name = request.form['name']
        target = request.form['select_target']
        description = request.form['description']
        difficulty = request.form['difficulty']
        time_per_set = request.form['time_per_set']

        for i in range(len(config_filters)):
            form_list = request.form.getlist('filters' + str(i + 1))
            if any(sublist for sublist in form_list if sublist):
                filters += form_list

        exercise = Exercise(name = name, target=target, description = description, difficulty = difficulty,
                            time_per_set = time_per_set, filters=filters)

        try:
            db.session.add(exercise)
            db.session.commit()
            Exercise.update_counters()
            link_to_go= f'list/ex{exercise.counter}/edit'

            return redirect(link_to_go)
        except:
            return 'Ошибка при сохранении в базу'
    else:
        return render_template('create_exercises.html', targets=targets, config_filters=config_filters)

# ------------------------------------------------TRAIN----------------------------------------------------------------
@app.route('/train_add_ex', methods=['POST', 'GET'])
def train_add_ex():

    if request.method == 'POST':    # при получении данных с формы

        # try:
        #     train = session['train']
        # except:
        #     return '<h1>Ошибка: Тренировка не найдена</h1>'
        # train_id = train.training_id
        train_id = request.form.get('train_id_hidden')
        ex_id = request.form.get('select_exercise')
        sets = request.form.get('sets')
        reps = request.form.get('reps')

        # ищу в таблице связей training_exercise по тренировке и упражнениям
        training_exercise = TrainingExercise.query.filter_by(training_id = train_id, exercise_id = int(ex_id)).first()
        if not training_exercise:   # добавлю в базу только если не существует такого
            training_exercise = TrainingExercise(training_id = train_id,
                                                 exercise_id = int(ex_id),
                                                 sets = int(sets),
                                                 repetitions = int(reps))

            try:
                db.session.add(training_exercise)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return f'Ошибка добавления в базу training_exercise {e}'

    return redirect(url_for('edit_train', train_id=train_id))


@app.route('/train_del_exercise/<int:train_id>/<int:ex_id>')
def train_del_exercise(train_id, ex_id):

    training_exercise = TrainingExercise.query.filter_by(training_id=train_id, exercise_id=ex_id).first()

    if training_exercise:
        db.session.delete(training_exercise)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f'Ошибка: Не удалось удалить из базы -- {e}'
    else:
        return 'TrainingExercise не определено'


    return redirect(url_for('edit_train', train_id=train_id))


@app.route('/edit_exercise_in_train/<int:train_id>', methods=['POST', 'GET'])
def edit_exercise_in_train(train_id):
    try:
        train = Training.query.get(train_id)
    except:
        return 'Ошибка: тренировка не найдена'

    if request.method == 'POST':
        exercise_id = request.form.get('exercise_id')
        sets = request.form.get('modal_sets')
        reps = request.form.get('modal_reps')

        training_exercice = TrainingExercise.query.filter_by(training_id=train_id, exercise_id=exercise_id).first()
        training_exercice.sets = sets
        training_exercice.repetitions = reps

        try:
            db.session.commit()
        except:
            return 'Ошибка: не удалось перезаписать в базу новые данные'

    return redirect(url_for('edit_train', train_id=train.training_id))


@app.route("/new_train", methods=['POST', 'GET'])
def new_train():

    if request.method == 'POST':
        train_name = request.form.get('train_name')

        train = Training.query.filter_by(name=train_name).first()

        if train:
            new_train = Training(name=train_name)
            db.session.add(new_train)
            try:
                db.session.commit()
                new_train.name = f"{train_name} ({new_train.training_id})"
                db.session.commit()
            except:
                db.session.rollback()
                return 'Ошибка при создании новой тренировки (не сохранились изменения в базе)'
        else:
            new_train = Training(name=train_name)
            db.session.add(new_train)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                return 'Ошибка при создании новой тренировки (не сохранились изменения в базе)'


        session['train'] = new_train

        return redirect(url_for('edit_train', train_id=new_train.training_id))

    trains_list = Training.query.all()

    return render_template('new_train.html', trains_list=trains_list)


@app.route('/edit_train/<int:train_id>', methods=['POST', 'GET'])
def edit_train(train_id):
    config_filters = config.FILTER_LIST # основные фильтры из конфига (список списков)
    config_filter_targets = config.FILTER_TARGETS   # список фильтров таргета - групп мышц
    train = Training.query.get(train_id)  # нахожу тренировку по ID которое передано в роуте
    exercise_filter_list = session.get('exercise_filter_list', [])  # загрузка списка фильтров из сессии, или пустой
    target_filter = session.get('target_filter','-1')   # загрузка фильтра таргета из сессии, по умолч -1 (все)

    # Создаем список условий для каждой группы фильтров - хз как оно работате делал чатГПТ. главное работает
    group_conditions = []
    for group in exercise_filter_list:
        group_condition = or_(*[Exercise.filters.contains(filter) for filter in group])
        group_conditions.append(group_condition)

    # Объединяем все групповые условия оператором and_
    combined_condition = and_(*group_conditions)

    # Применяем фильтр к запросу
    filtered_exercises = Exercise.query.filter(combined_condition).all()

    # применяем фильтр по группе мышц
    if int(target_filter) >= 0:
        target_filter_name = config_filter_targets[int(target_filter)+1]
        exercises = [ex for ex in filtered_exercises if ex.target == target_filter_name]    # отбираю по полю таргет
    else:
        exercises = filtered_exercises  # если фильтр -1 (все) то не фильтрую

    if train:
        session['train'] = train
        te_info_list = get_training_connections(train.training_id) # функция для получения связанных с тренировкой полей
        # te_info_list = [[Exercise, sets, repetitions, weight], [...], ...]    -
        session['te_info_list'] = te_info_list
    total_time = 0
    for te_info in te_info_list:
        total_time += te_info[0].time_per_set * te_info[1]


    return render_template('edit_train.html', train=train, te_info_list=te_info_list,
                           exercises=exercises, config_filters=config_filters, exercise_filter_list=exercise_filter_list,
                           config_filter_targets=config_filter_targets, target_filter=target_filter, total_time=total_time)


@app.route('/train_rename', methods=['POST', 'GET'])
def train_rename():

    if request.method == 'POST':

        train_id = request.form.get('train_id_hidden')

        train = Training.query.get(train_id)

        if train is None:
            return 'Ошибка: тренировка для переименования не найдена'


        train_new_name = request.form.get('train_new_name')

        train.name = train_new_name
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Не удалось сохранить в базу тренировку с новым именем'


    return redirect(url_for('edit_train', train_id=train.training_id))


@app.route("/train_delete", methods=['POST', 'GET'])
def train_delete():

    if request.method == 'POST':
        train_id = request.form.get('train_id_hidden')
        train = Training.query.get(train_id)
        db.session.delete(train)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return f'Ошибка базы данных: Не удалось удалить тренировку {train.name}'

    return redirect('new_train')

@app.route('/get_exercise_filter_list', methods=['POST', 'GET'])
def exercise_filter_list():
    config_filters = config.FILTER_LIST
    try:
        train = session['train']
    except:
        return '<h1>Ошибка: Тренировка не найдена</h1>'
    train_id = train.training_id
    exercise_filter_list = []

    if request.method == 'POST':    # если принимаются данные с формы беру фильтры и сохраняю в сессии
        for i in range(len(config_filters)):
            exercise_filter_list.append(request.form.getlist('filters' + str(i + 1)))  # снимаю фильтрі в списки

        session['exercise_filter_list'] = exercise_filter_list
        target_filter = request.form.get('select_target')
        session['target_filter'] = target_filter

    return redirect(url_for('edit_train', train_id=train_id))

# ------------------------------------------------PLANS----------------------------------------------------------------
@app.route('/plan_create', methods=['POST', 'GET'])
def plan_create():
    # берем переменные из конфига и задаем новые пустые для работы с ними
    levels = config.TRAINING_LEVELS
    groups = config.GROUPS
    targets_dict = {}

    # словарь из сессии со всеми данными сессии
    bmi_dict = session.get('bmi_dict', {})

    # берем из базы все планы для вывода на странице
    plans = Plan.query.all()

    # берем данные с формы, если они отправлены
    if request.method == 'POST':
        # берем данные из инпутов на форме по имени days_{key} где key это ключ из словаря GROUPS
        # делаем словарь targets_dict[key] = value {'fullbody':'1,2,3', ...}
        for key, group in groups.items():
            input_name = f'days_{key}'
            value = request.form.get(input_name)
            if value != '':
                targets_dict[key] = value

        bmi_dict['level_day'] = request.form.get('level_day')
        bmi_dict['strength'] = request.form.get('strength')
        bmi_dict['sets_high'] = request.form.get('sets_high')
        bmi_dict['sets_low'] = request.form.get('sets_low')
        bmi_dict['rec'] = request.form.get('rec')
        bmi_dict['groups'] = targets_dict

        # работа с базой данных. делаю элемент класса план и сохраняю его
        plan = Plan(
            level_day = bmi_dict['level_day'],
            strength = bmi_dict['strength'],
            sets_high = bmi_dict['sets_high'],
            sets_low = bmi_dict['sets_low'],
            rec = bmi_dict['rec'],
            groups = targets_dict
        )

        # если запись с level_day существует в базе то просто комит, если нет то добавить
        existing_record = Plan.query.filter_by(level_day=plan.level_day).first()
        if not existing_record:
            db.session.add(plan)
        else:
            for field in ['strength', 'sets_high', 'sets_low', 'rec', 'groups']:
                setattr(existing_record, field, getattr(plan, field))

        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Ошибка при сохранении плана \n'

        session['bmi_dict'] = bmi_dict
        return redirect(url_for('plan_create'))

    return render_template('plan_create.html', levels=levels, bmi_dict=bmi_dict, groups=groups, plans=plans)


@app.route('/plan_load/<string:level_day>')
def plan_load(level_day):
    plan = Plan.query.filter_by(level_day=level_day).first()
    bmi_dict = {}

    bmi_dict['level_day'] = plan.level_day
    bmi_dict['strength'] = plan.strength
    bmi_dict['sets_high'] = plan.sets_high
    bmi_dict['sets_low'] = plan.sets_low
    bmi_dict['rec'] = plan.rec
    bmi_dict['groups'] = plan.groups

    session['bmi_dict'] = bmi_dict

    return redirect(url_for('plan_create'))

# ------------------------------------------------LOGIC----------------------------------------------------------------
@app.route('/logic', methods=['POST', 'GET'])
def logic():
    excluded = session.get('excluded', [])
    selected_result = session.get('selected_result', [])
    max_effort = session.get('max_effort', [70])
    targets_list = session.get('targets_list', [])
    excluded_exercises = []
    all_muscles = {}


    exercises = Exercise.query.all()

    selected_result = select_exercises(targets_list, max_effort, excluded)
    excluded_exercises = Exercise.query.filter(Exercise.exercise_id.in_(excluded)).all()

    if request.method == 'POST':
        try:
            max_effort = int(request.form['max_effort'])    # можно попробовать скалировать max_effort от повторений
        except ValueError:
            max_effort = 70
        targets_list = request.form.getlist('target')

        selected_result = select_exercises(targets_list, max_effort, excluded)
        excluded_exercises = Exercise.query.filter(Exercise.exercise_id.in_(excluded)).all()

        session['selected_result'] = selected_result
        session['max_effort'] = max_effort
        session['targets_list'] = targets_list

    all_muscles = count_muscles(selected_result)


    return render_template('logic.html', exercises=exercises, selected_result=selected_result, max_effort=max_effort,
                           targets_list=targets_list, excluded_exercises=excluded_exercises, all_muscles=all_muscles)


@app.route('/logic/exclude/<int:ex_id>', methods=['POST', 'GET'])   # добавить в исключения
def logic_exclude(ex_id):

    excluded = session.get('excluded', [])
    if ex_id in excluded:
        return redirect(url_for('logic'))

    excluded.append(ex_id)
    # exercises = Exercise.query.all()

    session['excluded'] = excluded

    selected_result = session.get('selected_result', [])
    max_effort = session.get('max_effort', [])
    targets_list = session.get('targets_list', [])
    print(excluded)
    return redirect(url_for('logic'))


@app.route('/logic/retrieve/<int:ex_id>')   # удалить из исключений
def logic_retrieve(ex_id):
    excluded = session.get('excluded', [])
    if ex_id in excluded:
        excluded.remove(ex_id)
    session['excluded'] = excluded
    return redirect(url_for('logic'))


@app.route('/migration')
def migration():
    return render_template('migration.html')


@app.route('/migration/clear_session')
def clear_session():
    session.clear()
    return redirect('/')

@app.route('/migration/new_base')
def migration_new():
    with app.app_context():
        try:
            db.create_all()
            return '<h2>Таблицы добавлены</h2>'
        except Exception as e:
            return f'<h2>Ошибка: {str(e)}</h2>'


@app.route('/users_center', methods=['POST', 'GET'])
def users_center():

    user = User.query.filter_by(name='Admin').first()
    if not user:
        user = User(
            name = 'Admin',
            email = 'takura2012@gmail.com'
            )
        db.session.add(user)
        db.session.commit()

    # добавление всех связей для пользователя
    if False:
        # Получаем тренировки, которые хотим назначить пользователю
        training_ids_to_assign = [2, 3]  # ID тренировок, которые хотим назначить
        trainings_to_assign = Training.query.filter(Training.training_id.in_(training_ids_to_assign)).all()

        # Создаем объекты UserTraining для каждой тренировки и добавляем их в список
        user_trainings_to_assign = []
        for training in trainings_to_assign:
            user_training = UserTraining(
                user=user,
                training=training,
                assigned=True  # Устанавливаем флаг, что тренировка назначена
            )
            user_trainings_to_assign.append(user_training)

        # Добавляем список объектов UserTraining в сессию и коммитим изменения
        db.session.add_all(user_trainings_to_assign)
        db.session.commit()

        # Получаем тренировки, для которых нужно создать UserTrainingExercise
        trainings_to_assign = Training.query.filter(Training.training_id.in_(training_ids_to_assign)).all()

        # Создаем объекты UserTrainingExercise для каждой тренировки и упражнения
        for user_training in user.trainings:
            for training_exercise in user_training.training.exercises:
                training_exercise_in_db = TrainingExercise.query.filter_by(training_id=user_training.training_id,
                                                                           exercise_id=training_exercise.exercise_id).first()
                user_training_exercise = UserTrainingExercise(
                    user_training=user_training,
                    exercise=training_exercise,
                    sets=training_exercise_in_db.sets,
                    repetitions=training_exercise_in_db.repetitions,
                    weight=0  # Ваше значение веса
                )
                db.session.add(user_training_exercise)

        # Добавление изменений в базу данных
        db.session.commit()

    # вывод от пользователя всех его объектов
    if False:
        user_trainings = user.trainings
        # список объектов UserTraining из за trainings = relationship('UserTraining', back_populates='user') в классе User
        for user_train in user_trainings:
            print(user_train.training)
            for ex in user_train.training.exercises:
                print(ex)
                for user_training_exercise in ex.user_training_exercises:
                    print(user_training_exercise.sets, user_training_exercise.repetitions)

    return render_template('users_center.html', user=user)


if __name__ == '__main__':
    app.run(debug=True)
