import cv2

# Load the hand cascade classifier
hand_cascade = cv2.CascadeClassifier('haarcascade_palm.xml')

# Initialize webcam and variables
cap = cv2.VideoCapture(0)
prev_x = 0  # Store previous x-coordinate for movement comparison

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect hands
    hands = hand_cascade.detectMultiScale(gray, 1.1, 4)

    for (x, y, w, h) in hands:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Track movement and display direction
        if prev_x > 0:  # Compare to previous frame
            direction = "Right" if x > prev_x else "Left"
            cv2.putText(frame, f"Direction: {direction}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        prev_x = x  # Update previous x-coordinate

    cv2.imshow('Hand Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
