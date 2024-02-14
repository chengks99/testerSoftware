import cv2
import numpy as np
import os
from argparse import ArgumentParser
import pathlib

#Step 1: Obtain frame data from the test videos

#Capture Video and Read Img/Frames
def Video_Read(video_path):
    #capture video
    cap = cv2.VideoCapture(video_path)

    #while video is opened, capture the frame
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

#Read Img
def Image_Read(image_path):
    frame = cv2.imread(image_path)

    return frame


#Step 2: Mask the images captured and Check Tester Screen
def mask(video_path):
    # image = Image_Read(image_path)
    cap = cv2.VideoCapture(video_path)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break  # End of video or error

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define the blue color range (adjust these values based on your blue shade)
        lower_blue = np.array([50, 120, 50])
        upper_blue = np.array([140, 255, 255])

        # Threshold the HSV image to get only blue colors
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Initialize top and bottom y-coordinates
        top_y = 0
        bottom_y = frame.shape[0]

    # debug_image = frame.copy()
    # Loop over the contours to find the top and bottom bars
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > frame.shape[1] * 0.99:  # Check if the contour is wide enough (adjust threshold as needed)
                if y < frame.shape[0] // 2:  # Top half of the image
                    top_y = max(top_y, y + h)  # Update the top bar's bottom boundary
                else:  # Bottom half of the image
                    bottom_y = min(bottom_y, y)  # Update the bottom bar's top boundary

    # Crop the image
        if bottom_y > top_y:
            cropped_image = frame[top_y:bottom_y, 0:frame.shape[1]]
            cv2.imshow('Cropped Image', cropped_image)
        else:
            print("Invalid crop dimensions. Skipping frame.")

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
            break
    # cv2.waitKey(0)
    cap.release()
    cv2.destroyAllWindows()


