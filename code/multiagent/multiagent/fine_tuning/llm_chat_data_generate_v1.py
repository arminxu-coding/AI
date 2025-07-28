import asyncio
import copy

from pydantic import BaseModel, Field
from typing import List
from multiagent.llm import llm_api
from multiagent.utils.common_util import StrUtil

"""
使用llm自动生成对话聊天数据
"""

system_prompt_human_query = """
我现在是需要你给我设一个任务，我的目标是想要构造一批：在点咖啡场景下顾客和营业员的多轮交互点咖啡场景中，我需要你帮我基于这个场景构造一批多轮对话中的用户提问的query。
---------------------------------------------

但是下面我需要明确一下我的要求和目标。

## 要求
1、我的系统是一个智能点咖啡场景的智能助手，采用语言对话方式与顾客交流并完成点咖啡
2、你需要生成顾客提问query，内容需要符合多轮对话人交互的语气，并且生成query对应的意图 必须是我下面设定的意图列表：
    （1）配置订单槽位意图
    意图名称：order_configuration
    意图描述：订单槽位配置，顾客通过一句话或多句话表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）
    示例：“我要一杯冰美式，打包带走”、“来杯低糖的拿铁，用燕麦奶，温度不要太烫”
    
    （2）修改订单槽位意图
    意图名称：order_modification
    意图描述：订单槽位修改，顾客对已确认的订单信息提出调整请求，可以修改之前已经配置好的订单槽位信息，例如品名、杯型、甜度等等配置项。
    示例：“刚才点错了，改成抹茶拿铁”、“换成热的”、“我还是要甜一点的”
    
    （3）商品推荐
    意图名称：product_recommend
    意图描述：商品推荐，顾客含义不够明确想要点的商品是什么 或者 具有推荐的要求时，进行推荐商品给顾客进行选择。
    示例：“推荐一款适合搭配早餐的咖啡组合”、“有啥新品推荐吗”、“推荐一些果味咖啡”
    
    （4）配置推荐
    意图名称：configuration_recommend
    意图描述：配置推荐，顾客希望获得个性化建议或 配置推荐，但是必须当前顾客已经确认了需要点的咖啡品类。
    示例：“第一次喝拿铁，甜度怎么选比较合适？”、“有啥推荐的搭配”
    
    （5）信息咨询
    意图名称：info_inquiry
    意图描述：信息咨询，顾客进行询问菜单、价格、规格、成分或制作工艺等信息。
    示例：“你们有摩卡吗？”、“冷萃咖啡是怎么制作的？”、“标准甜是多甜”、“标准美式多少钱”、“还有什么甜度”
    
    （6）确认下单
    意图名称：confirm_place_order
    意图描述：确认下单，顾客的提问中是明确了 确认下单含义，进行帮助顾客完成商品的下单，确认下单的同时不允许修改配置，只能仅仅含义确认下单的含义
    示例：“好的”、“下单吧”、“可以了”、“就这样子”、“就这样下单” ...
    
    （7）取消订单
    意图名称：cancel_order
    意图描述：取消下单，顾客的提问中是明确了 取消下单 含义，那么需要结束本次的点单的流程，并将订单取消
    示例：“不下了”、“取消订单”、“不点了”、"我不要了，谢谢" ...
    
    （8）确定支付
    意图名称：confirm_pay
    意图描述：确定支付，顾客的提问中含义是确定进行支付，需要拉取最后的支付流程(支付二维码或微信支付消息推送)，同时会结束点单流程
    示例：“好的支付”、“确定支付”、“可以了就这样，支付吧” ...
    
    （9）拒识
    意图名称：unknown
    意图描述：拒识意图，以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景
    示例：“你好，今天生意不错啊！”、“打开车窗，空调温度降低一点”、“帮我播放七里香”、“导航到北京大学” ...
3、需要生成一轮完整的顾客对话提问query，保障最后生成的对话数据完整性
4、咖啡品具有的配置槽位有如下：
    - product_name： 具体的咖啡品名
    - cup_size: 具有的杯型选项值
    - bean: 具有的咖啡豆选项值
    - milk: 具有的牛奶选项值
    - coffee_liquid: 具有的咖啡液选项值
    - sugar_level：具有的甜度选项值
    - temperature: 具有的温度选项值
    - flavour: 具有的咖啡的风味选项值
    - cream: 具有的奶油选项值
5、顾客进行点单的咖啡品 以及 对应的配置项最好是下面这些，不过你可以进行随机捏造
[
    {"product_name": "橙C美式(首创)", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "茉莉花香美式", "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "羽衣轻体果蔬茶", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["少甜", "标准甜", "少少甜", "微甜", "不另外加糖"]}, 
    {"product_name": "柚C冰茶", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"], "flavour": ["茉莉花香"]}, 
    {"product_name": "抹茶瑞纳冰", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["少甜", "少少甜"]}, 
    {"product_name": "抹茶拿铁", "temperature": ["冰", "热"], "sugar_level": ["少少甜", "标准甜", "少甜", "微甜", "不另外加糖"], "cream": ["无奶油"], "milk": ["纯牛奶", "燕麦奶"], "cup_size": ["大杯"]}, 
    {"product_name": "耶加雪菲·美式", "cup_size": ["12oz"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC铂金豆"]}, 
    {"product_name": "耶加雪菲·拿铁", "cup_size": ["12oz"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC铂金豆"]}, 
    {"product_name": "长安的荔枝冰萃", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "夏日西瓜冷萃", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "flavour": ["不含椰浆", "椰浆"]}, 
    {"product_name": "长安的荔枝冻冻", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "flavour": ["栀子花香"]}, 
    {"product_name": "轻咖柠檬茶", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["少少甜", "标准甜", "少甜", "微甜", "不另外加糖"], "flavour": ["茉莉花香", "栀子花香"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "燕麦拿铁", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "凤梨美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "冷萃", "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "柚C美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "大西瓜生椰冷萃", "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "丝绒拿铁", "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "cup_size": ["大杯"]}, 
    {"product_name": "生椰丝绒拿铁", "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "cream": ["无奶油"], "cup_size": ["大杯"]}, 
    {"product_name": "轻咖椰子水", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "coffee_liquid": ["含轻咖"]}, 
    {"product_name": "青瓜椰子水", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "葡萄柠檬茶", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"], "flavour": ["茉莉花香", "栀子花香"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "鲜萃轻轻栀子", "cup_size": ["大杯 16oz", "特大杯 20oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "不另外加糖"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "柠C美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "栀子花香拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "微甜", "不另外加糖"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "生椰拿铁", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "葡萄冰萃美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "bean": ["IIAC金奖豆"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "拿铁", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "一杯黑巧", "temperature": ["冰", "热"], "cream": ["无奶油"], "cup_size": ["大杯"]}, 
    {"product_name": "摩卡", "cup_size": ["大杯 16oz"], "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少少甜"], "cream": ["无奶油"], "milk": ["纯牛奶", "燕麦奶"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "精萃澳瑞白", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "标准美式", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "milk": ["无奶", "双份奶", "单份奶"]}, 
    {"product_name": "焦糖玛奇朵", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少甜", "少少甜"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "橙C冰茶", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"], "flavour": ["茉莉花香"]}, 
    {"product_name": "耶加雪菲·澳瑞白", "cup_size": ["12oz"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC铂金豆"]}, 
    {"product_name": "熊猫陨石拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["少甜", "标准甜", "少少甜"]}, 
    {"product_name": "加浓美式", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "milk": ["无奶", "双份奶", "单份奶"]}, 
    {"product_name": "抹茶好喝椰", "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "cup_size": ["大杯"]}, 
    {"product_name": "冻冻生椰拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "椰青冰萃美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "纯牛奶", "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "cup_size": ["大杯"]}, 
    {"product_name": "香草拿铁", "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少甜", "少少甜"], "milk": ["纯牛奶", "燕麦奶"], "cup_size": ["大杯"]}, 
    {"product_name": "卡布奇诺", "temperature": ["热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "cup_size": ["大杯"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "冰镇杨梅瑞纳冰", "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"]}, 
    {"product_name": "冰吸生椰拿铁", "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "海盐焦糖拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜"]}, 
    {"product_name": "香草丝绒拿铁", "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少甜", "少少甜"], "cream": ["无奶油"], "cup_size": ["大杯"]}, 
    {"product_name": "鲜萃轻轻茉莉", "cup_size": ["大杯 16oz", "特大杯 20oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "不另外加糖"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "海盐焦糖冰摇美式", "temperature": ["冰"], "sugar_level": ["少少甜", "标准甜", "少甜"]}, 
    {"product_name": "茉莉花香拿铁", "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "微甜", "不另外加糖"], "milk": ["纯牛奶", "燕麦奶"], "cup_size": ["大杯"]}
]

## 目标
1.根据用户的任务进行生成一个一个的顾客 点咖啡场景的 多轮对话数据，对话的意图可以是点单相关意图内容、也可以是拒识的意图，你可以随机组织和发挥，但最终保证订单交互过程对话完整即可
2.生成的只能是顾客的query，而不是是营业员的回复语
3.一个顾客的多轮对话的轮次可以随机，但最少需要2轮

输出示例：
[
    [
        "有什么适合夏天的新品推荐吗？",
        "听起来夏日西瓜冷萃不错，来一杯大杯，冰的，少甜。",
        "对了，甜度换成少少甜吧，我不太喜欢太甜。",
        "下单吧。"
    ],
    [
        "你们有摩卡吗？",
        "那给我来一杯热的摩卡，大杯，标准甜，纯牛奶。",
        "摩卡加奶油的话口感怎么样？",
        "好的，那就这样子下单吧。"
    ]
]

## 输出格式规范
以标准json格式输出如下内容：
```json
[
    [
        "<顾客提问query1>",
        "<顾客提问query2>",
        "<顾客提问query3>",
        ...
    ],
    [
        "<顾客提问query1>",
        "<顾客提问query2>",
        ...
    ],
    ...
]
```
"""

