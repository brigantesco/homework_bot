import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log',
                              encoding='UTF-8',
                              maxBytes=50_000_000,
                              backupCount=5
                              )
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение: {TELEGRAM_CHAT_ID}: {message}')
    except telegram.TelegramError as telegram_error:
        logger.error(f'Cообщение в телеграмм не отправилось: {telegram_error}')


class StatusCodeNot200(Exception):
    """Ошибка статуса запроса отлиичном от 200."""

    pass


class RequestsErrorGetApiAnswer(Exception):
    """Ошибка отправки запроса."""

    pass


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as request_error:
        msg = f'Исключение (RequestException): {request_error}'
        logging.error(msg)
        raise RequestsErrorGetApiAnswer(msg) from request_error
    if homework_statuses.status_code != HTTPStatus.OK:
        msg = f'Ошибка: Статус код {homework_statuses.status_code}'
        logger.error(msg)
        raise StatusCodeNot200(msg)
    try:
        return homework_statuses.json()
    except json.JSONDecodeError:
        logger.error('Ошибка json')
        raise json.JSONDecodeError('Ошибка json')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logger.error('Response не словарь')
        raise TypeError('Response не словарь')
    try:
        lst = response['homeworks']
    except KeyError:
        logger.error('Нет ключа homeworks')
        raise KeyError('Ошибка: нет ключа homeworks')
    try:
        return lst[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')


def parse_status(homework):
    """Извлекает из информации о статусе проверки."""
    if 'homework_name' not in homework:
        logger.error('Нет ключа "homework_name"')
        raise KeyError('Нет ключа "homework_name"')
    if 'status' not in homework:
        logger.error('Нет ключа "status"')
        raise KeyError('Нет ключа "status"')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Неизвестный статус: {homework_status}')
        raise KeyError(f'Неизвестный статус: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    dict_token = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}
    msg = ('Отсутствует переменная окружения:')
    tokens_bool = True
    for token, value in dict_token.items():
        if value is None:
            tokens_bool = False
            logger.critical(f'{msg} {token}')
    return tokens_bool


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(1)
    status = None
    msg_err = None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date', current_timestamp)
            msg = parse_status(check_response(response))
            if msg != status:
                send_message(bot, msg)
                status = msg
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            if message != msg_err:
                send_message(bot, message)
                msg_err = message
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
