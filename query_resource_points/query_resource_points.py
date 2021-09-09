
from urllib import request
from PIL import Image,ImageMath
from io import BytesIO
import json
import os
import time
import base64
import math



LABEL_URL      = 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/map/label/tree?app_sn=ys_obc'
POINT_LIST_URL = 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/map/point/list?map_id=2&app_sn=ys_obc'
MAP_URL        = "https://api-static.mihoyo.com/common/map_user/ys_obc/v1/map/info?map_id=2&app_sn=ys_obc&lang=zh-cn"

header = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'

FILE_PATH = os.path.dirname(__file__)

MAP_PATH = os.path.join(FILE_PATH,"icon","map_icon.jpg")
Image.MAX_IMAGE_PIXELS = None


# 这个常量放在up_map()函数里更新
CENTER = None
DISTANCE = 500

zoom = 0.5
resource_icon_offset = (-int(150*0.5*zoom),-int(150*zoom))
map_min_hw = 500


data = {
    "all_resource_type":{
        # 这个字典保存所有资源类型，
        # "1": {
        #         "id": 1,
        #         "name": "传送点",
        #         "icon": "",
        #         "parent_id": 0,
        #         "depth": 1,
        #         "node_type": 1,
        #         "jump_type": 0,
        #         "jump_target_id": 0,
        #         "display_priority": 0,
        #         "children": []
        #     },
    },
    "can_query_type_list":{
        # 这个字典保存所有可以查询的资源类型名称和ID，这个字典只有名称和ID
        # 上边字典里"depth": 2的类型才可以查询，"depth": 1的是1级目录，不能查询
        # "七天神像":"2"
        # "风神瞳":"5"

    },
    "all_resource_point_list" :[
            # 这个列表保存所有资源点的数据
            # {
            #     "id": 2740,
            #     "label_id": 68,
            #     "x_pos": -1789,
            #     "y_pos": 2628,
            #     "author_name": "✟紫灵心✟",
            #     "ctime": "2020-10-29 10:41:21",
            #     "display_state": 1
            # },
    ],
    "sort_resource_point_list":{
        # 这个字典存放已经分类好的资源点组，查询资源点时每个组会生成一张图片
        # "2":[
        #     [{"x_pos": -1789,"y_pos": 2628},]
        # ]
    },
    "date":"" #记录上次更新"all_resource_point_list"的日期
}


def update_map_icon():
    # 更新地图文件
    print("正在更新地图文件")
    schedule = request.Request(MAP_URL)
    schedule.add_header('User-Agent', header)

    with request.urlopen(schedule) as f:
        rew_data = f.read().decode('utf-8')
        data = json.loads(rew_data)["data"]["info"]["detail"]
        data = json.loads(data)

    map_url = data['slices'][0][0]["url"]
    request.urlretrieve(map_url, MAP_PATH)



def up_icon_image(sublist):
    # 检查是否有图标，没有图标下载保存到本地
    id = sublist["id"]
    icon_url = sublist["icon"]

    icon_path = os.path.join(FILE_PATH,"icon",f"{id}.png")

    if not os.path.exists(icon_path):
        print(f"正在更新图标 {id}")
        schedule = request.Request(icon_url)
        schedule.add_header('User-Agent', header)
        with request.urlopen(schedule) as f:
            icon = Image.open(f)
            icon = icon.resize((150, 150))

            box_alpha = Image.open(os.path.join(FILE_PATH,"icon","box_alpha.png")).getchannel("A")
            box = Image.open(os.path.join(FILE_PATH,"icon","box.png"))

            try:
                icon_alpha = icon.getchannel("A")
                icon_alpha = ImageMath.eval("convert(a*b/256, 'L')", a=icon_alpha, b=box_alpha)
            except ValueError:
                # 米游社的图有时候会没有alpha导致报错，这时候直接使用box_alpha当做alpha就行
                icon_alpha = box_alpha

            icon2 = Image.new("RGBA", (150, 150), "#00000000")
            icon2.paste(icon, (0, -10))

            bg = Image.new("RGBA", (150, 150), "#00000000")
            bg.paste(icon2, mask=icon_alpha)
            bg.paste(box, mask=box)

            with open(icon_path, "wb") as icon_file:
                bg.save(icon_file)

def is_point_distance(x1,y1,x2,y2,distance = DISTANCE):
    # 计算两点之间的距离看是不是小于 distance
    # 是的话返回 True 否则返回 False
    x = max(x1,x2) - min(x1,x2)
    y = max(y1,y2) - min(y1,y2)

    return math.sqrt(x*x + y*y) < distance

