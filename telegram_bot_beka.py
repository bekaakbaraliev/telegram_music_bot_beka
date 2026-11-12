import os
import asyncio
import tempfile
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp
import imageio_ffmpeg

# --- НАСТРОЙКИ ---
TOKEN = "8689339887:AAGoYXdeU3QyY2xLHc2vvBntyJGLRm4OCsM"
PORT = int(os.environ.get("PORT", 8080))

# Путь к ffmpeg через imageio-ffmpeg
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

# --- FLASK СЕРВЕР ДЛЯ UPTIME (24/7 на Render) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- TELEGRAM БОТ ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! 🎵 Отправь мне ссылку на видео с YouTube, и я скачаю его для тебя в формате MP3."
    )

@dp.message()
async def download_audio(message: types.Message):
    url = message.text.strip()
    
    if not url.startswith("http"):
        await message.answer("Пожалуйста, отправьте корректную ссылку на YouTube.")
        return

    status_msg = await message.answer("⏳ Скачиваю и конвертирую трек...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Настройки yt-dlp с усиленным обходом блокировок
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
            'restrictfilenames': True,
            'ffmpeg_location': ffmpeg_path,
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player-client': ['android', 'web']
                }
            }
        }

        try:
            loop = asyncio.get_running_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return os.path.splitext(filename)[0] + ".mp3", info.get('title', 'audio')

            mp3_path, title = await loop.run_in_executor(None, extract)

            if os.path.exists(mp3_path):
                audio_file = types.FSInputFile(mp3_path)
                await message.answer_audio(audio=audio_file, caption=f"🎧 {title}")
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ Не удалось найти готовый файл.")

        except Exception as e:
            error_text = str(e)
            print(f"Ошибка: {error_text}")
            # Бот выведет точный текст ошибки в Telegram, чтобы мы поняли причину
            await status_msg.edit_text(f"❌ Ошибка загрузки:\n<code>{error_text[:300]}</code>", parse_mode="HTML")

async def main():
    keep_alive()
    print("Бот успешно запущен и ждет сообщения...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
