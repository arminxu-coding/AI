# Agent技术原理



## 一、初识 Agent

AI Agent，称为人工智能代理，或者称为AI智能体，它是一种模拟人类智能行为的人工智能系统，以大型语言模型(LLM)作为其核心规划决策引|擎。

能够感知环境，做出决策，并执行任务以实现特定的目标。

**举个栗子🌰**

通俗说，可以将Agent智能体比作一个自动执行任务的小助手。它利用人工智能技术来完成特定的活动或作业，想象一下，你有一个看不见的机器人，它可以根据你的命令或者自己的判断来帮你做事。这个看不见的机器人就是我们说的“智能体”

举个例子，想象你在家里用智能音箱(如天猫精灵或小米小爱同学)，你说:“帮我放今天的新间，"智能音箱就会根据你的命令，从网络上获取最新的新闻，并通过音箱插报出来。

这时，智能音箱就是一个智能体，它感知到了你的语音命令，然后在数字环境中获取新闻信息，并执行了播放新闻的任务。甚至，你打开抖音，帮你推荐你喜欢的视频，其实抖音app就是一个智能体，它感知了你的兴趣爱好和用户行为，然后给你推荐视频，让你体验教字娱乐

**原理**

Agents定义为：`LLM` + `memory` + `planning skills` + `tool use`，即大语言模型、记忆、任务规划、工具使用的集合

如果抽象出来就是这样子的：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250505214523754.png" alt="image-20250505214523754" style="zoom:30%;" />

## 二、Agent 架构

### 1、设计模式

选用 **吴恩达分享的Al Agents** 设计模式进行概要

1. 感知(Perception)

   llm 多模态

   Agent通过感知系统从环境中收集信息，这些信息可以是文本、图像、声音等多种形式，感知是Agent理解周遭世界的第一道工序

2. 规划(Planning)

   对问题进行拆解得到解决路径，既进行任务规划，类似于思维链，分解复杂任务，找到路径

3. 便用工具(ToolUse)

   评估自己所需的工具，进行工具选择，并生成调用工具请求，这些行动可能是物理的，如机器人的移动，也可能是虚拟的，如软件系统的数据处理，我电脑里面的未归档文件做好归档

4. 协作(Multiagent Collaboration)

   多Agent，不同类型的助理(agent)，可以通过协作组成一个团队或一家公司

5. 记忆(memory)

   messages

   短期记忆包括提示词上下文，工具的返回值，已经完成的推理路径;

   长期记忆包括可访问的外部长期存储，例如 **RAG知识库**

#### 1.1、工具定义(tools)

简单理解就是针对于自己的业务定义有哪些工具（哪些功能 -> 业务）

举个栗子：假设我们 是一个`出行服务的agent`，那么我们产品业务可能具有如下功能

- 出行路线规划
- 加油站点规划
- 旅游景点规划
- 服务区休息规划
- ...

那么上面的这些功能，都可以被定义为tool，也就是说这个tool是一个非常抽象的概念，简单理解 就是你具有什么工具帮助用户处理什么任务 最后结果用户需求

这些tool之间可以存在关系，可以是并行关系、串行关系、路由关系、流程关系...

#### 1.2、任务规划(plan)

1. 子目标&拆解(Subgoal and decomposition)

   我们处理问题的时候会采用“分治”的思想，将复杂任务拆解成一个个小任务处理。

   这个在 Agent 的实现中也是一样，一个复杂任务不太可能一次性就能解决的，需要拆分成多个并行或串行的子任务来进行求解，从而提升处理复杂问题的能力。

2. 反思&完善(Reflection and refinement)

   Agent 能够对过去的行动决策进行自我反思，完善过去的行动决策和纠正以前的错误来迭代改进 ReAct提示词技术 就是很经典的反思和完善过程，

   结合 ReAct提示词技术的 Agent 会在执行下一步action的时候，加上LLM 自己的思考过程，并将思考过程、执行的工具及参数、执行的结果放到 prompt中，让LLM 对当前和先前的任务完成度有更好的反思能力，从而提升模型的问题解决能力。

