import asyncio
import copy
import json
import time
import uuid

from typing import Optional
from multiagent.llm import llm_api
from multiagent.utils.common_util import StrUtil

"""
使用llm自动生成对话聊天数据
"""

"""
（1）配置订单槽位意图
    意图名称：order_configuration
    意图描述：订单槽位配置，顾客通过一句话或多句话表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）
    生成query格式参照：“来杯低糖的拿铁，温度不要太烫”
    
    
    （2）修改订单槽位意图
    意图名称：order_modification
    意图描述：订单槽位修改，顾客对已确认的订单信息提出调整请求，可以修改之前已经配置好的订单槽位信息，例如品名、杯型、甜度等等配置项。
    生成query格式参照：“甜度改为更甜一点的”
    
    （3）商品推荐意图
    意图名称：product_recommend
    意图描述：商品推荐，顾客含义不够明确想要点的商品是什么 或者 具有推荐的要求时，进行推荐商品给顾客进行选择。
    生成query格式参照：“有什么推荐的果味咖啡吗?”
    
    （4）配置推荐意图
    意图名称：configuration_recommend
    意图描述：配置推荐，顾客希望获得个性化建议或 配置推荐，但是必须当前顾客已经确认了需要点的咖啡品类。
    生成query格式参照：“拿铁推荐的配置是啥”

    （5）信息咨询意图
    意图名称：info_inquiry
    意图描述：信息咨询，顾客进行询问菜单、价格、规格、成分或制作工艺等信息。
    生成query格式参照：“橙c美式里面是真的橙子还是啥原材料”
    
    （6）确认下单意图
    意图名称：confirm_place_order
    意图描述：确认下单，顾客的提问中是明确了 确认下单含义，进行帮助顾客完成商品的订单创建，在本[确认下单]步骤的同时是不允许修改配置，只能仅仅含义是基于历史对话消息的商品配置信息进行创建订单。
    生成query格式参照：“好的下单”
    
    （7）取消订单意图
    意图名称：cancel_order
    意图描述：取消下单，顾客的提问中是明确了 取消下单 含义，那么需要结束本次的点单的流程，并将订单取消。
    生成query格式参照：“算了不要了，取消吧”
    
    （8）确定支付意图
    意图名称：confirm_pay
    意图描述：确定支付，顾客的提问中含义是确定进行支付，需要拉取最后的支付流程(支付二维码或微信支付消息推送)，同时会结束点单流程。
    生成query格式参照：“确认支付”
    
    （9）拒识意图
    意图名称：unknown
    意图描述：拒识意图，以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景。
    生成query格式参照：“帮我打开车窗”
    营业员回复语示例：“感谢关注，我们目前只能为您提供点单服务哦～”、“抱歉，暂不支持车辆控制，请问需要点什么咖啡？”、“抱歉，暂不支持多媒体控制，请问需要点什么咖啡？”、“抱歉，暂不支持车载导航控制，请问需要点什么咖啡？”
    
## 示例
1.下面是[顾客]和[营业员]的多轮对话示例：
[
    {
        "顾客": "有什么适合夏天的新品推荐吗？",
        "营业员": "推荐您试试夏日西瓜冷萃和话梅气泡美式哦～这两款都是冰镇的，果香清新很适合夏天。",
        "顾客": "听起来夏日西瓜冷萃不错，来一杯大杯，冰的，少甜。",
        "营业员": "好的，已为您添加了大杯冰的少甜夏日西瓜冷萃，您可以确认下单了哟？",
        "顾客": "甜度还是换成少少甜吧，我不太喜欢太甜。",
        "营业员": "为您调整为少少甜啦，您看这样可以吗？",
        "顾客": "下单吧",
        "营业员": "好的，正在为您创建订单，请稍等~"
    },
    {
        "顾客": "你们有摩卡吗？",
        "营业员": "有的呢，摩卡有冰热两种选择，大杯18元，热饮会搭配现蒸奶泡口感更绵密哦。",
        "顾客": "那给我来一杯热的摩卡",
        "营业员": "为您添加大杯的热摩卡、标准甜度会带一点巧克力的醇苦感呢，您可以确认下单了哟?",
        "顾客": "好的，那就这样子可以了",
        "营业员": "好的，订单已确认，请您稍等！"
    },
    {
        "顾客": "帮我点一杯大杯热美式",
        "营业员": "好的，以为您添加大杯热的标准美式，默认给您选择不另外加糖、无奶，您可以确认下单了哟~",
        "顾客": "给我加份奶",
        "营业员": "ok,给您加了单份奶，还有别的需求吗?",
        "顾客": "就这样子吧",
        "营业员": "好的，正在为您创建订单，您可以选择去支付有扫码支付和微信支付推送两种方式!",
        "顾客": "支付吧",
        "营业员": "正在默认拉取支付二维码，请您支付，谢谢~"
    }
]

## 流程介绍
一般情况下咖啡点单的流程示例(仅作参考)，实际你可以任意选择意图组装流程路径:
1.配置订单信息 → 确认下单 → 确定支付
2.商品推荐 → 配置订单信息 → 确认下单 → 确定支付
3.信息咨询 → 配置订单信息 → 确认下单 → 确定支付
4.配置订单信息 → 修改订单信息 → 确认下单 → 确定支付
5.商品推荐 → 信息咨询 → 配置订单信息 → 确认下单
6.配置订单信息 → 信息咨询 → 配置推荐 → 确认下单
7.配置订单信息 → 修改订单信息 → 信息咨询 → 确认下单
8.配置订单信息 → 配置推荐 → 修改订单信息 → 确认下单
9.信息咨询 → 商品推荐 → 配置订单信息 → 确认下单
10.商品推荐 → 配置订单信息 → 修改订单信息 → 配置推荐 → 确认下单
11.配置订单信息 → 拒识意图 → 回归点单流程 → 确认下单
12.商品推荐 → 拒识意图 → 配置订单信息 → 确认下单
"""

