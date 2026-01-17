"""
Video Upload Service - загрузка видео из Telegram на Google Drive
"""
import asyncio
import os
import tempfile
from typing import Optional
from aiogram import Bot
from app.infrastructure.google.drive_manager import GoogleDriveManager

class VideoUploadService:
    def __init__(self, drive_manager: GoogleDriveManager, folder_id: str):
        self.drive_manager = drive_manager
        self.folder_id = folder_id
    
    async def upload_telegram_video(self, bot: Bot, file_id: str, new_filename: str = None) -> Optional[str]:
        """
        Скачивает видео из Telegram и загружает на Google Drive
        
        Returns:
            Google Drive link или None при ошибке
        """
        temp_file = None
        try:
            # Generate default filename if none provided (backward compat)
            # But caller should provide meaningful name now.
            if not new_filename:
                # Fallback to old simple ID based name if forgot
                # But better to enforce passing it.
                # Let's generate simple one just in case.
                new_filename = f"video_{file_id[:10]}.mp4"
            
            # Ensure extension
            if not new_filename.lower().endswith(('.mp4', '.mov')):
                new_filename += ".mp4"
                
            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_path = temp_file.name
            temp_file.close()
            
            print(f"📥 Downloading video {file_id[:20]}... to {temp_path}")
            
            # Скачиваем из Telegram
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, temp_path)
            
            print(f"📤 Uploading to Drive...")
            
            # Загружаем на Drive в отдельном потоке (blocking operation)
            loop = asyncio.get_running_loop()
            drive_link = await loop.run_in_executor(
                None,
                lambda: self.drive_manager.upload_file(
                    temp_path,
                    self.folder_id,
                    new_filename
                )
            )
            
            if drive_link:
                print(f"✅ Video uploaded: {drive_link}")
            else:
                print(f"❌ Upload failed")
            
            return drive_link
            
        except Exception as e:
            print(f"❌ Video upload error: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Удаляем временный файл
            if temp_file and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
