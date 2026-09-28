# Инструкция по запуску и проверке (Walkthrough)

## 1. Установка зависимостей
```bash
cd /root/video_loader

# Нужен Python 3.11+ — yt-dlp больше не поддерживает 3.10
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Системные пакеты: ffmpeg для склейки DASH-потоков, aria2 для быстрой
# загрузки с YouTube
sudo apt update
sudo apt install -y ffmpeg aria2 python3.11-venv
```

> ⚠️ **Проверьте, что установился `curl_cffi`:**
> ```bash
> pip show curl_cffi
> ```
> Без него TikTok отдаёт заглушку вместо страницы и скачивание падает с
> `Unexpected response from webpage request`. Он есть в `requirements.txt`,
> но `pip install` из-за конфликта зависимостей может его пропустить.

## 2. Настройка
Отредактируйте файл `.env`:
```bash
nano .env
chmod 600 .env
```
Вставьте ваш `BOT_TOKEN`. Пути к кукам (`COOKIES_YT_PATH`, `COOKIES_INST_PATH`) уже прописаны.

> 🔒 `.env` содержит токен бота и указывает на файлы с живой сессией.
> Права должны быть `600`, иначе любой пользователь машины прочитает токен.

## 3. Как получить cookies.txt (для YouTube/Instagram)
Если бот не может скачать видео (ошибка "empty file" или "sign in required"), нужны куки.
**Важно: `yt-dlp` принимает только формат Netscape (не JSON!).**

### Способ 1: Расширение "Get cookies.txt LOCALLY" (Рекомендуется)
1.  Установите расширение для Chrome/Firefox: **"Get cookies.txt LOCALLY"**.
    Расширения вроде EditThisCookie сливают куки на сторонний сервер — их лучше не использовать.
2.  **YouTube**:
    *   Зайдите на YouTube, войдите в аккаунт.
    *   Экспорт -> Сохранить как `cookies_yt.txt`.
3.  **Instagram**:
    *   Зайдите на Instagram, войдите в аккаунт.
    *   Экспорт -> Сохранить как `cookies_inst.txt`.
    *   Обязательны `sessionid`, `ds_user_id` и `csrftoken` — без `sessionid` Instagram ничего не отдаст.
4.  Загрузите файлы на сервер в папку `/root/video_loader/`.
5.  Проверьте `.env` (там уже прописаны стандартные пути).

### Способ 2: без SSH — одноразовый загрузчик
Если доступа по SSH нет, на сервере есть готовый скрипт. Он слушает один
случайный порт, требует токен в URL, принимает ровно один файл и гасит сокет:
```bash
python3 tools/cookie_upload.py
```
Скрипт напечатает готовую команду `curl` — выполните её на своей машине.

### Проверка, что куки рабочие
```bash
./venv/bin/yt-dlp --cookies cookies_inst.txt -F "https://www.instagram.com/reel/<SHORTCODE>/"
```
Если список форматов пуст, а пост точно с видео — куки не подходят.

> ⏳ **Куки протухают.** Instagram-сессия живёт несколько недель, потом
> появляется ошибка про вход. Обновляйте файл тем же способом.

## 4. Пробный запуск
Запустите бота вручную, чтобы убедиться в отсутствии ошибок:
```bash
./venv/bin/python main.py
```
Если видите `INFO:root:Starting bot...`, значит всё работает. Можно проверять в Telegram.

## 5. Верификация (Тестирование)
1.  **Start**: Отправьте боту `/start`.
2.  **YouTube**: Отправьте ссылку на видео или Shorts. Убедитесь, что видео пришло с подписью.
3.  **Instagram Reels**: Отправьте ссылку на Reels — должно прийти видео.
4.  **Instagram карусель**: Отправьте ссылку на пост из фотографий — должен прийти альбом.
    Если вместо альбома придёт «нет видео», значит куки протухли (см. п. 3).
5.  **TikTok**: Отправьте ссылку на TikTok. Проверьте отсутствие водяного знака.
6.  **Ошибки**: Пришлите заведомо приватное видео — бот должен ответить
    коротким сообщением на русском, а не сырым трейсбеком yt-dlp.
7.  **Inline**: В любом чате напишите `@BotName youtube.com/watch?v=...` и нажмите на всплывающее окно.

## 6. Настройка автозапуска (Daemon)
Чтобы бот работал постоянно и потреблял мало ресурсов:

1.  Создайте файл сервиса:
    ```bash
    nano /etc/systemd/system/videoloader.service
    ```
2.  Вставьте конфиг (замените пути, если они отличаются):
    ```ini
    [Unit]
    Description=Telegram Media Downloader Bot
    After=network.target

    [Service]
    User=root
    WorkingDirectory=/root/video_loader
    ExecStart=/root/video_loader/venv/bin/python main.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
3.  Активируйте и запустите:
    ```bash
    systemctl daemon-reload
    systemctl enable videoloader
    systemctl restart videoloader
    ```
4.  Проверка статуса и логов:
    ```bash
    systemctl status videoloader
    journalctl -u videoloader -f
    ```

## 7. Обслуживание

### Обновление yt-dlp
TikTok и Instagram ломают свои экстракторы каждые пару недель. Проверяйте версию:
```bash
pip index versions yt-dlp        # актуальная доступна
pip install -U yt-dlp
systemctl restart videoloader
```
> После обновления yt-dlp обязательно проверьте, что не сломался TikTok:
> новые версии зависят от `curl_cffi`, и без имитации TLS сервис отдаёт
> пустую заглушку вместо страницы.

### Чистка временных файлов
Бот сам удаляет временные файлы после каждой загрузки, включая неудачные
попытки. Проверить, что всё чисто:
```bash
ls downloads/
```
Должно быть пусто (при отсутствии активных загрузок).

