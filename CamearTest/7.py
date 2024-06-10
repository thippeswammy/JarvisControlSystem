import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands.Hands(
    max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
prev_landmarks = None

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    # Flip the frame horizontally for a later selfie-view display (optional)
    frame = cv2.flip(frame, 1)

    # Convert the frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with MediaPipe Hands
    results = mp_hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        landmarks = results.multi_hand_landmarks[0].landmark

        # Check the length of landmarks before accessing specific indices
        if len(landmarks) > 4 and prev_landmarks is not None and len(prev_landmarks) > 4:
            # Calculate movement differences
            x_difference = landmarks[4].x - prev_landmarks[4].x
            y_difference = landmarks[4].y - prev_landmarks[4].y

            # Determine direction based on movement
            direction_x = "Right" if x_difference > 0 else "Left" if x_difference < 0 else "None"
            direction_y = "Up" if y_difference > 0 else "Down" if y_difference < 0 else "None"

            # Display movement and direction information on the frame
            cv2.putText(frame, f"X Diff: {x_difference:.2f}, Y Diff: {y_difference:.2f}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Direction: X: {direction_x}, Y: {direction_y}", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Visualize hand landmarks (optional)
            # mp_drawing.draw_landmarks(frame, landmarks, mp_hands.HAND_CONNECTIONS)

    # Update previous landmarks for next iteration
    prev_landmarks = landmarks if landmarks else None

    # Show the processed frame
    cv2.imshow("Hand Movement Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