user_prompt_human_query = """
任务：帮助我按照要求，生成 {num}个顾客多轮对话数据
"""

system_prompt_ai_reply = """
我现在是需要你给我设一个任务，我的目标是想要构造一批：在点咖啡场景下顾客和营业员的多轮交互点咖啡场景中，我需要你帮我基于用户提供的每一个[顾客提问]进行回复对话，需要注意上下文的连贯性。
---------------------------------------------

但是下面我需要明确一下我的要求和目标。

## 要求
1、我的系统是一个智能点咖啡场景的智能助手，采用语言对话方式与顾客交流并完成点咖啡
2、你需要基于顾客的提问理解其中的意图，并进行生成对应的回复，内容需要符合多轮对话人交互的语气，其中顾客提问query的意图 会是我下面设定的意图列表：
    （1）配置订单槽位意图
    意图名称：order_configuration
    意图描述：订单槽位配置，顾客通过一句话或多句话表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）
    顾客提问示例：“我要一杯冰美式，打包带走”、“来杯低糖的拿铁，用燕麦奶，温度不要太烫”
    营业员回复语示例：“好的，为您添加了一杯冰的标准美式，选择了自提带走，请问可以下单了吗？”、“不好意思，当前拿铁没有低糖的哦～为您添加了不另外加糖的拿铁，您看可以吗？”
    
    （2）修改订单槽位意图
    意图名称：order_modification
    意图描述：订单槽位修改，顾客对已确认的订单信息提出调整请求，可以修改之前已经配置好的订单槽位信息，例如品名、杯型、甜度等等配置项。
    顾客提问示例：“刚才点错了，改成抹茶拿铁”、“换成热的”、“我还是要甜一点的”
    营业员回复语示例：“好的，已移除了拿铁，已为您添加为抹茶拿铁，可以下单了哟”、“已给您调整好了，拿铁现在是冷的”、“为您将甜度调整为标准甜，口感会更浓郁哦～”
    
    （3）商品推荐
    意图名称：product_recommend
    意图描述：商品推荐，顾客含义不够明确想要点的商品是什么 或者 具有推荐的要求时，进行推荐商品给顾客进行选择。
    顾客提问示例：“推荐一款适合搭配早餐的咖啡组合”、“有啥新品推荐吗”、“推荐一些果味咖啡”
    营业员回复语示例：“为您推荐柚C美式，含真实柚子汁，清爽解腻～”、“为您推荐新品海盐焦糖冰摇美式、长安的荔枝冻冻、海盐焦糖拿铁～”、“果味咖啡推荐话梅气泡美式和柚C美式，酸甜清爽，适合夏季！”
    
    （4）配置推荐
    意图名称：configuration_recommend
    意图描述：配置推荐，顾客希望获得个性化建议或 配置推荐，但是必须当前顾客已经确认了需要点的咖啡品类。
    顾客提问示例：“第一次喝拿铁，甜度怎么选比较合适？”、“有啥推荐的搭配”
    营业员回复语示例：“推荐标准甜，口感均衡，适合初次尝试拿铁。”、“生椰拿铁搭配少甜和冰块，能更好激发椰香风味哦～”

    （5）信息咨询
    意图名称：info_inquiry
    意图描述：信息咨询，顾客进行询问菜单、价格、规格、成分或制作工艺等信息。
    顾客提问示例：“你们有摩卡吗？”、“冷萃咖啡是怎么制作的？”、“标准甜是多甜”、“标准美式多少钱”、“还有什么甜度”
    营业员回复语示例：“有的，摩卡有冰热两种选择”、“冷萃是用低温水慢萃取12小时，口感顺滑无苦涩。”、“标准甜是每杯加1.5勺糖浆，甜度适中。”、“标准美式15元，中杯或大杯可选。”、“摩卡的糖度有标准甜、少少甜，您想选择哪一种呢”
    
    （6）确认下单
    意图名称：confirm_place_order
    意图描述：确认下单，顾客的提问中是明确了 确认下单含义，进行帮助顾客完成商品的下单，确认下单的同时不允许修改配置，只能仅仅含义确认下单的含义
    顾客提问示例：“好的”、“下单吧”、“可以了”、“就这样子”、“就这样下单” ...
    营业员回复语示例：“好的，正在为您创建订单，请稍等~”
    
    （7）取消订单
    意图名称：cancel_order
    意图描述：取消下单，顾客的提问中是明确了 取消下单 含义，那么需要结束本次的点单的流程，并将订单取消
    顾客提问示例：“不下了”、“取消订单”、“不点了”、"我不要了，谢谢" ...
    营业员回复语示例：“好的，订单已取消，欢迎下次光临！”、“已为您取消，期待再次为您服务～”、“不客气，随时欢迎您再来点单！”
    
    （8）确定支付
    意图名称：confirm_pay
    意图描述：确定支付，顾客的提问中含义是确定进行支付，需要拉取最后的支付流程(支付二维码或微信支付消息推送)，同时会结束点单流程
    顾客提问示例：“好的支付”、“确定支付”、“可以了就这样，支付吧” ...
    营业员回复语示例：“好的，请您继续手动完成支付～”
    
    （9）拒识
    意图名称：unknown
    意图描述：拒识意图，以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景
    顾客提问示例：“你好，今天生意不错啊！”、“打开车窗，空调温度降低一点”、“帮我播放七里香”、“导航到北京大学” ...
    营业员回复语示例：“感谢关注，我们目前只能为您提供点单服务哦～”、“抱歉，暂不支持车辆控制，请问需要点什么咖啡？”、“抱歉，暂不支持多媒体控制，请问需要点什么咖啡？”、“抱歉，暂不支持车载导航控制，请问需要点什么咖啡？”

3、需要根据用户提供的 顾客对话提问query，生成与其一一对应的营业员回复语，要保障最后生成的对话数据完整性
4、咖啡商品订单信息具有的配置槽位有如下：
    - product_name： 具体的咖啡品名
    - cup_size: 具有的杯型选项值
    - bean: 具有的咖啡豆选项值
    - milk: 具有的牛奶选项值
    - coffee_liquid: 具有的咖啡液选项值
    - sugar_level：具有的甜度选项值
    - temperature: 具有的温度选项值
    - flavour: 具有的咖啡的风味选项值
    - cream: 具有的奶油选项值
5、顾客进行点单的咖啡品 以及 对应的配置项最好是下面这些，不过你可以进行随机捏造
[
    {"product_name": "橙C美式(首创)", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "茉莉花香美式", "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "羽衣轻体果蔬茶", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["少甜", "标准甜", "少少甜", "微甜", "不另外加糖"]}, 
    {"product_name": "柚C冰茶", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"], "flavour": ["茉莉花香"]}, 
    {"product_name": "抹茶瑞纳冰", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["少甜", "少少甜"]}, 
    {"product_name": "抹茶拿铁", "temperature": ["冰", "热"], "sugar_level": ["少少甜", "标准甜", "少甜", "微甜", "不另外加糖"], "cream": ["无奶油"], "milk": ["纯牛奶", "燕麦奶"], "cup_size": ["大杯"]}, 
    {"product_name": "耶加雪菲·美式", "cup_size": ["12oz"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC铂金豆"]}, 
    {"product_name": "耶加雪菲·拿铁", "cup_size": ["12oz"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC铂金豆"]}, 
    {"product_name": "长安的荔枝冰萃", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "夏日西瓜冷萃", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "flavour": ["不含椰浆", "椰浆"]}, 
    {"product_name": "长安的荔枝冻冻", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "flavour": ["栀子花香"]}, 
    {"product_name": "轻咖柠檬茶", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["少少甜", "标准甜", "少甜", "微甜", "不另外加糖"], "flavour": ["茉莉花香", "栀子花香"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "燕麦拿铁", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "凤梨美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "冷萃", "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "柚C美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "大西瓜生椰冷萃", "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "丝绒拿铁", "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "cup_size": ["大杯"]}, 
    {"product_name": "生椰丝绒拿铁", "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "cream": ["无奶油"], "cup_size": ["大杯"]}, 
    {"product_name": "轻咖椰子水", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "coffee_liquid": ["含轻咖"]}, 
    {"product_name": "青瓜椰子水", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "葡萄柠檬茶", "cup_size": ["超大杯"], "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"], "flavour": ["茉莉花香", "栀子花香"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "鲜萃轻轻栀子", "cup_size": ["大杯 16oz", "特大杯 20oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "不另外加糖"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "柠C美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "栀子花香拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "微甜", "不另外加糖"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "生椰拿铁", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "葡萄冰萃美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "bean": ["IIAC金奖豆"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "拿铁", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "一杯黑巧", "temperature": ["冰", "热"], "cream": ["无奶油"], "cup_size": ["大杯"]}, 
    {"product_name": "摩卡", "cup_size": ["大杯 16oz"], "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少少甜"], "cream": ["无奶油"], "milk": ["纯牛奶", "燕麦奶"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "精萃澳瑞白", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "标准美式", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "milk": ["无奶", "双份奶", "单份奶"]}, 
    {"product_name": "焦糖玛奇朵", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少甜", "少少甜"], "milk": ["纯牛奶", "燕麦奶"]}, 
    {"product_name": "橙C冰茶", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"], "flavour": ["茉莉花香"]}, 
    {"product_name": "耶加雪菲·澳瑞白", "cup_size": ["12oz"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "bean": ["IIAC铂金豆"]}, 
    {"product_name": "熊猫陨石拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["少甜", "标准甜", "少少甜"]}, 
    {"product_name": "加浓美式", "cup_size": ["大杯 16oz"], "bean": ["IIAC金奖豆"], "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "milk": ["无奶", "双份奶", "单份奶"]}, 
    {"product_name": "抹茶好喝椰", "temperature": ["冰", "热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"], "cup_size": ["大杯"]}, 
    {"product_name": "冻冻生椰拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "椰青冰萃美式", "cup_size": ["大杯 16oz", "超大杯 24oz"], "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "纯牛奶", "temperature": ["热", "冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "cup_size": ["大杯"]}, 
    {"product_name": "香草拿铁", "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少甜", "少少甜"], "milk": ["纯牛奶", "燕麦奶"], "cup_size": ["大杯"]}, 
    {"product_name": "卡布奇诺", "temperature": ["热"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜", "香草"], "cup_size": ["大杯"], "bean": ["IIAC金奖豆"]}, 
    {"product_name": "冰镇杨梅瑞纳冰", "temperature": ["冰"], "sugar_level": ["微甜", "标准甜", "少甜", "少少甜", "不另外加糖"]}, 
    {"product_name": "冰吸生椰拿铁", "temperature": ["冰"], "sugar_level": ["不另外加糖", "标准甜", "少甜", "少少甜", "微甜"]}, 
    {"product_name": "海盐焦糖拿铁", "cup_size": ["大杯 16oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜"]}, 
    {"product_name": "香草丝绒拿铁", "temperature": ["热", "冰"], "sugar_level": ["标准甜", "少甜", "少少甜"], "cream": ["无奶油"], "cup_size": ["大杯"]}, 
    {"product_name": "鲜萃轻轻茉莉", "cup_size": ["大杯 16oz", "特大杯 20oz"], "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "不另外加糖"], "coffee_liquid": ["不含轻咖", "含轻咖"]}, 
    {"product_name": "海盐焦糖冰摇美式", "temperature": ["冰"], "sugar_level": ["少少甜", "标准甜", "少甜"]}, 
    {"product_name": "茉莉花香拿铁", "temperature": ["冰", "热"], "sugar_level": ["少甜", "标准甜", "少少甜", "微甜", "不另外加糖"], "milk": ["纯牛奶", "燕麦奶"], "cup_size": ["大杯"]}
]

## 目标
1.根据用户的任务和提供的 顾客对话query列表 进行生成一个一个的顾客 点咖啡场景的 多轮营业员回复语的对话数据，但是必须坚决杜绝使用 上述给出的[营业员回复语示例]作为结果输出
2.生成的只能是营业员回复语，而不是是顾客提问query等其他类型的回复内容
3.生成的回复语，需要根据顾客提问query的上下文进行分析 然后生成回复语，需要保证其本身上下文内容的连贯性

## 示例
下面是两个顾客的多轮对话：
[
    [
        "有什么适合夏天的新品推荐吗？",
        "听起来夏日西瓜冷萃不错，来一杯大杯，冰的，少甜。",
        "对了，甜度换成少少甜吧，我不太喜欢太甜。",
        "下单吧。"
    ],
    [
        "你们有摩卡吗？",
        "那给我来一杯热的摩卡，大杯，标准甜，纯牛奶。",
        "摩卡加奶油的话口感怎么样？",
        "好的，那就这样子下单吧。"
    ]
]
下面是根据两个顾客的多轮对话 生成的 营业员回复语信息：
[
    [
        "推荐您试试夏日西瓜冷萃和话梅气泡美式哦～这两款都是冰镇的，果香清新很适合夏天。",
        "好的，已为您添加大杯冰的少甜夏日西瓜冷萃，我可以帮您下单哟？",
        "为您调整为少少甜啦，冰镇西瓜冷萃的清爽感会更突出，您看这样可以吗？",
        "好的，正在为您创建订单，请稍等~"
    ],
    [
        "有的呢，摩卡有冰热两种选择，大杯18元，热饮会搭配现蒸奶泡口感更绵密哦。",
        "为您准备了热摩卡，大杯、纯牛奶，标准甜度会带一点巧克力的醇苦感呢。",
        "抱歉现在摩卡暂不支持加奶油呢，只有无奶油选择",
        "好的，订单已确认，请您稍等！"
    ]
]

## 输出格式规范
以标准json格式输出如下内容：
```json
[
    [
        "<基于顾客提问query的营业员回复1>",
        "<基于顾客提问query的营业员回复2>",
        "<基于顾客提问query的营业员回复3>",
        ...
    ],
    [
        "<基于顾客提问query的营业员回复1>",
        "<基于顾客提问query的营业员回复2>",
        ...
    ],
    ...
]
```
"""
user_prompt_ai_reply = """
任务：帮助我按要求，根据下面提供的 {num}个顾客多轮对话数据 生成 营业员回复语

顾客多轮对话数据：
{human_query_list}
"""