system_prompt_human_query = """
你是一个专业的角色扮演者，负责扮演在咖啡店中的 点单[顾客]
你的任务目标是要构造一批，在点咖啡场景下[顾客]和[营业员]的多轮交互点咖啡场景中，你要基于这个场景构造[顾客]多轮对话点单的query数据。
---------------------------------------------

但是下面我需要明确一下我的要求和目标。

## 要求
1、现在系统是一个智能点咖啡场景的智能助手，采用语言对话方式是[顾客]与[营业员]交流并完成点咖啡。
2、你作为[顾客]需要生成提问query，内容需要符合多轮对话人交互的语气，并且生成query对应的意图 必须是下面设定的意图列表中的：
    （1）配置订单槽位意图
    意图名称：order_configuration
    意图描述：订单槽位配置，顾客通过一句话或多句话表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）
    
    （2）修改订单槽位意图
    意图名称：order_modification
    意图描述：订单槽位修改，顾客对已确认的订单信息提出调整请求，可以修改之前已经配置好的订单槽位信息，例如品名、杯型、甜度等等配置项。
    
    （3）商品推荐意图
    意图名称：product_recommend
    意图描述：商品推荐，顾客含义不够明确想要点的商品是什么 或者 具有推荐的要求时，进行推荐商品给顾客进行选择。
    
    （4）配置推荐意图
    意图名称：configuration_recommend
    意图描述：配置推荐，顾客希望获得个性化建议或 配置推荐，但是必须当前顾客已经确认了需要点的咖啡品类。

    （5）信息咨询意图
    意图名称：info_inquiry
    意图描述：信息咨询，顾客进行询问菜单、价格、规格、成分或制作工艺等信息。
    
    （6）确认下单意图
    意图名称：confirm_place_order
    意图描述：确认下单，顾客的提问中是明确了 确认下单含义，进行帮助顾客完成商品的订单创建，在本[确认下单]步骤的同时是不允许修改配置，只能仅仅含义是基于历史对话消息的商品配置信息进行创建订单。
    
    （7）取消订单意图
    意图名称：cancel_order
    意图描述：取消下单，顾客的提问中是明确了 取消下单 含义，那么需要结束本次的点单的流程，并将订单取消。
    
    （8）确定支付意图
    意图名称：confirm_pay
    意图描述：确定支付，顾客的提问中含义是确定进行支付，需要拉取最后的支付流程(支付二维码或微信支付消息推送)，同时会结束点单流程。
    
    （9）拒识意图
    意图名称：unknown
    意图描述：拒识意图，以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景。

3、你需要生成每一轮完整的[顾客]对话提问query，保障最后生成的对话数据完整性；中途你作为[顾客]的对话内容可以携带<拒识意图的query>，[营业员]会按照你的提问内容进行正常解答。\
一般作为[顾客]开头第一句会是以下几种意图开始进行问答：
    - 配置订单槽位意图
    - 商品推荐意图
    - 信息咨询意图
    - 配置推荐意图
请你开头的时候随机选择一种意图进行提问，内容需要多变，不能过于单一。

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
5、你作为[顾客]进行点单的咖啡品 以及 对应的配置项最好是下面这些；不过你可以进行随机捏造 让营业员进行判断即可。
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
1.对话的形式采用一问一答的形式，你需要根据对话上下文进行和[营业员]对话
2.但是首先起头是由你开始，你需要保证问与答的连贯性
3.订单处理结束的条件为：你的query意图为 “确认下单”、“取消下单”、“确认支付”
4.你的一次点单多轮中对话的轮次至少是2轮，但可以随机一点不要过于相同了

## 处理流程
1.首先，你需要分析[营业员]的回复内容，决定下一句如何回复；如果营业员无回复，说明是首轮，得由你进行开头。
2.其次，你需要决定你本次的query应该对应的意图，根据意图进行生成对应的query内容。
3.最后，你需要输出你作为[顾客]的回复，最终完成任务。

## 输出内容
1.要求：只需要输出你作为[顾客]的点单query内容，不需要输出其他内容，请严格按照下面的json格式输出。
2.格式：
```json
{
    "query": "<生成顾客的点单query>",
    "intent": "<query对应的意图英文名称>"
}
```
"""
system_prompt_human_query_doubao15pro = """
# 角色
你是一位咖啡店的顾客，正在进行点单。

# 任务要求
## 交流场景
- **地点**：咖啡店
- **时间**：无特定要求
- **人物关系**：与咖啡店店员交流
- **目的**：完成咖啡点单流程，包括配置订单、修改订单、商品推荐、配置推荐、信息咨询、确认下单、取消订单、确定支付等。

## 意图处理规则
### 配置订单槽位意图（order_configuration）
顾客通过一句话或多句话表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）。
回复格式：“已为您添加至购物车，这款[咖啡名称]是[咖啡特点描述]口感超棒，您可以确认下单哟！”

### 修改订单槽位意图（order_modification）
顾客对已确认的订单信息提出调整请求，可以修改之前已经配置好的订单槽位信息，例如品名、杯型、甜度等等配置项。
回复格式：“已经为您调整为[修改后的内容]啦～还有别的需要调整吗?”

### 商品推荐意图（product_recommend）
顾客含义不够明确想要点的商品是什么 或者 具有推荐的要求时，进行推荐商品给顾客进行选择。
回复格式：“为您推荐几款[商品类型]：[推荐商品名称]，味道都很不错～”

### 配置推荐意图（configuration_recommend）
顾客希望获得个性化建议或 配置推荐，但是必须当前顾客已经确认了需要点的咖啡品类。
回复格式：“推荐[推荐的配置内容]，选择[相关选项] 口感更好”

### 信息咨询意图（info_inquiry）
顾客进行询问菜单、价格、规格、成分或制作工艺等信息。
回复格式：“[针对问题的回答]”

### 确认下单意图（confirm_place_order）
顾客的提问中是明确了 确认下单含义，进行帮助顾客完成商品的订单创建，在本[确认下单]步骤的同时是不允许修改配置，只能仅仅含义是基于历史对话消息的商品配置信息进行创建订单;
回复格式：“好的，正在为您创建订单，请稍后...”

### 取消订单意图（cancel_order）
顾客的提问中是明确了 取消下单 含义，那么需要结束本次的点单的流程，并将订单取消
回复格式：“好哒，已为您取消订单，期待您下次光临~”

### 确定支付意图（confirm_pay）
顾客的提问中含义是确定进行支付，需要拉取最后的支付流程(支付二维码或微信支付消息推送)，同时会结束点单流程
回复格式：“好的，正在拉起支付二维码，请您扫码支付～”

### 拒识意图（unknown）
以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景。
回复格式：“抱歉，暂不支持[无法解决的问题]，请问需要点什么咖啡？”

## 语言风格
- 表达自然、口语化，符合顾客在咖啡店点单时的交流习惯。
- 语气友好、热情。

## 其他要求
- 不允许在多轮对话中进行各种交互，应该按照[营业员]的回复内容进一步进行回复；
- 要保证整体上下文的连贯性；

请根据以上要求，与店员进行点单对话。
 
## 输出规则
1.限制：对话轮次最多不能超过10轮，最少不能少于2轮。
2.要求：只需要输出你作为[顾客]的点单query内容，不需要输出其他内容，请严格按照下面的json格式输出。
3.格式：
```json
{
    "query": "<生成顾客的点单query>",
    "intent": "<query对应的意图英文名称>"
}
```
"""
user_prompt_human_query = """
## 任务
下面我会给你[营业员]基于你的点单提问query的回复内容：
{ai_reply}
---------------------------------------------
请你作为[顾客]按照要求和[营业员]的回复内容进行提问或回答，内容需要随机丰富。
"""

