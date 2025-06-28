import threading
import queue
import time
from ai_agent import AIAgent
from data_saver import DataSaver
from face_detector import FaceDetector
from person_tracker import PersonTracker
from behavioral_analyzer import BehavioralAnalyzer
from behavioral_data_saver import BehavioralDataSaver


class AIBackgroundAnalyzer(threading.Thread):
    def __init__(self, frame_queue, data_saver, behavioral_data_saver, interval_seconds=0.5):
        super().__init__()
        self.frame_queue = frame_queue
        self.data_saver = data_saver
        self.behavioral_data_saver = behavioral_data_saver
        self.ai_agent = AIAgent()
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.face_detector = FaceDetector()
        self.person_tracker = PersonTracker()
        self.interval_seconds = interval_seconds
        self.running = True
        self.daemon = True
        self.frames_processed = 0
        self.frames_with_faces = 0
        self.display_manager = None  # הוספת הפניה ל-display_manager

    def set_display_manager(self, display_manager):
        """קביעת הפניה ל-display_manager"""
        self.display_manager = display_manager

    def run(self):
        print("AI background analyzer with behavioral analysis started.")
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if frame is not None:
                    self.frames_processed += 1

                    # זיהוי כל האנשים בפריים
                    detected_persons = self.person_tracker.detect_persons(frame)

                    # עדכן את display_manager עם רשימת האנשים הפעילים
                    active_person_ids = [pid for pid, _ in detected_persons]
                    if self.display_manager:
                        self.display_manager.update_active_persons(active_person_ids)

                    if not detected_persons:
                        # אין אנשים בפריים
                        print("No persons detected in frame")
                        self.data_saver.handle_empty_frame()
                        self.behavioral_data_saver.handle_empty_frame()
                    else:
                        self.frames_with_faces += 1
                        print(f"{len(detected_persons)} person(s) in frame")

                        # שלח ל-AI לניתוח חזותי (המאגר הראשון)
                        ai_response_json_string = self.ai_agent.analyze_frame(frame)

                        if ai_response_json_string:
                            self.data_saver.process_multi_person_analysis(
                                ai_response_json_string,
                                detected_persons
                            )
                        else:
                            print("Visual AI analysis failed or returned no data.")

                        # שלח ל-AI לניתוח התנהגותי (המאגר השני)
                        behavioral_response_json_string = self.behavioral_analyzer.analyze_behavior(frame)

                        if behavioral_response_json_string:
                            print("Behavioral AI analysis received. Processing...")
                            self.behavioral_data_saver.process_behavioral_analysis(
                                behavioral_response_json_string,
                                detected_persons
                            )
                        else:
                            print("Behavioral AI analysis failed or returned no data.")

                    # סטטיסטיקות דיבאג
                    if self.frames_processed % 20 == 0 and self.frames_processed > 0:
                        face_ratio = (self.frames_with_faces / self.frames_processed) * 100
                        active_persons = self.person_tracker.get_active_persons()
                        print(
                            f"\nStats: {self.frames_with_faces}/{self.frames_processed} frames with faces ({face_ratio:.1f}%)")
                        print(f"Active persons: {active_persons}")

                self.frame_queue.task_done()

            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error in AI background analyzer: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(self.interval_seconds)

        print("AI background analyzer stopped.")

    def stop(self):
        self.running = False