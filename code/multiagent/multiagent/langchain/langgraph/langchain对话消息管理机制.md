# LangChain对话消息管理机制

本文主要介绍我们在使用 `langgraph` 过程中，经常会定义一个函数用于承接每次 llm 执行之前的消息列表，也就是下方的定义:

```python
class State(TypedDict):
    # 定义一个langgraph中传输的消息列表messages（先别管为啥这么定义）
    messages: Annotated[list, add_messages]
```

## 引言

那么很奇怪呢？什么是 **Annotated** 什么是 **add_messages**，想要搞清楚这两个含义，首先我们得先明确一个点，也就是
每次llm执行之前会给什么东西发给llm，其实不言而喻的就是我们的对话消息列表messages，也称之为 chat-history:

1. SystemMessage
2. UserMessage
3. AiMessage
4. ToolMessage

那么其实上面定义的State也就是这个玩意儿，只是其中目前核心关注的是messages而已，其实还有别的例如model、tmepture...

所以我们理解了这里定义的类型一个 list[Message]，那么为啥是  **Annotated** + **add_messages**，下面给出解释：

## 1、Annotated

**作用：**标记状态字段的更新规则

**解释：**`Annotated` 是 Python 3.9+ 引入的类型注解工具（来自 `typing` 模块），语法为 `Annotated[类型, 元数据]`
，作用是给「类型」附加额外的元数据（可以是函数、类、常量等）。

在 LangGraph 中，它的核心用法是：**给状态字段（如 `messages`）标记「更新该字段时需要使用的函数」**。

## 2、add_messages

**作用：**消息合并的实际逻辑

**解释：**`add_messages` 是具体的「更新规则函数」，它定义了如何将「新消息」（`right`）合并到「历史消息」（`left`）中，核心逻辑包括：

- 用消息 `id` 判断是否需要替换（同 `id` 覆盖）；
- 新增无重复 `id` 的消息；
- 处理删除指令（`RemoveMessage`）；
- 可选的格式转换（如 `langchain-openai` 格式）。

它的输入是两个消息列表（`left` 为当前历史，`right` 为新消息），输出是合并后的新列表。这个函数本身是纯逻辑实现，不依赖框架，但需要符合框架对「更新器函数」的参数和返回值要求（如输入
`left` 和 `right`，返回合并结果）。

## 3、@_add_messages_wrapper

**作用：**适配框架接口的装饰器

**解释：**装饰器 `@_add_messages_wrapper` 的作用是「包装 `add_messages` 函数」，使其能被 LangGraph 框架正确识别和调用。具体来说，它解决了两个问题：

- **统一接口规范**：LangGraph 对「状态更新器函数」有固定的接口要求（比如输入参数的格式、返回值的类型）。`add_messages`
  是业务逻辑函数，装饰器会将其转换为符合框架规范的函数（例如处理参数校验、格式适配）。
- **绑定更新逻辑**：装饰器会给 `add_messages` 附加一些框架内部的标识（如标记这是一个「消息更新器」），让框架在读取 `Annotated`
  元数据时，能正确识别这是一个合法的更新器函数。

简单说，装饰器是 `add_messages` 和 LangGraph 框架之间的「翻译官」，确保框架能正确调用这个函数。

## 4、三者联动的完整流程

当在 LangGraph 中定义工作流（`StateGraph`）并运行时，这三者会按以下步骤自动维护对话历史 `messages`：

### 4.1、定义状态结构，通过 `Annotated` 绑定更新规则

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]  # 告诉框架：messages 用 add_messages 更新
```

此时，框架已经知道：`State` 中的 `messages` 字段需要用 `add_messages` 函数来更新。

### 4.2、节点返回新消息，触发状态更新

在工作流中，节点函数（如对话机器人的回复逻辑）会返回新的消息，格式通常是 `{"messages": [新消息列表]}`。例如：

```python
def chatbot_node(state: State) -> dict:
    # 生成一条新的 AI 消息
    return {"messages": [AIMessage(content="你好！", id="ai_1")]}
