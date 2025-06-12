import time
import json
import os


class SceneManager:
    """מחלקה לניהול סצנות"""

    def __init__(self, scenes_file='data/scenes.json'):
        self.scenes_file = scenes_file
        self.current_scene_id = None
        self.scene_start_time = None
        self.ensure_scenes_file()

    def ensure_scenes_file(self):
        """יוצר קובץ סצנות אם לא קיים"""
        os.makedirs(os.path.dirname(self.scenes_file), exist_ok=True)
        if not os.path.exists(self.scenes_file):
            self._save_scenes_data({"scenes": [], "current_scene": None})

    def _load_scenes_data(self):
        """טוען נתוני סצנות"""
        try:
            with open(self.scenes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"scenes": [], "current_scene": None}

    def _save_scenes_data(self, data):
        """שומר נתוני סצנות"""
        try:
            with open(self.scenes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving scenes data: {e}")

    def start_new_scene(self):
        """מתחיל סצנה חדשה"""
        # סיים את הסצנה הקודמת אם קיימת
        if self.current_scene_id:
            self.end_current_scene()

        # צור סצנה חדשה
        data = self._load_scenes_data()

        # מצא מספר סצנה חדש
        existing_scene_numbers = []
        for scene in data.get("scenes", []):
            try:
                scene_num = int(scene.get("scene_id", "0"))
                existing_scene_numbers.append(scene_num)
            except ValueError:
                continue

        new_scene_number = max(existing_scene_numbers, default=0) + 1
        self.current_scene_id = f"{new_scene_number:03d}"
        self.scene_start_time = time.time()

        # שמור את הסצנה החדשה
        new_scene = {
            "scene_id": self.current_scene_id,
            "start_time": self.scene_start_time,
            "end_time": None,
            "duration": None
        }

        data["scenes"].append(new_scene)
        data["current_scene"] = self.current_scene_id
        self._save_scenes_data(data)

        print(f"🎬 Started new scene: {self.current_scene_id}")
        return self.current_scene_id

    def end_current_scene(self):
        """מסיים את הסצנה הנוכחית"""
        if not self.current_scene_id:
            return

        end_time = time.time()
        duration = end_time - self.scene_start_time if self.scene_start_time else 0

        data = self._load_scenes_data()

        # עדכן את הסצנה הנוכחית
        for scene in data["scenes"]:
            if scene.get("scene_id") == self.current_scene_id:
                scene["end_time"] = end_time
                scene["duration"] = duration
                break

        data["current_scene"] = None
        self._save_scenes_data(data)

        print(f"🎬 Ended scene {self.current_scene_id} after {duration:.1f} seconds")

        self.current_scene_id = None
        self.scene_start_time = None

    def get_current_scene_info(self):
        """מחזיר מידע על הסצנה הנוכחית"""
        if not self.current_scene_id or not self.scene_start_time:
            return None

        elapsed = time.time() - self.scene_start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        return {
            "scene_id": self.current_scene_id,
            "elapsed_time": elapsed,
            "elapsed_formatted": f"{minutes:02d}:{seconds:02d}",
            "start_time": self.scene_start_time
        }

    def clear_all_scenes(self):
        """מנקה את כל הסצנות"""
        self.end_current_scene()
        self._save_scenes_data({"scenes": [], "current_scene": None})
        print("🧹 Cleared all scenes")

    def get_scenes_summary(self):
        """מחזיר סיכום של כל הסצנות"""
        data = self._load_scenes_data()
        return data.get("scenes", [])