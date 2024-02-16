import cv2
import numpy as np
from argparse import ArgumentParser
import pathlib
import time
import cv2
import time


def frame_difference2(filename):
    # Open the video
    cap = cv2.VideoCapture(filename)

    # Determine the video's frame rate (FPS) and size for VideoWriter
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)  # Doubled width for side-by-side frames
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Setup VideoWriter to save the output
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('processed_output.mp4', fourcc, fps, (frame_width, frame_height))

    # Calculate the end frame number for 30 minutes
    end_frame_number = 30 * 60 * fps  # 30 minutes * 60 seconds * FPS

    # Initialize variables
    last_state = None
    unchanged_start_time = None
    display_text = ""
    frame_count = 0  # Initialize frame count

    # Read the first frame
    ret, prev_frame = cap.read()
    prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None

    while ret and frame_count < end_frame_number:
        # Increment frame count
        frame_count += 1

        # Read the next frame
        ret, current_frame = cap.read()
        if not ret:
            break  # Break the loop if there are no more frames

        # Process the frame
        current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        frame_diff = cv2.absdiff(current_frame_gray, prev_frame_gray)
        _, thresh_diff = cv2.threshold(frame_diff, 150, 255, cv2.THRESH_BINARY)

        # Determine state based on the frame difference
        display_text = 'State 3: Frame Changed' if cv2.countNonZero(thresh_diff) > 0 else 'State 4: Frame Unchanged'

        # Prepare the frame for display and output file
        thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)
        concatenated_frame = cv2.hconcat([current_frame, thresh_diff_bgr])
        cv2.putText(concatenated_frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Show the frame
        cv2.imshow('Original and Significant Changes', concatenated_frame)

        # Write the frame to the output file
        out.write(concatenated_frame)

        # Update the previous frame
        prev_frame_gray = current_frame_gray

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()



def frame_difference(args):
    # Open the video
    cap = cv2.VideoCapture(args.filename)

    # Read the first frame
    ret, prev_frame = cap.read()

    # Convert the first frame to grayscale
    prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

    last_state = None
    unchanged_start_time = None
    display_text = ''

    while True:
        # Read the next frame
        ret, current_frame = cap.read()
        if not ret:
            break  # Break the loop if there are no more frames
            # Convert the current frame to grayscale for difference calculation
        current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        # Compute the absolute difference between the current frame and the previous frame
        frame_diff = cv2.absdiff(current_frame_gray, prev_frame_gray)

        # Apply thresholding to the frame difference to keep only significant changes
        _, thresh_diff = cv2.threshold(frame_diff, 200, 255, cv2.THRESH_BINARY)  # Threshold adjusted to 30

        if cv2.countNonZero(thresh_diff) > 0:
            current_state = 'State 3: Frame Changed'
            if last_state == 'State 4: Frame Unchanged':
                # Calculate and print the elapsed time in seconds
                elapsed_time = time.time() - unchanged_start_time
                print(f"{current_state} after {elapsed_time:.2f} seconds of no change.")
                display_text = (f"{current_state} after {elapsed_time:.2f} seconds of no change.")
        else:
            current_state = 'State 4: Frame Unchanged'
            if last_state != 'State 4: Frame Unchanged':
                # Capture the start time of the unchanged state
                unchanged_start_time = time.time()
                print(current_state)
            display_text = current_state

        last_state = current_state


        # Convert the thresholded difference back to BGR to concatenate with the original color frame
        thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)

        # Ensure both frames are the same size, here assuming `current_frame` is the base size
        thresh_diff_bgr_resized = cv2.resize(thresh_diff_bgr, (current_frame.shape[1], current_frame.shape[0]))

        # Concatenate the original frame with the thresholded frame difference side by side
        concatenated_frame = cv2.hconcat([current_frame, thresh_diff_bgr_resized])

        # Display the state on the concatenated frame
        cv2.putText(concatenated_frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Display the concatenated frame
        cv2.imshow('Original and Significant Changes', concatenated_frame)

        # Update the previous frame to the current one (in grayscale)
        prev_frame_gray = current_frame_gray

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture object and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()


def main(args):
    frame_difference(args)


if __name__ == "__main__":
    # parser = ArgumentParser()
    # parser.add_argument("filename", type=str)
    #
    # args = parser.parse_args()
    # main(args)
    frame_difference2('/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4')







# import cv2
# import numpy as np
# import os
# from argparse import ArgumentParser
# import pathlib
#
# def clamp_color(color):
#     return np.clip(color, 0, 255)
# def get_cnts(thresh):
#     cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     return cnts[0] if len(cnts) == 2 else cnts[1]
#
# def filter_color(frame, color, noise):
#     return cv2.inRange(frame, clamp_color(color - noise), clamp_color(color + noise))
#
# count = {}
#
# def detect(frame, prev_flags=set()):
#     notif_frame = frame.copy()
#     frame = frame.copy()
#     frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
#
#     count["all"] = count.get("all", 0) + 1
#     # print(f"Debug: all {count['all']}")
#
#     flags = set()
#     ## Detect User Interaction
#     ### Detect Popup
#     popup_thres = filter_color(frame_hsv, popup_color, popup_noise)
#     popup_thres = cv2.blur(popup_thres, (5, 5))
#     cnts = get_cnts(popup_thres)
#     new_cnts = []
#     for c in cnts:
#         _, _, w, h = cv2.boundingRect(c)
#         if w * h < 5000:
#             continue
#         c = cv2.convexHull(c)
#         poly = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
#         if poly.shape[0] == 4:
#             new_cnts.append(c)
#     cnts = new_cnts
#
#     ### Detect button in popups
#     btn_thres = filter_color(frame_hsv, btn_color, btn_noise)
#     btn_thres = cv2.blur(btn_thres, (3, 3))
#     for c in cnts:
#         x, y, w, h = cv2.boundingRect(c)
#         crop = btn_thres[y:y + h, x:x + w]
#         btn_cnts = get_cnts(crop)
#         for btn_c in btn_cnts:
#             _, _, w, h = cv2.boundingRect(btn_c)
#             if w < 30 or h < 30 or w * h < 1000:
#                 continue
#             btn_c = cv2.convexHull(btn_c)
#             poly = cv2.approxPolyDP(btn_c, 0.02 * cv2.arcLength(btn_c, True), True)
#             if poly.shape[0] == 4:
#                 notification("Interaction", prev_flags, flags, notif_frame, msg_color=(255, 40, 40),
#                              save_dir=interact_dir)
#                 break
#
#     # ## Detect success
#     # success_thres = filter_color(frame, success_color, success_noise)
#     # cnts = get_cnts(success_thres)
#     # for c in cnts:
#     #     x, y, w, h = cv2.boundingRect(c)
#     #     if w > 20 and h > 20 and w*h > 100:
#     #         notification("Success", prev_flags, flags, notif_frame, msg_color = (40, 255, 40), save_dir=success_dir)
#     #         break
#
#     # ## Detect failure
#     # fail_thres = filter_color(frame, fail_color, fail_noise)
#     # fail_thres = cv2.blur(fail_thres, (20, 5))
#     # fail_thres = cv2.threshold(fail_thres, 10, 255, cv2.THRESH_BINARY)[1]
#     # cnts = get_cnts(fail_thres)
#     # for c in cnts:
#     #     x, y, w, h = cv2.boundingRect(c)
#     #     if w > 30 and h > 15 and w/h > 10:
#     #         notification("Failure", prev_flags, flags, notif_frame, msg_color = (0, 0, 255), save_dir=fail_dir)
#     #         break
#
#     if len(flags) == 0:
#         count["nth"] = count.get("nth", 0) + 1
#         # cv2.imwrite(str(nth_dir / f"{count['all']:04}_nth_{count['nth']:04}.jpg"), notif_frame)
#         # print(f"Debug: nth {count['all']}_{count['nth']}")
#
#     cv2.imwrite(str(all_dir / f"{count['all']:04}.jpg"), frame)
#     cv2.imwrite(str(nth_dir / f"{count['all']:04}.jpg"), notif_frame)
#     cv2.imwrite(str(interact_dir / f"{count['all']:04}.jpg"), frame_hsv)
#     # cv2.imshow('frame', notif_frame)
#     # cv2.waitKey(1)
#
#     return flags
#
#
# def video_difference(args):
#     cap = cv2.VideoCapture(args.filename)
#     prev_frame = None
#     prev_flags = set()
#
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break
#
#         frame_changed = prev_frame is None
#
#         if not frame_changed:
#             frame_diff = cv2.absdiff(prev_frame, frame) if prev_frame is not None else frame
#             frame_diff = cv2.cvtColor(frame_diff, cv2.COLOR_BGR2GRAY)
#
#
#             cv2.imshow('frame_difference', frame_diff)
#
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
#
#             frame_diff = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)[1]
#             diff_cnts = get_cnts(frame_diff)
#             for c in diff_cnts:
#                 _, _, w, h = cv2.boundingRect(c)
#                 if w > 10 and h > 10:
#                     frame_changed = True
#                     break
#
#         if frame_changed:
#             # print(time.time() - prev_time)
#             prev_flags = detect(frame, prev_flags)
#             prev_frame = frame
# def main(args):
#     if args.filename.endswith(".png"):
#         print("wrong file")
#     else:
#         print(2)
#         video_difference(args)
#
# if __name__ == "__main__":
#     parser = ArgumentParser()
#     parser.add_argument("filename", type=str)
#
#     args = parser.parse_args()
#     main(args)