```

当节点运行结束后，框架需要将这些新消息合并到当前状态的 `messages` 中。

### 4.3、框架自动调用 `add_messages` 完成合并

框架会执行以下操作：

1. 提取当前状态中的 `messages` 作为 `left`（历史消息）；
2. 提取节点返回的 `messages` 作为 `right`（新消息）；
3. 因为 `messages` 字段被 `Annotated` 标记了 `add_messages`，框架会调用被 `@_add_messages_wrapper` 装饰后的
   `add_messages` 函数，传入 `left` 和 `right`；
4. 用 `add_messages` 的返回值（合并后的消息列表）更新状态中的 `messages` 字段。

### 4.4、多轮迭代，自动维护历史

在多轮对话中，每次节点运行都会重复步骤 2-3：

- 新消息不断通过 `add_messages` 合并到历史中；
- 若有重复 `id` 的消息，自动替换；
- 若有删除指令，自动移除对应消息。

最终实现「无需手动处理合并逻辑，对话历史自动维护」的效果。

**举例：一次完整的联动过程**

假设初始状态 `state = {"messages": [HumanMessage(content="Hi", id="h1")]}`，节点返回
`{"messages": [AIMessage(content="Hello", id="a1")]}`：

1. 框架读取 `State` 定义，发现 `messages` 绑定了 `add_messages`；
2. 提取 `left = [HumanMessage(id="h1")]`（当前历史），`right = [AIMessage(id="a1")]`（新消息）；
3. 调用 `add_messages(left, right)`，返回合并结果 `[HumanMessage(id="h1"), AIMessage(id="a1")]`；
4. 更新状态 `state["messages"]` 为合并结果，完成一次更新。

如果下一轮节点返回 `{"messages": [HumanMessage(content="Hi again", id="h1")]}`（同 `id` 替换）：

- `left` 是上一轮的 `[h1, a1]`，`right` 是 `[h1_new]`；
- `add_messages` 会用 `h1_new` 替换 `h1`，结果为 `[h1_new, a1]`；
- 状态自动更新为新列表。

### 4.5、总结

三者的联动核心是：

- `Annotated` 标记「哪个函数负责更新字段」；
- `@_add_messages_wrapper` 确保「这个函数能被框架调用」；
- `add_messages` 实现「具体的更新逻辑」。

最终，LangGraph 框架通过读取 `Annotated` 元数据，自动调用装饰后的 `add_messages` 函数，在每次节点运行后完成消息合并，从而实现对话历史的自动维护。

上面还是很复杂的原理，其实有一个核心的概念就是：

> LangGraph 状态管理机制：通过类型注解标记状态字段的更新规则，通过装饰器适配规则函数，最终让框架自动调用规则函数完成状态更新。

其实如果不进行理解也是可以的，直接使用即可，仅仅是langgraph封装的很复杂而已，简单理解就是简单的东西他们经过工程化之后过于复杂了，反而不利于开发者读懂

（`这就是传说中的炫技，我想达到的水平，可惜奈何实力不够😀`）







------







下面将给出一个完整的详细解释，来自于gpt的内容，看看就好

## 5、详细解释

这段代码是 LangChain（尤其是 LangGraph 框架）中用于**管理消息列表合并与更新**的核心工具，主要功能是合并两个消息列表（`left`和
`right`），并根据消息 ID 处理 “新增”“替换”“删除” 逻辑。它在多轮对话、状态管理场景中非常重要，下面从功能、细节、使用案例和结果展开说明。

### 5.1、核心功能：消息列表的智能合并

`add_messages` 函数的核心作用是：将两个消息列表（`left` 作为基础列表，`right` 作为待合并列表）合并为一个新列表，遵循以下规则：

- **新增**：如果 `right` 中的消息 ID 在 `left` 中不存在，则直接追加到合并结果中。
- **替换**：如果 `right` 中的消息 ID 与 `left` 中某个消息的 ID 相同，则用 `right` 的消息替换 `left` 的消息。
- **删除**：如果 `right` 中包含 `RemoveMessage` 类型的消息（且 ID 存在于 `left` 中），则从合并结果中删除该 ID 对应的消息；若
  `RemoveMessage` 的 ID 为 `REMOVE_ALL_MESSAGES`，则清空之前的所有消息，只保留 `right` 中该消息之后的内容。
- **格式转换**：支持将合并后的消息转换为 `langchain-openai` 格式（适配 OpenAI 的消息结构，如文本、图片块等）。

### 5.2、代码细节解析

#### 1. 函数参数

- `left: Messages`：基础消息列表（通常是已有的历史消息）。
- `right: Messages`：待合并的消息列表（通常是新生成的消息）。
- `format: Literal["langchain-openai"] | None`：可选参数，指定输出消息的格式。`None` 表示保持原始格式；`"langchain-openai"`
  表示转换为符合 OpenAI 规范的消息结构（如支持文本块、图片 URL 块等）。

#### 2. 内部逻辑拆解

##### （1）类型统一与消息转换

```python
# 确保left和right是列表（如果传入单个消息则转为列表）
if not isinstance(left, list):
    left = [left]
