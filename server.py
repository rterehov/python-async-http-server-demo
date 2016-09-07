import os
import json
import asyncio
import logging

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
    if number in primes_set:
        return True

    # Четные, кроме числа 2, проверять смысла нет.
    if number % 2 == 0:
        return False

    max_ = sqrt(number) + 1
    curr = 3
    while curr < max_:
        if number % curr == 0:
            return False
        curr += 2 # двигаемся по нечетным
        await asyncio.sleep(0.00000001)

    primes_set.add(number)
    return True


async def get_prime_factors(number):
    """
    Разложение числа на простые множители.
    Используется простой алгоритм перебора с оптимизациями. При этом перед тем,
    как начать вычисления, проверяется, не является ли переданное число простым.

    """

    res = results.get(number, [number] if await is_prime(number) else [])
    if not res:
        i = 1
        tmp = number
        while i < tmp:
            i += 1
            if is_prime(i) and tmp % i == 0:
                tmp /= i
                res.append(i)
                logging.debug('{}: {} {}'.format(number, i, int(tmp)))
                i = 1
            await asyncio.sleep(0.00000001)
    results[number] = res
    return res


def static_serve(path, writer):
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
        query = (
            'HTTP/1.1 404 \'File not found\'\r\n'
            '\r\n'
        ).encode('utf-8')

    writer.write(query)

    if f:
        writer.write(bytes(f.read(), 'utf8'))
        f.close()

    writer.close()
    return


@asyncio.coroutine
def handle(reader, writer):
    """
    Асинхронный обработчик соединений.

    Работает с запросами в объеме, достаточном для демонстрации. 

    """
    first_line = True
    content_length = 0
    curr_func, args = reader.readline, ()
    while not reader.at_eof():
        try:
            data = yield from asyncio.wait_for(curr_func(*args), timeout=5)
            line = data.decode()

            if not line:
                break

            if first_line:
                first_line = False
                method, path, version = line.split()
                path = 'index.html' if path == '/' else path
                if method == 'GET':
                    return static_serve(path, writer)

            if curr_func == reader.read:
                number, id = map(lambda x: x.split('=')[-1], line.split('&'))
                number = int(number)
                logging.debug(line)
                break

            if 'Content-Length' in line:
                content_length = int(line.split(':')[-1].strip())
            elif line == '\r\n':
                curr_func, args = reader.read, (content_length,)

        except concurrent.futures.TimeoutError:
            logging.warning('TIMEOUT!!!')
            break

    res = yield from get_prime_factors(number)
    res = json.dumps({
        'id': id,
        'number': number,
        'res':  ' * '.join(map(str, res)),
    })
    query = (
        'HTTP/1.1 200 OK\r\n'
        'Content-type: text/json\r\n'
        '\r\n'
    ).encode('utf-8')
    writer.write(query)
    writer.write(bytes(res, "utf8"))
    writer.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    server_gen = asyncio.start_server(handle, port=8081)
    server = loop.run_until_complete(server_gen)
    logging.info('Server started: {0}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()
