Тестовое задание для поступления в Школу Бекенд-разработки Яндекса в 2022 году.

[![CI](https://github.com/Dest0re/backend-school2022/actions/workflows/ci.yml/badge.svg)](https://github.com/Dest0re/backend-school2022/actions/workflows/ci.yml)
## Что это такое
Приложение упаковано в Docker-контейнер.
Внутри доступны две команды: megamarket-api для запуска веб-сервера и
megamarket-db для управления состоянием базы данных.

## Что с этим делать
### Применить миграции:
```shell
docker run -it \
    -e MEGAMARKET_PG_URL=postgresql://user:strngpsswrd@localhost/megamarket \
    dest0re/megamarket megamarket-db upgrade head
```

### Запустить REST API веб-сервер на порту 8081:
```shell
docker run -it -p 8081:8081 \
    -e MEGAMARKET_PG_URL=postgresql://user:strngpsswrd@localhost/megamarket \
    dest0re/megamarket megamarket-api
```

Документация доступна на http://localhost:8081/doc

### Получить список команд:
```shell
docker run dest0re/megamarket megamarket-db --help
docker run dest0re/megamarket megamarket-api --help
```
Многие опции запуска доступны для указания через переменные окружения.


## Как это развернуть?
```shell
cd deploy
ansible-playbook -i hosts.ini -K playbook.yaml
```

## Разработка
### Makefile
В файле `Makefile` перечислены задачи для удобного локального развёртывания.

### Тестирование
Для тестов используется библиотека Pytest.


## Ссылки
При разработке я во многом опирался на [курс лекций](https://www.youtube.com/playlist?list=PLQC2_0cDcSKBHamFYA6ncnc_fYuEQUy0s) Академии Яндекса девятнадцатого года.

Очень помогло [Практическое руководство по разработке бэкенд-сервиса на Python](https://habr.com/en/company/yandex/blog/499534/) от одного из преподавателей Школы.
Большое за это спасибо.

