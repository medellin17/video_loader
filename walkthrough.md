# Инструкция по запуску и проверке (Walkthrough)

## 1. Установка зависимостей
```bash
cd /root/video_loader
# Создаем venv (если еще нет)
python3 -m venv venv
# Активируем
source venv/bin/activate
# Устанавливаем зависимости
pip install -r requirements.txt

# (Опционально, но рекомендуется) Установить ffmpeg
# Это позволит скачивать видео в максимальном качестве (1080p+).
# Без ffmpeg качество может быть ограничено 720p, но бот продолжит работать.
# sudo apt update && sudo apt install ffmpeg
```

## 2. Настройка
Отредактируйте файл `.env`:
```bash
nano .env
```
Вставьте ваш `BOT_TOKEN`. Поле `COOKIES_PATH` можно оставить пустым, если не используете куки.

## 3. Как получить cookies.txt (для YouTube/Instagram)
Если бот не может скачать видео (ошибка "empty file" или "sign in required"), нужны куки.
**Важно: `yt-dlp` принимает только формат Netscape (не JSON!).**

### Способ 1: Расширение "Get cookies.txt LOCALLY" (Рекомендуется)
1.  Установите расширение для Chrome/Firefox: **"Get cookies.txt LOCALLY"**.
2.  **YouTube**:
    *   Зайдите на YouTube, войдите в аккаунт.
    *   Экспорт -> Сохранить как `cookies_yt.txt`.
3.  **Instagram**:
    *   Зайдите на Instagram, войдите в аккаунт.
    *   Экспорт -> Сохранить как `cookies_inst.txt`.
4.  Загрузите файлы на сервер в папку `/root/video_loader/`.
5.  Проверьте `.env` (там уже прописаны стандартные пути).

### Способ 2: Расширение "Cookie-Editor"
То, что вы скинули (Cookie-Editor), обычно экспортирует в JSON.
1.  Если в нем есть кнопка "Export as Netscape" — используйте её.
2.  Если нет — используйте расширение из Способа 1.

## 4. Пробный запуск
Запустите бота вручную, чтобы убедиться в отсутствии ошибок:
```bash
python main.py
```
Если видите `INFO:root:Starting bot...`, значит всё работает. Можно проверять в Telegram.

## 4. Верификация (Тестирование)
1.  **Start**: Отправьте боту `/start`.
2.  **YouTube**: Отправьте ссылку на видео или Shorts. Убедитесь, что видео пришло с подписью.
3.  **Instagram**: Отправьте ссылку на Reels.
4.  **TikTok**: Отправьте ссылку на TikTok. Проверьте отсутствие водяного знака.
5.  **Inline**: В любом чате напишите `@BotName youtube.com/watch?v=...` и нажмите на всплывающее окно.

## 5. Настройка автозапуска (Daemon)
Чтобы бот работал постоянно и потреблял мало ресурсов:

1.  Отредактируйте путь в файле сервиса (если нужно). Создайте файл:
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
    systemctl start videoloader
    ```
4.  Проверка статуса:
    ```bash
    systemctl status videoloader
    ```
