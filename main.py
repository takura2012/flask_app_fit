from flask import Flask, render_template, url_for, request, redirect, session, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import json
import config
from _models import Exercise, Muscle, ExerciseMuscle, db, Training, User, Plan
from sqlalchemy import Column, Integer, String, ForeignKey
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

    users = User.query.all()
    const_config = {}
    const_config['levels'] = config.TRAINING_LEVELS
    const_config['filter_list'] = config.FILTER_LIST
    index_dict = session.get('index_dict', {})
    if 'filter_list' not in index_dict:
        index_dict['filter_list'] = ['1','4','7','8']
    print(index_dict['filter_list'])

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


@app.route('/relate_tables', methods=['POST', 'GET'])
def relate_tables():
    exercises = Exercise.query.all()
    muscles = Muscle.query.all()
    ex_mus = ExerciseMuscle.query.all()
    if request.method == 'POST':
        return 'PASS'
    else:
        return render_template('relate_tables.html', ex_mus=ex_mus)


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


@app.route('/train')
def trainings_list():
    const_config = {}
    index_dict = session.get('index_dict', {})

    if 'filter_list' not in index_dict:
        index_dict['filter_list'] = ['1','4','7','8']

    const_config['filter_list'] = config.FILTER_LIST
    all_exercises = Exercise.query.all()
    # filter here
    exercises = [ex for ex in all_exercises]
    exercises_in_train = []

    return render_template('train.html', exercises=exercises, exercises_in_train=exercises_in_train, const_config=const_config, index_dict=index_dict)


@app.route('/training_create', methods=['POST', 'GET'])
def training_create():
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
        return redirect(url_for('training_create'))

    return render_template('training_create.html', levels=levels, bmi_dict=bmi_dict, groups=groups, plans=plans)


@app.route('/training_load/<string:level_day>')
def training_load(level_day):
    plan = Plan.query.filter_by(level_day=level_day).first()
    bmi_dict = {}

    bmi_dict['level_day'] = plan.level_day
    bmi_dict['strength'] = plan.strength
    bmi_dict['sets_high'] = plan.sets_high
    bmi_dict['sets_low'] = plan.sets_low
    bmi_dict['rec'] = plan.rec
    bmi_dict['groups'] = plan.groups

    session['bmi_dict'] = bmi_dict

    return redirect(url_for('training_create'))


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
    session.clear()
    return render_template('migration.html')


@app.route('/migration/save')
def migration_save():
    return redirect('/migration')


@app.route('/migration/load')
def migration_load():
    return redirect('/migration')


@app.route('/migration/new_base')
def migration_new():
    with app.app_context():
        try:
            db.create_all()
            return '<h2>Таблицы добавлены</h2>'
        except Exception as e:
            return f'<h2>Ошибка: {str(e)}</h2>'


if __name__ == '__main__':
    app.run(debug=True)