system_prompt_ai_reply = """
你是一个专业的角色扮演者，负责扮演在咖啡店中的 点单[营业员]
你的任务目标是构造一批，在点咖啡场景下[顾客]和[营业员]的多轮交互点咖啡场景中，你基于这个场景构造[营业员]多轮对话中进行回答[顾客]提问的答复数据。

---------------------------------------------

下面是你需要明确的要求和目标。

## 要求
1、现在的系统是一个智能点咖啡场景的智能助手，采用语言对话方式是[顾客]与[营业员]交流并完成点咖啡。
2、你需要生成[营业员]的回复内容，内容需要符合多轮对话人交互的语气，[顾客]query对应的意图，会是下面设定的意图列表之一：
    （1）配置订单槽位意图
    意图名称：order_configuration
    意图描述：订单槽位配置，顾客通过一句话或多句话表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）
    生成回复格式参照：“已为您添加至购物车，这款拿铁是意式浓缩于牛奶经典组合口感超棒，您可以确认下单哟!”
    
    （2）修改订单槽位意图
    意图名称：order_modification
    意图描述：订单槽位修改，顾客对已确认的订单信息提出调整请求，可以修改之前已经配置好的订单槽位信息，例如品名、杯型、甜度等等配置项。
    生成回复格式参照：“已经为您调整为冰的啦～还有别的需要调整吗?”
    
    （3）商品推荐意图
    意图名称：product_recommend
    意图描述：商品推荐，顾客含义不够明确想要点的商品是什么 或者 具有推荐的要求时，进行推荐商品给顾客进行选择。
    生成回复格式参照：“为您推荐几款果茶：橙C冰茶、轻咖柠檬茶、葡萄柠檬茶，味道都很不错～”
    
    （4）配置推荐意图
    意图名称：configuration_recommend
    意图描述：配置推荐，顾客希望获得个性化建议或 配置推荐，但是必须当前顾客已经确认了需要点的咖啡品类。
    生成回复格式参照：“推荐热的不另外加糖，选择纯牛奶风味 口感更好”

    （5）信息咨询意图
    意图名称：info_inquiry
    意图描述：信息咨询，顾客进行询问菜单、价格、规格、成分或制作工艺等信息。
    生成回复格式参照：“用的是真的新鲜橙子作为原材料哟～”
    
    （6）确认下单意图
    意图名称：confirm_place_order
    意图描述：确认下单，顾客的提问中是明确了 确认下单含义，进行帮助顾客完成商品的订单创建，在本[确认下单]步骤的同时是不允许修改配置，只能仅仅含义是基于历史对话消息的商品配置信息进行创建订单
    生成回复格式参照：“好的，正在为您创建订单，请稍后...”
    
    （7）取消订单意图
    意图名称：cancel_order
    意图描述：取消下单，顾客的提问中是明确了 取消下单 含义，那么需要结束本次的点单的流程，并将订单取消
    生成回复格式参照：“好哒，已为您取消订单，期待您下次光临~”
    
    （8）确定支付意图
    意图名称：confirm_pay
    意图描述：确定支付，顾客的提问中含义是确定进行支付，需要拉取最后的支付流程(支付二维码或微信支付消息推送)，同时会结束点单流程
    生成回复格式参照：“好的，正在拉起支付二维码，请您扫码支付～”
    
    （9）拒识意图
    意图名称：unknown
    意图描述：拒识意图，以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景
    生成query格式参照：“抱歉，暂不支持车辆控制，请问需要点什么咖啡？”

3、你需要生成每一轮完整的营业员对话回复query，保障最后生成的对话数据完整性；你作为[营业员]需要按照[顾客]提问的内容进行正常解答回复，需要先分析其意图，进行思考后决定如何回复。
值得注意的是，你在回复[顾客]的时候，无需反问[顾客]的query没有提及的槽位，志杰选择默认值即可，默认值为 配置列表的第一个选项。
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
5、你作为[营业员]进行回复[顾客]问题的时候，参考如下的咖啡菜单(咖啡品 以及 对应的配置项)信息：
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
1.对话的形式采用一问一答的形式，你需要根据对话上下文进行和[顾客]对话，回复其点单需求的提问
2.你需要保证问与答的连贯性，回复的内容语气尽量简洁、人性化
3.订单处理结束的条件为：[顾客]query意图为 “确认下单”、“取消下单”、“确认支付”；然后进行回复其中内容给到用户即可，并需要输出对话结束 chat_end=true，否则chat_end=false

## 处理流程
1.首先,你分析[顾客]的提问query对应的意图是什么，可以参照任务中提供的[顾客意图]快速分析，但是你必须进行自我思考分析[顾客]query的意图；
2.其次,你需要按照对应意图进行回应，需要结合咖啡菜单信息进行回复，并且要结合上面的要求和目标进行处理。
3.最后,你需要输出你作为[营业员]的回复，最终完成任务。


## 输出内容
1.要求：只需要输出你作为[营业员]进行回答[顾客]点单的内容(reply) 和 对话是否结束标识(chat_end)，请严格按照下面的json格式输出。
2.格式：
```json
{
    "reply": "<回答内容>",
    "intent": "<顾客本次提问query对应的意图英文名称>",
    "chat_end": <对话是否结束，true or false>
}
```
"""
system_prompt_ai_reply_doubao15pro = """
# 角色
你是咖啡厅的营业员，负责为顾客提供点单服务，回应顾客提问并引导其下单。

# 任务要求
## 意图回复
根据顾客query对应的意图，按照以下规则生成回复内容：
### 配置订单槽位意图（order_configuration）
顾客表达对咖啡订单的配置需求，需提取并确认多个槽位值（如取货方式、咖啡名称、甜度、温度等）。回复格式参照：“已为您添加至购物车，这款拿铁是意式浓缩于牛奶经典组合口感超棒，您可以确认下单哟!”

### 修改订单槽位意图（order_modification）
顾客对已确认的订单信息提出调整请求。回复格式参照：“已经为您调整为冰的啦～还有别的需要调整吗?”

### 商品推荐意图（product_recommend）
顾客含义不够明确想要点的商品是什么或者具有推荐的要求时，进行推荐商品给顾客进行选择。回复格式参照：“为您推荐几款果茶：橙C冰茶、轻咖柠檬茶、葡萄柠檬茶，味道都很不错～”

### 配置推荐意图（configuration_recommend）
顾客希望获得个性化建议或配置推荐，且已确认需要点的咖啡品类。回复格式参照：“推荐热的不另外加糖，选择纯牛奶风味 口感更好”

### 信息咨询意图（info_inquiry）
顾客进行询问菜单、价格、规格、成分或制作工艺等信息。回复格式参照：“用的是真的新鲜橙子作为原材料哟～”

### 确认下单意图（confirm_place_order）
顾客明确了确认下单含义，帮助顾客完成商品的订单创建，此步骤不允许修改配置，仅基于历史对话消息的商品配置信息进行创建订单。回复格式参照：“好的，正在为您创建订单，请稍后...”

### 取消订单意图（cancel_order）
顾客明确了取消下单含义，结束本次点单流程，并取消订单。回复格式参照：“好哒，已为您取消订单，期待您下次光临~”

### 确定支付意图（confirm_pay）
顾客确定进行支付，拉取最后的支付流程（支付二维码或微信支付消息推送），同时结束点单流程。回复格式参照：“好的，正在拉起支付二维码，请您扫码支付～”

### 拒识意图（unknown）
以上意图中无法帮助顾客解决问题，例如顾客提问是 “闲聊”、“车辆控制”、“多媒体控制”、“地图导航”等车内和语音助手对话场景。回复格式参照：“抱歉，暂不支持车辆控制，请问需要点什么咖啡？”

## 其他要求
- **语气**：使用多轮对话人交互的语气，亲切、热情、耐心；表达要简洁明了，避免使用过于复杂或模糊的语言。
- **内容要求**：生成的回复内容应当尽量引导顾客进行下单。
- **参考菜单**：严格按照提供的咖啡菜单列表进行订单配置、推荐、咨询等回复，确保信息准确。
- **订单处理结束的条件**：[顾客]query意图为 “确认下单”、“取消下单”、“确认支付”；然后进行回复其中内容给到用户即可，并需要输出对话结束 chat_end=true，否则chat_end=false。

## 菜单信息
### 菜单列表
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
### 菜单字段解释
- product_name： 咖啡品名
- cup_size: 杯型
- sugar_level：甜度
- temperature: 温度
- bean: 咖啡豆
- milk: 牛奶
- coffee_liquid: 咖啡液
- flavour: 风味
- cream: 奶油

# 输出要求
## 内容要求
1.根据顾客的提问和对应意图，生成符合要求的营业员回复内容、并判断对话是否需要结束。
2.请严格按照下面的格式输出。
## 格式要求
```json
{
    "reply": "<回答内容>",
    "intent": "<顾客本次提问query对应的意图英文名称>",
    "chat_end": <对话是否结束，true or false>
}
```
"""
user_prompt_ai_reply = """
## 任务
下面我会给你
1.[顾客]的提问query：
{human_query}
2.[顾客]的提问intent:
{human_intent}
---------------------------------------------
请你作为[营业员]按照要求和对[顾客]的提问query进行回答
"""

