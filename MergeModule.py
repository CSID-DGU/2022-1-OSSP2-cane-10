import numpy as np
from sqlalchemy import false, true
from enum import Enum


class Road(Enum):
    background = 0
    bike_lane = 1  # 자전거 도로
    caution_zone = 2  # 주의 구역
    crosswalk = 3  # 횡단 보도
    guide_block = 4  # 점자 블록
    roadway = 5  # 차도
    sidewalk = 6  # 인도


def count_roads(arr):  # 도로 카테고리 별 픽셀 수
    # 입력
    # arr : numpy array
    # return : 인덱스 별 픽셀 수 ex list[6] = sidewalk 픽셀 수
    roads = []
    for r in Road:
        roads += (arr == r.value).sum()
    return roads


def reduce_arr(arr: np.ndarray, n: int) -> np.ndarray:
    # 입력
    # arr : 2차원 numpy array
    # n : int
    # return : 1/n로 축소된 arr
    if arr.ndim !=2:
      print("2차원 배열만 처리 가능합니다.")
      return
    
    column, row = arr.shape
    for i in range(column, 0, -n):
      arr = np.delete(arr, i, axis=0)

    for i in range(row, 0, -n):
      arr = np.delete(arr, i, axis = 1)
    
    return arr

class MergeModule:
    def __init__(self):
        self.now_road = 0  # 현재도로 초기값 background

    def current_road(self, class_segmap, distance):  # 현재 나의 도로 enum 값
        # 입력
        # class_segmap : 인식된 도로의 class로 segmentation된 numpy array(img size)
        y, x = class_segmap.shape
        # y 축의 하단 20%, x축의 중앙 30%로 Indexing
        roads = count_roads(class_segmap[int(y*0.75):, int(x*0.3):int(x*0.65)])
        new_road = roads.index(max(roads))  # 현재 나의 도로 enum 값
        self.now_road = new_road  # 현재 나의 도로 update

    def dep_road(self, class_segmap, distance, reduce = 4):  # 도로 별 거리
        # 입력
        # class_segmap : 인식된 도로의 class로 segmentation된 1 channel numpy array(img size)
        # distance : 픽셀 별 상대적 거리, 1 channel numpy array(img size)
        # 출력
        # Road에 저장된 도로 클래스 별로 거리가 존재하는 경우 0~1 사이의 실수로, 아닌 경우, 100.0을 출력 
        # 배열 크기는 Road에 저장된 도로 클래스의 수와 같다.
        # ex) [0.1, 0.4, 0.3, 0.1, 100.0, 0.3, 0.12]

        res = [100.0 for r in Road] # 도로 수만큼 100.0을 원소로 가지는 배열 생성

        reduced_segmap = reduce_arr(class_segmap, reduce) # 1/reduce로 축소
        reduced_distance = reduce_arr(distance, reduce)

        reduced_segmap.reshape(-1) # 1차원으로 차원 축소
        reduced_distance.reshape(-1)

        for class_seg, distance in zip(reduced_segmap, reduced_distance):
          if res[class_seg] > distance:
            res[class_seg] = distance # 저장된 최소 거리보다 작은 값이 입력으로 들어오면, 클래스의 최소 거리를 업데이트

        return res

    def dep_objects(self, object_class, objcet_location, distance):  # 장애물 별 거리
        # 입력
        # objcet_class : 인식된 장애물의 class, [장애물, 장애물, 장애물, ...] ex)[1, 2, 3,...]
        # objcet_location : 인식된 장애물의 위치, [[[왼쪽 위 점], [오른쪽 위 점], [왼쪽 아래 점], [오른쪽 아래 점]], ...] ex) [[[x1,y1], [x2,y1], [x1,y2], [x2,y2]], ...]
        # distance : 픽셀 별 상대적 거리, 1 channel numpy array
        res = []
        for loc in objcet_location:
            y1, y2, x1, x2 = map(
                int, [loc[0][1], loc[3][1], loc[0][0], loc[1][0]])  # 값 수정해야함
            # distance를 장애물의 범위 내로 슬라이싱
            cut_distance = distance[y1:y2, x1:x2]
            res.append(np.min(cut_distance))  # 최솟값 추가
        return object_class, res

    def loc_object(self, size, objcet_location):  # 장애물 위치(좌측, 중앙, 우측)
        # 입력
        # size : 가로 x 세로, ex) (width, height)
        # objcet_location : 인식된 장애물의 위치, [[[왼쪽 위 점], [오른쪽 위 점], [왼쪽 아래 점], [오른쪽 아래 점]], ...] ex) [[[x1,y1], [x2,y1], [x1,y2], [x2,y2]], ...]
        # 출력
        # 좌측, 중앙, 우측 해당 여부, [bool, bool, bool]
        res = [false, false, false]
        width, height = size
        right, left = objcet_location[0][0][0], objcet_location[0][1][0]
        if width/3 > left:
            res[0] = true  # 좌측 true로
        elif width*2/3 > left:
            res[1] = true  # 중앙을 true로
        else:
            res[2] = true  # 우측을 true로
            return res

        if width/3 > right:
            pass  # 좌측 이미 true일 것이므로 pass
        elif width*2/3 > right:
            res[1] = true  # 중앙 true로
        else:
            res[2] = true  # 우측을 true로
        return res  # 함수 종료
