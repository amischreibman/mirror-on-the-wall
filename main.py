import cv2  # ייבוא OpenCV לבדיקת מקשים
import queue  # ייבוא מודול לתורים בטוחים
from camera_utils import Camera  # ייבוא מחלקת Camera
from display_utils import DisplayManager  # ייבוא מחלקת DisplayManager
from ai_background_analyzer import AIBackgroundAnalyzer  # ייבוא מחלקת AIBackgroundAnalyzer
from data_saver import DataSaver  # ייבוא מחלקת DataSaver


def run_mirror_app():  # פונקציה ראשית להפעלת האפליקציה
    print("Mirror app started. Press 'Esc' to exit.")  # הודעת התחלה
    print("Press 'D' to toggle JSON data overlay.")  # הודעה להצגת נתונים

    camera = Camera(camera_index=0)  # יצירת אובייקט מצלמה
    display = DisplayManager(window_name='Mirror on the Wall')  # יצירת אובייקט תצוגה
    data_saver = DataSaver(output_dir='data')  # יצירת אובייקט לשמירת נתונים

    frame_queue = queue.Queue(maxsize=5)  # יצירת תור לפריימים לניתוח AI

    # שינוי מרווח הזמן ל-1 שנייה במקום 2 לקבלת יותר עדכונים
    ai_analyzer = AIBackgroundAnalyzer(frame_queue, data_saver, interval_seconds=1)  # אתחול תהליכון AI

    if not camera.open():  # ניסיון פתיחת המצלמה
        return  # יציאה אם נכשלה פתיחה

    display.setup_window()  # הגדרת חלון התצוגה למסך מלא
    ai_analyzer.start()  # התחלת תהליכון ניתוח ה-AI ברקע

    try:  # בלוק לטיפול בשגיאות וניקוי
        while True:  # לולאת ריצה ראשית
            ret, frame = camera.read_frame()  # קריאת פריים מהמצלמה
            if not ret:  # בדיקה אם הקריאה נכשלה
                break  # יציאה מהלולאה

            # הצגת הפריים עם נתיב קובץ ה-JSON
            display.show_frame(frame, data_saver.get_file_path())  # הצגת הפריים המעובד (ראי)

            # נסה להכניס פריים לתור עבור ה-AI.
            try:
                frame_queue.put_nowait(frame.copy())  # הכנסת עותק של הפריים לתור
            except queue.Full:  # אם התור מלא
                pass  # דילוג על הפריים הנוכחי

            key = cv2.waitKey(1)  # המתנה ללחיצת מקש
            if key == 27:  # בדיקה אם נלחץ מקש Esc
                print("Esc key pressed. Exiting.")  # הודעת יציאה
                break  # יציאה מהלולאה
            elif key != -1:  # אם נלחץ מקש כלשהו (לא -1)
                # קליטת לחיצת מקש 'd' (עבור אנגלית או עברית)
                if chr(key & 0xFF).lower() == 'd':  # בדיקה אם המקש הוא 'd'
                    display.toggle_json_overlay()  # החלפת מצב שכבת הנתונים
                # הוספת מקש לניקוי נתונים ידני
                elif chr(key & 0xFF).lower() == 'c':  # בדיקה אם המקש הוא 'c'
                    print("Manual clear requested")
                    data_saver.accumulated_person_data = {}
                    # data_saver.frames_without_person = data_saver.clear_threshold

    finally:  # קטע קוד שירוץ תמיד, גם אם יש שגיאה
        ai_analyzer.stop()  # איתות לתהליכון ה-AI לעצור
        ai_analyzer.join()  # המתנה לסיום עבודת תהליכון ה-AI
        camera.release()  # שחרור משאבי מצלמה
        display.cleanup()  # ניקוי משאבי תצוגה
        print("Mirror app closed.")  # הודעת סיום


if __name__ == "__main__":  # בדיקה אם הקובץ מופעל ישירות
    run_mirror_app()  # הפעלת הפונקציה הראשית