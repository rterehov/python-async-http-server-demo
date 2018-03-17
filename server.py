import os
import json
import asyncio
import logging

from urllib import parse
from math import sqrt
from os import curdir, sep

import concurrent.futures


# Кешируем уже вычисленные простые числа.
# Предзаполнение двойкой позволяет использовать на 1 проверку меньше при
# вычислении.
primes_set = set([2])

# Кешируем результаты.
results = dict()


async def is_prime(number):
    """
    Проверка, является ли число простым.
    Простое число - натуральное число, имеющее ровно два различных
    натуральных делителя - единицу и самого себя.

    """
    if number < 2:
        return False

    if number in primes_set:
        return True

    # Четные числа все непростые.
    if number % 2 == 0:
        return False

    # Двигаемся по нечетным числам, т.к. четные все непростые.
    i = 0
    for curr in range(3, int(sqrt(number)) + 1, 2):
        if number % curr == 0:
            return False

        # даем другим сопрограммам возможность выполниться
        i += 1
        if i > 100:
            await asyncio.sleep(0.00000001)
            i = 1

    primes_set.add(number)
    return True


async def get_prime_factors(number):
    """
    Разложение числа на простые множители.
    Используется простой алгоритм перебора с оптимизациями. При этом перед
    тем, как начать вычисления, проверяется, не является ли переданное число
    простым.

    """
    res = results.get(number, [number] if await is_prime(number) else [])
    if not res:
        i = 1
        tmp = number
        while i < tmp:
            i += 1
            if await is_prime(i) and tmp % i == 0:
                tmp /= i
                res.append(i)
                logging.info('{}: {} {}'.format(number, i, int(tmp)))
                i = 1
    results[number] = res
    return res

async def errors_handler(writer, code, message):
    query = 'HTTP/1.1 {} \'{}\'\r\n\r\n'.format(code, message)
    writer.write(query.encode('utf-8'))
    writer.close()

async def handler_404(writer):
    return await errors_handler(writer, 404, 'File not found')

async def handler_408(writer):
    return await errors_handler(writer, 408, 'Request Timeout')

async def send_json(writer, data):
    query = (
        'HTTP/1.1 200 OK\r\n'
        'Content-type: text/json\r\n'
        '\r\n'
    ).encode('utf-8')
    writer.write(query)
    writer.write(bytes(json.dumps(data), "utf8"))
    writer.close()

async def static_serve(path, writer):
    """
    Простой обработчик статики. Нужен для удобства демонстрации.
    Поддерживает js и html файлы.

    """
    path = curdir + sep + path
    ct = ''
    f = None
    if os.path.exists(path):
        f = open(path)
        if path.endswith(".html"):
            ct = 'text/html'
        if path.endswith(".js"):
            ct = 'text/javascript'

    if ct and f:
        query = (
            'HTTP/1.1 200 OK\r\n'
            'Content-type: ' + ct + '\r\n'
            '\r\n'
        ).encode('utf-8')
    else:
        return await handler_404(writer)

    writer.write(query)

    if f:
        writer.write(bytes(f.read(), 'utf8'))
        f.close()

    writer.close()
    return


async def handle(reader, writer):
    """
    Обработчик соединений.
    Работает с запросами в объеме, достаточном для демонстрации.

    """
    id = None
    number = None
    content_length = 0

    # Для наших целей достаточно прочитать первую строку.
    try:
        data = await asyncio.wait_for(reader.readline(), timeout=1)
    except concurrent.futures.TimeoutError:
        logging.warning('TIMEOUT!!!')
        return await handler_408(writer)
    finally:
        reader.feed_eof()

    line = data.decode()
    logging.info(line)

    # Разрешаем только GET запросы
    method, url, _ = line.split()
    if method != 'GET':
        return await handler_404(writer)

    # Парсим запрос и вычленяем нужные параметры
    _, _, path, _, query, _ = parse.urlparse(url)
    if query:
        qs = parse.parse_qs(query)
        number = qs.get('number', [])[0]
        id = qs.get('id', [])[0]

    # Если нужных параметров нет, считаем, что запросили статику
    if not all((number, id)):
        path = 'index.html' if path == '/' else path
        return await static_serve(path, writer)

    # Проверка входящих данных, расчет и формирование тела ответа
    response = {'id': id, 'number': number}
    try:
        number = int(number)
        assert number > 0
    except:
        response.update({'res': 'Введите целое число большее 0'})
    else:
        res = await get_prime_factors(number)
        response.update({'res':  ' * '.join(map(str, res))})

    # Отправляем ответ
    return await send_json(writer, response)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    server_gen = asyncio.start_server(handle, port=8081)
    server = loop.run_until_complete(server_gen)
    print('Starting Python Asynchronous Server Demo at http://{}'
          .format(':'.join(map(str, server.sockets[0].getsockname()))))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()
