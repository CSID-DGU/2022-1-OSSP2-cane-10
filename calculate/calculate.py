# 임계값 설정 임계값을 넘는 장애물만 장애물 배열 넣는다.
# 도로 이탈은 높은 위험도로 설정한다.
# 횡단보도 일정거리 이하로 들어오면 장애물에 넣는다.
import numpy as np
import MergeModule
# 위험도의 최대값은 100으로 설정
# 거리는 대략적인 상대값이 나오고 이 상대적인 값도 정확하지 않기 때문에 소수점 첫째자리까지만 사용
# 도로이탈의 위험도는 특정 거리안에서 100 상수로 설정 같은 위험도가 있더라도 가장 우선순위로 한다.
# 같은 거리에서 위험도는 
# 도로이탈 > 차량 > 이륜차 > 자전거 = 사람 > 소화전 > 가로수 > 전봇대으로 설정
# 위험 수준을 4가지로 구분해서 나눈다 도로이탈, 차량, {자전거, 사람}, {소화전, 가로수, 전봇대}
# 5, 10
class Data:
    same_side = np.array([[9, 7, 5],
                          [8, 6, 2],
                          [4, 3, 1]])
    def trans_distance(self, distance):
        if distance >= 0 and distance < 0.1:
            return 0
        elif distance >= 0.1 and distance < 0.2:
            return 0.1
        elif distance >= 0.2 and distance < 0.3:
            return 0.2
        elif distance >= 0.3 and distance < 0.4:
            return 0.3
        elif distance >= 0.4 and distance < 0.5:
            return 0.4
        elif distance >= 0.5 and distance < 0.6:
            return 0.5
        elif distance >= 0.6 and distance < 0.7:
            return 0.6
        elif distance >= 0.7 and distance < 0.8:
            return 0.7
        elif distance >= 0.8 and distance < 0.9:
            return 0.8
        else:
            return 0.9
    def calculate_danger(self, obj_class, obj_distance):
        # 5. car 7. truck 8. bus 10. motorcycle
        if obj_class == 5 or obj_class == 7 or obj_class == 8 or obj_class == 10:
            i = 0
        # 1. person 11. movable_signage
        elif obj_class == 1 or obj_class == 11:
            i = 1
        # 2. pole 3. bollard 4. tree_trunk 6. trafficlight 9. traffic_sign 12. potted_plant 13. wheelchair
        else:
            i = 2
        if obj_distance >= 0 and obj_distance <= 0.3:
            j = 0
        elif obj_distance >= 0.4 and obj_distance <= 0.7:
            j = 1
        else:
            j = 2
        return self.same_side[i][j]
    
    def return_highest_danger(self, object_class, loc_obj_res, dep_obj_res, dep_road_res, cur_road):
        #입력
        # object_class : 인식된 장애물의 class, [장애물, 장애물, 장애물, ...] ex)[1, 2, 3,...]
        # loc_obj_res : 인식된 장애물의 위치
        # dep_obj_res : 인식된 장애물의 거리
        # dep_road_res : 도로별 가장 가까운 거리
		# cur_road : 현재 사용자가 있는 도로의 종류
        #현재 도로가 인도일 때 차도가 일정거리 이내이면 도로이탈 반환
        # cur_road 6: 차도
        # cur_road 3: 횡단보도
        if cur_road == 6 and dep_road_res[5] <= 0.15:
            res = np.array([-1, 0])
            return res
        if cur_road == 3 and dep_road_res[5] <= 0.2:
            res = np.array([-2, 0])
            return res
        danger = -1
        #한 프레임 내의 장애물의 위험도를 계산하여 가장 높은 위험도를 가진 장애물의 종류와 위치를 반환
        for i in range(len(dep_obj_res)):
            temp = self.calculate_danger(object_class[i], dep_obj_res[i])
            if danger < temp:
                res = [object_class[i], loc_obj_res[i]]
        return np.array(res)
                
        
    def __init__(self):
        self.danger = 0
        
    def __lt__(self, other):
        return self.danger < other.danger