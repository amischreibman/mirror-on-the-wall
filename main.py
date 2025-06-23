import queue
import cv2
from data_saver import DataSaver
from behavioral_data_saver import BehavioralDataSaver
from ai_background_analyzer import AIBackgroundAnalyzer
from camera_utils import Camera
from display_utils import DisplayManager


def run_mirror_app():
    # יצירת אובייקטים
    camera = Camera()
    display_manager = DisplayManager()
    data_saver = DataSaver()
    behavioral_data_saver = BehavioralDataSaver()
    frame_queue = queue.Queue(maxsize=10)
    display_manager.set_behavioral_data_saver(behavioral_data_saver)
    import builtins
    builtins.display_manager = display_manager

    # הגדרת חלון התצוגה
    display_manager.setup_window()

    # יצירת והפעלת thread לניתוח AI ברקע (כולל ניתוח התנהגותי)
    ai_analyzer = AIBackgroundAnalyzer(frame_queue, data_saver, behavioral_data_saver, interval_seconds=0.5)
    ai_analyzer.start()

    # פתיחת המצלמה
    if not camera.open():
        print("Failed to open camera. Exiting.")
        return

    print("Mirror app started. Press 'Esc' to exit.")
    print("Press 'D' to toggle JSON data overlay.")
    print("Press 'G' to toggle grid display.")
    print("Press 'SPACE' to switch between visual and behavioral analysis modes.")
    print("Press 'C' to clear visual data.")
    print("Press 'B' to clean and unify behavioral data.")
    print("Press 'T' to toggle timer display.")
    print("Press 'I' to toggle info display.")
    print("Press 'F' to toggle fullscreen mode.")

    frame_count = 0

    # לולאה ראשית להרצת האפליקציה
    while True:
        if cv2.getWindowProperty(display_manager.window_name, cv2.WND_PROP_VISIBLE) < 1:
            print("Window was closed. Exiting.")
            break

        # קריאת פריים מהמצלמה
        ret, frame = camera.read_frame()
        if not ret or frame is None:
            print("Failed to read frame from camera.")
            break

        frame_count += 1

        # הדפסת מצב כל 100 פריימים
        if frame_count % 100 == 0:
            print(
                f"Frame {frame_count}: Mode={display_manager.display_mode}, Overlay={display_manager.show_json_overlay}")

        # .AI-ניסה להכניס פריים לתור עבור ה
        try:
            frame_queue.put_nowait(frame.copy())
        except queue.Full:
            pass

        # הצגת פריים על המסך (כולל נתוני שני המאגרים)
        display_manager.show_frame(frame, data_saver.file_path, behavioral_data_saver.get_file_path(),
                                   ai_analyzer.person_tracker.get_active_persons())        # בדיקת מקשים
        key = cv2.waitKey(1)
        if key == 27:  # מקש Esc
            print("Esc key pressed. Exiting.")
            break
        elif key != -1 and key != 255:
            # בדיקה אם המקש הוא 'd' או 'D' או 226 (ג' בעברית)
            if key == ord('d') or key == ord('D') or key == 226:
                print("Toggle JSON overlay!")
                display_manager.toggle_json_overlay()
            # בדיקה אם המקש הוא 'g' או 'G' או 231 (ע' בעברית)
            elif key == ord('g') or key == ord('G') or key == 231:
                print("Toggle grid!")
                display_manager.toggle_grid()
            # בדיקה אם המקש הוא רווח (מקש 32)
            elif key == 32:  # מקש רווח
                print("Switching display mode!")
                display_manager.toggle_display_mode()
            # בדיקה אם המקש הוא 'c' או 'C' - התחלת סצנה חדשה
            elif key == ord('c') or key == ord('C'):
                print("Starting new scene!")
                data_saver.start_new_scene()
                behavioral_data_saver.start_new_scene()
                # איפוס person tracker
                ai_analyzer.person_tracker.reset()
                # טריגר למעבר הדרגתי בתצוגה
                if display_manager.show_json_overlay:
                    display_manager.trigger_scene_transition()
            # בדיקה אם המקש הוא 'b' או 'B' - ניקוי נתונים התנהגותיים
            elif key == ord('b') or key == ord('B'):
                print("Cleaning behavioral data!")
                behavioral_data_saver.clean_duplicate_sessions()
                # בדיקה אם המקש הוא 't' או 'T' - הצגת טיימר
            elif key == ord('t') or key == ord('T'):
                print("Toggle timer display!")
                display_manager.toggle_timer()
            # בדיקה אם המקש הוא 'i' או 'I' - הצגת מידע
            elif key == ord('i') or key == ord('I'):
                print("Toggle info display!")
                display_manager.toggle_info()
            elif key == ord('f') or key == ord('F'):
                print("Toggle fullscreen!")
                display_manager.toggle_fullscreen()

    # ניקוי לפני יציאה
    print("Cleaning up...")
    ai_analyzer.stop()
    ai_analyzer.join()
    camera.release()
    cv2.destroyAllWindows()
    print("Mirror app closed.")


if __name__ == "__main__":
    run_mirror_app()