>**ReAct** 本质上是一种设计模式，类似于我们在开发项目当中使用到的 **23中设计模式** 一样的概念，是目前在Agent开发当中使用的模式。

**ReAct** 的提示模板，大致格式如下:

```txt
thought: ...
action: ...
observation: ...
...(loop重复以上过程)
```

#### 1.3、记忆(memory)

记忆可以定义为用于获取、存储、保留以及随后检索信息的过程。

1. 短期记忆(Short-Term Memory (STM) )

   可以理解为多轮对话的上下文窗口，受到Transformer 有限上下文窗口长度的限制，所以尽管对话很长，短期记忆理想情况只保留大模型能够处理的上下文窗口的上限，如果是 firstin first out的模式，则只保留最近的几次对话内容。

   >可以简单理解就是，我们在多轮对话中的上下文历史，我们可以通过 messages 进行传递llm，但是其实还是有很多别的形式都可以成为短期记忆

2. 长期记忆(Long-Term Memory(LTM))

   可以理解为外置知识库，在 Agent 处理任务的过程中作为额外检索数据的地方。
   
   >可以简单理解，向量数据库可以被称之为长期记忆，可以经过 rag 的手段进行检索额外的数据

#### 1.4、工具使用(action)

尽管大语言模型在预训练阶段学习了大量的知识，但只能够与大模型"纸上谈兵”，它只会说、不会做，同时也不能回答一些如天气，时间之类的简单问题。

Agent 对于工具的使用就是弥补大模型只说不做的缺陷。

Agent 可以调用外部 API 来获取模型权重中缺失的颜外信息，包括当前时间、地理位置信息、代码执行能力、对专有知识库的访问等。

Agent 的工作机制

```txt
[接受任务] 用户提交任务给agent
[组装提示词] agent 收到用户任务，对于输入信息结合本身业务架构处理 合并成新的 prompt
[与大模型交互] agent 将prompt给到llm，得到llm输出 下一步需要执行的动作和思考过程
[循环执行] agent 会执行llm返回的 action_list，进行观察结果，判断是否需要进行下一步action，或者执行tool获取额外的信息
```



最后说一下agent有哪些应用领域：

我总结来说，任何领域都可以使用llm agent进行重构一遍，但是这个需要强依赖于基座llm的能力

目前常见 Al Agent技术应用的领域：

客户服务(Customer Service):自动回答客户咨询，提供个性化服务。

医疗诊断(Medical Diagnosis):辅助医生进行疾病诊断和治疗方案推荐。

**股市交易**(StockTrading):自动化交易系统，根据市场数据做出买卖决策。

智能交通(IntelligentTransportation):自动驾驶车辆和交通管理系统。也就是我们常听说的端到端智驾，有兴趣的大佬可以自行了解。

**教育辅导**(Educational Tutoring):个性化学习助手，根据学生的学习进度提供辅导



### 2、Agent开发范式

#### 2.1、应用开发变化

本质上，所有的 Agent 设计模式都是将人类的思维、管理模式以结构化prompt的方式告诉大模型来进行规划，并调用工具执行,正断迭代的方法。从这个角度来说，Agent设计模式很像传统意义上的程序开发范式，但是泛化和场景通用性远大于传统的程序开发范式。在Agent设计模式中，prompt可以类比为Python这类高级编程语言，大模型可以类比于程序语言编译&解释器

在大模型时代，AI agent编程给IT行业带来了哪些革命性的改变:

1. **传统编程语言时代**

   以Java、C++、Rust等语言为典型代表，这个时代的软件开发最重要的一件事就是“抽象建模”产品经理或者技术经理需要深刻地理解现实世界的业务场景和业务需求，然后将业务需求转化为逻辑流和数据流的处理逻辑，用编程语言进行抽象描述，并且明确定义输入和输出的字段和格式，然后将软件代码运行在一定的VM平台上，通过简单易用的U交互向终端用户提供产品价值。

