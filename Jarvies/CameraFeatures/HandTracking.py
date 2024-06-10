import cv2
import mediapipe as mp


def detect_hand_direction(frame):
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands()

    # Convert the frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with Mediapipe Hands
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        landmarks = results.multi_hand_landmarks[0].landmark
        x_values = [landmark.x for landmark in landmarks]

        # Check the direction of hand movement
        if x_values[0] < x_values[-1]:
            return "Left to Right"
        elif x_values[0] > x_values[-1]:
            return "Right to Left"

    return "No movement detected"


# Open the camera
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    # Flip the frame horizontally for a later selfie-view display
    frame = cv2.flip(frame, 1)

    # Detect hand direction
    direction = detect_hand_direction(frame)

    # Display the direction on the frame
    cv2.putText(frame, direction, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Show the frame
    cv2.imshow("Hand Direction Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
