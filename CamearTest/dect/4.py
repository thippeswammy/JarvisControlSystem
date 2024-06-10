import cv2
import mediapipe as mp


def detect_hand_movement(frame, prev_x):
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands()

    # Convert the frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with Mediapipe Hands
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        landmarks = results.multi_hand_landmarks[0].landmark

        # Get the x-coordinate of a specific landmark (e.g., the tip of the index finger - landmark[8])
        current_x = landmarks[8].x * frame.shape[1]

        # Calculate the difference in x-coordinates to determine movement direction
        x_difference = current_x - prev_x

        return x_difference, current_x

    return 0, 0


# Open the camera
cap = cv2.VideoCapture(0)

# Initial x-coordinate
prev_x = 0

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    # Flip the frame horizontally for a later selfie-view display
    frame = cv2.flip(frame, 1)

    # Detect hand movement
    x_diff, prev_x = detect_hand_movement(frame, prev_x)

    # Display the movement on the frame
    cv2.putText(frame, f"X Diff: {x_diff:.2f}", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Show the frame
    cv2.imshow("Hand Movement Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
