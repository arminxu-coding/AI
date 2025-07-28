import json
import re
import unicodedata
from typing import Type, List, Any
from pydantic import BaseModel


class ModelUtil:
    @staticmethod
    def model_list_to_json_str(model_list: List[BaseModel], indent: int = None) -> str:
        """
        将 BaseModel 对象列表序列化为 JSON 字符串
        :param model_list: List[BaseModel]
        :param indent: 缩进格式 (可选)
        :return: JSON 字符串
        """
        dict_list = [item.model_dump() for item in model_list]
        return json.dumps(dict_list, allow_nan=False, ensure_ascii=False, indent=indent)

    @staticmethod
    def json_str_to_model_list(json_str: str, model_type: Type[BaseModel]) -> List[BaseModel]:
        """
        将 JSON 字符串反序列化为 BaseModel 列表
        :param json_str: JSON 字符串
        :param model_type: 目标模型类型（如 AppItem）
        :return: List[BaseModel]
        """
        dict_list = json.loads(json_str)
        return [model_type(**item) for item in dict_list]


class StrUtil:
    @staticmethod
    def json_str_loads(content: str) -> dict | list:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        if ObjectUtil.is_json(content):
            return json.loads(content)
        patterns = [
            r'<content>(.*?)</content>',  # 标签形式
            r'```json\s*(.*?)\s*```',  # JSON 代码块
            r'```\s*(.*?)\s*```',  # 普通代码块
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                json_str = match.group(1)
                json_str = re.sub(r'[\n\s]+', ' ', json_str).strip()
                return json.loads(json_str)
        raise ValueError("content does not contain a valid JSON string")


class ObjectUtil:
    @staticmethod
    def is_empty(obj: Any) -> bool:
        """
        判断对象是否为空或为 None。
        支持以下类型：
        - str: 空字符串或仅包含空白字符
        - dict: 空字典或 None
        - list: 空列表或 None
        - 其他类型: None 判定为空
        """
        if obj is None:
            return True

        if isinstance(obj, str):
            obj = obj.strip()
            if len(obj) == 0:
                return True
            # 检查是否仅包含空白字符
            for char in obj:
                if not unicodedata.category(char).startswith('Z'):
                    return False
            return True

        if isinstance(obj, (dict, list)):
            return len(obj) == 0

        return False

    @staticmethod
    def is_not_empty(obj: Any) -> bool:
        """
        判断对象是否非空。
        """
        return not ObjectUtil.is_empty(obj)

    @staticmethod
    def is_json(obj: str) -> bool:
        """
        判断字符串是否为有效的 JSON 格式。
        """
        if ObjectUtil.is_empty(obj):
            return False
        try:
            json.loads(obj)
            return True
        except Exception as e:
            return False