if not isinstance(right, list):
    right = [right]

# 将输入的消息转换为标准BaseMessage对象（处理不同格式的消息输入）
left = [message_chunk_to_message(cast(BaseMessageChunk, m)) for m in convert_to_messages(left)]
right = [message_chunk_to_message(cast(BaseMessageChunk, m)) for m in convert_to_messages(right)]
```

这一步确保输入的消息（无论原始格式如何，如字典、字符串、Message 对象）都被转换为 LangChain 标准的 `BaseMessage` 类型（如
`HumanMessage`、`AIMessage` 等），统一处理格式。

##### （2）消息 ID 处理

```python
# 为没有ID的消息自动生成UUID（确保每个消息有唯一标识）
for m in left:
    if m.id is None:
        m.id = str(uuid.uuid4())
for idx, m in enumerate(right):
    if m.id is None:
        m.id = str(uuid.uuid4())
    # 检查是否有"删除所有消息"的标记
    if isinstance(m, RemoveMessage) and m.id == REMOVE_ALL_MESSAGES:
        remove_all_idx = idx
```

每个消息必须有唯一 ID（用于判断是否需要替换 / 删除），如果用户未指定，自动生成 UUID。同时检测 `right` 中是否有 “删除所有消息”
的指令（`RemoveMessage` 且 ID 为 `REMOVE_ALL_MESSAGES`）。

##### （3）合并逻辑

- **处理 “删除所有消息”**：如果 `right` 中存在 `REMOVE_ALL_MESSAGES`，则合并结果仅保留 `right` 中该消息之后的内容（清空历史消息）。

  ```python
  if remove_all_idx is not None:
      return right[remove_all_idx + 1 :]
  ```

- **常规合并（替换 / 新增 / 删除）**：

  ```python
  merged = left.copy()  # 以left为基础
  merged_by_id = {m.id: i for i, m in enumerate(merged)}  # 用字典记录left中消息ID与索引的映射
  ids_to_remove = set()  # 记录需要删除的消息ID
  
  for m in right:
      if m.id in merged_by_id:  # 若right的消息ID在left中存在
          if isinstance(m, RemoveMessage):  # 如果是删除指令，标记待删除
              ids_to_remove.add(m.id)
          else:  # 否则替换left中的消息
              merged[merged_by_id[m.id]] = m
      else:  # 若ID不存在
          if isinstance(m, RemoveMessage):  # 不能删除不存在的消息，抛错
              raise ValueError(f"Attempting to delete a message with an ID that doesn't exist ('{m.id}')")
          # 新增消息到合并列表
          merged.append(m)
          merged_by_id[m.id] = len(merged) - 1
  
  # 最终移除所有标记为删除的消息
  merged = [m for m in merged if m.id not in ids_to_remove]
  ```

##### （4）格式转换

如果指定 `format="langchain-openai"`，则调用 `_format_messages` 将消息转换为 OpenAI 兼容的格式（例如，图片消息会转为
`image_url` 结构）：

```python
if format == "langchain-openai":
    merged = _format_messages(merged)
```

#### 3. 装饰器 `@_add_messages_wrapper`

这是 LangGraph 框架的内部装饰器，主要作用是将 `add_messages` 函数标记为 “状态更新器”，使其能在 LangGraph
的状态管理中被自动调用（例如，当定义状态中的 `messages` 字段时，通过 `Annotated` 关联该函数，实现消息的自动合并）。

### 5.3、`State` 类的作用

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]
```

这是 LangGraph 中定义 “状态结构” 的典型方式：

