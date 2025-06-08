import queue  # ייבוא מודול לתורים בטוחים לשימוש בתהליכונים
import cv2  # ייבוא OpenCV
from data_saver import DataSaver  # ייבוא מחלקת DataSaver
from ai_background_analyzer import AIBackgroundAnalyzer  # ייבוא מנתח הרקע
from camera_utils import Camera  # ייבוא כלי המצלמה
from display_utils import DisplayManager  # ייבוא מנהל התצוגה


def run_mirror_app():  # הגדרת הפונקציה הראשית להרצת האפליקציה
    # יצירת אובייקטים
    camera = Camera()  # יצירת אובייקט למצלמה
    display_manager = DisplayManager()  # יצירת מנהל תצוגה
    data_saver = DataSaver()  # יצירת אובייקט לשמירת נתונים
    frame_queue = queue.Queue(maxsize=10)  # יצירת תור לפריימים עם גודל מקסימלי של 10

    # הגדרת חלון התצוגה
    display_manager.setup_window()  # קריאה להגדרת חלון

    # יצירת והפעלת thread לניתוח AI ברקע
    ai_analyzer = AIBackgroundAnalyzer(frame_queue, data_saver, interval_seconds=0.5)
    ai_analyzer.start()  # הפעלת התהליכון

    # פתיחת המצלמה
    if not camera.open():  # פתיחת המצלמה
        print("Failed to open camera. Exiting.")
        return

    print("Mirror app started. Press 'Esc' to exit.")  # הודעת התחלה
    print("Press 'D' to toggle JSON data overlay.")  # הודעה על מקש D
    print("Press 'C' to clear all data.")  # הודעה על מקש C

    # לולאה ראשית להרצת האפליקציה
    while True:
        # קריאת פריים מהמצלמה
        ret, frame = camera.read_frame()  # קריאת פריים
        if not ret or frame is None:  # בדיקה אם הקריאה נכשלה
            print("Failed to read frame from camera.")  # הודעת שגיאה
            break  # יציאה מהלולאה

        # .AI-ניסה להכניס פריים לתור עבור ה
        try:
            frame_queue.put_nowait(frame.copy())  # הכנסת העתק של הפריים לתור
        except queue.Full:  # אם התור מלא
            pass  # דילוג על הפריים הנוכחי

        # הצגת פריים על המסך
        display_manager.show_frame(frame, data_saver.get_file_path())  # הצגת הפריים ונתוני JSON

        # בדיקת מקשים
        key = cv2.waitKey(1)  # המתנה למקש
        if key == 27:  # מקש Esc
            print("Esc key pressed. Exiting.")
            break
        elif key != -1 and key != 255:  # אם נלחץ מקש כלשהו
            # בדיקה אם המקש הוא 'd' או 'D' או 226 (ג' בעברית)
            if key == ord('d') or key == ord('D') or key == 226:
                print("Toggle JSON overlay!")
                display_manager.toggle_json_overlay()
            # בדיקה אם המקש הוא 'c' או 'C' או 225 (ב' בעברית)
            elif key == ord('g') or key == ord('G') or key == 231:  # ע בעברית
                print("Toggle grid!")
                display_manager.toggle_grid()

    # ניקוי לפני יציאה
    print("Cleaning up...")  # הודעת ניקוי
    ai_analyzer.stop()  # עצירת תהליכון הניתוח
    ai_analyzer.join()  # המתנה לסיום התהליכון
    camera.release()  # שחרור המצלמה
    display_manager.cleanup()  # ניקוי משאבי התצוגה
    print("Mirror app closed.")  # הודעת סיום


if __name__ == "__main__":  # בדיקה אם הקובץ רץ ישירות
    run_mirror_app()  # הרצת האפליקציה