2. **ML/DL编程时代**

   在传统编程时代，程序员们遇到了一个棘手的问题，就是当面对一些超高维的复杂问题(例如图像识别、长文本处理)的时候，传统的if-else逻辑范式几乎无法解决此类问题。

   直到出现了神经网络技术之后，程序员们发现可以通过训练一个神经网络(相当于开发了一个程序)就可以很容易图像/文本处理问题。

   但是在这个范式中，现实世界的业务场景和软件代码的逻辑之间依然存在非常巨大的鸿沟，建模、UL流程图这些传统编程中必不可少的步器依然组碍了软件的大规模应用。

3. **AI Agent编程时代**

   进入大模型编程时代，现实世界和软件逻辑世界的鸿沟被无限缩短了，原本用于描述和表征现实世界的自然语言、图片、音频等模态语言，可以直接以代码的形态，被大模型这种新型的程序解释器解释并执行。

   可以这么说，在AI Agent编程时代，改变的是建模范式，不变的是数据流和逻辑流。


>什么是建模范式？
>
>什么是数据流？
>
>什么是逻辑流？

#### 2.2、开发注意事项

在实际应用场景中进行Agent开发之前，有一些关键点需要注意事项。

1. Agent 的规划能力依赖于 **prompt工程能力**，它比想象中更重要、执行起来也更琐碎。

   目前LLM 的数学、逻辑推理能力在 COT的基础上也仅能勉强达到及格水平，**所以不要让Agent一次性做复杂的推理性规划工作**，而是**把复杂任务人工拆解**后再教给Agent。当然这个论点随着基模的逐步发展和强大可能逐步重要性降低

2. Agent 的 Action 能力强烈依赖于**基座模型的 function calling 能力**。

   Function call

   Prompt -> output + code -> tool

   在规划 Agent 之前，对模型的 function calling 能力要充分调研,

   加州伯克利大学发布了一个 function caling [榜单](htps:/gorila.cs.berkeley.edu/leaderboard.html)，其中表现最好的GPT4准确率是 86%，还不够理想。

3. Agent 的记忆力分为 **短期记忆** 和 **长期记忆**。

   短期记忆由 prompt负责 (in-context learning)，类似 Plan and resolve 模式中的"碎碎念”，告诉Agent已完成了啥，原始目标是啥在长期记忆中，事实性证明 记忆用RAG实现(外部知识库)，程序性记忆可用微调或者增量预训练实现(向模型中注入知识)

4. Agent 的**反思能力依赖于它的记忆能力**。

   上述几点正好对应着 Agent 的四大能力：规划、反省、记忆、执行

   用一张图来表示，其中绿色代表对 Agent 开发友好，红色代表对 Agent 应用开发有一些难以逾越的阻碍因素，需要靠产品降级来解决。

Agent开发者的窘境

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250505214329460.png" alt="image-20250505214329460" style="zoom:50%;" />

### 3、Agent设计模式

#### 3.1、Zero-Shot模式

这是最接近C端大多数人初次体验ChatGPT时的交互模式。

在这种Agent橫式之下，用户的输入问题不增加任何 **prompt template** 处理，直接被传入了大模型中，并将大横型返回结果直接返回给了终端用户在大多数的终端应用开发场最中，这种Agent开发模式都是无法满足需求的

#### 3.2、Few-Shot 模式

这种模式和PlainPrompt最大的区别在于，它开始有了prompt template逻辑，因为prompt template的存在，开发者得以调用大模型的context-learning(上下文学习)能力

Few-Shot模式应该是B端开发场景中使用频率最高的一种`Agent范式`，大体上，这种范式中有几个核心组成部分:

1. 角色描述：一句话描述清楚你希望大模型扮演什么样的角色，以及需要具备的能力和技能
2. 指令任务描述：可以是一句话，也可以通过提示词引导大模型按照一定的步逐步解决问题
3. 样例：一个完整的“任务-解决方案”示例，或者是入参/出参的格式工程师可以通过大模型的指令遵循能力，将原本需要通过复杂规则定义和处理的环节，都通过大模型量做一遍，提升工作效率

#### 3.3、ReAct 模式

原始项目：https:/github.com/ysymyth/ReAct

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250505215526951.png" alt="image-20250505215526951" style="zoom:50%;" />

