import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
previous_wrist_x = None

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Ignoring empty camera frame.")
        continue

    image.flags.writeable = False
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image)

    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    image_height, image_width, _ = image.shape
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Extract wrist coordinates
            wrist_x = hand_landmarks.landmark[0].x * image_width
            # wrist_y = hand_landmarks.landmark[0].y * image_height
            # print('wrist_x', wrist_x)
            # Compare with previous coordinates to determine direction
            if previous_wrist_x is not None:
                if abs(previous_wrist_x - wrist_x) > 5:
                    direction = "Right" if wrist_x < previous_wrist_x else "Left"
                else:
                    # print(abs(previous_wrist_x - wrist_x))
                    direction = 'constant'
                cv2.putText(image, f"Direction: {direction}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            previous_wrist_x = wrist_x

    cv2.imshow('Hand Tracking', image)

    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
