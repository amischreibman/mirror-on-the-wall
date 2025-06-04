import os  # ייבוא מודול לגישה למערכת הקבצים
import json  # ייבוא מודול לעבודה עם פורמט JSON
from datetime import datetime  # ייבוא לטיפול בתאריך ושעה


class DataSaver:  # הגדרת מחלקה לשמירת נתונים
    def __init__(self, output_dir='data', filename='current_mirror_state.json'):  # פונקציית אתחול
        self.output_dir = output_dir  # תיקיית פלט
        self.file_path = os.path.join(self.output_dir, filename)  # נתיב מלא לקובץ JSON
        self._ensure_output_directory_exists()  # וודא שתיקיית הפלט קיימת
        self._initialize_json_file()  # אתחול/טעינת קובץ JSON
        self.accumulated_data = {}  # מילון לצבירת כל הנתונים
        self.frames_without_person = 0  # ספירת פריימים ללא אדם
        self.clear_threshold = 5  # כמה פריימים ללא אדם לפני מחיקה

    def _ensure_output_directory_exists(self):  # פונקציה פרטית לוודא קיום תיקייה
        if not os.path.exists(self.output_dir):  # בדיקה אם התיקייה לא קיימת
            os.makedirs(self.output_dir)  # יצירת התיקייה
            print(f"Created output directory: {self.output_dir}")  # הדפסת הודעה

    def _initialize_json_file(self):  # פונקציה פרטית לאתחול/טעינת קובץ JSON
        if not os.path.exists(self.file_path):  # אם הקובץ לא קיים
            initial_data = {  # מבנה הנתונים הראשוני
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # חותמת זמן עדכון אחרון
                "people": []  # רשימה ריקה של אנשים
            }
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:  # פתיחת קובץ לכתיבה
                    json.dump(initial_data, f, indent=4, ensure_ascii=False)  # כתיבת נתונים ראשוניים
                print(f"Initialized new JSON state file: {self.file_path}")  # הודעת אתחול
            except IOError as e:  # טיפול בשגיאות קובץ
                print(f"Error initializing JSON file {self.file_path}: {e}")  # הדפסת שגיאה
        else:
            print(f"Using existing JSON state file: {self.file_path}")  # הודעה על שימוש בקובץ קיים

    def _load_current_state(self):  # פונקציה פרטית לטעינת המצב הנוכחי מהקובץ
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:  # פתיחת קובץ לקריאה
                return json.load(f)  # טעינת הנתונים
        except (IOError, json.JSONDecodeError) as e:  # טיפול בשגיאות קובץ או JSON
            print(f"Error loading current state from {self.file_path}: {e}")  # הדפסת שגיאה
            return {"last_updated": "", "people": []}  # החזרת מבנה ריק במקרה שגיאה

    def _save_current_state(self, data):  # פונקציה פרטית לשמירת המצב המעודכן
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:  # פתיחת קובץ לכתיבה
                json.dump(data, f, indent=4, ensure_ascii=False)  # כתיבת הנתונים
        except IOError as e:  # טיפול בשגיאות קובץ
            print(f"Error saving current state to {self.file_path}: {e}")  # הדפסת שגיאה

    def add_analysis_result(self, ai_response_json_string):  # פונקציה לעדכון מצב הניתוח
        if not ai_response_json_string:  # בדיקה אם אין תשובה
            print("No AI data to process.")  # הודעה
            return  # יציאה

        try:
            newly_detected_people = json.loads(ai_response_json_string)  # טעינת הנתונים החדשים מה-AI
        except json.JSONDecodeError as e:  # טיפול בשגיאת JSON
            print(f"Error decoding AI response JSON: {e}")  # הדפסת שגיאה
            return  # יציאה

        current_state = self._load_current_state()  # טעינת המצב הקיים מהקובץ

        # אם זוהו אנשים
        if len(newly_detected_people) > 0:
            self.frames_without_person = 0  # איפוס ספירת פריימים ללא אדם

            # צבור את כל הנתונים מכל האנשים שזוהו
            for person_data in newly_detected_people:
                for key, value in person_data.items():
                    # סנן ערכים שאינם רצויים
                    value_str = str(value).strip().lower()
                    if not value_str or value_str in ['no', 'none', 'not visible', 'n/a']:
                        continue  # דלג על ערכים ריקים או שליליים

                    if key not in self.accumulated_data:
                        # שדה חדש - פשוט הוסף
                        self.accumulated_data[key] = value
                        print(f"Added new field: {key} = {value}")
                    elif key in ["jewelry", "held_objects", "accessories"]:
                        # שדות מצטברים - בדוק אם הפריט כבר קיים
                        existing_items = set(item.strip().lower() for item in self.accumulated_data[key].split(","))
                        new_items = set(item.strip().lower() for item in str(value).split(","))

                        # בדוק אם יש פריטים באמת חדשים (שלא קיימים כבר)
                        really_new_items = new_items - existing_items
                        if really_new_items:
                            # הוסף רק את הפריטים החדשים
                            all_items = [item.strip() for item in self.accumulated_data[key].split(",")]
                            for new_item in str(value).split(","):
                                if new_item.strip().lower() not in existing_items:
                                    all_items.append(new_item.strip())
                            self.accumulated_data[key] = ", ".join(all_items)
                            print(f"Added new items to {key}: {', '.join(really_new_items)}")
                    elif key in ["upper_garment_color", "lower_garment_color", "footwear_color", "hair_color",
                                 "eye_color"]:
                        # עבור צבעים ותיאורים - אפשר לעדכן אם יש תיאור מדויק יותר
                        old_value = self.accumulated_data[key].lower()
                        new_value = str(value).lower()
                        # עדכן רק אם הערך החדש מכיל יותר מידע
                        if len(new_value) > len(old_value) or (new_value != old_value and "with" in new_value):
                            self.accumulated_data[key] = value
                            print(f"Updated {key}: {old_value} -> {value}")
                    # אחרת - שמור את הערך הקיים (לא מעדכן)

            # שמור את הנתונים המצטברים
            current_state["people"] = [self.accumulated_data] if self.accumulated_data else []
            print(f"Total accumulated fields: {len(self.accumulated_data)}")

        else:
            # אם לא זוהו אנשים
            self.frames_without_person += 1
            print(f"No people detected. Frames without person: {self.frames_without_person}/{self.clear_threshold}")

            if self.frames_without_person >= self.clear_threshold:
                # נקה את הנתונים
                if self.accumulated_data:
                    print("Person left frame. Clearing all accumulated data.")
                    self.accumulated_data = {}
                current_state["people"] = []
            else:
                # שמור את הנתונים הקיימים
                current_state["people"] = [self.accumulated_data] if self.accumulated_data else []

        # עדכון זמן ושמירה
        current_state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_current_state(current_state)

    def get_file_path(self):  # פונקציה להחזרת נתיב קובץ ה-JSON
        return self.file_path  # החזרת הנתיב המלא לקובץ JSON