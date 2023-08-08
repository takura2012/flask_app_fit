
import json

ex_filename = 'exercise_list.json'
mus_filename = 'muscles_list.json'


def to_dict(obj, exclude_attrs=[]):
    return {attr: getattr(obj, attr) for attr in dir(obj)
            if attr not in exclude_attrs and not callable(getattr(obj, attr)) and not attr.startswith('_')}


def save_json(objects, fname):
    exclude_attrs = ['query', 'metadata', 'registry']  # Указываем атрибуты, которые нужно исключить
    data = []
    for obj in objects:
        obj_dict = to_dict(obj, exclude_attrs)
        data.append(obj_dict)
    with open(fname, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def load_json(fname):
    with open(fname, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data




