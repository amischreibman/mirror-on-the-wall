import cv2 # ייבוא ספריית OpenCV לטיפול במצלמה

class Camera: # הגדרת מחלקה לטיפול במצלמה
    def __init__(self, camera_index=0): # פונקציית אתחול למחלקה
        self.camera_index = camera_index # שמירת אינדקס המצלמה (ברירת מחדל: 0)
        self.cap = None # אתחול משתנה ללכידת וידאו כ-None

    def open(self): # פונקציה לפתיחת המצלמה
        self.cap = cv2.VideoCapture(self.camera_index) # אתחול לכידת וידאו מהמצלמה
        if not self.cap.isOpened(): # בדיקה אם המצלמה נפתחה
            print(f"Error: Could not open camera {self.camera_index}.") # הדפסת הודעת שגיאה
            return False # החזרת שקר אם נכשלה הפתיחה
        return True # החזרת אמת אם נפתחה בהצלחה

    def read_frame(self): # פונקציה לקריאת פריים מהמצלמה
        if self.cap is None: # בדיקה אם המצלמה פתוחה
            return False, None # החזרת שקר ו-None אם לא פתוחה
        ret, frame = self.cap.read() # קריאת פריים
        if not ret: # בדיקה אם קריאת הפריים הצליחה
            print("Error: Could not read frame.") # הדפסת הודעת שגיאה
        return ret, frame # החזרת הצלחה והפריים

    def release(self): # פונקציה לשחרור משאבי המצלמה
        if self.cap: # בדיקה אם אובייקט הלכידה קיים
            self.cap.release() # שחרור המצלמה
            self.cap = None # איפוס האובייקט ל-None