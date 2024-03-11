import cv2
import numpy as np
import time

import threading
import sys
import logging
import pathlib
scriptPath = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(scriptPath.parent / 'common'))
from jsonutils import json2str

class TesterDetection(object):
    def __init__(self, redis_conn, id, detectionType=1) -> None:
        ''' init tester detection module'''
        self.redis_conn = redis_conn
        self.detType = detectionType
        self.id = id
        self.alert = False

        logging.debug('Tester Detection Module start and wait for initialization command')

    def load_configuration(self):
        ''' load necessary configuration '''

        CAPTURE_DONE = False
        ''' FIXME: load parameter/configuration'''

        logging.debug('Configuration setting successed: {}'.format(CAPTURE_DONE))
        self.redis_conn.publish(
            'tester.{}.result'.format(self.id),
            json2str({
                'stage': 'beginCapture',
                'status': 'success' if CAPTURE_DONE else 'failed'
            })
        )

    def capture_test_screen (self):
        ''' capture test screen '''

        TEST_READY = False
        ''' FIXME: capture image and make sure test screen ready '''

        logging.debug('Configuration setting successed: {}'.format(TEST_READY))
        self.redis_conn.publish(
            'tester.{}.result'.format(self.id),
            json2str({
                'stage': 'testScreen',
                'status': 'success' if TEST_READY else 'failed'
            })
        )
    
    def _mask_compare (self):
        ''' masking and comparison thread '''
        while True:

            ''' 
                FIXME: start getting image, mask and compare the image
                FIXME: once detected call redis_conn to send out the result
                FIXME: stage should be popup | alert based on detection stage
                FIXME: if alert is True, start counting 5s to check interaction
            '''

            if self.th_quit.is_set():
                break

    def start_mask_compare (self):
        ''' start masking and compare '''
        self.th_quit = threading.Event()
        self.th = threading.Thread(target=self._mask_compare)
        self.th.start()
    
    def set_alert_stage (self, stage, status=False):
        ''' setting of alert stage '''
        self.alert = status
        _stage = 'Detection' if stage == 'alert-msg' else 'Switch'
        logging.debug('Alert set to {} by {}'.format(self.alert, _stage))
    
    def close (self):
        self.th_quit.set()


def video_capture(file):
    #video capture
    cap = cv2.VideoCapture(file)

    #frame characteristics
    new_frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return cap, frame_width, frame_height

def mask_image(frame, frame_height, threshold):
    frame = frame[:int(frame_height * threshold), :]

    return frame, threshold

def test_screen(file):
    cap, frame_width, frame_height = video_capture(file)

    ret, prev_frame = cap.read()
    prev_frame, threshold = mask_image(prev_frame, frame_height, threshold=0.96)

    prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None
    full_screen_change = (frame_width * frame_height * threshold) * 0.5

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        #grayscale the frame
        frame, _ = mask_image(frame, frame_height, threshold=0.96)
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_diff = cv2.absdiff(frame_gray, prev_frame_gray)
        _, thresh_diff = cv2.threshold(frame_diff, 50, 255, cv2.THRESH_BINARY)

        #nonzero pixel count
        nonzero_pixels = cv2.countNonZero(thresh_diff)

        #if nonzero pixel values greather than thresholding == UI detected
        if nonzero_pixels > full_screen_change:
            cv2.putText(frame, 'State 4: No Alarm', (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 0, 255), 2, cv2.LINE_AA)


        else:
            cv2.putText(frame, 'State 2: Not in Tester UI', (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 0, 255), 2, cv2.LINE_AA)

        thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)
        concatenated_frame = cv2.hconcat([frame, thresh_diff_bgr])

        cv2.imshow('Video Feed', concatenated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def change_detection(file):

    #return cap from video_capture function
    cap, frame_height, frame_width = video_capture(file)

    #save previous frame and convert to grayscale
    ret, prev_frame = cap.read()
    prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None

    #on and off flags
    flag = False
    current_state = 0

    #thresholded area for contours
    min_area = 15000

    #fps for short clip
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = int(fps * 30)  # 180 seconds for 3 minutes
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    #fps for 5 second time stop
    fps_stop = int(fps * 5)
    frame_counter = 0

    #video save
    # fourcc = cv2.VideoWriter_fourcc(*'XVID')
    # out = cv2.VideoWriter('new_algo_test.mp4', fourcc, fps, (frame_width, frame_height))

    while ret:
        #save current frame
        ret, current_frame = cap.read()
        if not ret:
            break

        #detecting changes
        current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        frame_diff = cv2.absdiff(current_frame_gray, prev_frame_gray)
        _, thresh_diff = cv2.threshold(frame_diff, 50, 255, cv2.THRESH_BINARY)

        #detecting popup changes
        nonzero_pixels = cv2.countNonZero(thresh_diff)
        significant_change_threshold = (frame_width * frame_height) * 0.001
        minor_change_threshold = (frame_width * frame_height) * 0.0001
        # significant_change_detected = False

        # contouring
        contours, _ = cv2.findContours(thresh_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_change_detected = any(cv2.contourArea(contour) > min_area for contour in contours)
        # for contour in contours:
        #     if cv2.contourArea(contour) > min_area:
        #         significant_change_detected = True
        #         x, y, w, h = cv2.boundingRect(contour)
        #         # Draw the rectangle on the current frame to visualize the change
        #         cv2.rectangle(current_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green rectangle


        if nonzero_pixels > significant_change_threshold and significant_change_detected:
            if not flag:
                # current_state = 1
                frame_counter = 0
                flag = True
        elif nonzero_pixels > minor_change_threshold and flag:
            current_state = 0
            flag = False

        if flag:
            if frame_counter >= fps_stop:
                current_state = 1
            frame_counter += 1

        if current_state == 1:
            display_text = 'State 3: Alarm'
            text_color = (0, 255, 0)
        else:
            display_text = 'State 4: No Alarm'
            text_color = (0, 0, 255)

        thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)
        cv2.putText(current_frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        concatenated_frame = cv2.hconcat([current_frame, thresh_diff_bgr])
        # cv2.putText(concatenated_frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)

        # Show the frame
        cv2.imshow('Original and Significant Changes', concatenated_frame)

        prev_frame_gray = current_frame_gray

        # out.write(concatenated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    # out.release()
    cv2.destroyAllWindows()





if __name__ == "__main__":
    tester_check = '/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-29 08-08-11 SDU CT Tester.mp4'
    ui_check = '/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4'
    # test_screen(tester_check)
    change_detection(ui_check)