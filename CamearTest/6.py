import cv2
import mediapipe as mp


def detect_hand_movement(frame, prev_landmarks):
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands()

    # Convert the frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with Mediapipe Hands
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        landmarks = results.multi_hand_landmarks[0].landmark

        # Check the length of landmarks before accessing specific indices
        if len(landmarks) > 4 and prev_landmarks is not None and len(prev_landmarks) > 4:
            # Check the movement in the y-axis (up or down)
            y_difference = landmarks[4].y - prev_landmarks[4].y

            # Check the movement in the x-axis (left or right)
            x_difference = landmarks[4].x - prev_landmarks[4].x

            return x_difference, y_difference

    return 0, 0


# Open the camera
cap = cv2.VideoCapture(0)

# Previous landmarks to calculate the difference
prev_landmarks = None

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    # Flip the frame horizontally for a later selfie-view display
    frame = cv2.flip(frame, 1)

    # Detect hand movement
    try:
        x_diff, y_diff = detect_hand_movement(frame, prev_landmarks)

        # Display the movement on the frame
        cv2.putText(frame, f"X Diff: {x_diff:.2f}, Y Diff: {y_diff:.2f}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Show the frame
        cv2.imshow("Hand Movement Detection", frame)

        # Update previous landmarks
        prev_landmarks = results.multi_hand_landmarks[0].landmark if results.multi_hand_landmarks else None

    except Exception as e:
        print(f"Error: {e}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
