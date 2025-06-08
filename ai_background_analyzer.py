import threading  # ייבוא מודול לריבוי תהליכונים
import queue  # ייבוא מודול לתורים בטוחים לשימוש בתהליכונים
import time  # ייבוא מודול לטיפול בזמן (לצורך השהייה)
from ai_agent import AIAgent  # ייבוא מחלקת AIAgent
from data_saver import DataSaver  # ייבוא מחלקת DataSaver
from face_detector import FaceDetector  # ייבוא מחלקת זיהוי פנים
from person_tracker import PersonTracker  # ייבוא מחלקת מעקב אנשים


class AIBackgroundAnalyzer(threading.Thread):  # הגדרת מחלקה כיורשת Thread
    def __init__(self, frame_queue, data_saver, interval_seconds=0.5):  # פונקציית אתחול
        super().__init__()  # קריאה לפונקציית האתחול של מחלקת האב (Thread)
        self.frame_queue = frame_queue  # תור לקבלת פריימים
        self.data_saver = data_saver  # אובייקט לשמירת נתונים
        self.ai_agent = AIAgent()  # אתחול סוכן AI
        self.face_detector = FaceDetector()  # אתחול זיהוי פנים מקומי
        self.person_tracker = PersonTracker()  # אתחול מעקב אנשים
        self.interval_seconds = interval_seconds  # מרווח בין ניתוחים
        self.running = True  # דגל לשליטה על ריצת התהליכון
        self.daemon = True  # הגדרת התהליכון כ-daemon
        self.frames_processed = 0  # מונה פריימים שעובדו
        self.frames_with_faces = 0  # מונה פריימים עם פנים

    def run(self):  # הפונקציה שתרוץ בתהליכון הנפרד
        print("AI background analyzer with multi-person tracking started.")  # הודעת התחלה
        while self.running:  # לולאת ריצה כל עוד התהליכון פעיל
            try:
                # מנסה לקחת פריים מהתור בלי לחכות לנצח, עם timeout קצר
                frame = self.frame_queue.get(timeout=0.1)  # קבלת פריים מהתור
                if frame is not None:  # בדיקה אם התקבל פריים תקין
                    self.frames_processed += 1

                    # זיהוי כל האנשים בפריים
                    detected_persons = self.person_tracker.detect_persons(frame)

                    if not detected_persons:
                        # אין אנשים בפריים
                        print("No persons detected in frame")
                        self.data_saver.handle_empty_frame()
                    else:
                        self.frames_with_faces += 1
                        print(f"{len(detected_persons)} person(s) in frame")

                        # שלח ל-AI לניתוח
                        ai_response_json_string = self.ai_agent.analyze_frame(frame)

                        if ai_response_json_string:  # אם התקבלה תשובה
                            print("AI analysis received. Processing with multi-person tracking...")
                            # העבר את רשימת האנשים שזוהו ל-data_saver
                            self.data_saver.process_multi_person_analysis(
                                ai_response_json_string,
                                detected_persons
                            )
                        else:
                            print("AI analysis failed or returned no data.")

                    # סטטיסטיקות דיבאג
                    if self.frames_processed % 20 == 0 and self.frames_processed > 0:
                        face_ratio = (self.frames_with_faces / self.frames_processed) * 100
                        active_persons = self.person_tracker.get_active_persons()
                        print(
                            f"\nStats: {self.frames_with_faces}/{self.frames_processed} frames with faces ({face_ratio:.1f}%)")
                        print(f"Active persons: {active_persons}")

                self.frame_queue.task_done()  # סימון שהמשימה בוצעה בתור

            except queue.Empty:  # אם התור ריק
                pass  # לא עושה כלום, ממשיך הלאה
            except Exception as e:  # טיפול בשגיאות כלליות בתהליכון
                print(f"Error in AI background analyzer: {e}")  # הדפסת שגיאה
                import traceback
                traceback.print_exc()

            time.sleep(self.interval_seconds)  # המתנה לפני ניתוח נוסף

        print("AI background analyzer stopped.")  # הודעת סיום

    def stop(self):  # פונקציה לעצירת התהליכון
        self.running = False  # שינוי דגל העצירה