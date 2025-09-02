# 提取结构化输出哪种方式更好

**Prompting vs JSON-Mode vs Function-Calling vs Constrained-Generation vs SAP**

本文宗旨：探究从 LLM 中提取结构化数据的每种方法的详细技术说明

>**预习：什么是结构化生成？**
>
>结构化生成是指强迫 LLM 生成一些你可以解析为数据模型并然后程序化使用的数据。

从 LLM 中提取结构化数据/进行函数调用的最常见方法是通过某种方式让 LLM 输出 JSON，然后调用 `JSON.parse` 。

然而，没有理由假设 JSON（Web API 的常用序列化格式）应该是 LLMs 的理想序列化格式。鉴于 LLMs 的随机性，甚至可能所有严格的序列化格式都是次优的，因为单个错误就可能导致整个序列化无效。

在本文中，我们将阐述：

1. 解释每种当前结构化数据提取技术的工作原理
2. 讨论每种技术的优缺点
3. 引入一种新技术，SAP（模式对齐解析），它在伯克利函数调用排行榜上达到了最先进的准确率（跳转到 SAP）

## 问题空间

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211501066.png" alt="image-20250821150148024" style="zoom:50%;" />

给定一个 QUERY 和一个 SCHEMA，我们可以改变生成输出可能性的方法有三种：

1. 改变我们构建提示和呈现 SCHEMA 的方式
2. 改变生成标记的方式
3. 改变我们解析模型输出以符合我们期望的结构的方式

## 总共 9 种技术

