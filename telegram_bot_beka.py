import os
import tempfile
import asyncio
from threading import Thread
from flask import Flask
import imageio_ffmpeg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from yt_dlp import YoutubeDL

# ==========================================
# ТОКЕН БОТА (уже вставлен ваш)
# ==========================================
TOKEN = "8689339887:AAGoYXdeU3QyY2xLHc2vvBntyJGLRm4OCsM"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================================
# ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖАНИЯ РАБОТЫ 24/7
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Telegram Music Bot is active and running 24/7! 🚀"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==========================================
# КОМАНДЫ И ОБРАБОТЧИКИ БОТА
# ==========================================
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! Я твой личный музыкальный бот без рекламы.\n\n"
        "Отправь мне ссылку на YouTube-видео или трек, и я пришлю тебе MP3!"
    )

@dp.message()
async def download_music(message: types.Message):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("⚠️ Пожалуйста, отправь корректную ссылку на YouTube (начинающуюся с http).")
        return

    processing_msg = await message.answer("⏳ Скачиваю и конвертирую музыку, подожди пару секунд...")

    temp_dir = tempfile.gettempdir()
    
    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        await message.answer(f"❌ Ошибка инициализации FFmpeg: {str(e)}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass
        return

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
    }

    mp3_filename = None
    try:
        # Скачивание и конвертация
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"
            title = info.get('title', 'Audio')

        if not os.path.exists(mp3_filename):
            raise FileNotFoundError("Не удалось найти сгенерированный MP3 файл после конвертации.")

        # Отправка файла пользователю
        audio = types.FSInputFile(mp3_filename)
        await message.answer_audio(
            audio=audio, 
            caption=f"🎵 {title}\n✨ Скачано через твоего личного бота"
        )
        
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при скачивании:\n`{str(e)}`", parse_mode="Markdown")
        
    finally:
        # Удаление временного файла в любом случае (даже при ошибке)
        if mp3_filename and os.path.exists(mp3_filename):
            try:
                os.remove(mp3_filename)
            except:
                pass
                
        # Удаление служебного сообщения о загрузке
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass

async def main():
    keep_alive()
    print("Бот успешно запущен и ждет сообщения...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")