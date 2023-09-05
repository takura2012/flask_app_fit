from flask import Flask, render_template, url_for, request, redirect, session, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from collections import Counter
import json
import config
from _models import Exercise, Muscle, ExerciseMuscle, db, User, Plan, TrainingExercise, \
    Training, UserTraining, UserTrainingExercise, Plan_Trainings
from sqlalchemy import Column, Integer, String, ForeignKey, and_, or_
from sqlalchemy.orm import relationship
from datetime import datetime
from _logic import *
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid


app = Flask(__name__)
app.config.from_object('config')

db.init_app(app)
Session(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/user_login', methods=['POST', 'GET'])
def user_login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(name=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))

        flash('Ошибка входа', 'danger')

    return redirect(url_for('index'))


@app.route('/user_logout')
def user_logout():

    logout_user()

    return redirect(url_for('index'))


@app.route('/register', methods=['POST', 'GET'])
def register():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        email = request.form['email']
        conditions = or_(User.name == username, User.email == email)
        user = User.query.filter(conditions).first()

        if not user:
            user = User(name=username, password=hashed_password, email=email)
            db.session.add(user)
            try:
                db.session.commit()
            except:
                return ('Ошибка добавления пользователя в базу')
        else:
            flash('Пользователь с такими данными уже существует')
            return redirect('register')

        return redirect(url_for('index'))


    return render_template('/modals/register.html')


