import cv2

# Open the camera
cap = cv2.VideoCapture(0)

# Initialize variables for hand tracking
previous_x = 0
direction = ""

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Convert the frame to grayscale for better processing
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise and improve tracking
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Use background subtraction (optional)
    # You may need to adjust the parameters based on your environment
    fgmask = cv2.createBackgroundSubtractorMOG2().apply(blurred)

    # Thresholding to get a binary image
    _, thresholded = cv2.threshold(fgmask, 128, 255, cv2.THRESH_BINARY)

    # Find contours in the binary image
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find the contour with the largest area (assuming it is the hand)
    if contours:
        max_contour = max(contours, key=cv2.contourArea)
        moments = cv2.moments(max_contour)

        # Calculate the center of mass of the hand
        cx = int(moments['m10'] / moments['m00'])

        # Determine the direction of movement
        if cx > previous_x:
            direction = "Right"
        elif cx < previous_x:
            direction = "Left"

        previous_x = cx

        # Draw the contour and direction on the frame
        cv2.drawContours(frame, [max_contour], -1, (0, 255, 0), 2)
        cv2.putText(frame, f"Direction: {direction}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Display the frame
    cv2.imshow('Hand Movement Detection', frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

# Release the camera and close the window
cap.release()
cv2.destroyAllWindows()
