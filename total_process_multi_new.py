import cv2
import numpy as np
from odmodule.odmodule import OdModel
from depmodule.depmodule import DepModel
from segmodule import segmodule
from mergemodule.mergemodule import MergeModule
from alarmmodule.alarmmodule import Alarm
from calculate.calculate import Data
from threading import Thread
import time

def od_pred(id, img):
    print("장애물 인식 모듈 Loaded")
    global object_class, object_location, size, OdModule
    od_outputs, _ = OdModule.predict(img)
    object_class = od_outputs['instances'].pred_classes.cpu().numpy()
    size = od_outputs['instances'].image_size
    object_location = od_outputs['instances'].pred_boxes.tensor.cpu().numpy()
    object_location = object_location.astype(int)
    print("장애물 인식 모듈 Finished")


def seg_pred(id, img):
    print("도로 인식 모듈 Loaded")
    global class_segmap, SegModule
    segmap, _ = SegModule.predict(img)
    class_segmap = segmodule.convert(segmap)
    print("도로 인식 모듈 Finished")


def dep_pred(id, img):
    print("거리 예측 모듈 Loaded")
    global distance, DepModule
    image = DepModule.preprocess_image(img)
    distance = DepModule.predict(image)
    print("거리 예측 모듈 Finished")

def exe_alarm(id, image, classes, direction, order, object_location):
    print("알람 모듈 Loaded")
    global ArModule
    num = len(classes)
    for i in range(num):
        if classes[i] == -1 or classes[i] == -2:
            ArModule.runmodule(classes[i], direction[i])
            # 도로 시각화
        else:
            res_img = cv2.rectangle(image, (object_location[order[i]][0], object_location[order[i]][1]),
                                    (object_location[order[i]][2], object_location[order[i]][3]), (0, 0, 255), 2)
            ArModule.runmodule(classes[i], direction[i])
            cv2.imshow("result", res_img)
            cv2.waitKey(2000)
    print("알람 모듈 Finished")


OdModule = OdModel()
SegModule = segmodule.SegModule()
DepModule = DepModel()
DepModule.load_model(model_name="mono_640x192")
MgModule = MergeModule()
CacModule = Data()
ArModule = Alarm()

cap = cv2.VideoCapture("street3.avi")

while(True):
    start = time.time()
    ret, image = cap.read()

    object_location, object_class, size = None, None, None
    th1 = Thread(
        target=od_pred, args=(1, image))
    th1.start()

    class_segmap = None
    th2 = Thread(target=seg_pred, args=(2, image))
    th2.start()

    distance = None
    th3 = Thread(target=dep_pred, args=(3, image))
    th3.start()

    th1.join()
    th2.join()
    th3.join()

    print("정보 종합 모듈 Loaded")
    MgModule.current_road(class_segmap)
    cur_road = MgModule.now_road
    dep_road_res = MgModule.dep_road(class_segmap, distance)
    od_classes, res = MgModule.dep_objects(
        object_class, object_location, distance)
    od_location = MgModule.loc_object(size, object_location)
    print("정보 종합 모듈 Finished")

    print("위험도 계산 모듈 Loaded")
    classes, direction, order = CacModule.return_highest_danger(
        od_classes, od_location, res, dep_road_res, cur_road)
    print("위험도 계산 모듈 Finished")

    th4 = Thread(target=exe_alarm, args=(4, image, classes, direction, order, object_location))
    th4.start()

    end = time.time()
    print(f"{end - start:.5f} sec")