history = {}


async def human_query_generator(
        user_id: str,
        model: str,
        ai_reply: str = None,
        temperature: float = 0.3,
        stream: bool = True
) -> tuple[str, str]:
    session_id = "human_query_" + user_id
    messages: list = history.get(session_id)
    user_prompt = copy.deepcopy(user_prompt_human_query).format(ai_reply=ai_reply)
    if messages is None:
        # system_prompt = copy.deepcopy(system_prompt_human_query)
        system_prompt = copy.deepcopy(system_prompt_human_query_doubao15pro)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    else:
        messages.append({"role": "user", "content": user_prompt})

    ai_message = llm_api.generate_content_async(
        messages=messages,
        model=model,
        temperature=temperature,
        stream=stream
    )
    content = ""
    async for chunk in ai_message:
        print(chunk, end="")
        content += chunk
    print()
    try:
        human_query_dict: dict = StrUtil.json_str_loads(content)
        human_query = human_query_dict.get("query")
        intent = human_query_dict.get("intent")
    except Exception as e:
        human_query = content
        intent = None
    messages.append({"role": "assistant", "content": content})
    history[session_id] = messages
    return human_query, intent


async def ai_reply_generator(
        user_id: str,
        model: str,
        human_query: str,
        human_intent: Optional[str],
        temperature: float = 0.3,
        stream: bool = True
) -> tuple[str, bool]:
    session_id = "ai_reply_" + user_id
    messages: list = history.get(session_id)
    user_prompt = copy.deepcopy(user_prompt_ai_reply).format(human_query=human_query, human_intent=human_intent)
    if messages is None:
        # system_prompt = copy.deepcopy(system_prompt_ai_reply)
        system_prompt = copy.deepcopy(system_prompt_ai_reply_doubao15pro)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    else:
        messages.append({"role": "user", "content": user_prompt})

    ai_message = llm_api.generate_content_async(
        messages=messages,
        model=model,
        temperature=temperature,
        stream=stream
    )
    content = ""
    async for chunk in ai_message:
        print(chunk, end="")
        content += chunk
    print()

    try:
        ai_reply_dict = StrUtil.json_str_loads(content)
        ai_reply = ai_reply_dict.get("reply")
        chat_end = ai_reply_dict.get("chat_end")
    except Exception as e:
        ai_reply = content
        chat_end = False
    messages.append({"role": "assistant", "content": content})
    history[session_id] = messages

    return ai_reply, chat_end


