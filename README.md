# pro-autocliker

Desktop auto-clicker competing with OP Auto Clicker. Python 3.12+, CustomTkinter + pynput.

## Features (v0.1)

- Click at cursor or fixed position, with optional cursor restore
- Interval with jitter, count (0 = infinite), single/double/hold
- Global hotkeys: F6 start/stop, F7 record macro, F12 emergency stop
- Macro recording & playback
- Profiles (save/load/delete)
- Scheduler (one-shot / daily)
- Script DSL (click, move, wait, loop)
- Multi-clicker (up to 8 streams)

## Run

```bash
pip install -e .
python -m autoclicker
```

## Tests

```bash
pytest -q
mypy --strict src
```

## Data

Stored under `%APPDATA%/pro-autocliker` (Windows) or `~/.config/pro-autocliker`.

---

# pro-autocliker (RU)

Настольный авто-кликер — конкурент OP Auto Clicker. Python 3.12+, CustomTkinter + pynput.

## Возможности (v0.1)

- Клик по курсору или фиксированной позиции, с возвратом курсора
- Интервал с джиттером, счётчик (0 = бесконечно), одиночный/двойной/удержание
- Глобальные хоткеи: F6 старт/стоп, F7 запись макроса, F12 аварийный стоп
- Запись и воспроизведение макросов
- Профили (сохранить/загрузить/удалить)
- Планировщик (разовый / ежедневный)
- Скриптовый DSL (click, move, wait, loop)
- Мульти-кликер (до 8 потоков)

## Запуск

```bash
pip install -e .
python -m autoclicker
```

## Тесты

```bash
pytest -q
mypy --strict src
```