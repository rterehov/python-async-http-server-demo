# Пример простого асинхронного http-сервера на python3.5 и asyncio

[![Build Status](https://travis-ci.org/rterehov/python-async-http-server-demo.svg?branch=master)](https://travis-ci.org/rterehov/python-async-http-server-demo)

## Сценарий работы

1. Пользователь вводит в клиент (браузер) число.
2. Клиент отправляет число на сервер.
3. Сервер раскладывает число на простые множители и отправляет клиенту ответ.
4. Клиент сообщает результат пользователю.

### При этом
1. Пользователь может ввести в клиенте несколько чисел, не дожидаясь получения
ответов от сервера.
2. Сервер поддерживает одновременное обслуживание нескольких клиентов.


## Запуск

```shell
cd python-async-http-server-demo
python server.py
```

## Тесты

```shell
cd python-async-http-server-demo
pytest --cov=server.py
```