def grouping(point_list):
    # 对资源点进行分组，传入一个资源点列表，遍历列表把里的近的点位放在一起，
    # 最后返回一个嵌套的列表
    nested_list = []
    while point_list:
        son_list = []
        temp_list = []
        index = 0
        son_list.append(point_list[0])
        loop_fiag = True
        while loop_fiag:
            loop_fiag = False
            unclassified = []
            for unclassified_index in range(1,len(point_list)):
                add_flag = True
                for i in range(index,len(son_list)):
                    x1 = son_list[i]["x_pos"]
                    y1 = son_list[i]["y_pos"]
                    x2 = point_list[unclassified_index]["x_pos"]
                    y2 = point_list[unclassified_index]["y_pos"]
                    if is_point_distance(x1,y1,x2,y2):
                        temp_list.append(point_list[unclassified_index])
                        add_flag = False
                        loop_fiag = True
                        break
                if add_flag:
                    unclassified.append(point_list[unclassified_index])

            for point in temp_list:
                son_list.append(point)
            index = len(son_list) - 1
            point_list = unclassified

            if not loop_fiag:
                nested_list.append(son_list)

    return nested_list


def sort_resource_point():
    # 遍历资源点，把资源点按照ID进行分类，然后调用 grouping() 来对点的距离进行分组

    for resource_point in data["all_resource_point_list"]:
        resource_id = str(resource_point["label_id"])
        x_pos = resource_point["x_pos"]
        y_pos = resource_point["y_pos"]
        if not resource_id in data["sort_resource_point_list"]:
            # 第一次分组
            new_list = [{"x_pos":x_pos,"y_pos":y_pos}]
            data["sort_resource_point_list"].setdefault(resource_id,new_list)
            continue
        else:
            # 如果有了这个ID直接添加数据
            temp_dict = {"x_pos":x_pos,"y_pos":y_pos}
            data["sort_resource_point_list"][resource_id].append(temp_dict)

    for resource_id in data["sort_resource_point_list"].keys():
        data["sort_resource_point_list"][resource_id] = grouping(data["sort_resource_point_list"][resource_id])



def up_label_and_point_list():
    # 更新label列表和资源点列表

    schedule = request.Request(LABEL_URL)
    schedule.add_header('User-Agent', header)
    with request.urlopen(schedule) as f:
        if f.code != 200:  # 检查返回的状态码是否是200
            raise ValueError(f"资源标签列表初始化失败，错误代码{f.code}")
        label_data = json.loads(f.read().decode('utf-8'))

        for label in label_data["data"]["tree"]:
            data["all_resource_type"][str(label["id"])] = label
            for sublist in label["children"]:
                data["all_resource_type"][str(sublist["id"])] = sublist
                data["can_query_type_list"][sublist["name"]] = str(sublist["id"])
                up_icon_image(sublist)
            label["children"] = []

    schedule = request.Request(POINT_LIST_URL)
    schedule.add_header('User-Agent', header)
    with request.urlopen(schedule) as f:
        if f.code != 200:  # 检查返回的状态码是否是200
            raise ValueError(f"资源点列表初始化失败，错误代码{f.code}")
        test = json.loads(f.read().decode('utf-8'))
        data["all_resource_point_list"] = test["data"]["point_list"]

    sort_resource_point()
    data["date"] = time.strftime("%d")


def up_map(re_download_map = False):
    global CENTER

    if (not os.path.exists(MAP_PATH)) or (re_download_map):
        update_map_icon()

    schedule = request.Request(MAP_URL)
    schedule.add_header('User-Agent', header)
    with request.urlopen(schedule) as f:
        rew_data = f.read().decode('utf-8')
        data = json.loads(rew_data)["data"]["info"]["detail"]
        data = json.loads(data)

    CENTER = data["origin"]




# 初始化
up_label_and_point_list()
up_map()




