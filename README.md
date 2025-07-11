Edumaster - платформа обмена курсов для учителей и студентов. (backend)

### Запуск сервера
#### Через Docker
1) Копируем репозиторий и переходим в него
```bash
git clone https://github.com/delawer33/edumaster
```
```
cd edumaster
```
2) В `edumaster/app/core` создаем файл `.env` по примеру в файле `.env_example` (можно просто скопировать его содержимое в файл `.env`)

3) Запускаем docker-compose
```
sudo docker compose up -d
```

#### Локально на машине
1) Копируем репозиторий и переходим в него
```bash
git clone https://github.com/delawer33/edumaster
```
```
cd edumaster
```
2) В `edumaster/app/core` создаем файл `.env` по примеру в файле `.env_example` (можно просто скопировать его содержимое в файл `.env`)

3) Создаем виртуальное окружение python3.12, активируем его, устанавливаем зависимости

```
python3 -m venv .venv
```
```
source .venv/bin/activate
```
```
pip install -r requirements.txt
```
4) Запускаем сервисы `postgres` и `minio` (можно использовать docker-compose.yaml файл, закомментировав в нем сервис `app` и запустив команду `sudo docker compose up -d`)

5) Запускаем сервер 

```
python3 -m app.main
```

Swagger-документация на `localhost:8000/docs`

