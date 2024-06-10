import os


def open_ease_of_access_setting(category, subcategory=None):
    settings_map = {
        "vision": {
            "display": "ms-settings:easeofaccess-display",
            "mouse_pointer": "ms-settings:easeofaccess-mousepointer",
            "text_cursor": "ms-settings:easeofaccess-textcursor",
            "magnifier": "ms-settings:easeofaccess-magnifier",
            "color_filters": "ms-settings:easeofaccess-colorfilter",
            "high_contrast": "ms-settings:easeofaccess-highcontrast",
            "narrator": "ms-settings:easeofaccess-narrator"
        },
        "hearing": {
            "audio": "ms-settings:easeofaccess-audio",
            "closed_captions": "ms-settings:easeofaccess-closedcaptions"
        }
        # Add more categories and settings as needed
    }

    if category.lower() in settings_map:
        if subcategory:
            subcategory = subcategory.lower()
            if subcategory in settings_map[category.lower()]:
                os.system(f"start {settings_map[category.lower()][subcategory]}")
                print(f"{category.capitalize()} > {subcategory.capitalize()} Setting opened.")
            else:
                print(f"Unsupported subcategory: {subcategory}")
        else:
            print(f"Specify a subcategory for the {category.capitalize()} category.")
    else:
        print(f"Unsupported category: {category}")


# Example usage:
open_ease_of_access_setting("vision", "display")
open_ease_of_access_setting("vision", "mouse_pointer")
open_ease_of_access_setting("vision", "text_cursor")
open_ease_of_access_setting("vision", "magnifier")
open_ease_of_access_setting("vision", "color_filters")
open_ease_of_access_setting("vision", "high_contrast")
open_ease_of_access_setting("vision", "narrator")

open_ease_of_access_setting("hearing", "audio")
open_ease_of_access_setting("hearing", "closed_captions")
# Add more calls as needed
