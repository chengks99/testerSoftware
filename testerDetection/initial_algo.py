import cv2
import numpy as np
import time
import pathlib
import sys
from plugin_module import PluginModule

scriptPath = pathlib.Path(__file__).parent.resolve()
sys.path.append(str(scriptPath.parent / 'common'))
import argsutils as au
from jsonutils import json2str

class detection:
    def __init__(self, file, ref_id, redis_conn):

        self.file = file

        #video extraction
        self.cap = None

        #frame charateristics
        self.frame_width = None
        self.frame_height = None
        self.new_frame_width = None

        #frame processing
        self.fps = 0
        self.fps_stop = 0
        self.prev_frame_time = 0

        #minimum area contour
        self.min_area = 2000

        #on off flags
        self.flag = False
        self.frame_counter = 0
        self.current_state = 0

        #detection variables
        self.prev_frame_gray = None
        self.frame_threshold = None
        self.threshold = None

        #video
        self.display_text = None
        self.text_color = None

        self.redis_conn = redis_conn
        self.id = ref_id


    def user_parameter(self):
        # parameter for threshold
        print("For Type 1 Tester UI: input frame threshold = 5 & threshold = 150\n")
        print("For Type 2 Tester UI: input frame threshold = 30 \n")
        print("For Type 3 Tester UI: input frame threshold = 5 & threshold = 50\n")

        self.frame_threshold = float(input("Please input the framing threshold: "))
        self.threshold = float(input("Please input the threshold: "))

        if self.redis_conn and self.id:
            self.redis_conn.publish(
                'tester.{}.result'.format(self.id),
                json2str({
                    'stage': 'init',
                    'status': 'success'
                })
            )


    def video_capture(self):
        # video capture
        self.cap = cv2.VideoCapture(self.file)

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        start_frame = int(fps * 40)  # 180 seconds for 3 minutes
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        if not self.cap.isOpened():
            print("Error Opening File")
            return
        # frame characteristics
        self.new_frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # fps processing
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps_stop = int(self.fps * self.frame_threshold)

        if self.redis_conn and self.id:
            self.redis_conn.publish(
                'tester.{}.result'.format(self.id),
                json2str({
                    'stage': 'beginCapture',
                    'status': 'success'
                })
            )



    def tester_screen_check(self, nonzero_pixels, full_screen_change):
        if self.current_state == -1:
            self.display_text = 'State 2: Not in Test Screen'
            self.text_color = (0, 0, 255)
            if nonzero_pixels > full_screen_change:
                self.current_state = 0

        # return self.current_state, self.display_text, self.text_color


    def alarm(self, nonzero_pixels, significant_change_detected, significant_change_threshold):
        if nonzero_pixels > significant_change_threshold and significant_change_detected:
            if not self.flag:
                self.frame_counter = 0
                self.flag = True
            else:
                self.flag = False
                self.current_state = 0

        if self.flag:
            if self.frame_counter >= self.fps_stop:
                self.current_state = 1  # Alarm state
            self.frame_counter += 1

        # return self.current_state, self.flag


    def alarm_reset(self, nonzero_pixels, minor_change_threshold, mouse_change_threshold):
        if nonzero_pixels > minor_change_threshold and self.flag and nonzero_pixels < mouse_change_threshold:
            self.current_state = 0
            self.flag = False

        # return self.current_state, self.flag

    def process_frames(self):

        # save previous frame and convert to grayscale
        ret, prev_frame = self.cap.read()
        self.prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if ret else None

        while True:
            ret, current_frame = self.cap.read()
            if not ret:
                break

            current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            frame_diff = cv2.absdiff(current_frame_gray, self.prev_frame_gray)
            _, thresh_diff = cv2.threshold(frame_diff, self.threshold, 255, cv2.THRESH_BINARY)

            nonzero_pixels = cv2.countNonZero(thresh_diff)
            significant_change_threshold = (self.frame_width * self.frame_height) * 0.001
            full_screen_change = (self.frame_width * self.frame_height) * 0.5
            minor_change_threshold = (self.frame_width * self.frame_height) * 0.0001
            mouse_change_threshold = (self.frame_width * self.frame_height) * 0.0005

            contours, _ = cv2.findContours(thresh_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            significant_change_detected = any(cv2.contourArea(contour) > self.min_area for contour in contours)

            self.tester_screen_check(nonzero_pixels, full_screen_change)



            self.alarm(nonzero_pixels, significant_change_detected, significant_change_threshold)



            self.alarm_reset(nonzero_pixels, minor_change_threshold, mouse_change_threshold)


            # print(self.flag)


            # Insert display and frame writing logic here as necessary

            if self.current_state == 1:
                self.display_text = 'State 3: Alarm'
                self.text_color = (255, 0, 255)
            else:
                self.display_text = 'State 4: No Alarm'
                self.text_color = (0, 255, 0)

            thresh_diff_bgr = cv2.cvtColor(thresh_diff, cv2.COLOR_GRAY2BGR)
            cv2.putText(current_frame, self.display_text, (400, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.text_color, 2)
            # cv2.putText(current_frame, frame_time_text, (800, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 165, 0), 2)
            concatenated_frame = cv2.hconcat([current_frame, thresh_diff_bgr])

            # Show the frame
            cv2.imshow('Original and Significant Changes', concatenated_frame)

            self.prev_frame_gray = current_frame_gray

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()

    def main(self):
        self.user_parameter()
        self.video_capture()
        self.process_frames()



if __name__ == "__main__":
    tester_check = '/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-29 08-08-11 SDU CT Tester.mp4'
    type_1 = '/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-26 10-36-47-ex2 SDU CT Tester.mp4' #40
    type_2 = '/Users/juneyoungseo/Documents/Panasonic/test_videos/2023-12-28 08-17-11 VSEB SEB Tester.mp4'


    type_3_1 = '/Users/juneyoungseo/Documents/Panasonic/test_videos/2024-01-05 11-49-29 SDU V2 Tester.mp4' #2620

    #problem: after sig change -> detect small mouse movement change for user interaction, but it also detects log movements
    type_3_2 = '/Users/juneyoungseo/Documents/Panasonic/test_videos/2024-01-09 13-01-57 NC CS4 SIB Tester.mp4' #1700

    #problem: the user do not move mouse -> instead just press ENTER to move on
    type_3_3 = '/Users/juneyoungseo/Documents/Panasonic/test_videos/2024-01-05 11-49-29 SDU V2 Tester.mp4' #660
#
#     # test_screen(tester_check)
#     # change_detection(type_1) #Type 1
#     # change_detection(tester_check) #starter screen
#     # change_detection(type_2) #Type 2
#     # change_detection(type_3_1) #type 3
#     # change_detection(type_3_3) #type 3
    detection_instance = detection(type_3_3)
    detection_instance.main()





