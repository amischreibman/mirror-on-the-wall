import os
import json
import time
from categories import PersonCategories
class DataSaver:
    def __init__(self, output_dir='data', filename='current_mirror_state.json'):
        self.output_dir = output_dir
        self.filename = filename
        self.file_path = os.path.join(output_dir, filename)
        self.person_categories = {}  # person_id -> PersonCategories instance

        # יצירת תיקייה אם לא קיימת
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # משתנים לניהול סשנים
        self.current_session = None  # הסשן הנוכחי
        self.current_session_id = None  # מזהה הסשן הנוכחי
        self.frames_without_person = 0  # ספירת פריימים ללא אדם
        self.clear_threshold = 2  # פריימים לפני ניקוי

        # מעקב אחרי תיאורים לכל אדם
        self.person_descriptions = {}  # person_id -> set of descriptions

    def _load_data(self):
        """טוען נתונים מהקובץ או מחזיר מבנה ריק"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"sessions": []}

    def _save_data(self, data):
        """שומר נתונים לקובץ JSON"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"✅ Data saved to {self.file_path}")
        except Exception as e:
            print(f"❌ Error saving file: {e}")

    def process_multi_person_analysis(self, ai_response_json_string, detected_persons):
        """מעבד ניתוח AI עבור מספר אנשים"""
        print(f"\n=== DataSaver Multi-Person Analysis ===")
        print(f"Detected persons: {[(pid, is_new) for pid, is_new in detected_persons]}")

        # איפוס מונה הפריימים ללא אדם
        self.frames_without_person = 0

        # ניקוי התגובה מ-Gemini
        clean_text = self._extract_valid_json(ai_response_json_string)
        if not clean_text:
            print("❌ No valid JSON found in response")
            return

        try:
            # פרסור ה-JSON
            parsed = json.loads(clean_text)

            # חילוץ רשימת האנשים מהתגובה
            ai_persons = []
            if isinstance(parsed, dict):
                if "session" in parsed and isinstance(parsed["session"], list):
                    ai_persons = parsed["session"]
                elif "person_id" in parsed and "descriptions" in parsed:
                    # אדם בודד
                    ai_persons = [parsed]
            elif isinstance(parsed, list):
                ai_persons = parsed

            print(f"AI returned {len(ai_persons)} person(s)")

            # התאם בין האנשים שה-AI זיהה לאנשים שאנחנו עוקבים אחריהם
            matched_persons = self._match_ai_to_tracked(ai_persons, detected_persons)

            # בדוק אם צריך סשן חדש
            need_new_session = self._check_need_new_session(detected_persons)

            if need_new_session:
                # סגור סשן קודם אם קיים
                if self.current_session:
                    self._finalize_current_session()

                # צור סשן חדש
                self._create_new_session(matched_persons)
            else:
                # עדכן סשן קיים
                self._update_current_session(matched_persons)
                # אם אין סשן פעיל - צור אחד
                if self.current_session is None:
                    self._create_new_session(matched_persons)
                else:
                    # עדכן סשן קיים
                    self._update_current_session(matched_persons)

        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
        except Exception as e:
            print(f"❌ Error processing data: {e}")
import traceback
traceback.print_exc()