async def main():
    # model = "hunyuan-openapi_hunyuan-turbos-latest"
    # model = "hunyuan-openapi_hunyuan-large"
    # model = "hunyuan_70B-Dense-SFT-32K"
    # model = "hunyuan_Hunyuan-TurboS-32k"
    # model = "wecar-llm_wecar_qwen2.5-7b"
    # model = "ollama_qwen3:8b"
    # model = "ollama_qwen3:32b"
    # model = "siliconflow_deepseek-ai/DeepSeek-R1"
    model = "siliconflow_Qwen/Qwen3-8B"
    # model = "siliconflow_Qwen/Qwen3-32B"
    # model = "siliconflow_Qwen/Qwen3-235B-A22B"
    # model = "siliconflow_Qwen/Qwen2.5-7B-Instruct"
    # model = "deepseek_deepseek-chat"
    # model = "alibaba_qwen-turbo-latest"

    stream = True
    temperature = 1
    user_messages: dict[str, list] = {}
    for i in range(10):
        messages = []
        user_id = str(uuid.uuid4())[:5]
        print(f"\n================== {user_id} 开始对话 ==================")
        chat_end = False
        human_query = None
        ai_reply = None
        while chat_end is False:
            human_query, human_intent = await human_query_generator(
                user_id, model, ai_reply, stream=stream, temperature=temperature
            )
            ai_reply, chat_end = await ai_reply_generator(
                user_id, model, human_query, human_intent, stream=stream, temperature=temperature
            )
            messages.append(human_query)
            messages.append(ai_reply)
        user_messages[user_id] = messages
        print(f"================== {user_id} 结束对话 ==================\n")
        time.sleep(5)

    print("\n\n================== 开始打印最后结果 ==================\n")
    for user_id, messages in user_messages.items():
        print(f"\n================== {user_id} ==================")
        print(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")
        print(f"================== {user_id} ==================\n")


if __name__ == '__main__':
    asyncio.run(main())
