# MindNavigator

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt](https://img.shields.io/badge/Qt-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![UI](https://img.shields.io/badge/UI-Desktop_App-1f6feb)](#)

**MindNavigator** — настольное приложение для навигации по рабочим пространствам, задачам и проектам. Оно объединяет список задач, проекты и карты в едином интерфейсе с кастомным заголовком окна и боковой навигацией, помогая быстро переключаться между режимами работы.

## Возможности
- Рабочая область задач с фильтрацией по проектам.
- Разделы «Проекты» и «Карты» с отдельными рабочими областями.
- Единый интерфейс с левым меню и навигационной колонкой.
- Плейсхолдеры для будущих режимов («Заметки», «Файлы», «Объекты», «Настройки»).

## Требования
- Python 3.10+
- PySide6
- qtawesome

## Установка зависимостей
```bash
pip install -r requirements.txt
```

## Запуск
```bash
python main.py
```

## Структура проекта
- `main.py` — входная точка приложения.
- `mindnavigator/main_window.py` — главное окно и переключение режимов.
- `mindnavigator/workspaces/` — рабочие пространства (задачи, проекты, карты).
- `assets/` — иконки и сплэш-экран.

## Ресурсы
Убедитесь, что рядом с `main.py` есть каталог `assets/` со следующими файлами:
- `assets/icon.ico`
- `assets/splash.jpg`
