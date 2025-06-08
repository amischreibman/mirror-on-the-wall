import cv2
import numpy as np
import time


class PersonTracker:
    """מחלקה לעקיבה אחרי מספר אנשים בו-זמנית"""

    def __init__(self):
        # אתחול גלאי פנים
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # מעקב אחרי מספר אנשים
        self.tracked_persons = {}  # מילון: person_id -> {bbox, last_seen}
        self.person_timeout = 1.0
        #        self.iou_threshold = 0.3  # סף לקביעה שזה אותו אדם

        # מונה אנשים
        self.person_counter = 1000  # מתחיל מ-1000 כדי להיות 4 ספרות

    def detect_persons(self, frame):
        """מזהה את כל האנשים בפריים ומחזיר רשימה של (person_id, is_new)"""
        # זיהוי פנים בפריים
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        current_time = time.time()
        detected_persons = []
        matched_person_ids = set()

        print(f"\n=== PersonTracker: {len(faces)} face(s) detected ===")

        # עבור כל פנים שזוהו
        for face_bbox in faces:
            x, y, w, h = face_bbox

            # הרחב את התיבה התוחמת לכלול יותר מהגוף
            person_bbox = (
                max(0, x - w // 2),
                max(0, y - h // 2),
                min(frame.shape[1], w * 2),
                min(frame.shape[0], h * 3)
            )

            # אם אין אף אדם במעקב - צור חדש
            if len(self.tracked_persons) == 0:
                self.person_counter += 1
                new_id = self.person_counter
                self.tracked_persons[new_id] = {
                    'bbox': person_bbox,
                    'last_seen': current_time
                }
                matched_person_ids.add(new_id)
                detected_persons.append((new_id, True))  # True = חדש
                print(f"  Person {new_id}: NEW (first person)")
            else:
                # יש כבר אדם - השתמש במזהה הקיים
                existing_id = list(self.tracked_persons.keys())[0]
                self.tracked_persons[existing_id]['bbox'] = person_bbox
                self.tracked_persons[existing_id]['last_seen'] = current_time
                matched_person_ids.add(existing_id)
                detected_persons.append((existing_id, False))  # False = לא חדש
                print(f"  Person {existing_id}: SAME (reusing existing ID)")

        # נקה אנשים שלא נראו זמן רב
        persons_to_remove = []
        for person_id, person_data in self.tracked_persons.items():
            if person_id not in matched_person_ids:
                time_since_seen = current_time - person_data['last_seen']
                if time_since_seen > self.person_timeout:
                    persons_to_remove.append(person_id)
                    print(f"  Person {person_id}: LEFT (timeout: {time_since_seen:.1f}s)")

        for person_id in persons_to_remove:
            del self.tracked_persons[person_id]

        return detected_persons
    def _calculate_iou(self, box1, box2):
        """חישוב Intersection over Union בין שתי תיבות"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        # חישוב אזור החפיפה
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        # חישוב האיחוד
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - intersection_area

        return intersection_area / union_area if union_area > 0 else 0

    def get_active_persons(self):
        """מחזיר רשימה של כל האנשים הפעילים"""
        return list(self.tracked_persons.keys())

    def reset(self):
        """איפוס המעקב"""
        self.tracked_persons.clear()
        print("PersonTracker reset - all persons cleared")