ReAct 原理很简单，没有 ReAct 之前，**Reasoning**和 **Act** 是分割开来的，ReAct针对给出的问题，**先进行思考**，再根据**思考的结果行动**，然后**观测行动的结果**，如果不满足要求，再进行`思考、行动，直至得到满意的结果为止`。

ReAct 的基本思想是增强了动作空间，其中前者是原始的动作空间，后者是语言模型空间，一个来自语言模型空间的动作一般称作**thought**，它不会影响外部环境，因此也不会收到观测反馈，只会基于当前环境进行推理得到有用信息，进而支持后续的推理和动作执行。

采用few-shot In-context学习来生成解决问题的action和thought席列，每个in-context样例是由action、thought、observation构成的行为轨迹，在推理占主导地位的应用中，我们交替生成thought和action，这样完整的行为轨迹就是多个thought-action-observation步骤相反在决策生成任务中(涉及大量action)，thought只会在行为轨迹中最相关的位置稀疏出现。

举个例子，让孩子帮忙去厨房里拿一瓶酱油，告诉ta-步步来(COT提示词策略)：

- 先看看台面上有没有
- 再拉开灶台底下抽屉里看看
- 再打开油烟机左边吊柜里看看

在没有 ReAct 的情况就是：不管在第几步找到酱油，孩子都会把这几个地方都看看(Action)

有 ReAct 的情况是：

- Action1：先看看台面上有没有
- Observation1：台面上没有酱油，执行下一步
- Action2：再拉开灶台底下抽展里看看
- Observation2：抽屉里有酱油
- Action3：把酱油拿出来

在论文的开头作者也提到人类智能的一项能力，即每次执行行动后都有一个"自言自语的反思(0bservation:我现在做了啥，是不是已经达到了目的)这相当于让 Agent 能够维持短期记忆。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250505220224083.png" alt="image-20250505220224083" style="zoom:40%;" />

一个ReAct流程里，关键是三个概念:

**Thought**

由LLM模型生成，是LLM产生行为和依据，可以根据LLM的思考，来衡量他要采取的行为是否合理这是一个可用来判断本次决策是否合理的关键依据。相较于人类，thought的存在可以让LLM的决策变得更加有可解释性和可信度

**Act**

Act是指LLM判断本次需要执行的具体行为Act一般由**行为** 和 **对象**组成。用编程的说法就是API名称和对应的入参LLM模型最大的优势是，可以根据Thought的判断，选择需要使用的API并生成需要填入API的参数从而保证了ReAct框架在执行层面的可行性

**Obs**

LLM框架对于外界输入的获取。就像LLM的五官，将外界的反信息同步给LLM模型，协助LLM模型进一步的做分析或者决策



一个完整的ReAct的行为，包涵以下几个流程:

1. 输入目标：任务的起点。可以是用户的query(手动输入)，也可以是依靠触发器(比如系统故障报警) 等等任何形式。

2. Loop：LLM模型开始分析问题需要的步骤(**Thought**)，按步骡执行**Act**，根据观家到的信息(**Obs**)，循环执行这个过程，直到判断任务目标达成。

3. Finlsh：任务最终执行成功，返回最终结果。



由此，我们可以看到 Agent 要落地一个场景，需要定制两项内容

1. prompt 模板中 **few-shot** 中的内容
2. **function-calling** 中的外部工具定义

prompt 模板中fewshot 本质上就是**人类思维模式的结构化体现**，通过査间各个设计模式的 prompt 模板是很好的学习 Agent 设计模式的方法，习得这个方法可以用同样的方法理解其他的设计模式。

#### 3.4、Plan-and-Solve 模式

为了提升LLM的多步推理(multi-step reasoning)能力，讨论COT问题中 Zero-Shot 时 对推理质量的提升。

论文Plan-and.Solve Prompting分析了Zero-Shot COT时的错误分布：

- 计算错误(7%)
- 步骡遗滑错误(12%)
- 语义理解错误(27%)

为了解决计算错误：提升LLM生成的推理步骡(reasoningsteps)质量，又对PS promptin&进行了扩展，提出了PS+ prompting

