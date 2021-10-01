# Log Analyzer

📚Домашнее задание разработано для курса ["Python Developer. Professional"](https://otus.ru/lessons/python-professional/?utm_source=github&utm_medium=free&utm_campaign=otus)

## Задача

Разработать скрипт который обрабатывает при запуске последний лог в LOG_DIR, в результате работы должен получится отчет (html-файл).
То есть скрипт читает лог, парсит нужные поля, считает необходимую
статистику по url'ам и рендерит шаблон report.html

## Запуск

Для запуска приложения требуется конфигурационный ini-файл, по умолчанию -  `config.ini`.
Путь к конфигурационному файлу можно указать при помощи ключа `--config` / `-c`

```bash
python log_parser.py --config custom_config.ini
```
