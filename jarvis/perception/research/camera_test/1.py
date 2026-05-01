import cv2
import mediapipe as mp

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# Initialize OpenCV camera capture
cap = cv2.VideoCapture(0)

while cap.isOpened():
    # Read a frame from the camera
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame from camera. Exiting...")
        break

    # Flip the frame horizontally for a selfie-view display
    frame = cv2.flip(frame, 1)

    # Convert the frame from BGR to RGB for MediaPipe
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with MediaPipe Hands
    results = hands.process(image_rgb)

    # Convert the frame back to BGR
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

    # Check if hand landmarks are detected
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw hand landmarks on the frame
            mp_drawing.draw_landmarks(
                image_bgr, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Extract landmark positions for relevant points
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_finger = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_finger = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            ring_finger = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
            pinky_finger = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]

            # Get image dimensions
            image_height, image_width, _ = image_bgr.shape

            # Calculate distances between thumb and fingers
            thumb_index_distance_x = abs((thumb.x - index_finger.x) * image_width)
            thumb_index_distance_y = abs((thumb.y - index_finger.y) * image_height)
            thumb_middle_distance_x = abs((thumb.x - middle_finger.x) * image_width)
            thumb_middle_distance_y = abs((thumb.y - middle_finger.y) * image_height)
            thumb_ring_distance_x = abs((thumb.x - ring_finger.x) * image_width)
            thumb_ring_distance_y = abs((thumb.y - ring_finger.y) * image_height)
            thumb_pinky_distance_x = abs((thumb.x - pinky_finger.x) * image_width)
            thumb_pinky_distance_y = abs((thumb.y - pinky_finger.y) * image_height)

            # Define thresholds for gesture recognition
            # Number 0: All fingers closed
            if (thumb_index_distance_x < 50 and thumb_index_distance_y < 50 and
                thumb_middle_distance_x < 50 and thumb_middle_distance_y < 50 and
                thumb_ring_distance_x < 50 and thumb_ring_distance_y < 50 and
                thumb_pinky_distance_x < 50 and thumb_pinky_distance_y < 50):
                cv2.putText(image_bgr, "Number 0", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Number 5: Thumb extended, other fingers closed
            elif (thumb_index_distance_x > 100 and thumb_index_distance_y < 50 and
                  thumb_middle_distance_x < 50 and thumb_middle_distance_y < 50 and
                  thumb_ring_distance_x < 50 and thumb_ring_distance_y < 50 and
                  thumb_pinky_distance_x < 50 and thumb_pinky_distance_y < 50):
                cv2.putText(image_bgr, "Number 5", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Display the processed image with annotations
    cv2.imshow('Hand Gesture Recognition', image_bgr)

    # Exit loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