- `State` 继承 `TypedDict`，用于定义多智能体 / 工作流中传递的状态数据结构（类似字典的键值对）。
- `messages` 是状态中的一个字段，存储对话消息列表。
- `Annotated[list, add_messages]` 表示：当更新 `messages` 字段时，自动使用 `add_messages` 函数进行合并（而不是简单覆盖）。这是
  LangGraph 的核心特性，确保多轮对话中消息列表能 “智能更新”（保留历史、处理替换 / 删除）。

### 5.4、使用案例与结果展示

#### 案例 1：基础合并（新增消息）

```python
from langchain_core.messages import AIMessage, HumanMessage

# 基础消息列表（left）
msgs1 = [HumanMessage(content="Hello", id="1")]
# 待合并消息列表（right）
msgs2 = [AIMessage(content="Hi there!", id="2")]

# 合并
result = add_messages(msgs1, msgs2)
print(result)
```

**结果**：两个消息列表合并，`right` 中的新消息被追加：

```plaintext
[HumanMessage(content='Hello', id='1'), AIMessage(content='Hi there!', id='2')]
```

#### 案例 2：替换已有消息（同 ID 覆盖）

```python
# 基础消息列表（left）
msgs1 = [HumanMessage(content="Hello", id="1")]
# 待合并消息列表（right）：同ID但内容不同
msgs2 = [HumanMessage(content="Hello again", id="1")]

# 合并
result = add_messages(msgs1, msgs2)
print(result)
```

**结果**：`right` 中同 ID 的消息替换了 `left` 中的消息：

```plaintext
[HumanMessage(content='Hello again', id='1')]
```

#### 案例 3：在 LangGraph 中管理对话状态

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph


# 定义状态结构：messages字段用add_messages自动合并
class State(TypedDict):
    messages: Annotated[list, add_messages]


# 定义节点函数：生成一条AI消息
def chatbot(state: State) -> dict:
    return {"messages": [AIMessage(content="Hello, I'm a bot!", id="ai_1")]}


# 构建工作流
builder = StateGraph(State)
builder.add_node("chatbot", chatbot)  # 添加节点
builder.set_entry_point("chatbot")  # 入口节点
builder.set_finish_point("chatbot")  # 结束节点
graph = builder.compile()

# 运行工作流（初始状态为空）
result = graph.invoke({})
print(result["messages"])
```

**结果**：状态中的 `messages` 字段通过 `add_messages` 自动更新，包含生成的 AI 消息：

```plaintext
[AIMessage(content="Hello, I'm a bot!", id="ai_1")]
```

#### 案例 4：删除消息与格式转换

```python
from langchain_core.messages import RemoveMessage

# 基础消息列表
left = [
    HumanMessage(content="First message", id="1"),
    AIMessage(content="First reply", id="2")
]

# 待合并列表：先删除ID=1的消息，再新增一条消息
right = [
    RemoveMessage(id="1"),  # 删除ID=1的消息
    HumanMessage(content="New message", id="3")  # 新增消息
]

# 合并（不指定格式）
result = add_messages(left, right)
print("合并后（原始格式）：", result)

# 合并（指定OpenAI格式）
result_openai = add_messages(left, right, format="langchain-openai")
print("合并后（OpenAI格式）：", result_openai)
```

**结果**：

- 原始格式：ID=1 的消息被删除，新增 ID=3 的消息。
- OpenAI 格式：消息内容被转换为符合 OpenAI 规范的结构（如文本块）。

```plaintext
合并后（原始格式）：[AIMessage(content='First reply', id='2'), HumanMessage(content='New message', id='3')]
合并后（OpenAI格式）：[AIMessage(content='First reply', id='2'), HumanMessage(content='New message', id='3')]  # 示例，实际会转换为OpenAI的消息结构
```

### 5.5、总结

`add_messages` 是 LangChain 中管理消息列表的核心工具，通过 “ID 匹配” 实现消息的新增、替换和删除，确保多轮对话状态的一致性。结合
LangGraph 的 `State` 类（用 `Annotated` 关联），可以在工作流 / 多智能体系统中自动维护消息状态，无需手动处理合并逻辑。

其典型应用场景包括：多轮对话机器人、智能体之间的消息传递、带历史记录的交互系统等，尤其适合需要 “增量更新” 消息列表的场景。