| 类别              | 技术                                                         |
| :---------------- | :----------------------------------------------------------- |
| Prompt（提示词）  | [Naive Approach](https://boundaryml.com/blog/schema-aligned-parsing#naive-approach)<br />[Prompt Engineering](https://boundaryml.com/blog/schema-aligned-parsing#prompt-engineering)<br />[Prompt Engineering + Parsing ](https://boundaryml.com/blog/schema-aligned-parsing#prompt-engineering--parsing) |
| Model（依赖模型） | [JSON Mode JSON](https://boundaryml.com/blog/schema-aligned-parsing#json-mode)<br />[Constrained Generation](https://boundaryml.com/blog/schema-aligned-parsing#constrained-generation)<br />[Function Calling](https://boundaryml.com/blog/schema-aligned-parsing#function-calling) |
| Parser（解析器）  | [LLM Retries](https://boundaryml.com/blog/schema-aligned-parsing#llm-retries)<br />[AST Parsing](https://boundaryml.com/blog/schema-aligned-parsing#ast-parsing)<br />[SAP](https://boundaryml.com/blog/schema-aligned-parsing#sap) |

## 技术比较

我们在伯克利函数调用排行榜数据集上运行了最流行的技术。以下是结果：

| Model                                 | Function Calling | Python AST Parser | SAP       |
| :------------------------------------ | :--------------- | :---------------- | :-------- |
| gpt-3.5-turbo                         | 87.5%            | 75.8%             | **92%**   |
| gpt-4o                                | 87.4%            | 82.1%             | **93%**   |
| claude-3-haiku claude-3-俳句          | 57.3%            | 82.6%             | **91.7%** |
| gpt-4o-mini                           | 19.8%            | 51.8%             | **92.4%** |
| claude-3-5-sonnet claude-3-5-十四行诗 | 78.1%            | 93.8%             | **94.4%** |
| llama-3.17b                           | -                | 60.9%             | **76.8%** |

>Dataset had n=1000 per model and comes from Berkeley Function Calling Leaderboard thanks to the Gorilla Team.

## 技术拆解

### 1、朴素方法

将问题和模式作为 JSON 模式注入模型，调用 `JSON.parse(..)` 对响应进行处理

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211505880.png" alt="image-20250821150534831" style="zoom:50%;" />

建议：请不要这样做，LLMs 在自行生成 JSON 时效果不佳。

完整prompt示例：

```text
Generate a resume in JSON format based on the SCHEMA defined below: 
{
 type: "object",
 properties: {
    name: {
      type: "string",
      required: true,
    },
    contact: {
      type: "object",
      properties: {
        email: {
          type: "string",
          required: true,
        },
        phone: {
          type: "string",
          required: false,
        }
      },
      required: true,
    },
    education: {
      type: "array",
      items: {
        type: "object",
        properties: {
          institution: {
            type: "string",
            required: true,
          },
          degree: {
            type: "string",
            required: true,
          },
          year: {
            type: "string",
            required: true,
          }
        }
      },
      required: true,
    },
    experience: {
      type: "array",
      items: {
        type: "object",
        properties: {
          company: {
            type: "string",
            required: true,
          },
          role: {
            type: "string",
            required: true,
          },
          duration: {
            type: "string",
            required: true,
          }
        }
      },
      required: true,
    },
    skills: {
      type: "array",
      items: {
        type: "string"
      },
      required: true,
    }
 }
}
```



### 2、Prompt Engineering

尽量更好地解释期望的格式。例如：要求它不要犯常见的 JSON 错误

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211516934.png" alt="image-20250821151633882" style="zoom:50%;" />

请也不要这样做，原因和上面一样。

### 3、Prompt Engineering + Parsing

增加一些程序稳健性。仅在 `JSON.parse` 条件下解析。

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211521187.png" alt="image-20250821152107106" style="zoom:50%;" />

写起来很快，虽然 LLM 不会总是照你的话做，但至少你在努力，值得表扬。

### 4、JSON Mode

将模型允许生成的令牌限制为仅那些可以解析为 JSON 的令牌。在模型完成 JSON 对象后停止。

示例：在已经生成 `{ "key"` 后，LLM 必须选择一个以 `:` 开头的令牌，以确保生成有效的 JSON。

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211523727.png" alt="image-20250821152353666" style="zoom:50%;" />

这个模式本质是引来与对应厂商的模型是否支持了这个 Json-Model 参数，其实也非常不推荐。

但是：JSON 模式肯定有效。至少它总是可以解析的，但 JSON 模式既过于严格又不够严格。

1. JSON 过于僵化，无法使用那些受益于冗长表达的技术，如思维链或推理（参见 [CoT](https://arxiv.org/pdf/2201.11903) 论文，在某些数据集中准确率提高了 40%）。
2. JSON 并不够严格。 `{ "foo": 1 }` 是有效的 JSON，但如果你想要 `{ "foo": int[] }` ，那会接近但仍然不正确。
3. 在更大规模的数据集上进行比较时，错误率通常在 10% 以上（参见 BFCL）。
4. 最重要的是，并非每个model都支持这种技术

### 5、Constrained Generation

JSON 模式的更通用版本。不仅允许生成有效 JSON 的令牌，还在生成令牌的每一步中仅允许非常特定的令牌。

示例：

- 采用语法限制： `[0-9]{1,2}\.[0-9]{0,2}` - 一个匹配小数点前一到两位数字，小数点后零到两位数字的正则表达式。
- 我们首先只允许 LLM 选择匹配数字的标记。
- 例如，在 `83` 之后，LLM 将被迫选择以 `.` 开头的标记。

>在这种情况下，由于受限生成，LLM 从未生成过大于 99.99 的数字，因为语法会移除任何三位及以上的数字。

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211528468.png" alt="image-20250821152813407" style="zoom:50%;" />

虽然比 JSON 模式更具通用性，但这种方法仅适用于提供接受语法接口的开源模型。对于简单的系统，编写语法很容易，但随着团队规模的扩大和成员的多样化，长期维护语法几乎是不可能的。编写合适的语法可能难度堪比编写编译器。

>问题：如何修改语法以允许使用变量？
>
>说实话我也不知道

### 6、Function Calling

这里的思路是 **fine-tune模型**，使其能够智能地判断何时使用 JSON 模式。

**示例生成：**

1. 教给模型一个新的特殊标记 `USE_TOOL` 。
2. 每当模型生成 `USE_TOOL` 令牌时，将所有后续令牌切换到 JSON 模式。
3. 一旦 JSON 完成（通过程序检测，而不是通过模型），允许模型从所有令牌中进行选择，包括 `USE_TOOL` 。
4. 循环，直到模型发出 `END_TOKEN` 令牌。

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211535664.png" alt="image-20250821153544617" style="zoom:50%;" />

这是我发现的一种随着时间变化而改变观点的方法。由于函数调用需要在特殊的 `USE_TOOL` 标记上训练模型，因此之前并不是所有提供商都支持。随着它变得更为常见，并且接口正在变得越来越标准化，我对此也逐渐感到满意。不过，我仍然有一些保留：

1. 函数调用同样遭受着与 JSON 模式相同的模式不准确问题。 `{ "foo": 1 }` 是有效的 JSON，但如果你想使用 `{ "foo": int[] }` ，它会接近但仍然不正确
2. 大多数 API 依赖于 JSON 模式，这在标记的 token 极为浪费
3. 很多 model 仍然不支持这一功能
4. 支持这一功能的模型在使用函数调用时，准确性往往低于仅基于提示的技术

尽管如此，它确实克服了 JSON 模式的一些关键问题，比如支持基于冗余的技术。例如，你可以在触发标记之前进行思维链推理。

### 7、LLM Retries

反复调用模型，直到生成可解析的内容，或者将解析错误传递给模型，希望在它再次尝试时能获得好的结果。这种方法是像 Langchain、Instructor 和 Marvin 这样的库用来可靠地获取结构化数据的技术。

>这里很值得去阅读 LangChain 的源码，其中也有多种方案，探究越深就懂得越多.

这是目前唯一我认为有可能成为游戏规则改变者的技术，但目前还没有以有趣的方式使用。

所以，还是不是很推荐。

如今，许多库将 LLM 当作锤子，将所有问题都扔给它解决。 `JSON.parse` 因包含注释而失败？还是因为多余的逗号？请让 LLM 修复错误，然后再尝试解析。

这会增加系统的无界延迟和成本。LLM 本身已经很慢且昂贵（尽管正在变得更快更便宜，但仍然比大多数软件慢得多）。

示例：

```text
// Data model
class Person {
  name string
  job string
  birth_year int
  age int @assert(
    this == now().year - birth_year,
    "{this} doesn't match {birth_year} given {now().year}"
  )
}

// To fix it, instead of giving the LLM everything (the entire data model), just give it the error and only the properties that are relevant to age.
{
"error": "age=30 doesn't match birth_year=1990 given now.year=2024",
"birth_year": 1990,
"age": 30
}

```

然而，我看到潜力的是在更复杂的系统中修复逻辑不一致。大规模进行这种修复，LLM 可能是唯一的方法。例如，在年龄相差 3 年的情况下进行修复。当前的方法很可能会重新运行整个模型，但更复杂的方法是只给 LLM 错误和相关属性，从而降低成本和延迟。这将是一个更高效的解决方案，但需要大量的工程工作（以及编译器）才能实现。

### 8、Language-Specific AST parsers

依赖模型固有的输出代码能力，以及现有的抽象语法树解析器来读取代码，然后将其转换为 JSON。示例输出： `[GetTriangleArea(base=5, height=10)]` （注意，这符合 Python 语法）转换为 JSON 后： `{ "GetTriangleArea": {"base": 5, "base": 10} }`

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211540120.png" alt="image-20250821154043025" style="zoom:50%;" />

这里要特别指出 伯克利的猩猩团队（参见伯克利[函数调用排行榜](https://gorilla.cs.berkeley.edu/leaderboard.html)）。

这是我见过的少数几个跳出 JSON、XML 和其他类似格式的想法之一，试图以 LLM 可能更容易理解的方式重新定义问题。生成代码的问题在于，代码，就像 JSON 一样，仍然是一种非常严格的语法。虽然代码中几乎没有多余的标记（如 JSON 中的 `:` 或 `"` ），但你仍然依赖于一个你通常无法控制的解析器（即编程语言的语法解析器）。如果 LLM 不小心发出的空格数量不对，可能会完全改变 Python 解析器读取输出的内容。

### 9、Schema Aligned Parsing (SAP)

与其依赖模型严格理解我们期望的格式，不如编写一个解析器，该解析器可以宽容地读取输出文本，并利用原始模式的知识应用错误修正技术。

看看实测结果：

| Model                                 | Function Calling | Python AST Parser | SAP       |
| :------------------------------------ | :--------------- | :---------------- | :-------- |
| gpt-3.5-turbo                         | 87.5%            | 75.8%             | **92%**   |
| gpt-4o                                | 87.4%            | 82.1%             | **93%**   |
| claude-3-haiku claude-3-俳句          | 57.3%            | 82.6%             | **91.7%** |
| gpt-4o-mini                           | 19.8%            | 51.8%             | **92.4%** |
| claude-3-5-sonnet claude-3-5-十四行诗 | 78.1%            | 93.8%             | **94.4%** |
| llama-3.17b                           | -                | 60.9%             | **76.8%** |

>注意⚠️：
>
>我们不使用 json_schema 来处理 SAP，而是使用 baml_schema，这是一种更紧凑的方式来定义模式。这是因为我们在解析时不需要像 JSON 那样严格，所以可以省略引号等字符。更多详情请参阅：[你的提示使用了比需要的多 4 倍的 tokens](https://boundaryml.com/blog/type-definition-prompting-baml)。

#### 什么是 SAP，为什么它能如此出色？

SAP 的核心理念是假设模型会出错，并构建一个足够 robust 的解析器来处理这些错误。对于某些任务来说，这几乎是不可能实现的，但在结构化数据提取的背景下，是受到 Jon Postel（TCP/IP 的创造者）提出的 Postel 法则的启发：`对自己做到保守，对别人做到宽容`。

从宏观角度来看，可以将这个问题类比为 LeetCode 中的“编辑距离”问题，但不同的是，我们问的是：“将模型的输出调整为符合模式解析所需的最小成本编辑是什么？”最简单的成本函数可能是莱文斯坦距离，但我们使用了一个考虑了模式的自定义成本函数。

开源代码：https://github.com/boundaryml/baml

同时，这里提供三个示例来展示我们使用的一些错误修正技术：

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211545591.png" alt="image-20250821154558559" style="zoom:50%;" />

LLM 的错误由 SAP 修正：

- 添加了一个注释
- 使用了分数而不是浮点数
- 忘记 `stands_for` 周围的引号
- 没有转义字符串中的换行符或 `"`
- 包含了多余的逗号

<img src="https://raw.githubusercontent.com/arminxu-coding/image/main/2025/202508211547323.png" alt="image-20250821154714262" style="zoom:50%;" />

LLM 的错误由 SAP 修正：

- `"Amazon"` 被返回为 `string` ，但 `Founder.prior_jobs` 应该是 `string[]`

#### 使用SAP

在 SAP 中使用的更多错误纠正技术包括：

- 未引号字符串
- 未转义的引号和字符串中的新行
- 缺少逗号
- 缺少冒号
- 缺少括号
- 命名错误的键
- 将分数转换为浮点数
- 移除对象中的多余键
- 去除冗余输出
- 在 LLM 产生多个输出时，选择最佳候选者
- 由于流式传输而完成部分对象
- 等等

官方文档：https://docs.boundaryml.com/docs/get-started/quickstart/python

1. 编写一个 BAML 方案

```baml
// my_app/baml_src/my_schema.baml
class Resume {
  name string @description("first and last name")
  email string?
  experience Experience[]
}
 
class Experience {
  title string
  company string
}
```

2. 用 BAML 编写 LLM 提示

```baml
// my_app/baml_src/my_schema.baml
// ...
 
function ExtractResume(text: string) -> Resume {
  client "openai/gpt-4o"
  prompt #"
    Describe this resume.
    {{ ctx.output_format }}
 
    {{ _.role('user') }}
    {{ text }}
  "#
}
```

3. 在你选择的语言中创建绑定，并像使用原生函数一样使用 BAML 定义的函数（带有自动补全和类型！）

```sh
$ pip install baml-py
$ baml-cli generate --from /path/to/my_schema.baml --target "python/pydantic"
```

```python
from baml_client import b
 
# resume will always be a Pydantic model of type Resume
resume = b.ExtractResume("""
  Vaibhav Gupta
  vbv@boundaryml.com
  - Founder @ BoundaryML
""")
 
# BAML will automatically validate the response via SAP and cast it to a Pydantic model
```



## 总结

其实看到这里，能够大致了解了，让llm输出的结果变成结构化的结果的方案，下面是我的几种意见：

- 想要简单快捷，直接使用 `function-calling` 即可，便于理解，现在很多模型都支持了
- 不想要依赖于第三方，就通过自己的提示词去实现即可，让llm输出json格式数据，用 `json-repair` 这类支持修正json的库
- 如果使用了框架，那么直接使用 `LangChain` 即可，方案成熟 代码便捷
- 如果想使用开源第三方，那么可以尝试使用 `SAP`，但是我还是不推荐 有点复杂了，还需要重新学习，成本大