class Resource_map(object):

    def __init__(self,resource_name,point_list):
        self.resource_id = str(data["can_query_type_list"][resource_name])

        self.map_image = Image.open(MAP_PATH)
        self.map_size = self.map_image.size

        # 地图要要裁切的左上角和右下角坐标
        # 这里初始化为地图的大小
        self.x_start = self.map_size[0]
        self.y_start = self.map_size[1]
        self.x_end = 0
        self.y_end = 0

        self.resource_icon = Image.open(self.get_icon_path())
        self.resource_icon = self.resource_icon.resize((int(150*zoom),int(150*zoom)))

        self.resource_xy_list = self.get_resource_point_list(point_list)

    def get_icon_path(self):
        # 检查有没有图标，有返回正确图标，没有返回默认图标
        icon_path = os.path.join(FILE_PATH,"icon",f"{self.resource_id}.png")

        if os.path.exists(icon_path):
            return icon_path
        else:
            return os.path.join(FILE_PATH,"icon","0.png")

    def get_resource_point_list(self,point_list):
        temp_list = []
        for resource_point in point_list:
            # 获取xy坐标，然后加上中心点的坐标完成坐标转换
            x = resource_point["x_pos"] + CENTER[0]
            y = resource_point["y_pos"] + CENTER[1]
            temp_list.append((int(x),int(y)))
        return temp_list


    def paste(self):
        for x,y in self.resource_xy_list:
            # 把资源图片贴到地图上
            # 这时地图已经裁切过了，要以裁切后的地图左上角为中心再转换一次坐标
            x -= self.x_start
            y -= self.y_start
            self.map_image.paste(self.resource_icon,(x + resource_icon_offset[0] , y + resource_icon_offset[1]),self.resource_icon)


    def crop(self):
        # 把大地图裁切到只保留资源图标位置
        for x,y in self.resource_xy_list:
            # 找出4个方向最远的坐标，用于后边裁切
            self.x_start = min(x, self.x_start)
            self.y_start = min(y, self.y_start)
            self.x_end = max(x, self.x_end)
            self.y_end = max(y, self.y_end)

        # 先把4个方向扩展150像素防止把资源图标裁掉
        self.x_start -= 150
        self.y_start -= 150
        self.x_end += 150
        self.y_end += 150

        # 如果图片裁切的太小会看不出资源的位置在哪，检查图片裁切的长和宽看够不够
        if (self.x_end - self.x_start)<map_min_hw:
            center = int((self.x_end + self.x_start) / 2)
            self.x_start = center - map_min_hw/2
            self.x_end  = center + map_min_hw/2
        if (self.y_end - self.y_start)<map_min_hw:
            center = int((self.y_end + self.y_start) / 2)
            self.y_start = center - map_min_hw/2
            self.y_end  = center + map_min_hw/2

        self.map_image = self.map_image.crop((self.x_start,self.y_start,self.x_end,self.y_end))

    def get_cq_cod(self):

        if not self.resource_xy_list:
            return "没有这个资源的信息"

        self.crop()

        self.paste()

        bio = BytesIO()
        self.map_image.save(bio, format='JPEG')
        base64_str = 'base64://' + base64.b64encode(bio.getvalue()).decode()

        return f"[CQ:image,file={base64_str}]"

    def get_resource_count(self):
        return len(self.resource_xy_list)



def get_resource_map_mes(name):

    if data["date"] !=  time.strftime("%d"):
        up_label_and_point_list()

    if not (name in data["can_query_type_list"]):
        return f"没有 {name} 这种资源。\n发送 原神资源列表 查看所有资源名称"

    resource_id = data["can_query_type_list"][name]
    count = 0
    mes = f"资源 {name} 的位置如下\n"
    for point_list in data["sort_resource_point_list"][resource_id]:
        map = Resource_map(name,point_list)
        count += map.get_resource_count()
        mes += map.get_cq_cod()

    mes += f"\n\n※ {name} 一共找到 {count} 个位置点\n※ 数据来源于米游社wiki"

    return mes



def get_resource_list_mes():

    temp = {}

    for id in data["all_resource_type"].keys():
        # 先找1级目录
        if data["all_resource_type"][id]["depth"] == 1:
            temp[id] = []

    for id in data["all_resource_type"].keys():
        # 再找2级目录
        if data["all_resource_type"][id]["depth"] == 2:
            temp[str(data["all_resource_type"][id]["parent_id"])].append(id)

    mes = "当前资源列表如下：\n"

    for resource_type_id in temp.keys():

        if resource_type_id in ["1","12","50","51","95","131"]:
            # 在游戏里能查到的数据这里就不列举了，不然消息太长了
            continue

        mes += f"{data['all_resource_type'][resource_type_id]['name']}："
        for resource_id in temp[resource_type_id]:
            mes += f"{data['all_resource_type'][resource_id]['name']}，"
        mes += "\n"

    return mes



