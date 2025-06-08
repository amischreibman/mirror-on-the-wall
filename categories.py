# קובץ categories.py

class PersonCategories:
    """מחלקה לניהול קטגוריות תיאורים"""

    def __init__(self):
        # הגדרת קטגוריות ומילות מפתח
        self.categories = {
            "age": {
                "keywords": ["גיל", "בן", "בת", "שנה", "שנים", "נראה", "בערך"],
                "items": []
            },
            "body_colors": {
                "keywords": ["עור", "שיער", "עיניים", "קעקוע", "צבע", "גוון", "בהיר", "כהה", "חום", "שחור", "בלונד",
                             "אדום", "ירוק", "כחול"],
                "items": []
            },
            "upper_clothing": {
                "keywords": ["חולצה", "חולצת", "סווטשירט", "ז'קט", "מעיל", "בלייזר", "טישרט", "טי שירט", "סוודר"],
                "items": []
            },
            "lower_clothing": {
                "keywords": ["מכנסיים", "מכנס", "ג'ינס", "שורטס", "חצאית", "שמלה"],
                "items": []
            },
            "accessories": {
                "keywords": ["שעון", "טבעת", "שרשרת", "עגילים", "צמיד", "משקפיים", "כובע", "תכשיט"],
                "items": []
            },
            "physical_features": {
                "keywords": ["גובה", "ס\"מ", "סנטימטר", "רזה", "שמן", "חזק", "גוף", "מבנה", "זקן", "שפם", "צלקת", "חלק",
                             "שרירי"],
                "items": []
            },
            "footwear": {
                "keywords": ["נעליים", "נעלי", "נעל", "סנדלים", "כפכפים", "מגפיים", "גרביים"],
                "items": []
            }
        }

    def categorize_description(self, description):
        """מחזירה את שם הקטגוריה עבור תיאור נתון"""
        description_lower = description.lower()

        for category_name, category_data in self.categories.items():
            for keyword in category_data["keywords"]:
                if keyword in description_lower:
                    return category_name

        # אם לא נמצאה התאמה, החזר קטגוריה כללית
        return "general"

    def add_item_to_category(self, person_id, description):
        """מוסיף פריט לקטגוריה המתאימה"""
        category = self.categorize_description(description)

        if category not in self.categories:
            self.categories[category] = {"keywords": [], "items": []}

        # בדוק אם הפריט כבר קיים בקטגוריה
        if description not in self.categories[category]["items"]:
            self.categories[category]["items"].append(description)

        return category

    def get_active_categories(self, person_id):
        """מחזירה רק קטגוריות שיש בהן פריטים"""
        active = {}
        for category_name, category_data in self.categories.items():
            if category_data["items"]:
                active[category_name] = category_data["items"]
        return active

    def clear_person_data(self, person_id):
        """מנקה נתונים של אדם ספציפי"""
        for category_data in self.categories.values():
            category_data["items"] = []

    def update_category_items(self, category_name, new_items):
        """מעדכן פריטים בקטגוריה (מחליף במקום הוספה)"""
        if category_name in self.categories:
            self.categories[category_name]["items"] = new_items

    def process_person_descriptions(self, person_id, descriptions_list):
        """מעבד רשימת תיאורים ומחלק לקטגוריות"""
        categorized_data = {}

        for description in descriptions_list:
            category = self.categorize_description(description)

            if category not in categorized_data:
                categorized_data[category] = []

            # בדוק אם התיאור כבר קיים בקטגוריה
            if description not in categorized_data[category]:
                categorized_data[category].append(description)

        return categorized_data

    def merge_with_existing_categories(self, person_id, new_categorized_data):
        """מעדכן קטגוריות קיימות עם נתונים חדשים"""
        updated_categories = {}

        for category_name, new_items in new_categorized_data.items():
            if category_name in self.categories:
                existing_items = self.categories[category_name]["items"].copy()
                # הגבל ל-5 פריטים מקסימום בכל קטגוריה
                if len(existing_items) >= 5:
                    existing_items = existing_items[-4:]  # השאר רק 4 אחרונים
                for new_item in new_items:
                    # חפש אם יש פריט דומה (אותו סוג פריט)
                    item_replaced = False
                    for i, existing_item in enumerate(existing_items):
                        if self._is_same_item_type(existing_item, new_item):
                            # החלף את הפריט הישן בחדש
                            existing_items[i] = new_item
                            item_replaced = True
                            break

                    # אם לא נמצא פריט דומה, הוסף כחדש
                    if not item_replaced:
                        existing_items.append(new_item)

                self.categories[category_name]["items"] = existing_items
                updated_categories[category_name] = existing_items
            else:
                # קטגוריה חדשה
                self.categories[category_name] = {"keywords": [], "items": new_items}
                updated_categories[category_name] = new_items

        return updated_categories

    def _is_same_item_type(self, old_item, new_item):
        """בודק אם שני תיאורים חולקים מילה משותפת"""
        # פיצול המשפטים למילים
        old_words = set(old_item.lower().split())
        new_words = set(new_item.lower().split())

        # אם יש מילה משותפת (לא כולל מילות קישור קצרות)
        ignore_words = {"את", "של", "עם", "על", "ל", "ב", "ה", "ו", "או", "גם"}

        common_words = old_words.intersection(new_words) - ignore_words

        # אם יש מילה משותפת משמעותית - זה אותו סוג פריט
        return len(common_words) > 0


    def handle_mixed_descriptions(self, description):
        """טיפול בתיאורים מעורבים שיכולים להיות בכמה קטגוריות"""
        categories_found = []
        description_lower = description.lower()

        for category_name, category_data in self.categories.items():
            for keyword in category_data["keywords"]:
                if keyword in description_lower:
                    categories_found.append(category_name)
                    break

        # אם נמצאו כמה קטגוריות, החזר את הראשונה או הספציפית ביותר
        if categories_found:
            # העדפה לקטגוריות ספציפיות
            priority_order = ["age", "body_colors", "accessories", "upper_clothing", "lower_clothing", "footwear",
                              "physical_features"]
            for priority_cat in priority_order:
                if priority_cat in categories_found:
                    return priority_cat
            return categories_found[0]

        return "general"

    def get_display_ready_data(self, person_id):
        """מחזירה נתונים מוכנים לתצוגה - רק קטגוריות עם תוכן"""
        display_data = {}

        for category_name, category_data in self.categories.items():
            if category_data["items"]:  # רק אם יש פריטים
                display_data[category_name] = category_data["items"]

        return display_data