def _match_ai_to_tracked(self, ai_persons, detected_persons):
    """מתאים בין אנשים שה-AI זיהה לאנשים שאנחנו עוקבים אחריהם"""
    matched = []

    # אם יש אותו מספר אנשים, נתאים לפי סדר
    if len(ai_persons) == len(detected_persons):
        for i, ai_person in enumerate(ai_persons):
            tracked_id = detected_persons[i][0]
            is_new = detected_persons[i][1]
            descriptions = ai_person.get("descriptions", [])

            matched.append({
                "person_id": tracked_id,
                "descriptions": descriptions,
                "is_new": is_new
            })
        else:
            # אם המספרים לא תואמים, ניקח את המינימום
            print(f"Warning: AI detected {len(ai_persons)} but tracker detected {len(detected_persons)}")
            for i in range(min(len(ai_persons), len(detected_persons))):
                tracked_id = detected_persons[i][0]
                is_new = detected_persons[i][1]
                descriptions = ai_persons[i].get("descriptions", [])

                matched.append({
                    "person_id": tracked_id,
                    "descriptions": descriptions,
                    "is_new": is_new
                })

        return matched

    def _create_new_session(self, matched_persons):
        """יוצר סשן חדש עם מבנה מקוטגר"""
        self.current_session_id = self._generate_next_session_id()
        self.current_session = {
            "session_id": self.current_session_id,
            "session": []
        }

        # הוסף כל אדם לסשן
        for person_data in matched_persons:
            person_id = person_data["person_id"]
            descriptions = person_data["descriptions"]

            # אתחול קטגוריות עבור האדם
            if person_id not in self.person_categories:
                self.person_categories[person_id] = PersonCategories()

            # עיבוד לקטגוריות
            categorized_data = self.person_categories[person_id].process_person_descriptions(person_id, descriptions)
            self.person_categories[person_id].merge_with_existing_categories(person_id, categorized_data)

            self.current_session["session"].append({
                "person_id": person_id,
                "categories": self.person_categories[person_id].get_display_ready_data(person_id)
            })

        print(f"Created NEW session {self.current_session_id} with {len(matched_persons)} person(s)")
        self._save_new_session()

    def _update_current_session(self, matched_persons):
        """מעדכן סשן קיים עם תיאורים מקוטגרים"""
        print(f"Updating existing session {self.current_session_id}")

        session_updated = False

        for person_data in matched_persons:
            person_id = person_data["person_id"]
            new_descriptions = person_data["descriptions"]

            # אתחול קטגוריות עבור האדם אם לא קיים
            if person_id not in self.person_categories:
                self.person_categories[person_id] = PersonCategories()

            # עיבוד התיאורים החדשים לקטגוריות
            categorized_data = self.person_categories[person_id].process_person_descriptions(person_id,
                                                                                             new_descriptions)

            # עדכון הקטגוריות הקיימות
            updated_categories = self.person_categories[person_id].merge_with_existing_categories(person_id,
                                                                                                  categorized_data)

            # מצא את האדם בסשן הנוכחי
            person_found = False
            for person in self.current_session["session"]:
                if person["person_id"] == person_id:
                    person_found = True

                    # עדכון המבנה החדש במקום descriptions
                    person["categories"] = self.person_categories[person_id].get_display_ready_data(person_id)

                    if updated_categories:
                        print(f"  Person {person_id}: updated categories: {list(updated_categories.keys())}")
                        session_updated = True
                    else:
                        print(f"  Person {person_id}: no category updates")

                    break

            # אם האדם לא נמצא בסשן, הוסף אותו
            if not person_found:
                print(f"  Person {person_id}: NEW to session")
                self.current_session["session"].append({
                    "person_id": person_id,
                    "categories": self.person_categories[person_id].get_display_ready_data(person_id)
                })
                session_updated = True

        if session_updated:
            self._update_session_in_file()
        else:
            print("No updates needed for current session")

    def _save_new_session(self):
        """שומר סשן חדש לקובץ"""
        if not self.current_session:
            return

        data = self._load_data()
        data["sessions"].append(self.current_session.copy())
        self._save_data(data)

    def _update_session_in_file(self):
        """מעדכן סשן קיים בקובץ"""
        if not self.current_session or not self.current_session_id:
            return

        data = self._load_data()

        # מצא ועדכן את הסשן
        for i, session in enumerate(data["sessions"]):
            if session.get("session_id") == self.current_session_id:
                data["sessions"][i] = self.current_session.copy()
                self._save_data(data)
                print(f"Updated session {self.current_session_id} in file")
                return

        # אם לא נמצא - הוסף כחדש
        print(f"Session {self.current_session_id} not found - adding as new")
        self._save_new_session()

    def _finalize_current_session(self):
        """סוגר את הסשן הנוכחי"""
        if self.current_session:
            print(f"Finalizing session {self.current_session_id}")
            self._update_session_in_file()
            self.current_session = None
            self.current_session_id = None

    def _generate_next_session_id(self):
        """מייצר מזהה סשן חדש"""
        data = self._load_data()
        existing_ids = []

        for session in data.get("sessions", []):
            session_id = session.get("session_id", "000")
            try:
                existing_ids.append(int(session_id))
            except ValueError:
                continue

        next_id = max(existing_ids, default=0) + 1
        return f"{next_id:03d}"

    def _extract_valid_json(self, text):
        """מחלץ JSON תקין מהטקסט"""
        # הסרת רווחים מיותרים
        text = text.strip()

        # הסרת עטיפת markdown אם קיימת
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        # חיפוש אובייקט JSON (מתחיל ב-{ ונגמר ב-})
        start = text.find('{')
        end = text.rfind('}')

        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        # חיפוש מערך JSON
        start = text.find('[')
        end = text.rfind(']')

        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        return None

    def get_file_path(self):
        """מחזיר את הנתיב לקובץ"""
        return self.file_path


def handle_empty_frame(self):
    """מטפל בפריים ללא אנשים - לא סוגר סשן מיד"""
    self.frames_without_person += 1

    # סגור סשן רק אחרי זמן ארוך יותר (10 פריימים)
    if self.frames_without_person >= 10:
        if self.current_session:
            print("No persons detected for extended time - finalizing session")
            self._finalize_current_session()

def get_file_path(self):
    """מחזיר את הנתיב לקובץ"""
    return self.file_path

def clear_data(self):
    """מנקה את כל הנתונים"""
    self._save_data({"sessions": []})
    self.current_session = None
    self.current_session_id = None
    self.frames_without_person = 0
    self.person_descriptions.clear()
    print("All data cleared")