#Step 3: Contouring popup boxes
def detect_and_draw_popups(video_path):
    cap = cv2.VideoCapture(video_path)


    while True:
        ret, frame = cap.read()
        if not ret:
            break  # End of video or error

        cnts = 0

        # Convert the frame to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


        # Define the range for blue color in HSV
        lower_blue = np.array([100, 150, 0])
        upper_blue = np.array([140, 255, 255])

        # Threshold the HSV image to get only blue colors
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Draw rectangles around the detected popups
        for contour in contours:
            # Optional: filter contours by size here
            area = cv2.contourArea(contour)
            if area > 5000:
                cnts += 1
                # print(cnts)
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Drawing in green for visibility
        print(f'large number of contours detected in current frame: {cnts}')
        cv2.imshow('Detected Popups', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
            break

    cap.release()
    cv2.destroyAllWindows()


#Step 4: Total Code
def mask_and_detect_popups(video_path, output_dir):
    #capture video
    cap = cv2.VideoCapture(video_path)

    # Get the frames per second of the video
    fps = cap.get(cv2.CAP_PROP_FPS)

    #Initialize previous state and frame_counter
    prev_state = None
    frame_counter = 0

    screenshots_dir = os.path.join(output_dir, 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'output.txt')

    #opening output file for writing
    with open(output_file, 'w') as file:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break  # End of video or error

            # Get the current frame number and calculate the timestamp
            # frame_number = cap.get(cv2.CAP_PROP_POS_FRAMES)
            frame_counter += 1
            timestamp = frame_counter / fps

            # First masking operation based on one blue color range
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_blue_first = np.array([50, 120, 50])
            upper_blue_first = np.array([140, 255, 255])
            mask_first = cv2.inRange(hsv, lower_blue_first, upper_blue_first)
            contours_first, _ = cv2.findContours(mask_first, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            top_y = 0
            bottom_y = frame.shape[0]

            for contour in contours_first:
                x, y, w, h = cv2.boundingRect(contour)
                if w > frame.shape[1] * 0.99:
                    if y < frame.shape[0] // 2:
                        # top_y = max(top_y, y + h)
                        continue
                    else:
                        bottom_y = min(bottom_y, y)

            if bottom_y > top_y:
                cropped_image = frame[top_y:bottom_y, :]

                # Second masking operation for detecting popups on the cropped frame
                hsv_cropped = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2HSV)
                lower_blue_second = np.array([50, 100, 0])
                upper_blue_second = np.array([140, 255, 255])
                mask_second = cv2.inRange(hsv_cropped, lower_blue_second, upper_blue_second)
                contours_second, _ = cv2.findContours(mask_second, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                cnts = 0

                for contour in contours_second:
                    area = cv2.contourArea(contour)
                    # print(area)
                    # if 21200 <= area <= 21300:
                    #     x, y, w, h = cv2.boundingRect(contour)
                    #     cv2.rectangle(cropped_image, (x, y), (x + w, y + h), (255, 255, 255), -1)

                    if area > 10000 and not (21000 <= area <= 21500) and not area >= 780000: #area of the panasonic logo
                        cnts += 1
                        x, y, w, h = cv2.boundingRect(contour)
                        # Drawing in green for visibility
                        cv2.rectangle(cropped_image, (x, y), (x + w, y + h), (0, 255, 0), 2)


                # print(f'Large number of contours detected in current frame: {cnts}')
                if cnts < 1:
                    current_state = 'State 0: No Tester Screen'
                elif cnts == 1:
                    current_state = 'State 1: Tester Screen'
                else:
                    current_state = f'State 2: {cnts - 1} PopUp Detected'

                # Print the current state only if it has changed since the last check
                if current_state != prev_state:
                    print(current_state)
                    file.write(f"{timestamp:.2f}s: {current_state}\n")

                    if cnts > 1:
                        image_filename = f"frame_{frame_counter}_popup_detected.jpg"
                        image_path = os.path.join(screenshots_dir, image_filename)
                        cv2.imwrite(image_path, frame)  # Save the frame as an image file
                        print(f"Saved screenshot: {image_path}")

                    prev_state = current_state


                cv2.imshow('Detected Popups on Cropped Image', cropped_image if 'cropped_image' in locals() else frame)

            # else:
            #     # print("Invalid crop dimensions. Skipping frame.")
            #     # continue
            #     cv2.imshow('Detected Popups on Cropped Image', frame)


                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        cap.release()
        cv2.destroyAllWindows()



if __name__ == "__main__":
    video_path = '/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4'
    video_path2 = '/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-29 08-08-11 SDU CT Tester.mp4'
    output_file = '/Users/juneyoungseo/Documents/Panasonic/output'
    # mask('/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4')
    # detect_and_draw_popups(video_path)
    mask_and_detect_popups(video_path2, output_file)

















##############################
#
# def clamp_color(color):
#     return np.clip(color, 0, 255)
#
# def filter_color(frame, color, noise):
#     return cv2.inRange(frame, clamp_color(color - noise), clamp_color(color + noise))
#
# def get_cnts(thresh):
#     cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     return cnts[0] if len(cnts) == 2 else cnts[1]
#
# popup_color = np.array([110, 225, 235])
# popup_noise = np.array([30, 30, 100])
#
# if __name__ == '__main__':
#     cap = cv2.VideoCapture('/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-29 08-08-11 SDU CT Tester.mp4')
#
#     kernel = np.ones((2,2), np.uint8)
#     while(True):
#         ret, frame = cap.read()
#         frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
#         frame_hsv = cv2.GaussianBlur(frame_hsv, (7,7), 0)
#         frame_hsv = cv2.medianBlur(frame_hsv, 3)
#
#
#         popup_thresh = filter_color(frame_hsv, popup_color, popup_noise)
#         popup_thresh = cv2.morphologyEx(popup_thresh, cv2.MORPH_GRADIENT, kernel)
#         popup_thresh = cv2.dilate(popup_thresh, kernel, iterations=5)
#
#         contours, hierarchy = cv2.findContours(popup_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#         if len(contours) > 0:
#             cv2.drawContours(frame, contours, -1, (0,255,0), 5)
#             c = max(contours, key = cv2.contourArea)
#             x,y,w,h = cv2.boundingRect(c)
#
#             cv2.rectangle(frame, (x,y), (x+w, y+h), (255,0,0), 8)
#
#         # cnts = get_cnts(popup_thresh)
#         # new_cnts = []
#         # for c in cnts:
#         #     _, _, w, h = cv2.boundingRect(c)
#         #     if w * h < 5000:
#         #         continue
#         #     c = cv2.convexHull(c)
#         #     poly = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
#         #     if poly.shape[0] == 4:
#         #         new_cnts.append(c)
#         # cnts = new_cnts
#
#         # ### Detect button in popups
#         # btn_thres = filter_color(frame_hsv, btn_color, btn_noise)
#         # btn_thres = cv2.blur(btn_thres, (3, 3))
#         # for c in cnts:
#         #     x, y, w, h = cv2.boundingRect(c)
#         #     crop = btn_thres[y:y + h, x:x + w]
#         #     btn_cnts = get_cnts(crop)
#         #     for btn_c in btn_cnts:
#         #         _, _, w, h = cv2.boundingRect(btn_c)
#         #         if w < 30 or h < 30 or w * h < 1000:
#         #             continue
#         #         btn_c = cv2.convexHull(btn_c)
#         #         poly = cv2.approxPolyDP(btn_c, 0.02 * cv2.arcLength(btn_c, True), True)
#         #         if poly.shape[0] == 4:
#         #             notification("Interaction", prev_flags, flags, notif_frame, msg_color=(255, 40, 40),
#         #                          save_dir=interact_dir)
#         #             break
#
#         cv2.imshow('frame', frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#
#     cap.release()
#     cv2.destroyAllWindows()