@app.route('/index', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def index():

    try:
        uncompleted_user_trainings = UserTraining.query.filter_by(user_id=current_user.id, assigned=True, completed=False).all()
    except:
        return render_template("index.html", current_user=current_user)

    return render_template("index.html", uncompleted_user_trainings=uncompleted_user_trainings, current_user=current_user)


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

# ------------------------------------------------BASE----------------------------------------------------------------

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
                    # print(f'Упражнение id: {ExMus.exercise_id} - {muscle.muscle_name} (id:{ExMus.muscle_id}) - на {ExMus.percent}%')

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
        time_per_set = int(request.form['time_per_set']) if request.form['time_per_set'] else 0

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

        train_id = request.form.get('train_id_hidden')
        if Training.query.get(train_id).owner != current_user.name:
            return redirect('index')
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
    if Training.query.get(train_id).owner != current_user.name:
        return redirect(url_for('index'))

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
        if train.owner != current_user.name:
            return redirect(url_for('index'))
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

    conditions = or_(Training.owner == 'admin', Training.owner == current_user.name)
    trains_list = Training.query.filter(conditions).all()
    if request.method == 'POST':
        train_name = request.form.get('train_name')
        new_name = generate_unique_train_name(train_name)

        new_train = Training(name=new_name, owner=current_user.name)
        db.session.add(new_train)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Ошибка при создании новой тренировки (не сохранились изменения в базе)'

        session['train'] = new_train

        return redirect(url_for('edit_train', train_id=new_train.training_id))

    return render_template('new_train.html', trains_list=trains_list)


@app.route('/edit_train/<int:train_id>', methods=['POST', 'GET'])
def edit_train(train_id):

    train = Training.query.get(train_id)  # нахожу тренировку по ID которое передано в роуте
    if train.owner != current_user.name:
        return redirect('index')

    config_filters = config.FILTER_LIST # основные фильтры из конфига (список списков)
    config_filter_targets = config.FILTER_TARGETS   # список фильтров таргета - групп мышц
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
        if train.owner != current_user.name:
            flash('У вас нет права переименовать эту тренировку')
            return redirect(url_for('edit_train', train_id=train_id))

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

        if train.owner != current_user.name:
            flash('У вас нет права удалить эту тренировку')
            return redirect(url_for('edit_train', train_id=train_id))

        user_trains = UserTraining.query.filter_by(training_id=train_id).all()
        user_trains_ids = [user_train.id for user_train in user_trains]
        user_train_exercises = UserTrainingExercise.query.filter(UserTrainingExercise.user_training_id.in_(user_trains_ids)).all()

        for user_train in user_trains:
            db.session.delete(user_train)

        for user_train_exercise in user_train_exercises:
            db.session.delete(user_train_exercise)

        plan_trains = Plan_Trainings.query.filter_by(training_id=train_id).all()
        for plan_train in plan_trains:
            db.session.delete(plan_train)

        # admin_plans = Plan.query.filter_by(owner='admin').all()
        #
        # for admin_plan in admin_plans:
        #     if Plan_Trainings.query.filter_by(plan_id=admin_plan.id).first():
        #         db.session.delete(admin_plan)

        db.session.delete(train)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f'Ошибка базы данных: Не удалось удалить тренировку {train.name} (id: {train.training_id})или связанные данные.\n {e}'

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
@app.route('/plans_all', methods=['POST', 'GET'])
def plans_all():

    plans = Plan.query.filter_by(owner=current_user.name).all()
    admin_plans = Plan.query.filter_by(owner='admin').all()
    plans += admin_plans
    plan_trainings = Plan_Trainings.query.all()
    trains = Training.query.all()

    trainings_in_plan = {}  # {plan: [trains], ...}

    for plan in plans:
        trainings_in_plan[plan] = []
        for plan_train in plan_trainings:

            for train in trains:
                if train.training_id == plan_train.training_id and plan_train.plan_id == plan.id:

                    train_time = 0
                    for exercise in train.exercises:
                        te = TrainingExercise.query.filter_by(training_id=train.training_id, exercise_id=exercise.exercise_id).first()
                        train_time += te.sets * exercise.time_per_set

                    trainings_in_plan[plan].append([train, train_time])

    return render_template('plans_all.html', trainings_in_plan=trainings_in_plan)


@app.route('/plan_new/<int:plan_id>', methods=['POST', 'GET'])
def plan_new(plan_id):

    conditions = or_(Training.owner == 'admin', Training.owner == current_user.name)
    trainings = Training.query.filter(conditions).all()

    if request.method == 'POST' and plan_id == 0:
        plan_name = request.form.get('plan_name')

        unique_name = generate_unique_plan_name(plan_name)

        plan = Plan(name=unique_name, owner=current_user.name)
        db.session.add(plan)

        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Ошибка при создании нового плана тренировок'
    else:
        plan = Plan.query.get(plan_id)
        if not plan:
            return redirect(url_for('plans_all'))
        if plan.owner != current_user.name:
            flash('У вас нет прав редактировать этот план!')
            return redirect(url_for('plans_all'))

    plan_trainings = Plan_Trainings.query.filter_by(plan_id=plan.id).all()


    return render_template('plan_new.html', trainings=trainings, plan=plan, plan_trainings=plan_trainings)


@app.route('/plan_rename', methods=['POST', 'GET'])
def plan_rename():
    if request.method == 'POST':

        plan_id = request.form.get('plan_id')
        plan_new_name = request.form.get('plan_new_name')
        plan = Plan.query.get(plan_id)
        if plan.owner != current_user.name:
            return redirect(url_for('index'))
        plan_new_name = generate_unique_plan_name(plan_new_name)

        plan.name = plan_new_name

        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Ошибка : не удалось сохранить в базу новое имя плана'

    return redirect(url_for('plan_new', plan_id=plan_id))


@app.route('/plan_delete/<int:plan_id>')
def plan_delete(plan_id):
    plan = Plan.query.get(plan_id)
    if plan.owner != current_user.name:
        return redirect(url_for('index'))
    plan_trainings = Plan_Trainings.query.filter_by(plan_id=plan_id).all()
    for plan_training in plan_trainings:
        db.session.delete(plan_training)

    try:
        db.session.commit()
    except Exception as e:
        return f'Ошибка: не удалось удалить связи план-тренировки : {e}'

    db.session.delete(plan)
    try:
        db.session.commit()
    except:
        return f'Ошибка: не удалось удалить план после удаления связей : {e}'

    return redirect(url_for('plans_all'))


@app.route('/plan_add_train', methods=['POST', 'GET'])
def plan_add_train():

    if request.method == 'POST':
        plan_id = request.form.get('plan_id_hidden')
        train_id = request.form.get('train_id_hidden')
        plan = Plan.query.get(plan_id)
        train = Training.query.get(train_id)

        if Plan.query.get(plan_id).owner != current_user.name:
            flash('У вас нет прав редактировать этот план!')
            return redirect(url_for('plans_all'))

        # для дубликатов:
        PT = Plan_Trainings(plan_id=plan_id, training_id=train_id)

        try:
            db.session.add(PT)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f'Ошибка: не удалось записать в базу добавленные тренировки ---- {e}'

        # plan_trainings = Plan_Trainings.query.filter_by(plan_id=plan.id).all()
        # for plan_train in plan_trainings:
        #     print(plan_train.plan_id, plan_train.training_id)

    return redirect(url_for('plan_new', plan_id=plan_id))


@app.route('/del_train_from_plan/<int:plan_trainings_id>')
def del_train_from_plan(plan_trainings_id):

    plan_training = Plan_Trainings.query.get(plan_trainings_id)
    plan_id = plan_training.plan_id
    if Plan.query.get(plan_id).owner != current_user.name:
        flash('У вас нет прав редактировать этот план!')
        return redirect(url_for('plans_all'))

    db.session.delete(plan_training)

    try:
        db.session.commit()
    except:
        db.session.rollback()
        return 'Ошибка: не удалось удалить связь плана и тренировки'

    return redirect(url_for('plan_new', plan_id=plan_id))
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
    # print(excluded)
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

# ------------------------------------------------TRAINING-PROGRESS----------------------------------------------------------------

@app.route('/current_train', methods=['POST', 'GET'])
def current_train():


    if not current_user:
        flash('Route current_train - usercheck failed, current_user is not defined')
        return render_template('current_train.html')

    all_user_trains = get_user_trains(current_user)
    current_train = get_user_assigned_train(current_user)

    if not current_train:
        return render_template('current_train.html', current_user=current_user)

    current_train_exlist = []
    for exercise in current_train.exercises:
        user_train = UserTraining.query.filter_by(user_id=current_user.id,
                                                  training_id=current_train.training_id,
                                                  assigned=True,
                                                  completed=False
                                                  ).first()
        user_training_exercise = UserTrainingExercise.query.filter_by(user_training_id=user_train.id,
                                                                      exercise_id=exercise.exercise_id
                                                                      ).first()
        current_train_exlist.append([exercise.name, user_training_exercise.sets, user_training_exercise.repetitions, user_training_exercise.weight, user_training_exercise.completed])

    return render_template('current_train.html', current_user=current_user, current_train=current_train, current_train_exlist=current_train_exlist)


@app.route('/assign_training/<int:plan_id>')
def assign_training(plan_id):

    if current_user:
        del_current_user_plan(current_user)

        if not assign_plan_to_user(current_user, plan_id):
            return 'Ошибка assign_plan_to_user'

    return redirect(url_for('index'))


@app.route('/user_complete_train/<int:train_id>')
def user_complete_train(train_id):

    if not current_user:
        flash('Ошибка в определении пользователя (в сессии нет пользователя)')
        return redirect(url_for('current_train'))
    # user = User.query.filter_by(name=current_user_name).first()

    res = set_train_complete(current_user.id, train_id)
    if res != 'OK':
        flash('Ошибка при установке завершения тренировки (запись в базу)')

    return redirect(url_for('index'))


@app.route('/train_progress_start', methods=['POST', 'GET'])
def train_progress_start():

    if request.method == 'POST':
        train_id = request.form.get('train_id')
        user_id = request.form.get('user_id')

        # нужно найти user-train-exercise
        user_training = UserTraining.query.filter_by(user_id=user_id, training_id=train_id, assigned=True, completed=False).first()
        user_training_exercise = UserTrainingExercise.query.filter_by(user_training_id=user_training.id, completed=False).first()

        exercise = Exercise.query.get(user_training_exercise.exercise_id)
        previous_weight = find_prev_weight(exercise.exercise_id, user_id)
        max_weight = find_max_weight(exercise.exercise_id, user_id)

    return render_template('current_exercise.html', exercise=exercise, previous_weight=previous_weight,
                           user_training=user_training, user_training_exercise=user_training_exercise, max_weight=max_weight)


@app.route('/train_progress_next', methods=['POST', 'GET'])
def train_progress_next():

    if request.method == 'POST':
        user_training_exercise_id = request.form.get('user_training_exercise_id')
        user_training_id = request.form.get('user_training_id')
        weight = request.form.get('weight', 0)
        user_training_exercise = UserTrainingExercise.query.get(user_training_exercise_id)
        user_training_exercise.completed = True
        user_training_exercise.weight = weight

        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Ошибка: не удалось записать в базу'

        user_training = UserTraining.query.get(user_training_id)
        train_id = user_training.training_id
        user_id = user_training.user_id

        user_training_exercises = UserTrainingExercise.query.filter_by(user_training_id=user_training_id, completed=False, skipped=False).first()
        if not user_training_exercises:

            set_train_complete(user_id, train_id)
            user_training_exercises = UserTrainingExercise.query.filter_by(user_training_id=user_training_id).all()
            finish_data = []
            for ute in user_training_exercises:
                ex = Exercise.query.get(ute.exercise_id) # для ссылки на статистику упражнений
                ex_id = ex.exercise_id
                ex_name = ex.name
                ex_skipped = ute.skipped
                weight = ute.weight
                finish_data.append({'ex_id':ex_id, 'ex_name':ex_name, 'ex_skipped':ex_skipped, 'weight':weight})

            return render_template('training_finished.html', finish_data=finish_data)

        url = url_for('train_progress_start', _external=True)  # URL целевого роута
        payload = {
            'train_id': train_id,
            'user_id': user_id
        }

    response = requests.post(url, data=payload)

    return response.content


@app.route('/train_progress_skip', methods=['POST', 'GET'])
def train_progress_skip():

    if request.method == 'POST':
        user_training_exercise_id = request.form.get('user_training_exercise_id')
        user_training_id = request.form.get('user_training_id')
        user_training_exercise = UserTrainingExercise.query.get(user_training_exercise_id)
        user_training_exercise.skipped = True

        try:
            db.session.commit()
        except:
            db.session.rollback()
            return 'Ошибка: не удалось записать в базу'

    url = url_for('train_progress_next', _external=True)

    payload = {
        'user_training_exercise_id':user_training_exercise_id,
        'user_training_id':user_training_id
    }

    response = requests.post(url, payload)

    return response.content


@app.route('/statistics')
def statistics():

    if not current_user:
        flash('Пользователь не в системе')
        return render_template("index.html")

    u_utr = UserTraining.query.filter_by(user_id=current_user.id, assigned=True, completed=False).all()
    c_utr = UserTraining.query.filter_by(user_id=current_user.id, assigned=True, completed=True).all()

    uncompleted_trainings = []
    for u_tr in u_utr:
        train = Training.query.get(u_tr.training_id)
        if train:
            uncompleted_trainings.append([train, u_tr.id])

    completed_trainings = []
    for c_tr in c_utr:
        train = Training.query.get(c_tr.training_id)
        if train:
            # Training, UserTraining.id, количество упражнений, дата завершения
            ex_count=len(train.exercises)
            formatted_datetime = c_tr.date_completed.strftime("%d-%m-%Y %H:%M")
            completed_trainings.append([train, c_tr.id, ex_count, formatted_datetime ])
    completed_trainings.reverse()

    return render_template('statistics.html', uncompleted_trainings=uncompleted_trainings, completed_trainings=completed_trainings, user=current_user)


@app.route('/statistics/delete/<int:user_training_id>')
def statistic_delete(user_training_id):

    user_training = UserTraining.query.get(user_training_id)
    if user_training.user_id != current_user.id:
        return redirect(url_for('index'))

    user_training_exercices = UserTrainingExercise.query.filter_by(user_training_id=user_training.id).all()

    for user_training_exercice in user_training_exercices:
        db.session.delete(user_training_exercice)

    db.session.delete(user_training)

    try:
        db.session.commit()
    except:
        db.session.rollback()
        return 'Ошибка: не удалось удалить тренировку'

    return redirect('/statistics')


@app.route('/statistics/details/<int:user_training_id>')
def statistic_details(user_training_id):

    user_training_exercises = UserTrainingExercise.query.filter_by(user_training_id=user_training_id).all()
    finish_data = []
    for ute in user_training_exercises:
        ex = Exercise.query.get(ute.exercise_id)  # для ссылки на статистику упражнений
        ex_id = ex.exercise_id
        ex_name = ex.name
        ex_skipped = ute.skipped
        weight = ute.weight
        finish_data.append({'ex_id': ex_id, 'ex_name': ex_name, 'ex_skipped': ex_skipped, 'weight': weight})

    return render_template('training_finished.html', finish_data=finish_data)


@app.route('/statistics/exercises', methods=['POST', 'GET'])
def statistics_exercises():

    if request.method == 'POST':
        # взял с формы ИД юзера
        user_id = request.form.get('user_id')
        trains_count = request.form.get('trains_count')

        exercises_struct = get_exercise_statistics(user_id)
        # [[55, 'Разогрев+ разминка (10 минут)', 4, 1, [{'date': '28-08-2023 10:03:04', 'weight': 0, 'skipped': False},

    return render_template('statistics_exercises.html', exercises_struct=exercises_struct, user_id=user_id, trains_count=trains_count)


@app.route('/personal')
def personal():

    if not current_user:
        return render_template('management.html')

    return render_template('personal.html', user=current_user)


@app.route('/management')
def management():

    if not current_user:
        return render_template('management.html')

    return render_template('management.html', user=current_user)


if __name__ == '__main__':

    # with app.app_context():
    #     try:
    #         db.create_all()
    #     except Exception as e:
    #         print(e)
    app.run(debug=True)
