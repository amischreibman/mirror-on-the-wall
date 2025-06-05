import cv2  # ייבוא ספריית OpenCV לתצוגה וציור
from screeninfo import get_monitors  # ייבוא פונקציה למידע על מסכים
import numpy as np  # ייבוא ספריית NumPy ליצירת תמונות (רקעים)
import json  # ייבוא מודול לעבודה עם פורמט JSON
import os  # ייבוא מודול לגישה למערכת הקבצים
from datetime import datetime  # לדיבאג


class DisplayManager:  # הגדרת מחלקה לניהול תצוגה
    def __init__(self, window_name='Mirror on the Wall'):  # פונקציית אתחול למחלקה
        self.window_name = window_name  # שמירת שם החלון
        self.screen_width = 0  # אתחול רוחב מסך
        self.screen_height = 0  # אתחול גובה מסך
        self._setup_screen_dimensions()  # קריאה לפונקציה לקבלת מימדי מסך
        self.show_json_overlay = False  # דגל לשליטה על הצגת שכבת הנתונים
        self.last_json_data = None  # שמירת נתונים אחרונים לדיבאג
        self.frame_count = 0  # מונה פריימים

    def _setup_screen_dimensions(self):  # פונקציה פרטית לקבלת מימדי מסך
        monitor = get_monitors()[0]  # קבלת פרטי המסך הראשי
        self.screen_width = monitor.width  # רוחב המסך
        self.screen_height = monitor.height  # גובה המסך

    def setup_window(self):  # פונקציה להגדרת חלון התצוגה
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)  # יצירת חלון רגיל
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)  # הגדרת מסך מלא

    def toggle_json_overlay(self):  # פונקציה להחלפת מצב הצגת הנתונים
        self.show_json_overlay = not self.show_json_overlay  # היפוך הדגל
        print(f"JSON overlay toggled: {'ON' if self.show_json_overlay else 'OFF'}")

    def show_frame(self, frame, json_data_path):  # פונקציה להצגת פריים עם נתוני JSON
        self.frame_count += 1
        frame_height, frame_width, _ = frame.shape  # קבלת מימדי פריים
        frame = cv2.flip(frame, 1)  # הפיכת הפריים לראי (שיקוף אופקי)

        aspect_ratio_frame = frame_width / frame_height  # יחס רוחב/גובה של הפריים
        aspect_ratio_screen = self.screen_width / self.screen_height  # יחס רוחב/גובה של המסך

        if aspect_ratio_frame > aspect_ratio_screen:  # אם הפריים רחב יותר מהמסך יחסית
            new_width = self.screen_width  # רוחב חדש הוא רוחב המסך
            new_height = int(new_width / aspect_ratio_frame)  # גובה חדש מחושב לפי יחס
        else:  # אם הפריים גבוה יותר מהמסך יחסית
            new_height = self.screen_height  # גובה חדש הוא גובה המסך
            new_width = int(new_height * aspect_ratio_frame)  # רוחב חדש מחושב לפי יחס

        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)  # שינוי גודל הפריים

        full_screen_frame = np.zeros((self.screen_height, self.screen_width, 3),
                                     dtype=np.uint8)  # יצירת רקע שחור עם NumPy

        x_offset = (self.screen_width - new_width) // 2  # היסט X לריכוז
        y_offset = (self.screen_height - new_height) // 2  # היסט Y לריכוז

        full_screen_frame[y_offset:y_offset + new_height,
        x_offset:x_offset + new_width] = resized_frame  # הצבת פריים במרכז

        # --- הוספת שכבת נתוני JSON אם הדגל פעיל ---
        if self.show_json_overlay:  # בדיקה אם להציג שכבת נתונים
            overlay_width = self.screen_width // 3  # רוחב הקונטיינר (שליש מסך)
            overlay_height = self.screen_height  # גובה הקונטיינר (כל גובה המסך)

            # יצירת מלבן שחור עבור הקונטיינר השמאלי
            cv2.rectangle(full_screen_frame, (0, 0), (overlay_width, overlay_height), (0, 0, 0),
                          -1)  # ציור מלבן שחור מלא

            # קריאת נתוני ה-JSON העדכניים בכל פריים!
            data_lines = []  # רשימה לאחסון שורות הטקסט להצגה
            if os.path.exists(json_data_path):  # בדיקה אם קובץ ה-JSON קיים
                try:
                    with open(json_data_path, 'r', encoding='utf-8') as f:  # פתיחת קובץ לקריאה
                        json_data = json.load(f)  # טעינת הנתונים

                        # דיבאג - בדיקה אם הנתונים השתנו
                        if self.frame_count % 30 == 0:  # כל 30 פריימים
                            print(f"\nDisplay Frame #{self.frame_count}")
                            if json_data != self.last_json_data:
                                print("JSON data has changed!")
                                self.last_json_data = json_data.copy()
                            else:
                                print("JSON data unchanged")

                        # הוספת timestamp לתצוגה
                        if "last_updated" in json_data:
                            data_lines.append(f"Updated: {json_data['last_updated']}")
                            data_lines.append("-" * 30)

                        if "people" in json_data and isinstance(json_data["people"], list):  # בדיקה למבנה נתונים תקין
                            if len(json_data["people"]) == 0:
                                data_lines.append("No people detected")
                            else:
                                for person_data in json_data["people"]:  # לולאה על כל אדם שזוהה
                                    person_id = person_data.get("person_id", "unknown")
                                    descriptions = person_data.get("descriptions", [])

                                    # כותרת לכל אדם
                                    data_lines.append(f"Person number {person_id}")
                                    data_lines.append("-" * 20)

                                    # הוספת כל ה-descriptions
                                    if descriptions:
                                        for description in descriptions:
                                            data_lines.append(description)
                                    else:
                                        data_lines.append("No descriptions available")

                                    data_lines.append("")  # רווח בין אנשים
                        else:
                            data_lines.append("No people data available")
                except (IOError, json.JSONDecodeError) as e:  # טיפול בשגיאות
                    data_lines.append(f"Error reading JSON: {e}")  # הודעת שגיאה
            else:
                data_lines.append("JSON file not found")

            # הצגת הטקסט
            y_pos = 30  # מיקום התחלתי לציר ה-Y
            line_height = 25  # גובה שורה
            font_scale = 0.6  # גודל פונט
            font_thickness = 1  # עובי פונט
            font_color = (0, 255, 0)  # צבע ירוק בהיר (BGR)
            header_color = (0, 255, 255)  # צבע צהוב לכותרות אנשים
            margin_right = 20  # מרחק מהקצה הימני

            for line in data_lines:  # לולאה על כל שורה בנתונים
                # וודא שהטקסט לא חורג מגבולות הקונטיינר
                if y_pos > overlay_height - line_height:  # בדיקה אם חורג מהגובה
                    # הוסף אינדיקציה שיש עוד נתונים
                    cv2.putText(full_screen_frame, "... more data ...", (10, overlay_height - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_color, font_thickness, cv2.LINE_AA)
                    break  # יציאה מהלולאה אם אין מקום

                # בחירת צבע לפי סוג השורה
                color = font_color
                if line.startswith("Person number"):
                    color = header_color

                # בדוק אם השורה ארוכה מדי ופצל אותה אם צריך
                max_width = overlay_width - margin_right - 10  # רוחב מקסימלי לטקסט
                (text_width, text_height), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                                                               font_thickness)

                # אם הטקסט ארוך מדי, חתוך אותו
                if text_width > max_width and len(line) > 10:
                    # חשב כמה תווים נכנסים
                    chars_per_width = len(line) / text_width
                    max_chars = int(max_width * chars_per_width * 0.9)  # רצון בטחון
                    display_text = line[:max_chars] + "..." if len(line) > max_chars else line
                else:
                    display_text = line

                cv2.putText(full_screen_frame, display_text, (10, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness, cv2.LINE_AA)
                y_pos += line_height

        # --- סוף הוספת שכבת נתוני JSON ---

        cv2.imshow(self.window_name, full_screen_frame)  # הצגת הפריים המלא בחלון

    def cleanup(self):  # פונקציה לניקוי משאבי תצוגה
        cv2.destroyAllWindows()  # סגירת כל חלונות OpenCV