为了解决多步推理的步骤缺失问题：提出了plan and solve(PS) prompting方法，它由两部分组成，首先设计计划，计划的目标是将整个任务划分为多个更小的子任务，然后根据计划执行子任务。

**实现原理**

这种设计模式是先有计划再来执行:

- 如果说 `ReAct` 更适合完成 `厨房拿酱油` 的任务

- 那么 `Plan & Solve` 更适合完成 `西红柿炒鸡蛋` 的任务

  你需要计划，并且过程中计划可能会变化(比如你打开冰箱发现没有西红柿时，你将购买西红柿作为新的步骤加入计划)

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511155528804.png" alt="image-20250511155528804" style="zoom:50%;" />

**规划器**

负责让 LLM 生成一个多步计划来完成一个大任务，代码中有 `Planner` 和 `Replanner`

`Planner` 负责第一次生成计划;

`Replanner` 是指在完成单个任务后，根据目前任务的完成情况进行 **Replan**，所以 Replanner 提示词中除了Zero-Shot，还会包含 目标、原有计划、已完成步骡的情况。

**执行器**

接受用户查询和规划中的步骡，并调用一个或多个工具来完成该任务，也就是 **Act的执行者** 方式各色各样。

**提示词实例**

简言之就是 Zero-Shot 的提升，下表是给出的一些 Plan and Solve 提示词

| 类型 | 案例prompt                                                   |
| ---- | ------------------------------------------------------------ |
| CoT  | 让我们逐步思考。                                             |
| PS   | 让我们首先理解问题并制定一个解决问题的计划。然后，让我们一步一步地执行这个计划来解决问题。 |
| PS+  | 让我们首先理解问题，提取相关变量及其对应的数字，并制定一个计划。然后，让我们执行计划，计算中间变量（注意正确的数字计算和常识），逐步解决问题，并给出答案。 |
| PS+  | 让我们制定一个计划并逐步解决问题。                           |
| PS+  | 让我们首先理解问题并制定一个完整的计划。然后，让我们执行计划并逐步推理问题。每一步都要回答子问题，“这个人是否翻转硬币以及硬币当前的状态是什么？”。根据硬币的最终状态，给出最终答案（注意每一次翻转和硬币的状态变化）。 |
| PS+  | 让我们首先准备相关信息并制定计划。然后，让我们分步骤回答问题（注意常识和逻辑一致性）。 |
| PS+  | 让我们首先理解问题，提取相关变量及其对应的数字，并制定和设计一个完整的计划。然后，让我们执行计划，计算中间变量（注意正确的数值计算和常识），逐步解决问题，并给出答案。 |

#### 3.5、Reason without Observation 模式

