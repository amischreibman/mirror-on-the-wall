import os
import json
import time


class BehavioralDataSaver:
    """מחלקה לשמירת נתוני ניתוח התנהגותי"""

    def __init__(self, output_dir='data', filename='behavioral_analysis.json'):
        self.output_dir = output_dir
        self.filename = filename
        self.file_path = os.path.join(output_dir, filename)

        # יצירת תיקייה אם לא קיימת
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # משתנים לניהול סשנים
        self.current_session = None
        self.current_session_id = None
        self.frames_without_person = 0
        self.clear_threshold = 2

        # רשימת כל המשפטים הזמינים להצגה
        self.available_insights = []

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
            print(f"✅ Behavioral data saved to {self.file_path}")
        except Exception as e:
            print(f"❌ Error saving behavioral file: {e}")

    def process_behavioral_analysis(self, ai_response_json_string, detected_persons):
        """מעבד ניתוח התנהגותי"""
        print(f"\n=== BehavioralDataSaver Analysis ===")
        print(f"Detected persons: {[(pid, is_new) for pid, is_new in detected_persons]}")

        # איפוס מונה הפריימים ללא אדם
        self.frames_without_person = 0

        # ניקוי התגובה
        clean_text = self._extract_valid_json(ai_response_json_string)
        if not clean_text:
            print("❌ No valid JSON found in behavioral response")
            return

        try:
            parsed = json.loads(clean_text)

            # חילוץ הניתוחים ההתנהגותיים
            behavioral_insights = parsed.get("behavioral_analysis", [])

            if not behavioral_insights:
                print("No behavioral insights received")
                return

            print(f"Received {len(behavioral_insights)} behavioral insights")

            # אם אין סשן פעיל - צור אחד
            if self.current_session is None:
                self._create_new_behavioral_session(behavioral_insights)
            else:
                # עדכן סשן קיים
                self._update_current_behavioral_session(behavioral_insights)

            # עדכן את רשימת המשפטים הזמינים להצגה
            self._update_available_insights()

        except json.JSONDecodeError as e:
            print(f"❌ Behavioral JSON decode error: {e}")
        except Exception as e:
            print(f"❌ Error processing behavioral data: {e}")
            import traceback
            traceback.print_exc()

    def _create_new_behavioral_session(self, behavioral_insights):
        """יוצר סשן חדש לניתוח התנהגותי"""
        self.current_session_id = self._generate_next_session_id()
        self.current_session = {
            "session_id": self.current_session_id,
            "behavioral_analysis": behavioral_insights.copy(),
            "timestamp": time.time()
        }

        print(f"Created NEW behavioral session {self.current_session_id} with {len(behavioral_insights)} insights")
        self._save_new_session()

    def _update_current_behavioral_session(self, new_insights):
        """מעדכן סשן קיים עם תובנות חדשות (ללא כפילויות)"""
        print(f"Updating existing behavioral session {self.current_session_id}")

        if not self.current_session:
            return

        # הוסף תובנות חדשות למאגר (ללא כפילויות)
        existing_insights = set(self.current_session.get("behavioral_analysis", []))
        added_count = 0

        for insight in new_insights:
            # וודא שהמשפט לא קיים כבר
            if insight not in existing_insights and len(insight.strip()) > 5:
                self.current_session["behavioral_analysis"].append(insight)
                existing_insights.add(insight)
                added_count += 1

        # הגבל את מספר המשפטים ל-50 מקסימום
        if len(self.current_session["behavioral_analysis"]) > 50:
            # שמור רק את 50 האחרונים
            self.current_session["behavioral_analysis"] = self.current_session["behavioral_analysis"][-50:]
            print("Limited behavioral insights to 50 most recent")

        if added_count > 0:
            print(
                f"Added {added_count} new behavioral insights (total: {len(self.current_session['behavioral_analysis'])})")
            self._update_session_in_file()
        else:
            print("No new behavioral insights to add")

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
                print(f"Updated behavioral session {self.current_session_id} in file")
                return

        # אם לא נמצא - הוסף כחדש
        print(f"Behavioral session {self.current_session_id} not found - adding as new")
        self._save_new_session()

    def _finalize_current_session(self):
        """סוגר את הסשן הנוכחי"""
        if self.current_session:
            print(f"Finalizing behavioral session {self.current_session_id}")
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
        text = text.strip()

        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        start = text.find('{')
        end = text.rfind('}')

        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        return None

    def _update_available_insights(self):
        """מעדכן את רשימת המשפטים הזמינים להצגה"""
        data = self._load_data()
        self.available_insights = []

        # אסוף את כל המשפטים מכל הסשנים
        for session in data.get("sessions", []):
            insights = session.get("behavioral_analysis", [])
            self.available_insights.extend(insights)

        # הסר כפילויות
        self.available_insights = list(set(self.available_insights))
        print(f"Available behavioral insights: {len(self.available_insights)}")

    def get_available_insights(self):
        """מחזיר את רשימת המשפטים הזמינים להצגה"""
        return self.available_insights.copy()

    def get_file_path(self):
        """מחזיר את הנתיב לקובץ"""
        return self.file_path

    def clear_data(self):
        """מנקה את כל הנתונים"""
        self._save_data({"sessions": []})
        self.current_session = None
        self.current_session_id = None
        self.frames_without_person = 0
        self.available_insights = []
        print("All behavioral data cleared")

    def clean_duplicate_sessions(self):
        """מנקה סשנים כפולים ומאחד אותם לסשן אחד"""
        data = self._load_data()
        if not data.get("sessions"):
            return

        # אסוף את כל המשפטים מכל הסשנים
        all_insights = []
        for session in data["sessions"]:
            insights = session.get("behavioral_analysis", [])
            all_insights.extend(insights)

        # הסר כפילויות ושמור רק משפטים איכותיים
        unique_insights = []
        seen = set()
        for insight in all_insights:
            if insight not in seen and len(insight.strip()) > 5:
                unique_insights.append(insight)
                seen.add(insight)

        # צור סשן אחד מאוחד
        unified_session = {
            "session_id": "001",
            "behavioral_analysis": unique_insights[-50:],  # רק 50 האחרונים
            "timestamp": time.time()
        }

        # שמור רק את הסשן המאוחד
        cleaned_data = {"sessions": [unified_session]}
        self._save_data(cleaned_data)

        print(f"Cleaned and unified sessions into one with {len(unique_insights[-50:])} unique insights")

    def handle_empty_frame(self):
        """מטפל בפריים ללא אנשים - לא סוגר סשן מיד"""
        self.frames_without_person += 1

        # סגור סשן רק אחרי זמן ארוך יותר (10 פריימים)
        if self.frames_without_person >= 10:
            if self.current_session:
                print("No persons detected for extended time - finalizing behavioral session")
                self._finalize_current_session()

    def start_new_scene(self):
        """מתחיל סצנה חדשה - סוגר את הנוכחית ומתחיל חדשה"""
        # סגור סשן נוכחי אם קיים
        if self.current_session:
            self._finalize_current_session()

        # נקה משתנים
        self.frames_without_person = 0

        print("Starting new scene - behavioral data will refresh")