class ChatDataResponse(BaseModel):
    is_model_response: bool = Field(default=True, description="为模型输出内容, 仅做页面内容展示")


async def human_query_generator(model: str, num: int = 1) -> List[List[str]]:
    system_prompt = copy.deepcopy(system_prompt_human_query)
    user_prompt = copy.deepcopy(user_prompt_human_query).format(num=num)
    ai_message = llm_api.generate_content_async(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=model,
        temperature=0.6,
        stream=True
    )
    content = ""
    async for chunk in ai_message:
        print(chunk, end="")
        content += chunk
    print()
    return StrUtil.json_str_loads(content)


async def ai_reply_generator(model: str, human_query_list: List[List[str]]) -> List[List[str]]:
    system_prompt = copy.deepcopy(system_prompt_ai_reply)
    user_prompt = copy.deepcopy(user_prompt_ai_reply).format(human_query_list=human_query_list, num=len(human_query_list))
    ai_message = llm_api.generate_content_async(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model=model,
        temperature=0.6,
        stream=True
    )
    content = ""
    async for chunk in ai_message:
        print(chunk, end="")
        content += chunk
    print()
    return StrUtil.json_str_loads(content)


async def main():
    # model = "hunyuan_hunyuan-turbos-latest"
    # model = "hunyuan_hunyuan-large"
    # model = "ollama_qwen3:8b"
    # model = "siliconflow_deepseek-ai/DeepSeek-R1"
    model = "siliconflow_Qwen/Qwen3-8B"
    # model = "siliconflow_Qwen/Qwen2.5-7B-Instruct"
    human_query_list = await human_query_generator(model, 1)
    ai_reply_list = await ai_reply_generator(model, human_query_list)

    print("\n================== 最后结果 ==================")
    for i, chat_list in enumerate(human_query_list):
        print("[")
        for j, query in enumerate(chat_list):
            print(f"\t问：{query}")
            print(f"\t答：{ai_reply_list[i][j]}")
        print("]")


if __name__ == '__main__':
    asyncio.run(main())