[论文](https://arxiv.org/abs/2305.18323)、[github项目](https://github.com/billxbf/RewoO/tree/main)

**核心思想**

原理是将 `推理(Reasoning)` 过程与 `外部观察(Observation)` 分离，以此来提高模型的效率和性能在传统的LLM增强系统中，如**ReAct模式**中，横型的推理过程是与外部工具的调用和观察结果紧密交织在一起的，这种模式虽然简单易用，但往往会导致计算复杂性高，因为需要多次调用语言横型(LLM)并重复执行操作，这不仅增加了计算成本，也增加了执行时间。REWOO模式通过以下几个步骤来优化这一过程:

1. Planner(规划器)

   首先，规划器接收用户输入的任务，并将其分解为一系列的计划(Plans)每个计划都详细说明了需要使用哪些外部工具以及如何使用这些工具来获取证据或执行特定的动作负责生成一个相互依赖的”链式计划”，定义每一步所依赖的上一步的输出

2. Worker(执行器)

   接下来，执行器根据规划器提供的计划，调用相应的外部工具来执行任务，并获取必要的信息或证据循环遍历每个任务，并将任务输出分配给相应的变量，当调用后续调用时，它还会用变量的结果替换变量

3. Solver(合井器)

   最后，合并器将所有计划的执行结果整合起来，形成对原始任务的最终解决方案这种模块化的设计显著减少了令牌消耗和执行时间，因为它允许一次性生成完整的工具链，而不是在每次迭代中都重复调用LLM此外，由于规划数据不依赖于工具的输出，因此可以在不实际调用工具的情况下对模型进行微调，进一步简化了微调过程

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511171253826.png" alt="image-20250511171253826" style="zoom:50%;" />

**提示词模版**

提示词模板中给出 few-shot内容中定义出每一步的 plan 都会依赖上一步的输入会把前面工具的输出 作为变量注入到下一步工具的提示词上下文中

```python
DEFAULT_PREFIX="对于这个任务，制定可以逐步解决问题的计划。对于每个计划，指示检索证据的外部工具和工具输入。您可以存储将证据转换为变量#E，以后的工具可以调用该变量。（Plan、#E1、Plan、#E2、Plan...）"

HOTPOTQA_PWS_BASE= '''
问题：科罗拉多造山带东段延伸到的地区的海拔范围是多少？

计划：搜索更多关于科罗拉多造山运动的信息。
#E1=维基百科[科罗拉多造山运动]

计划：找出科罗拉多造山运动东段延伸到的区域名称是什么？给定上下文：#E1
#E2=LLM[科罗拉多东部延伸到的地区名称是什么？给定上下文：#E1]

计划：搜索有关该地区的更多信息。
#E3=维基百科[#E2]

平面图：找出该区域的标高范围。
#E4=LLM[区域#E2的标高范围是多少？给定上下文：#E3]
'''
```



<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511171456211.png" alt="image-20250511171456211" style="zoom:50%;" />

#### 3.6、LLMCompiler 模式

[论文](https://arxiv.org/abs/2312.04511)、[github项目](https://github.com/SqueezeAILab/LLMCompiler)

**实现原理**

简单来说就是通过并行Function calling来提高效率

比如用户提问: "Scott Derrickson和Ed Wood是否是同一个国家的国民料"

planner：搜索"Scott Derrickson国籍" 和 搜索"Ed Wood国籍" 同时进行，最后合并即可

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511182607111.png" alt="image-20250511182607111" style="zoom:50%;" />

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511182622305.png" alt="image-20250511182622305" style="zoom:50%;" />

架构上它由三个组件组成:

1. **Planner(规划器)**：即将原始问题分解为一个 DAG(DirectAcyclc Graph,有向无环图)的任务列表,。
2. **TaskFetchingUnit(井行执行器)**：根据任务的依赖，调度任务并行执行。
3. **Joiner(合井器)**：综合DAG执行结果反馈给用户，如果没达预期可以重新规划任务

#### 3.7、Basic Reflection 模式

Basic Reflection 可以类比于学生(Generator)写作业，老师(Refector)来批改建议，学生根据批改建议来修改，如此反复Basic Reflection可以类比于左右互博

左手是Generator，负责根据用户指令生成结果;右手是Reflector，来审查Generator的生成结果并给出建议

**原理**

下图是Basic Reflection的原理，非常简单。

`Generator`：接收来自用户的输入，输出initialrespons

`Reflector`：接收来自Generator的response，根据开发者设置的要求，给出Reflections，即评语、特征、建议Generator再根据Reflector给出的反馈进行修改和优化，输出下一轮response，循环往复，直到循环次数

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511182831674.png" alt="image-20250511182831674" style="zoom:50%;" />

Basic Reflection的架构，非常适合于进行相对比较发散的内容生成类工作，比如文章写作、图片生成、代码生成等等,Basic Reflection是一种非常高效的反思类AAgent设计模式。

Basic Reflectlon 的思路非常朴素，使用成本较低，但是在实际应用中，BasicRefection也面临着一些缺陷:对于一些比较复杂的问题，显然需要Generator具备更强大的推理能力Generator生成的结果可能会过于发散，和我们要求的结果相去甚远

在一些复杂场景下，Generator和Refector之间的循环次数不太好定义，如果次数太少，生成效果不够理想;如果次数太多，对token的消耗会很大。我们有两种方法来优化Basic Refection，一种是边推理边执行的Self Discover横式，一种是增加了强化学习的Refexion横式。



#### 3.8、Reflexion 模式

[论文](https://arxiv.org/pdf/2303.11366.pdf)、github项目

**原理**

由于传统强化学习需要大量的训练样本和昂贵的横型微调，大横型很难快速有效地从错误经验中学习。最近涌现了ReActHupeingGPT等基于大橫型的任务决策框架，它们利用In-context learning的方式快速地指导模型执行任务，避免了传统微调方式带来的计算成本和时间成本

受前面工作的启发，提出了Reflexion框架，便用语言反馈信号来帮助agent从先前的失败经验中学习，具体地，Refexion将传统梯度更新中的参数信号转变为添加在大横型上下文中的语言总结，使得agent在下一个episode中能参考上次执行失败的失败经验，从而提高agent的执行效果，这个过程和人类反思(refexion)过程十分相似

作者在决策(AIWord)、推理(HOtQA)和代码生成(HumanEva)任务上进行了完整的对比实验，Refexion在不同的任务上均取得了不错的效果，特别是在代码生成任务上成为了最新的SOTA

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511183153918.png" alt="image-20250511183153918" style="zoom:50%;" />

如图所示，Reflexion框架包含四个组成部分:

**Actor**

由LLM担任，主要工作是基于当前环境生成下一步的动作。

**Evaluator**

主要工作是衡量Actor生成结果的质量，就像强化学习中的Reward函数对Actor的执行结果进行打分

**Self-reflexion**

一般由LLM担任，是Reflexion框架中最重要的部分，它能结合商散的reward信号(如success/fal)、traiectory(轨迹，也就是推理上下文)等生成具体且详细语言反馈信号，这种反馈信号会储存在Memory中，启发下一次实验的Actor执行动作。

相比reward分数，这种语言反馈信号储存更丰富的信息，例如在代码生成任务中，Reward只会告诉你任务是失败还是成功，但是Self-relexion会告诉你哪一步错了，错误的原因是什么等。

**Memory**

分为`短期记忆(short-term)` 和 `长期记忆(long-term)`。

在一次实验中的上下文称为短期记忆，多次试验中Self-reflexion的结果称为长期记忆。类比人类思考过程，在推理阶段Actor会不仅会利用短期记忆，还会结合长期记忆中存储的重要细节，这是Refexion框架能取得效果的关键，

Refexion是一个选代过程，Actor产生行动，Evaluator对Actor的行动做出评价，Self.Rfexion基于行动和评价形成反思，并将反思结果存储到长期记忆中，直到Actor执行的结果达到目标效果。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250511183656962.png" alt="image-20250511183656962" style="zoom:50%;" />

reflection 和 basic reflection的区别

1、reflexion会把之前的生成 -> tool调用结果 -> 评价 的所有过程数据，当做下次生成的prompt

2、可以通过外部工具查询教据来作为评价 修正的依据







## 三、思考反思

现阶段，很多模型本质上只有理解和推理能力，也就是 输入一个str -> 输出一个str。

学习这些知识是为了业务实现，但是更核心的是 不仅仅需要关注目前**技术的本身**，更加核心的是一定要学习**技术背后的原理**、**技术架构**、**设计思想**等等，这些更高层次的东西，更加需要的是阶段性的反思和思考。

**推荐阅读：**

- [mcp的应用场景&实际问题](https://mp.weixin.qq.com/s/0Gpt4jGCqZhYJsZFdrIkyw)

- [我们该怎么看到mcp](https://mp.weixin.qq.com/s/GrEWFqpmvp1LfURAT1XzZw)
- [Agent工作流深度分析](https://mp.weixin.qq.com/s/wGZ7G4e-Rch_EqirFt0Ybg)
- [主流Agent框架&mcp集成](https://mp.weixin.qq.com/s/WGOnLFLAZhdvxu1qUs8Aww)
- [基于 MCP 实现 AI 应用架构设计新范式](https://mp.weixin.qq.com/s/vHkVfIHnm_k8ZDnyj8Sb1Q)







## 四、深度学习ADK

### 1、adk中的核心组件流程

1. **定义llm_model**，给到adk中的agnet进行调用llm，一般情况这种都需要自定义 去实现如何将adk当中的协议信息 封装为对应llm请求的参数进行发送、然后将对应的llm返回的信息 解析封装为adk中的协议包

2. **定义agent**，也就是adk中具体的agent智能体，其中定义了一层抽象的概念进行帮助我们调度llm、执行tool、协议包转换。

   当然作为agent还有核心的就是 描述信息（system_prompt）、工具定义（tools）；当然adk中还提供了一系列好用的形式内容，例如：before_model_callback、before_tool_callback、example等等

3. **定义session_service**，也就是user和agent进行交互会话信息保存，其中包括了用户多轮query上下文、llm返回结果等等信息，核心的目的就是记录某次请求所处于的会话是什么，值得注意的是 默认其中实现的原理是基于 `agent + user_id + session_id` 进行作为联合key进行隔离会话，其中实现可以基于很多方式 例如：InMemorySessionService、InReidsSessionService、InMySqlSessionService 但需要自己进行实现。值得注意的是：其中不仅仅session是会话的内容，其中还包括了`LlmRequest（adk内部构件的本次请求中各种参数信息）`、`InvocationContext（一轮对话的上下文信息）`、`ToolContext（一次工具调用的上下文信息）`等等

4. **定义runner**，也就是去帮助agent进行运行的一个运行器，核心功能包括会话获取、对话创建、获取agent、调用agent执行；当然最终任务执行自然是 agent框架运行并调用tool的

5. 其他还有非常多的核心组件...

>值得学习的是，如果想要更加深刻和了解其中的原理，一定要进行阅读源码进行学习，这样子才能学习其中设计思路的奥秘，才能加强自己代码编写的能力



### 2、adk中的`system_prompt`构建原理

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250620005403554.png" alt="image-20250620005403554" style="zoom:50%;" />

其中包括了以下的红框中几个标准且常见的，其中会想 system_prompt 中添加如下几个：

- agent_transfer：将转换agent tool的使用描述 放入 **instructions** 中，并且会讲 `transfer_to_agent_tool` 放入tools列表中；核心作用 就是在多agent场景下 模型选择别的agent进行执行的时候 选择 `transfer_to_agent_tool` 方法输出 **agent_name** 让其调度对应的 agent。
- identity：将当前agent的名字和描述信息 放入 **instructions** 中，用于增强所处的agent的描述指令，用于加强辅助llm
- instructions：将当前agent定义的初识 instructions描述信息 放入 **instructions** 中，作为当前agent的system_prompt的使用指令
- esample_tool：将当前agent中定义的一些示例信息放入 **instructions** 中，用于给到llm示例
- _nl_planning：规划模块的指令，先不管
- .... 其他几个都先不管，比较高级，后面慢慢学习就深刻了





# 大模型微调

## 一、如果构造数据

推荐阅读：

1、如何高效构造大模型精调所需的高质量数据：https://km.woa.com/group/42722/articles/show/558824

2、【混元实操篇】大模型精调数据准备技巧硬核解读：https://km.woa.com/articles/show/598732

## 二、技术探索

1、微信领域大模型应用探索之路：https://km.woa.com/articles/show/617377?kmref=profile_feeds



# 真正的思考

经过这半年下来的学习和实践，可以清晰的发现两个问题，现阶段利用大模型本质上的工作是干什么：

1. 推理能力：**自然语言理解(NLU)、意图识别、对话管理、推理决策、状态跟踪、工具调用**
2. 对话能力：**标准的文生文能力**，用于解决在和用户对话的文字内容细节如何生存
3. 多模态能力：**标准的多模态能力**，可以解决在某些不同条件下有不同数据源 可直接交由模型进行推理

但是需要思考的是，如何运行大模型的能力实现工程化、系统化、分层/模版等设计





# 我学到的东西

1、腾讯云各类产品，分布式、微服务各框架技术；实战经验；

2、跨部门协作沟通；与车企联调打交道；

3、LLM；prompt工程；AI-Agent智能体；模型微调；
