import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import cv2
import time
import threading
import mediapipe as mp
from Jarvis.WindowsFeature import WINDOWS_SystemController


def cameraControl():
    mp_draw = mp.solutions.drawing_utils
    mp_hand = mp.solutions.hands

    tipIds = [4, 8, 12, 16, 20]

    video = cv2.VideoCapture(0)
    isFirst = True
    LastTime = None
    with mp_hand.Hands(min_detection_confidence=0.6,
                       min_tracking_confidence=0.6) as hands:
        while True:
            ret, image = video.read()
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = hands.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            lmList = []
            if results.multi_hand_landmarks:
                for hand_landmark in results.multi_hand_landmarks:
                    myHands = results.multi_hand_landmarks[0]
                    for _id, lm in enumerate(myHands.landmark):
                        h, w, c = image.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        lmList.append([_id, cx, cy])
                    mp_draw.draw_landmarks(image, hand_landmark, mp_hand.HAND_CONNECTIONS)
            fingers = []
            total = 0
            if len(lmList) != 0:
                if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
                    fingers.append(1)
                else:
                    fingers.append(0)
                for _id in range(1, 5):
                    if lmList[tipIds[_id]][2] < lmList[tipIds[_id] - 2][2]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                total = fingers.count(1)
                if total >= 1:
                    isFirst = True
                    # thread = threading.Thread(target=comm.sendCommend(total))
                    # thread.start()
                if total == 0:
                    if LastTime is None or LastTime == 'Max':
                        WINDOWS_SystemController.WindowsAppController.minimize_all_windows()
                        LastTime = "Min"
                    # cv2.rectangle(image, (20, 300), (270, 425), (0, 255, 0), cv2.FILLED)
                    cv2.putText(image, "0", (45, 375), cv2.FONT_HERSHEY_SIMPLEX,
                                2, (255, 0, 0), 5)
                    # cv2.putText(image, "LED", (100, 375), cv2.FONT_HERSHEY_SIMPLEX,
                    #             2, (255, 0, 0), 5)
                elif total == 1:
                    if LastTime is None or LastTime == 'Max':
                        WINDOWS_SystemController.WindowsAppController.minimize_all_windows()
                        LastTime = "Min"
                    # cv2.rectangle(image, (20, 300), (270, 425), (0, 255, 0), cv2.FILLED)
                    cv2.putText(image, "1", (45, 375), cv2.FONT_HERSHEY_SIMPLEX,
                                2, (255, 0, 0), 5)
                    # cv2.putText(image, "LED", (100, 375), cv2.FONT_HERSHEY_SIMPLEX,
                    #             2, (255, 0, 0), 5)
                elif total == 2:
                    if LastTime is None or LastTime == 'Max':
                        WINDOWS_SystemController.WindowsAppController.minimize_all_windows()
                        LastTime = "Min"
                    # cv2.rectangle(image, (20, 300), (270, 425), (0, 255, 0), cv2.FILLED)
                    cv2.putText(image, "2", (45, 375), cv2.FONT_HERSHEY_SIMPLEX,
                                2, (255, 0, 0), 5)
                    # cv2.putText(image, "LED", (100, 375), cv2.FONT_HERSHEY_SIMPLEX,
                    #             2, (255, 0, 0), 5)
                elif total == 3:
                    if LastTime is None or LastTime == 'Max':
                        WINDOWS_SystemController.WindowsAppController.minimize_all_windows()
                        LastTime = "Min"
                    # cv2.rectangle(image, (20, 300), (270, 425), (0, 255, 0), cv2.FILLED)
                    cv2.putText(image, "3", (45, 375), cv2.FONT_HERSHEY_SIMPLEX,
                                2, (255, 0, 0), 5)
                    # cv2.putText(image, "LED", (100, 375), cv2.FONT_HERSHEY_SIMPLEX,
                    #             2, (255, 0, 0), 5)
                elif total == 4:
                    if LastTime is None or LastTime == 'Min':
                        WINDOWS_SystemController.WindowsAppController.maximize_all_windows()
                        LastTime = "Max"

                    # cv2.rectangle(image, (20, 300), (270, 425), (0, 255, 0), cv2.FILLED)
                    cv2.putText(image, "4", (45, 375), cv2.FONT_HERSHEY_SIMPLEX,
                                2, (255, 0, 0), 5)
                    # cv2.putText(image, "LED", (100, 375), cv2.FONT_HERSHEY_SIMPLEX,
                    #             2, (255, 0, 0), 5)
                elif total == 5:
                    if LastTime is None or LastTime == 'Min':
                        WINDOWS_SystemController.WindowsAppController.maximize_all_windows()
                        LastTime = "Max"
                    # cv2.rectangle(image, (20, 300), (270, 425), (0, 255, 0), cv2.FILLED)
                    cv2.putText(image, "5", (45, 375), cv2.FONT_HERSHEY_SIMPLEX,
                                2, (255, 0, 0), 5)
                    # cv2.putText(image, "LED", (100, 375), cv2.FONT_HERSHEY_SIMPLEX,
                    #             2, (255, 0, 0), 5)
                # print("total =", total)
            elif isFirst and total == 0:
                # thread = threading.Thread(target=comm.sendCommend(0))
                # thread.start()
                isFirst = False
            cv2.imshow("Frame", image)
            k = cv2.waitKey(1)
            if k == ord('q'):
                break
    video.release()
    cv2.destroyAllWindows()
