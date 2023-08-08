from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    experience = db.Column(db.Integer, default=0)  # exp = train*strength
    level = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'User {self.id}'


class Exercise(db.Model):
    __tablename__ = 'exercises'

    exercise_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(20), default='')
    description = db.Column(db.String(300), nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    time_per_set = db.Column(db.Integer, nullable=False)
    counter = db.Column(db.Integer, default=0)
    filters = db.Column(JSON, default=[])   # LOCATION_FILTERS.keys

    muscles = relationship('Muscle', secondary='exercise_muscles')
    training_exercises = db.relationship('TrainingExercise', backref='exercise')

    def __repr__(self):
        return 'Exercise %r' % self.exercise_id

    @classmethod
    def update_counters(cls):
        exercises = cls.query.all()  # Получаем все записи класса Exercise из базы данных
        for counter, exercise in enumerate(exercises, start=1):
            exercise.counter = counter
        try:
            db.session.commit()  # Сохраняем изменения в базе данных
        except Exception as e:
            db.session.rollback()  # Откатываем изменения в случае возникновения ошибки
            raise e


class Muscle(db.Model):
    __tablename__ = 'muscles'

    muscle_id = db.Column(db.Integer, primary_key=True)
    muscle_name = db.Column(db.String(50), nullable=False)
    counter = db.Column(db.Integer, default=0)

    exercises = db.relationship('Exercise', secondary='exercise_muscles', overlaps="muscles")

    def __repr__(self):
        return 'Muscle %r' % self.muscle_id

    @classmethod
    def update_counters(cls):
        muscles = cls.query.all()  # Получаем все записи класса Muscle из базы данных
        for counter, muscle in enumerate(muscles, start=1):
            muscle.counter = counter
        try:
            db.session.commit()  # Сохраняем изменения в базе данных
        except Exception as e:
            db.session.rollback()  # Откатываем изменения в случае возникновения ошибки
            raise e


class ExerciseMuscle(db.Model):
    __tablename__ = 'exercise_muscles'

    exercise_id = Column(Integer, ForeignKey('exercises.exercise_id', ondelete='CASCADE'), primary_key=True)
    muscle_id = Column(Integer, ForeignKey('muscles.muscle_id', ondelete='CASCADE'), primary_key=True)
    percent = Column(Integer, default=0)


class Training(db.Model):
    __tablename__ = 'trainings'

    training_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

    exercises = db.relationship('Exercise', secondary='training_exercises')


    def __repr__(self):
        return 'Training %r' % self.training_id


class TrainingExercise(db.Model):
    __tablename__ = 'training_exercises'

    training_id = db.Column(db.Integer, db.ForeignKey('trainings.training_id', ondelete='CASCADE'), primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.exercise_id', ondelete='CASCADE'), primary_key=True)

    sets = db.Column(db.Integer)
    repetitions = db.Column(db.Integer)
    weight = db.Column(db.Integer)


class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    level_day = db.Column(db.String(10), unique=True, nullable=False)
    strength = db.Column(db.Integer, default=70)
    sets_high = db.Column(db.String(10), default='3x16')
    sets_low = db.Column(db.String(10), default='3x8')
    rec = db.Column(db.String(200), default='1_1')
    groups = db.Column(JSON, default=[])


if __name__ == '__main__':
    # Запуск приложения Flask (только для тестирования)
    pass
