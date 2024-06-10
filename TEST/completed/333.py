import Levenshtein


def find_closest_match(partial_name, app_list):
    closest_matches = {}
    for app in app_list:
        similarity = Levenshtein.ratio(partial_name.lower(), app.lower())
        if similarity >= 0.7:  # You can adjust this threshold as needed
            closest_matches[app] = similarity
    return closest_matches


# Sample list of applications
app_list = ["Microsoft Word", "Microsoft Excel", "Google Chrome", "Adobe Photoshop"]

partial_name = "micorosoft"  # Replace this with your partial name

matching_apps = find_closest_match(partial_name, app_list)
if matching_apps:
    print("Closest matching applications found:")
    for app, similarity in matching_apps.items():
        print(f"{app}: {similarity * 100:.2f}% similar")
else:
    print("No close matching applications found.")
