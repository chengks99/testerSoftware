import cv2
import numpy as np
import datetime as dt

import threading
import sys
import logging
import pathlib


scriptPath = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(scriptPath.parent / 'common'))
from jsonutils import json2str

DET_TYPE = [
    {'frame_threshold': 5, 'threshold': 150},
    {'frame_threshold': 30, 'threshold': 150},
    {'frame_threshold': 5, 'threshold': 50},
]


class TesterDetection(object):
    def __init__(self, file, redis_conn, id, detectionType=0, displayVid=False) -> None:
        ''' init tester detection module'''
        self.redis_conn = redis_conn
        self.detType = detectionType
        self.display_video = displayVid
        self.id = id
        self.stage = 'idle'

        #inits
        self.file = file
        self.new_frame_width = None
        self.frame_width = None
        self.frame_height = None

        self.frame_threshold = None
        self.threshold = None

        self.fps = 0
        self.fps_stop = 0

        self.flag = False
        self.frame_counter = 0
        self.current_state = 0

        self.min_area = 500


        self.prev_frame_gray = None

        logging.debug('Tester Detection Module start and wait for initialization command')

    def load_configuration(self):
        ''' load necessary configuration '''

        CAPTURE_DONE = False
        self.frame_threshold = DET_TYPE[self.detType]['frame_threshold']
        self.threshold = DET_TYPE[self.detType]['threshold']

        if self.frame_threshold and self.threshold:
            print(self.frame_threshold)
            print(self.threshold)
            CAPTURE_DONE = True

        logging.debug('Configuration setting successed: {}'.format(CAPTURE_DONE))
        self.redis_conn.publish(
            'tester.{}.result'.format(self.id),
            json2str({
                'stage': 'beginCapture',
                'status': 'success' if CAPTURE_DONE else 'failed'
            })
        )

    # FIXME: test screen detection
    def __test_screen_detection(self, frame):

        ''' detect test screen, return True if test screen detected, false otherwise'''
        current_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_diff = cv2.absdiff(current_frame_gray, self.prev_frame_gray)
        _, thresh_diff = cv2.threshold(frame_diff, self.threshold, 255, cv2.THRESH_BINARY)

        nonzero_pixels = cv2.countNonZero(thresh_diff)

        full_screen_change = (self.frame_width * self.frame_height) * 0.5

        if nonzero_pixels > full_screen_change:
            self.current_state = 0
            return True

        self.prev_frame_gray = current_frame_gray

        return True

    def capture_test_screen(self):
        ''' capture test screen '''
        TEST_READY = False

        _cap = cv2.VideoCapture(self.file)
        _cap.open(0, apiPreference=cv2.CAP_V4L2)

        ret, prev_frame = _cap.read()
        self.prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None

        ###???###
        # currTime = dt.datetime.now()
        # stopTime = currTime + dt.timedelta(seconds=timeout)

        #frame dimensions
        self.new_frame_width = int(_cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)
        self.frame_width = int(_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        #fps threshold
        self.fps = _cap.get(cv2.CAP_PROP_FPS)
        self.fps_stop = int(self.fps * self.frame_threshold)

        while not TEST_READY:
            _, _frame = _cap.read()
            TEST_READY = self.__test_screen_detection(_frame)
            print(TEST_READY)
            if self.display_video: cv2.imshow('testScreen', _frame)
            # _now = dt.datetime.now()
            # if _now > stopTime: break
        _cap.release()
        if self.display_video: cv2.destroyAllWindows()

        logging.debug('Configuration setting successed: {}'.format(TEST_READY))
        self.redis_conn.publish(
            'tester.{}.result'.format(self.id),
            json2str({
                'stage': 'testScreen',
                'status': 'success' if TEST_READY else 'failed'
            })
        )

    # FIXME: pop up detection
    def __popup_detection(self, nonzero_pixels, significant_change_detected, significant_change_threshold):
        ''' detect pop up, True if pop up detected, False otherwise '''

        if nonzero_pixels > significant_change_threshold and significant_change_detected:
            print('popup detected')
            return True


        return False


    # FIXME: user interaction detection
    def __interaction_detection(self, nonzero_pixels, minor_change_threshold, mouse_change_threshold):
        ''' detect user interfaction, True if detected, False otherwise '''

        if nonzero_pixels > minor_change_threshold and nonzero_pixels < mouse_change_threshold:
            print('interaction detected')
            return True

        return False


    def _mask_compare(self):
        ''' masking and comparison thread '''

        _cap = cv2.VideoCapture(self.file)
        _cap.open(0, apiPreference=cv2.CAP_V4L2)



        fps = _cap.get(cv2.CAP_PROP_FPS)
        start_frame = int(fps * 1410)  # 180 seconds for 3 minutes
        _cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)


        ret, prev_frame = _cap.read()
        self.prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None

        popUp = False
        alertTime = None

        while True:
            _, _frame = _cap.read()

            #process frame and thresholds
            current_frame_gray = cv2.cvtColor(_frame, cv2.COLOR_BGR2GRAY)
            frame_diff = cv2.absdiff(current_frame_gray, self.prev_frame_gray)
            _, thresh_diff = cv2.threshold(frame_diff, self.threshold, 255, cv2.THRESH_BINARY)

            nonzero_pixels = cv2.countNonZero(thresh_diff)
            significant_change_threshold = (self.frame_width * self.frame_height) * 0.001
            minor_change_threshold = (self.frame_width * self.frame_height) * 0.0001
            mouse_change_threshold = (self.frame_width * self.frame_height) * 0.0005

            contours, _ = cv2.findContours(thresh_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            significant_change_detected = any(cv2.contourArea(contour) > self.min_area for contour in contours)
            
            self.prev_frame_gray = current_frame_gray
            
            print(self.stage)
            
            if self.stage == 'reset':
                popUp = False
                self.stage = 'idle'
                print ('******* popUp: {}, stage: {}'.format(popUp, self.stage))

            if not popUp:
                popUp = self.__popup_detection(nonzero_pixels, significant_change_detected, significant_change_threshold)
                #print('no popup')
            if popUp:
                #print('yes popup')
                if self.stage == 'idle':
                    self.redis_conn.publish(
                        'tester.{}.result'.format(self.id),
                        json2str({
                            'stage': 'popUp',
                            'status': 'success'
                        })
                    )
                    alertTime = dt.datetime.now()
                    self.stage = 'preAlert'
                elif self.stage == 'preAlert':
                    interaction = self.__interaction_detection(nonzero_pixels, minor_change_threshold, mouse_change_threshold)
                    # print(f'interaction:{interaction}')
                    if interaction:
                        self.stage = 'reset'
                        self.redis_conn.publish(
                            'tester.{}.result'.format(self.id),
                            json2str({
                                'stage': 'alert-reset',
                                'status': 'success'
                            })
                        )
                    else:
                        _now = dt.datetime.now()
                        _diff = _now - alertTime
                        if _diff.total_seconds() > self.frame_threshold:
                            self.stage = 'alert'
                            self.redis_conn.publish(
                                'tester.{}.alert'.format(self.id),
                                json2str({
                                    'stage': 'alert',
                                    'status': 'activated'
                                })
                            )
            if self.display_video: cv2.imshow('Masking', _frame)
            if self.th_quit.is_set():
                break
        _cap.release()
        if self.display_video: cv2.destroyAllWindows()
        logging.debug('Masking & Comparison stopped')

    def start_mask_compare(self):
        ''' start masking and compare '''
        self.th_quit = threading.Event()
        self.th = threading.Thread(target=self._mask_compare)
        self.th.start()

    def set_alert_stage(self, stage, status=False):
        ''' setting of alert stage '''
        if status:  
            self.stage = 'reset'
        _stage = 'Detection' if stage == 'alert-msg' else 'Switch'
        logging.debug('Alert set to {} by {}'.format(self.stage, _stage))

    def close(self):
        self.th_quit.set()

#
# def video_capture(file):
#     # video capture
#     cap = cv2.VideoCapture(file)
#
#     # frame characteristics
#     new_frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)
#     frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#
#     return cap, frame_width, frame_height
#
#
# def mask_image(frame, frame_height, threshold):
#     frame = frame[:int(frame_height * threshold), :]
#
#     return frame, threshold
#
#
# def test_screen(file):
#     cap, frame_width, frame_height = video_capture(file)
#
#     ret, prev_frame = cap.read()
#     prev_frame, threshold = mask_image(prev_frame, frame_height, threshold=0.96)
#
#     prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None
#     full_screen_change = (frame_width * frame_height * threshold) * 0.5
#
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break
#
#         # grayscale the frame
#         frame, _ = mask_image(frame, frame_height, threshold=0.96)
#         frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#         frame_diff = cv2.absdiff(frame_gray, prev_frame_gray)
#         _, thresh_diff = cv2.threshold(frame_diff, 50, 255, cv2.THRESH_BINARY)
#
#         # nonzero pixel count
#         nonzero_pixels = cv2.countNonZero(thresh_diff)
#
#         # if nonzero pixel values greather than thresholding == UI detected
#         if nonzero_pixels > full_screen_change:
#             cv2.putText(frame, 'State 4: No Alarm', (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
#                         1, (0, 0, 255), 2, cv2.LINE_AA)
#
#
#         else:
#             cv2.putText(frame, 'State 2: Not in Tester UI', (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
#                         1, (0, 0, 255), 2, cv2.LINE_AA)
#
#         thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)
#         concatenated_frame = cv2.hconcat([frame, thresh_diff_bgr])
#
#         cv2.imshow('Video Feed', concatenated_frame)
#
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#
#     cap.release()
#     cv2.destroyAllWindows()
#
#
# def change_detection(file):
#     # return cap from video_capture function
#     cap, frame_height, frame_width = video_capture(file)
#
#     # save previous frame and convert to grayscale
#     ret, prev_frame = cap.read()
#     prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None
#
#     # on and off flags
#     flag = False
#     current_state = 0
#
#     # thresholded area for contours
#     min_area = 15000
#
#     # fps for short clip
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     start_frame = int(fps * 30)  # 180 seconds for 3 minutes
#     cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
#
#     # fps for 5 second time stop
#     fps_stop = int(fps * 5)
#     frame_counter = 0
#
#     # video save
#     # fourcc = cv2.VideoWriter_fourcc(*'XVID')
#     # out = cv2.VideoWriter('new_algo_test.mp4', fourcc, fps, (frame_width, frame_height))
#
#     while ret:
#         # save current frame
#         ret, current_frame = cap.read()
#         if not ret:
#             break
#
#         # detecting changes
#         current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
#         frame_diff = cv2.absdiff(current_frame_gray, prev_frame_gray)
#         _, thresh_diff = cv2.threshold(frame_diff, 50, 255, cv2.THRESH_BINARY)
#
#         # detecting popup changes
#         nonzero_pixels = cv2.countNonZero(thresh_diff)
#         significant_change_threshold = (frame_width * frame_height) * 0.001
#         minor_change_threshold = (frame_width * frame_height) * 0.0001
#         # significant_change_detected = False
#
#         # contouring
#         contours, _ = cv2.findContours(thresh_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#         significant_change_detected = any(cv2.contourArea(contour) > min_area for contour in contours)
#         # for contour in contours:
#         #     if cv2.contourArea(contour) > min_area:
#         #         significant_change_detected = True
#         #         x, y, w, h = cv2.boundingRect(contour)
#         #         # Draw the rectangle on the current frame to visualize the change
#         #         cv2.rectangle(current_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green rectangle
#
#         if nonzero_pixels > significant_change_threshold and significant_change_detected:
#             if not flag:
#                 # current_state = 1
#                 frame_counter = 0
#                 flag = True
#         elif nonzero_pixels > minor_change_threshold and flag:
#             current_state = 0
#             flag = False
#
#         if flag:
#             if frame_counter >= fps_stop:
#                 current_state = 1
#             frame_counter += 1
#
#         if current_state == 1:
#             display_text = 'State 3: Alarm'
#             text_color = (0, 255, 0)
#         else:
#             display_text = 'State 4: No Alarm'
#             text_color = (0, 0, 255)
#
#         thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)
#         cv2.putText(current_frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
#         concatenated_frame = cv2.hconcat([current_frame, thresh_diff_bgr])
#         # cv2.putText(concatenated_frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
#
#         # Show the frame
#         cv2.imshow('Original and Significant Changes', concatenated_frame)
#
#         prev_frame_gray = current_frame_gray
#
#         # out.write(concatenated_frame)
#
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#
#     # Cleanup
#     cap.release()
#     # out.release()
#     cv2.destroyAllWindows()
#
#
# if __name__ == "__main__":
#     tester_check = '/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-29 08-08-11 SDU CT Tester.mp4'
#     ui_check = '/Users/juneyoungseo/Documents/Panasonic/test videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4'
#     # test_screen(tester_check)
#     change_detection(ui_check)
#
#
#     def capture_test_screen(self, nonzero_pixels, full_screen_change):
#         ''' capture test screen '''
#
#         TEST_READY = False  # Initialize the flag before entering the loop
#
#         while True:
#             ret, current_frame = self.cap.read()
#             if not ret: continue
#
#             current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
#             frame_diff = cv2.absdiff(current_frame_gray, self.prev_frame_gray)
#             _, thresh_diff = cv2.threshold(frame_diff, self.threshold, 255, cv2.THRESH_BINARY)
#
#             nonzero_pixels = cv2.countNonZero(thresh_diff)
#             full_screen_change = (self.frame_width * self.frame_height) * 0.5
#
#             contours, _ = cv2.findContours(thresh_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#             significant_change_detected = any(cv2.contourArea(contour) > self.min_area for contour in contours)
#
#             self.capture_test_screen(nonzero_pixels, full_screen_change)
#
#             # Check if TEST_READY has been turned True, then break the loop
#             if TEST_READY:
#                 # Prepare and send out the Redis message before breaking
#                 self.redis_conn.publish(
#                     'tester.{}.result'.format(self.id),
#                     json2str({
#                         'stage': 'popup' if significant_change_detected else 'alert',  # or your specific logic here
#                         'status': 'success' if TEST_READY else 'failed'
#                     })
#                 )
#                 break  # Exit the loop
