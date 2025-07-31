# Agent设计与开发核心指南

## 1、核心哲学

“上下文工程优先于模型微调 (Context Engineering over Fine-tuning)”

原则: 与其投入大量时间和资源去微调一个模型，不如将精力集中在如何构建和管理输入给模型的上下文（Prompt）。

理由: 上下文工程的迭代速度快、成本低，且能更好地利用现有前沿模型强大的“即时学习”能力。对于绝大多数应用场景，这比微调更具性价比。

## 2、六大核心设计原则

### 2.1、追求上下文效率 

追求上下文效率 (Context Efficiency First)

目标：降低延迟，节约成本。

实施细则：

- `缓存前缀 (Cache the Prefix)`: 将所有固定不变的指令、背景信息、工具列表等（即 System Prompt）作为稳定的“前缀”。这部分内容只在会话开始时处理一次，其计算结果（KV-cache）在后续所有交互中被重复利用。
- `只增不减 (Append-Only)`: 绝对避免修改上下文的中间部分。所有的“思考”、“行动结果”、“新信息”都应以追加（Append）的方式添加到上下文的末尾。这能确保KV-cache的有效性。

### 2.2、引导模型注意力

引导模型注意力 (Guide Model's Attention)

目标: 确保 Agent 在多步骤任务中不“分心”或“忘记”目标。

实施细则:

- 复述目标 (Goal Recitation): 在 Agent 的“思考区”或“暂存区”（Scratchpad）中，强制它在每一步行动前，都简要复退一遍总体目标和当前计划。
- 动态待办列表 (Dynamic To-Do List): 让 Agent 维护一个任务清单，并明确标记已完成 [x]、待处理 [ ] 和失败 [!] 的状态。这为模型提供了清晰的路线图。
- 利用近因效应 (Recency Bias): 将当前最重要、最需要执行的指令放在整个 Prompt 的最末尾，以最大化其在注意力机制中的权重。

### 2.3、从错误中学习

从错误中学习 (Learn from Failure)

目标: 让 Agent 具备初步的自我修正能力，避免重复犯错。

实施细则:

- 记录失败 (Log Failures): 当一个工具调用失败或行动未达预期时，必须将失败的“行动”和“结果（错误信息）”明确记录在上下文中。
- 反思失败 (Reflect on Failures): 在下一步的“思考区”，引导 Agent 分析失败原因（例如：“上次使用搜索工具失败，因为查询语句过于模糊，这次我将尝试更具体的关键词。”）。

### 2.4、稳定工具空间

稳定工具空间 (Stabilize the Tool Space)

目标：避免因工具集变化导致模型困惑和缓存失效。

实施细则：

- 掩蔽而非移除 (Mask, Don't Remove): 即使某个工具在当前步骤不可用，也不要从工具列表中将其删除。应该通过一个状态（如 (disabled)）来“掩蔽”它。这维持了上下文结构的稳定性。

### 2.5、外化核心记忆

外化核心记忆 (Externalize Core Memory)

目标：突破上下文窗口的长度限制，处理海量信息。

实施细则：

- 利用外部存储: 对于长篇文档、历史数据等，不要直接塞进上下文。让 Agent 学会使用读写文件的工具，将这些信息存储在外部文件系统中。
- 摘要式记忆: 在上下文中只保留对外部信息的“指针”或“摘要”（例如：“我已将完整的访谈记录保存在 interview_transcript.txt，其核心观点是...”)。

### 2.6、动态打破僵局

动态打破僵局 (Dynamically Break Loops)

目标: 防止 Agent 陷入无效的重复行为循环。

实施细则:

- 引入变数 (Introduce Variation): 如果检测到 Agent 连续多次执行相同的失败操作，可以在 Prompt 中主动引入变化，例如建议它“尝试一种完全不同的方法”或“换一个工具试试”。
- 限制重试次数: 在 Agent 的内在逻辑中设置重试次数上限，达到上限后强制 Agent 寻求帮助或终止任务。

## 3、通用 Agent 规则模板 (Markdown 格式)

`使用说明:` 这是一个高复用性的“骨架”，您可以直接复制并填充具体内容来开发您的 Agent。它整合了上述所有设计原则。

### 3.1、最高目标

最高目标 (GOAL)

在此定义整个任务的最终、最高级别目标。Agent在每一步思考时都应回顾此目标。

> 示例: 成为一名顶级的个人助理，帮助用户高效管理日程和信息。

### 3.2、系统信息

系统信息 (system message/info)

存放不会改变的系统级信息，如日期、用户偏好等。

当前日期: 2025-07-21

用户偏好: 专业、简洁、中文

### 3.3、可用工具

可用工具 (AVAILABLE TOOLS)

原则: 稳定工具空间。列出所有【可能】用到的工具。通过 (status) 来“掩蔽”而非“移除”。

例如：

- search_engine (enabled): 用于在线搜索实时信息。
- file_writer (enabled): 用于将长文本写入文件。
- calculator (disabled): 用于执行数学计算。

### 3.4、计划

计划 (PLAN)

原则: 引导模型注意力 & 从错误中学习。Agent 的动态待办事项列表。

状态: [ ] 待办, [x] 完成, [!] 失败.

- 明确用户的具体需求。
- 搜索相关信息。
- 整理信息并向用户报告。

### 3.5、对话历史

对话历史 (HISTORY)

原则: 只增不减。记录用户和 Agent 之间的完整对话。

>User: 你好，帮我查一下今天有什么重要的科技新闻。
>
>Assistant (思考): 用户的目标是了解今天的科技新闻。计划的第一步是明确需求，用户已经明确了。所以我应该跳到第二步，使用搜索引擎。
>
>Assistant (行动): search_engine("今天的重要科技新闻")

### 3.6、草稿区

草稿区 (SCRATCHPAD)

原则: 引导模型注意力。Agent 的“思考区”或“草稿纸”。在决定行动前，在此处进行推理、分析和自我修正。

示例: 上一步的搜索结果返回了10条新闻，内容有点杂乱。我需要先对它们进行分类，然后挑选出与“人工智能”和“芯片技术”相关的3条进行重点报告。

### 3.7、当前指令

当前指令 (INSTRUCTION)

原则: 利用近因效应。这是给 Agent 的、当前这一步最明确、最核心的指令。

请根据以上所有信息，在 草稿区(SCRATCHPAD) 中进行思考，然后决定下一步的行动（调用工具或直接回应用户）。

## 4、LangChain实现 <带显式规划的Agent>

这个新案例展示了如何构建一个更高级的Agent，它会明确地创建并遵循一个计划。这需要我们自定义Agent的执行循环，而不是直接使用标准的AgentExecutor。

**依赖安装**

```shell
pip install langchain langchain-openai
```

**代码**

```python
import os
import re
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from typing import Dict, Any

# --- 准备工作: 设置API密钥 ---
# os.environ["OPENAI_API_KEY"] = "sk-..."

# --- 1. 定义工具 (与之前相同) ---
@tool
def search_engine(query: str) -> str:
    """用于在线搜索实时信息。"""
    print(f"--- [工具执行] 正在执行搜索: {query} ---")
    if "上下文工程" in query:
        return "搜索结果: 上下文工程是构建高效AI Agent的关键技术..."
    return f"关于 '{query}' 的搜索结果为空。"

@tool
def file_writer(filename: str, content: str) -> str:
    """用于将文本内容写入本地文件。"""
    print(f"--- [工具执行] 正在写入文件: {filename} ---")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"成功将内容写入文件: {filename}"
    except Exception as e:
        return f"错误: 写入文件失败 - {e}"

AVAILABLE_TOOLS = {
    "search_engine": search_engine,
    "file_writer": file_writer
}

# --- 2. 构建包含“PLAN”的Prompt模板 ---
# 我们在模板中明确加入了 {plan} 变量
PROMPT_TEMPLATE = """
# **最高目标 (GOAL)**
成为一名顶级的个人助理，帮助用户高效管理日程和信息，并根据指令完成任务。

## **系统信息 (SYSTEM INFO)**
- **当前日期**: 2025-07-21

## **可用工具 (AVAILABLE TOOLS)**
- `search_engine(query: str)`: 用于在线搜索实时信息。
- `file_writer(filename: str, content: str)`: 用于将文本内容写入本地文件。

## **计划 (PLAN)**
{plan}

## **对话历史 (HISTORY)**
{history}

## **当前指令 (INSTRUCTION)**
{instruction}
"""

# --- 3. 自定义Agent执行循环 ---

class PlanningAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def run(self, user_request: str):
        # 初始化Agent状态
        agent_state = {
            "plan": "任务计划待定。第一步是理解用户需求并制定计划。",
            "history": f"User: {user_request}",
            "instruction": "理解用户的请求，并在[PLAN]部分制定一个清晰、分步的计划。然后，在[ACTION]部分决定你的第一个行动。"
        }

        max_turns = 5
        for turn in range(max_turns):
            print(f"\n=============== 思考回合 {turn + 1} ================")
            
            # 1. 构建完整的Prompt
            prompt = PROMPT_TEMPLATE.format(**agent_state)
            print(f"--- [发送给LLM的Prompt] ---\n{prompt}\n--------------------------")

            # 2. 调用LLM
            llm_response = self.llm.invoke(prompt).content

            print(f"--- [LLM的响应] ---\n{llm_response}\n--------------------")

            # 3. 解析LLM的响应，分离出更新后的计划和下一步行动
            updated_plan, action_str = self._parse_response(llm_response)
            
            # 更新计划
            if updated_plan:
                agent_state["plan"] = updated_plan.strip()

            # 4. 执行行动
            if not action_str:
                print("Agent决定不执行任何行动，任务可能已完成。")
                break
            
            # 将行动加入历史记录
            agent_state["history"] += f"\nAssistant: {action_str}"
            
            if "Final Answer:" in action_str:
                print(f"任务完成！最终答案: {action_str.replace('Final Answer:', '').strip()}")
                break

            tool_name, tool_input = self._parse_tool_call(action_str)

            if tool_name in self.tools:
                try:
                    tool_result = self.tools[tool_name](tool_input)
                except Exception as e:
                    tool_result = f"工具执行出错: {e}"
                
                # 将工具结果加入历史，供下一轮思考
                agent_state["history"] += f"\nTool Result: {tool_result}"
                agent_state["instruction"] = "根据上一步的工具执行结果，更新你的计划状态，并在[ACTION]部分决定下一步行动。"
            else:
                agent_state["history"] += f"\nTool Result: 错误，尝试调用一个不存在的工具 '{tool_name}'。"
                agent_state["instruction"] = "你上一步尝试调用了一个不存在的工具。请检查你的拼写，并从可用工具列表中选择一个正确的工具。"

        else:
            print("达到最大思考回合数，任务终止。")

    def _parse_response(self, response: str) -> (str, str):
        """从LLM的响应中解析出计划和行动"""
        plan_match = re.search(r"\[PLAN\](.*?)\[ACTION\]", response, re.DOTALL)
        action_match = re.search(r"\[ACTION\](.*)", response, re.DOTALL)
        
        plan = plan_match.group(1) if plan_match else None
        action = action_match.group(1).strip() if action_match else None
        
        return plan, action

    def _parse_tool_call(self, action_str: str) -> (str, Any):
        """从行动字符串中解析出工具名称和输入"""
        # 这是一个简化的解析器，真实场景需要更鲁棒的实现
        match = re.match(r"(\w+)\((.*)\)", action_str)
        if match:
            tool_name = match.group(1)
            # 尝试处理简单的字符串或字典输入
            tool_input_str = match.group(2).strip()
            # 移除可能存在的引号
            if (tool_input_str.startswith("'") and tool_input_str.endswith("'")) or \
               (tool_input_str.startswith('"') and tool_input_str.endswith('"')):
                tool_input = tool_input_str[1:-1]
            else:
                tool_input = tool_input_str
            return tool_name, tool_input
        return None, None


# --- 4. 启动带规划的Agent ---
if __name__ == "__main__":
    llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
    planning_agent = PlanningAgent(llm, AVAILABLE_TOOLS)
    
    task = "帮我查一下“上下文工程”的最新进展，并总结成一份名为'context_engineering_report.txt'的报告。"
    planning_agent.run(task)
```

**代码如何体现“显式规划”？**

1. **定制化的Prompt**: `PROMPT_TEMPLATE` 中明确包含了 `{plan}` 占位符。
2. **明确的指令**: 在 `agent_state["instruction"]` 中，我们直接命令LLM去“制定计划”或“更新计划”。
3. **自定义循环**: 我们不再使用`AgentExecutor`，而是编写了一个`PlanningAgent`类和`run`方法，这个方法完整地控制了“构建Prompt -> 调用LLM -> 解析响应 -> 更新状态 -> 执行工具”的每一步。
4. **解析逻辑**: `_parse_response` 函数被用来从LLM的输出中精确地提取出`[PLAN]`和`[ACTION]`两部分内容。
5. **状态自我管理**: `agent_state` 字典在每一次循环中都被完整地维护和更新，尤其是`plan`字段，它承载了Agent对任务进度的“记忆”。

这个实现虽然比标准`AgentExecutor`更复杂，但它完美地复现了我们指南中提倡的“显式规划”原则，让Agent的行为更加透明、可控，也更容易调试。
