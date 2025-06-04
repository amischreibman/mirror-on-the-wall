import threading # ייבוא מודול לריבוי תהליכונים
import queue # ייבוא מודול לתורים בטוחים לשימוש בתהליכונים
import time # ייבוא מודול לטיפול בזמן (לצורך השהייה)
from ai_agent import AIAgent # ייבוא מחלקת AIAgent
from data_saver import DataSaver # ייבוא מחלקת DataSaver

class AIBackgroundAnalyzer(threading.Thread): # הגדרת מחלקה כיורשת Thread
    def __init__(self, frame_queue, data_saver, interval_seconds=0.5): # פונקציית אתחול (שונתה)
        super().__init__() # קריאה לפונקציית האתחול של מחלקת האב (Thread)
        self.frame_queue = frame_queue # תור לקבלת פריימים
        self.data_saver = data_saver # אובייקט לשמירת נתונים
        self.ai_agent = AIAgent() # אתחול סוכן AI
        self.interval_seconds = interval_seconds # מרווח בין ניתוחים (כעת 0.5 שניות)
        self.running = True # דגל לשליטה על ריצת התהליכון
        self.daemon = True # הגדרת התהליכון כ-daemon


    def run(self):  # הפונקציה שתרוץ בתהליכון הנפרד
        print("AI background analyzer started.")  # הודעת התחלה
        while self.running:  # לולאת ריצה כל עוד התהליכון פעיל
            try:
                # מנסה לקחת פריים מהתור בלי לחכות לנצח, עם timeout קצר
                frame = self.frame_queue.get(timeout=0.1)  # קבלת פריים מהתור
                if frame is not None:  # בדיקה אם התקבל פריים תקין
                    print("Sending frame to AI for analysis...")  # הודעה על שליחה לניתוח
                    ai_response_json_string = self.ai_agent.analyze_frame(frame)  # ניתוח הפריים
                    if ai_response_json_string:  # אם התקבלה תשובה
                        print("AI analysis received. Saving data.")  # הודעה על קבלת נתונים
                        self.data_saver.add_analysis_result(ai_response_json_string)  # שמירת הנתונים
                    else:
                        print("AI analysis failed or returned no data.")  # הודעה על כשל בניתוח
                self.frame_queue.task_done()  # סימון שהמשימה בוצעה בתור

            except queue.Empty:  # אם התור ריק
                pass  # לא עושה כלום, ממשיך הלאה
            except Exception as e:  # טיפול בשגיאות כלליות בתהליכון
                print(f"Error in AI background analyzer: {e}")  # הדפסת שגיאה

            time.sleep(self.interval_seconds)  # המתנה לפני ניתוח נוסף

        print("AI background analyzer stopped.")  # הודעת סיום

    def stop(self):  # פונקציה לעצירת התהליכון
        self.running = False  # שינוי דגל העצירה