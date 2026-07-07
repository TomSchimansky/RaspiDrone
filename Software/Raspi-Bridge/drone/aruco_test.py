import cv2


class CameraTest:
    def __init__(self):
        self.cam = cv2.VideoCapture(0)

    def grab_frames(self):
        print("isOpened:", self.cam.isOpened())

        while self.cam.isOpened():
            success, frame = self.cam.read()
            print(success, type(frame))

        self.cam.release()
        print("camera closed")


if __name__ == "__main__":
    cam = CameraTest()
    cam.grab_frames()
