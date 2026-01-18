import os
import re
import json
import requests
from urllib.parse import quote
from dotenv import load_dotenv


class CatUploader:
    def __init__(self, env_path=".env"):
        load_dotenv(env_path)
        self.yandex_token = os.getenv("YANDEX_DISK_TOKEN")
        self.group_name = os.getenv("GROUP_NAME", "PD-142")
        self.json_file = "upload_info.json"

        if not self.yandex_token:
            raise EnvironmentError("Переменная YANDEX_DISK_TOKEN не задана в .env!")

    def _sanitize_filename(self, text: str) -> str:
        """Converts text"""
        safe = re.sub(r'[^\w\-]', '_', text)
        safe = re.sub(r'_+', '_', safe).strip('_')
        return safe or "cat"

    def _get_cat_image(self, text: str) -> bytes:
        """Getting the image"""
        encoded_text = quote(text)
        url = f"https://cataas.com/cat/cute/says/{encoded_text}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Ошибка при получении изображения: {response.status_code} — {response.text}")
        return response.content

    def _save_locally(self, content: bytes, filename: str) -> str:
        """Saving the image"""
        os.makedirs(self.group_name, exist_ok=True)
        local_path = os.path.join(self.group_name, filename)
        with open(local_path, 'wb') as f:
            f.write(content)
        return local_path

    def _upload_to_yandex_disk(self, local_path: str, remote_path: str):
        """Uploading the file to YandexDisk"""
        headers = {"Authorization": f"OAuth {self.yandex_token}"}
        upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        params = {"path": remote_path, "overwrite": "true"}

        resp = requests.get(upload_url, headers=headers, params=params)
        if resp.status_code != 200:
            raise Exception(f"Не удалось получить ссылку для загрузки: {resp.json()}")

        upload_link = resp.json()["href"]

        with open(local_path, 'rb') as f:
            upload_resp = requests.put(upload_link, files={"file": f})
        if upload_resp.status_code not in (200, 201, 202):
            raise Exception(f"Ошибка загрузки: {upload_resp.text}")

    def _update_json_log(self, info: dict):
        """Updating JSON-file"""
        data = []
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []

        data.append(info)
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def upload_cat_with_text(self, text: str):
        """Upload"""
        if not text.strip():
            raise ValueError("Текст не может быть пустым!")

        text = text.strip()
        filename = f"{self._sanitize_filename(text)}.jpg"
        remote_path = f"{self.group_name}/{filename}"

        print("Получаем изображение с cataas.com...")
        image_bytes = self._get_cat_image(text)

        print("Сохраняем локально...")
        local_path = self._save_locally(image_bytes, filename)
        file_size = os.path.getsize(local_path)

        print("Загружаем на Яндекс.Диск...")
        self._upload_to_yandex_disk(local_path, remote_path)

        info = {
            "text_on_image": text,
            "filename": filename,
            "group_folder": self.group_name,
            "file_size_bytes": file_size,
            "yandex_disk_path": remote_path
        }

        self._update_json_log(info)

        print(f"Успешно! Файл: /{remote_path} ({file_size} байт)")
        print(f"Информация сохранена в {self.json_file}")


# if__name == "__main__"
if __name__ == "__main__":
    uploader = CatUploader()
    text = input("Введите текст для картинки: ")
    uploader.upload_cat_with_text(text)