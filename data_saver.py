import os  # ייבוא מודול לגישה למערכת הקבצים
import json  # ייבוא מודול לעבודה עם פורמט JSON
from datetime import datetime  # ייבוא לטיפול בתאריך ושעה


class DataSaver:  # הגדרת מחלקה לשמירת נתונים
    def __init__(self, output_dir='data', filename='current_mirror_state.json'):  # פונקציית אתחול
        self.output_dir = output_dir  # תיקיית פלט
        self.file_path = os.path.join(self.output_dir, filename)  # נתיב מלא לקובץ JSON
        self._ensure_output_directory_exists()  # וודא שתיקיית הפלט קיימת
        self._initialize_json_file()  # אתחול/טעינת קובץ JSON
        self.accumulated_data = {}  # מילון לצבירת נתונים לפי person_id

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
            session_data = json.loads(ai_response_json_string)  # טעינת הנתונים החדשים מה-AI
        except json.JSONDecodeError as e:  # טיפול בשגיאת JSON
            print(f"Error decoding AI response JSON: {e}")  # הדפסת שגיאה
            return  # יציאה

        current_state = self._load_current_state()  # טעינת המצב הקיים מהקובץ

        # אם יש session עם נתונים
        if session_data and "session" in session_data and len(session_data["session"]) > 0:
            self.frames_without_person = 0  # איפוס ספירת פריימים ללא אדם

            # עבור כל אדם בsession
            for person_data in session_data["session"]:
                person_id = str(person_data.get("person_id", "unknown"))
                descriptions = person_data.get("descriptions", [])

                # אם זה אדם חדש, צור entry חדש
                if person_id not in self.accumulated_data:
                    self.accumulated_data[person_id] = {
                        "person_id": person_id,
                        "descriptions": []
                    }
                    print(f"New person detected: {person_id}")

                # הוסף descriptions חדשים (רק אם הם לא קיימים כבר)
                existing_descriptions = set(self.accumulated_data[person_id]["descriptions"])
                new_descriptions_added = 0

                for description in descriptions:
                    if description and description not in existing_descriptions:
                        self.accumulated_data[person_id]["descriptions"].append(description)
                        existing_descriptions.add(description)
                        new_descriptions_added += 1

                if new_descriptions_added > 0:
                    print(f"Added {new_descriptions_added} new descriptions for person {person_id}")
                    print(f"Total descriptions for person {person_id}: {len(self.accumulated_data[person_id]['descriptions'])}")

            # עדכן את current_state עם הנתונים המצטברים
            current_state["people"] = list(self.accumulated_data.values())
            print(f"Total people tracked: {len(self.accumulated_data)}")

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
                current_state["people"] = list(self.accumulated_data.values())

        # עדכון זמן ושמירה
        current_state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_current_state(current_state)

    def get_file_path(self):  # פונקציה להחזרת נתיב קובץ ה-JSON
        return self.file_path  # החזרת הנתיב המלא לקובץ JSON