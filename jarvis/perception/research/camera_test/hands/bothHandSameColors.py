import cv2
import mediapipe as mp


def detect_hands(frame):
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands()

    # Convert the frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with Mediapipe Hands
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            for landmark in hand_landmarks.landmark:
                # Extract the landmark coordinates (x, y)
                x, y = int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0])

                # Draw a circle on each detected landmark
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        # Draw hand connections
        mp_drawing = mp.solutions.drawing_utils
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    return frame


# Open the camera
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    # Flip the frame horizontally for a later selfie-view display
    frame = cv2.flip(frame, 1)

    # Detect hands
    frame_with_hands = detect_hands(frame)

    # Show the frame with hand detection
    cv2.imshow("Hand Detection", frame_with_hands)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
