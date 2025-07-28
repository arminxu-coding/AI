# 知识检索增强

## 一、RAG

### 1、什么是RAG

我们说“大模型健忘”，其实说的是它的“知识储存能力有限”，尤其是面对企业内部专业文档、复杂背景知识时，一问三不知的现象比比皆是。

为了解决这个问题，**RAG（Retrieval-Augmented Generation）**应运而生，它通过检索外部知识增强生成回答的准确性，成了AI工程的“标准套路”。



### 2、RAG的局限 & GraphRAG的进化

其实传统RAG也有短板：**它只会“关键字匹配”，不会“理解知识结构”**，检索和生成之间始终隔着一层“信息语义的墙”。

这时，**GraphRAG**来了。

先来复习一下RAG架构的核心逻辑：

> 用户提问 → 文本向量化 → 相似文档检索 → 与问题拼接 → 喂给语言模型生成答案

这种方式虽然实用，但存在两个问题：

1. **知识是碎片化的**：检索结果是几个独立段落，不成体系
2. **模型“不会关系”**：无法理解A和B之间是什么关系

而GraphRAG的出现，就是为了解决这两点。



## 二、Graph-RAG

`GraphRAG` 它像一位擅长思维导图的“**图谱师**”，把文档中的知识关系“**连线、归类、层次化**”，让AI不仅能“查”，还能“懂” —— 这，是RAG的一次关键进化。

### 1、什么是GraphRAG

GraphRAG（Graph-enhanced Retrieval-Augmented Generation）是在RAG架构中引入**[知识图谱](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=知识图谱&zhida_source=entity)结构**的增强版本，其核心理念是：

> **将原始文档中的实体、概念和关系抽取出来，构建成图谱结构，再参与RAG流程。**

简单说，它让AI“有图可依”，不再“只看文本”。



### 2、GraphRAG架构

GraphRAG 具有三层增强：

1. **图谱构建层**：

   文本解析 → 实体识别 + 关系抽取 → 生成知识图谱（KG）

2. **图谱检索层**：

   用户问题向量化后，不只查文档，还查图谱上的相关节点和路径（更精确）

3. **语义生成层**：

   将图谱知识 + 文本片段 + 用户query 一起送进[LLM](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=LLM&zhida_source=entity)，生成更准确的回答

> **一句话总结：**
>
> **RAG**：查段落拼一拼；  **GraphRAG**：查图谱理逻辑，回答更有“章法”。

### 3、适用领域

如果你的场景涉及“知识密集 + 概念关联多”，那GraphRAG就是如虎添翼的选择！

- **医疗健康问答**：构建药物-症状-适应症-副作用的医学图谱，模型可回答：“这两种药能一起吃吗？”
- **法律合规解析**：从合同或法规中抽取“条款-行为-责任”的图谱，支持合规审查和法律问答
- **企业知识管理**：搭建“岗位-制度-流程”的组织图谱，HR助手能精准回答“试用期员工能请年假吗？”
- **生物科研与文献挖掘**：解析论文中的“基因-疾病-药物”结构，辅助科研人员快速理解科研图谱
- **产品知识图谱客服**：电商平台构建“产品-属性-FAQ-问题场景”的知识图谱，客服机器人变得更“专业

### 4、技术方案 & 实战框架

#### 4.1、技术栈核心

| 模块           | 推荐工具                                                     |
| -------------- | ------------------------------------------------------------ |
| 实体/关系抽取  | [SpaCy](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=SpaCy&zhida_source=entity)、[LlamaIndex](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=LlamaIndex&zhida_source=entity)、[OpenIE](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=OpenIE&zhida_source=entity)、LLM（GPT类） |
| 图谱存储与查询 | [Neo4j](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=Neo4j&zhida_source=entity)、NetworkX、Knowledge-Graph-Toolkit |
| 检索器         | FAISS / LlamaIndex Graph Retriever                           |
| 生成模型       | Qwen、Mistral、ChatGLM、GPT系列等                            |
| 框架整合       | [LangChain](https://zhida.zhihu.com/search?content_id=260206078&content_type=Article&match_order=1&q=LangChain&zhida_source=entity)、LlamaIndex、Haystack |

#### 4.2、示例代码

**基于LlamaIndex：**

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, SummaryGraph
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core.indices.composability import ComposableGraph
from llama_index.llms import OpenAI
# 加载文档
documents = SimpleDirectoryReader("docs/medical_qa").load_data()
# 创建图谱
graph_store = SimpleGraphStore()
graph = SummaryGraph.from_documents(documents, graph_store=graph_store)
# 创建索引
index = VectorStoreIndex.from_documents(documents)
# 合并成GraphRAG管道
graph_rag_chain = ComposableGraph([graph, index])
# 用户查询
response = graph_rag_chain.query("治疗高血压的药物有哪些？")
print(response)
```

**部署方式建议：**

- **图谱服务**：使用 Neo4j + REST API 提供图谱查询接口
- **LLM服务**：部署 LLM 本地模型（如 Qwen2.5-7B）接入 LangChain 调用
- **整合链路**：通过 LangChain Agent or GraphAgent 进行全流程协作调用

## 三、总结

### 1、GraphRAG优势 & 就允局限

| 优点               | 说明                                             |
| ------------------ | ------------------------------------------------ |
| ✅ 更强语义结构     | 图谱提供逻辑关系支持，不仅仅是文字匹配           |
| ✅ 上下文更精准     | 提供更聚焦的知识路径，避免无关段落干扰           |
| ✅ 支持可解释性查询 | 可追溯回答依据，如：“该结论来自图中某个路径链条” |
| ✅ 易与业务规则结合 | 可接入行业知识库、规则系统，实现半结构化知识融合 |

| 缺点               | 说明                                   |
| ------------------ | -------------------------------------- |
| ❌ 构建门槛高       | 图谱构建初期需要花时间标注、抽取和清洗 |
| ❌ 抽取错误影响较大 | 错误的关系图会误导模型回答             |
| ❌ 实时性相对不足   | 图谱更新速度较慢，不如全文检索动态     |

### 2、未来趋势

- 自动图谱构建工具链成熟（结合LLM的AutoKG技术）
- 图谱+Agent结合形成“思考路径”式问答
- 支持图谱编辑和多模态融合（如图+文本+音频）
- 行业专属图谱模板标准化，如金融、法律、医药

**从“搜索+拼贴”到“结构+理解”，GraphRAG让AI更“有脑子”：**

- **传统RAG**让AI变成了`开卷答题王`
- **GraphRAG**则让它具备了`逻辑推理和结构理解`的能力

在 AI 的能力演化中，`结构化知识注入`是下一步关键。而GraphRAG，就是这个阶段的重要标志。

如果你的数据本身是结构复杂、概念层次清晰的，那么不要犹豫——**GraphRAG一定是更优选项**。





# Tecnent内部GraphRAG的应用

## 一、GraphRAG简介

检索增强生成（RAG）主要是在内部知识库中搜索与用户查询最相关的内容，然后将其提供给LLM用于生成最终答案。

传统RAG的主要流程为：文档被分块（例如，按段落），通过embedding模型转换为相应embedding，并存储在向量数据库中。在检索过程中，查询也会转换为embedding，数据库会找到最相关的块，理论上包含语义上最相关的信息。

GraphRAG 是一种结构化、分层的RAG 方法，与使用纯文本片段的朴素语义搜索方法不同。 GraphRAG 过程包括从原始文本中提取知识图谱、构建社区层次结构、为这些社区生成摘要，然后在执行基于RAG的任务时利用这些结构。

## 二、为什么要GraphRAG？

通过将知识图谱作为结构化、特定领域上下文或事实信息的来源，GraphRAG 使LLMs能够为问题提供更精确、上下文感知和相关的答案，特别是对于需要全面理解大规模语义概括概念的复杂查询。数据集合甚至单个大型文档。

传统的向量搜索方法侧重于使用高维向量的非结构化数据，而 GraphRAG 利用知识图谱来更细致地理解和检索互连的异构信息。这种结构化方法增强了检索信息的上下文和深度，从而对用户查询做出更准确和相关的响应，特别是对于复杂或特定领域的主题。

1. 传统RAG中的chunk方式会召回一些噪声的片段，引入KG，可以通过实体层级特征增强相关性；
2. 传统RAG中chunk之间彼此是孤立的，缺乏关联，在跨文档问答任务上表现不太好，可以引入图谱，增强chunk之间关联，并提升相关性召回；
3. 假设已有KG数据存在，那么可以将KG作为一路召回信息源，补充上下文信息；
4. 将chunk之间形成KG，还可以提供Graph视角上的embedding，以补充召回特征。。

**代价是构建一个高质量的、灵活更新、计算简单的大规模图谱代价非常高。**

## 三、微软GraphRAG流程

GraphRAG分为三个主要阶段：图谱构建，图数据召回，图增强回答，下图就是GraphRAG的主要流程：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719201837879.png" alt="image-20250719201837879" style="zoom:30%;" />

接下来将介绍构建索引和检索的详细步骤。

### 3.1、构建索引

#### 3.1.1、切分TextUnit

与传统RAG一样，GraphRAG也需要将源文档转化为文本片段（TextUnits），这个片段既会被用于图谱抽取，也会作为知识的引用源，以便追溯回最初的原始文本内容。

文本切分大小（以Token数计算）默认是300个Token，作者发现1200个token大小的文本单元能取得更好效果。但是，越大的文本块大小会导致输出精度降低、召回率降低、并且降低参考文本的可读性；不过文本块尺寸越大，可以减少LLM调用次数，整个处理过程速度可以更快。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719201927611.png" alt="image-20250719201927611" style="zoom:50%;" />

#### 3.1.2、构建知识图谱

提取知识图谱中相关的元素，包括实体、关系、实体声明等。先提供entity_type，之后用LLM在不同的chunk里面提取潜在的实体、关系以及他们的描述。最后再用LLM合并相同含义的entity，总结他的description，这里会使用模型进行多轮反思“针对抽取结果是否有未识别出的实体？”，如果存在则进行补充抽取，来提升对于构建图谱最关键的实体三元组抽取的召回率。

声明代表实体的一些状态或时间限制的陈述，它的提取和上面的流程分开。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202024142.png" alt="image-20250719202024142" style="zoom:50%;" />

#### 3.1.3、Graph增强

有了实体和关系图，构建社区结构，并用其他信息扩充该图。这分为两个步骤：社区发现和图嵌入。提供了显式（社区）和隐式（嵌入）方法来理解图的拓扑结构。

1. 社区发现：在此步骤中，我们使用Hierarchical Leiden算法生成实体社区的层次结构。这个方法将对我们的图应用递归社区聚类，直到达到社区规模阈值。这使我们能够了解图的社区结构，并提供一种在不同粒度级别上总结图的方法。
2. 图嵌入：使用 Node2Vec 算法生成图的向量表示。这将使我们能够理解图的隐式结构，并提供额外的向量空间，以便在查询阶段搜索召回。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202105090.png" alt="image-20250719202105090" style="zoom:50%;" />

#### 3.1.4、社区摘要

现在，我们希望基于社区数据并为每个社区生成摘要。这让我们可以从多个粒度对整张图有一个高层次的了解。例如，如果社区A是顶级社区，我们将获得有关整个图的摘要。如果社区是较低级别的，我们将获得有关低层次集群的摘要。

1. 生成社区摘要：使用 LLM 生成每个社区的摘要。prompt中包含任务定义、社区子结构中的关键实体、关系和声明。
2. 生成社区向量表示：通过社区报告摘要、社区标题的文本嵌入来生成社区的embedding。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202134532.png" alt="image-20250719202134532" style="zoom:50%;" />

#### 3.1.5、文档处理

文档处理是对文档进行表示，并形成文档图，这一块的目的是对文档进行表征。它主要包含以下两部分：

1. 链接到文本单元：将每个文档与第一阶段创建的文本单元关联起来，能够理解哪些文档与哪些文本单元相关。
2. 文档嵌入：使用文档切片的平均嵌入来生成文档的向量表示。具体做法是重新分块文档，不重叠块，然后为每个块生成嵌入，创建这些块的加权平均值，按token计数加权，并将其用作文档嵌入，然后基于这种文档表示，能够理解文档之间的隐含关系，并帮助生成文档的网络表示。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202221576.png" alt="image-20250719202221576" style="zoom:40%;" />

### 3.2、检索

#### 3.2.1、Local Search

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202327792.png" alt="image-20250719202327792" style="zoom:40%;" />

1. 给定用户查询和可选的对话历史记录，Local search从知识图谱中识别与用户输入语义相关的一组实体。这些实体充当知识图谱的访问点，从而能够提取进一步的相关详细信息，例如连接的实体、关系、实体协变量、社区报告，以及实体关联的原始输入文档中提取相关文本块。
2. 然后对这些候选数据源进行优先级排序和过滤。
3. 最后根据预定义大小的单个上下文窗口来确定context，并生成最终的response。

#### 3.2.2、Global Search

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202417888.png" alt="image-20250719202417888" style="zoom:40%;" />

1. **Concatenation**：将社群摘要随机shuffle，并划分为预设的token大小的chunk，每个chunk作为一段context上下文。这样做确保了相关信息均匀分布，而不是聚集在单一的上下文窗口中。
2. **Map**：并行生成每个区块的中间答案。同时要求LLM为生成的答案打分，分数范围从0到200，表示示答案对目标问题的帮助程度，得分为0的答案将被排除。
3. **Reduce**：根据有用性得分，将中间社群答案降序排列，并逐步整合进新的上下文窗口，直至达到token限制，这一最终上下文将用于生成并返回给用户的全局答案。

### 3.3、GraphRAG在小说上的实战

#### 3.3.1、开源GraphRAG存在的问题

1. 微软开源的GraphRAG项目主要是针对英文的，对于中文文本会出现不适配的问题，例如进行文本切分的时候会出现乱码，英文prompt导致提取的实体关系也为英文等。需要针对中文场景进行优化。
2. GraphRAG并不是全能的，它与传统向量检索并不是冲突的，而是一种互补的关系。我们使用不同类型的问题进行测试，分别是**事实性问题**和**总结性问题。**

对于事实性问题，我们使用回答的准确率指标来衡量，下面表格是最终结果，可以看到GraphRAG在事实性问题上要明显弱于传统向量检索。

|               | **Accuracy** |
| ------------- | ------------ |
| **VectorRAG** | 0.33         |
| **GraphRAG**  | 0.04         |

对于总结性问题，我们使用pair-wise的方式对比他们的好坏，并从三个维度去衡量答案：

全面性：答案是否提供了足够的细节来全面覆盖问题的所有方面
多样性：答案是否从多个角度提供了丰富的视角和见解
赋能性：答案是否有效地帮助读者理解问题并作出明智的判断

|             | **VectorRAG** | **GraphRAG** |
| ----------- | ------------- | ------------ |
| **全面性**  | 29.69%        | 70.31%       |
| **多样性**  | 31.32%        | 68.68%       |
| **赋能性**  | 28.32%        | 71.68%       |
| **Overall** | 30.38%        | 69.62%       |

可以看到，GraphRAG在总结性问题上的回答效果要明显优于传统向量检索。所以GraphRAG和传统向量检索能力是互补的，对于文本中明确存在答案的事实性问题，传统向量检索就能做的很好，对于概括性的、跨多段落的问题，GraphRAG会比传统向量检索更加出色。

但是如果使用类似于HybridRAG[1]中暴力拼接的做法，那么上下文的准确度会大大下降，我们希望使用比较少的token达到比较好的效果。

#### 3.3.2、对开源GraphRAG的优化

##### 针对中文优化

**文本切分**

官方分块方法是把文档按照token数进行切分，对于中文来说容易出现乱码，对于中文我们用中文字符数对文本进行切分。这里可以参考langchain中splitter的做法，修改graphrag中的graphrag/index/verbs/text/chunk/strategies/tokens.py，添加中文文本切分方法。

```python
class ChineseRecursiveTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(
            self,
            separators: Optional[List[str]] = None,
            keep_separator: bool = True,
            is_separator_regex: bool = True,
            **kwargs: Any,
    ) -> None:
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or [
            r"\n\n",
            r"\n",
            r"。|！|？",
            r"\.\s|\!\s|\?\s",
            r"；|;\s",
            r"，|,\s",
        ]
        self._is_separator_regex = is_separator_regex

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """拆分传入的文本并返回处理后的块。"""
        final_chunks = []
        separator = separators[-1]
        new_separators = []
        for i, _s in enumerate(separators):
            _separator = _s if self._is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1:]
                break
```

**Prompt-Tune**

**自动微调**

在使用GraphRAG的过程中，一个主要挑战在于如何将其图形表示能力有效应用于特定的文档领域。不同文档领域各自拥有独特的结构和特征，简单地使用通用的GraphRAG模型往往难以达到预期效果。因此，需要根据各领域的特点对GraphRAG进行个性化调整，通过设计针对特定领域的Prompt，可以引导GraphRAG模型更好地理解和处理相关文档。Prompt-Tune的核心在于通过微调prompt（相当于微调了模型参数），使其能够捕捉特定领域的细微差异和独特特征，从而提升模型在该领域的表现。在使用Prompt-Tune时，使用的大模型必须是参数相对较大的，性能较好的那种，不然输出的Prompt质量可能较差。以下是使用Prompt-Tune的一个例子：

```basic
python -m graphrag.prompt_tune --root ./ragtest --domain "Chinese web novels" --language Chinese --chunk-size 512
```

 这样会生成了三个文件：community_report.txt、entity_extraction.txt和summarize_descriptions.txt，分别对应社区报告生成、实体抽取和总结描述prompt。他们统一遵循一个模版，即：

```
---解决任务的方法--- 
---任务的输入和输出---
---few-shot，3到5个左右---
---当前输入---
```

**手动微调**

由于自动微调时，每次给出的实体列表都会有所不同，这个过程缺乏可控性，通过手动调整Prompt，我们可以根据实际需求，精准定义需要提取的实体类型及其相关信息，从而确保提取结果的准确性和完整性。我们拿出输入文本片段给到GPT4，让他判别所要抽取的实体类别，然后再用实体类别让模型去抽取三元组，选择抽取三元组更符合你期望的实体类别。最后我们修改实体抽取prompt中任务说明部分、few-shot和real data部分的entity_types。

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202704598.png" alt="image-20250719202704598" style="zoom:35%;" />

上图是节点度数的直方图，左边是Prompt-Tune之前，右边是Prompt-Tune之后。经过Prompt-Tune之后，节点数量由**7531**增长到了**8880**个，同时高度数节点变得更多。

##### GraphRAG和VectorRAG结合

我们考虑使用GraphRAG来扩展知识库，具体方法是我们将实体列表和关系列表转换为元数据存储，生成embedding的文本为title和description做拼接，本地搜索时直接从知识库中做向量相似度匹配。每个实体或关系都是一个独立的召回单元，如果过长会进行切分chunk生成embedding。

同时我们也将图社区摘要保存为社区元数据存储，因为包含特殊格式字符，为了对齐其他知识库信息所以使用gpt-4o-mini做了清洗。这样的话全局搜索策略被简化为社区元数据存储上的搜索操作，而非采用MapReduce这样的全量扫描加二次汇总的方式。降低全局搜索的查询延迟。

以下是清洗前的社区摘要：

```text
# 五竹与范闲的复杂关系\n\n该社区围绕五竹与范闲的关系展开，五竹不仅是范闲的保护者，还在多个事件中扮演关键角色。江南作为重要地点，承载着多重故事，涉及多位角色的命运。五竹的背景复杂，涉及连环杀人案和与其他角色的紧张关系。\n\n## 五竹的保护者角色\n\n五竹在范闲的生活中扮演着保护者的角色，时常关注他的安全，并在关键时刻提供帮助。他不仅教导范闲武功，还在刺杀计划中观察范闲，显示出他在保护范闲方面的决心和能力。这种保护关系可能会引发其他角色的敌意，增加社区的紧张局势。[Data: 关系（0，+more）]\n\n## 江南的关键性\n\n江南是多个角色交织的关键场所，五竹、李承泽和谢必安等人在此进行重要活动。范闲计划前往江南接管叶轻眉留下的三大坊，这一行动可能会引发更大的冲突和复杂的情感纠葛。江南的紧张局势和多重故事使其成为社区的重要组成部分。[Data: 实体（156），关系（270，+more）]\n\n## 五竹与林珙的冲突\n\n五竹承认自己杀死了林珙，这一事件为他与范闲的关系增添了复杂性。范闲对这一秘密的了解可能会影响他对五竹的信任，进而影响他们的合作关系。这种冲突不仅影响了五竹的声誉，也可能对社区的稳定性造成威胁。[Data: 关系（293，+more）]\n\n## 神庙使者的威胁\n\n神庙使者模仿五竹的装扮，制造连环杀人案，试图带走范闲。这一事件不仅增加了社区的紧张局势，也使得五竹的保护角色面临挑战。神庙使者的存在可能会引发更大的冲突，影响社区的安全和稳定。[Data: 实体（575），关系（269，+more）]
```

 以下是清洗后的社区摘要：

```text
五竹与范闲的关系复杂而微妙。五竹不仅是范闲的保护者，还在多个事件中扮演关键角色。江南作为重要地点，承载着多重故事，涉及多位角色的命运。五竹的背景复杂，涉及连环杀人案和与其他角色的紧张关系。
五竹在范闲的生活中扮演着保护者的角色，时常关注安全，并在关键时刻提供帮助。不仅教导范闲武功，还在刺杀计划中观察范闲，显示出保护的决心和能力。这种保护关系可能引发其他角色的敌意，增加社区的紧张局势。
江南是多个角色交织的关键场所，五竹、李承泽和谢必安等人在此进行重要活动。范闲计划前往江南接管叶轻眉留下的三大坊，这一行动可能引发更大的冲突和复杂的情感纠葛。江南的紧张局势和多重故事使其成为社区的重要组成部分。
五竹承认自己杀死了林珙，这一事件为他与范闲的关系增添了复杂性。范闲对这一秘密的了解可能影响对五竹的信任，进而影响合作关系。这种冲突不仅影响五竹的声誉，也可能对社区的稳定性造成威胁。
神庙使者模仿五竹的装扮，制造连环杀人案，试图带走范闲。这一事件不仅增加了社区的紧张局势，也使得五竹的保护角色面临挑战。神庙使者的存在可能引发更大的冲突，影响社区的安全和稳定。
```

**重排序**

我们将最终召回的结果统一经过Reranker进行重排序，以下是经过归一化后entites、relationships、reports和chunk的得分分布，可以看到entities、relationships整体偏低，reports得分较为平均而chunk的得分明显会偏高，这可能是因为他们召回信息的粒度不对齐，导致得分不一致，未来这块还有继续优化的空间。

#### 3.3.3、最终效果

我们使用ragas（https://github.com/explodinggradients/ragas）进行评测，它可以衡量以下三个维度的指标：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719202947742.png" alt="image-20250719202947742" style="zoom:40%;" />

我们选用以下两个评测指标：

**Faithfulness**：衡量生成答案的事实准确性。给定上下文中正确事实的数量除以生成答案中的上下文总数。

**Answer relevance**：衡量生成的答案与问题的相关程度。该指标是使用question和answer计算的。例如，答案“法国位于西欧”。对于“法国在哪里以及它的首都是什么？”这个问题将获得较低的答案相关性，因为它只回答了问题的一半。

最终结果如下：

|               | **Tokens** | **Faithfulness** | **Answer relevance** |
| ------------- | ---------- | ---------------- | -------------------- |
| **VectorRAG** | 3000       | 0.76             | 0.09                 |
| **GraphRAG**  | 3000       | 0.73             | 0.07                 |
| **Hybrid**    | 3000       | 0.76             | 0.13                 |

可以看到，通过多知识库索引+Rerank的方式，能够有效增加相对于VectorRAG回答问题的相关度。

## 四、GraphRAG未来优化方向

GraphRAG其实就是在RAG的召回内容中加入图谱召回，来优化回答，主要包含以下三个部分：图谱构建，图数据召回，图增强回答，这些部分未来仍有很大的改进空间，这里分享一些有价值的优化方向。

### 4.1、知识图谱构建优化

#### Graphusion

>https://arxiv.org/abs/2410.17600
>
>Graphusion: A RAG Framework for Scientific Knowledge Graph Construction with a Global Perspective

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719203112201.png" alt="image-20250719203112201" style="zoom:40%;" />

大多数使用大模型构建知识图谱的方法关注的是局部视角，从单个句子或文档中抽取知识三元组，缺少一个融合过程以全局视角组合知识。

Graphusion介绍一种结合了全局视角的知识图谱构建的RAG框架，它包括三个主要步骤：

1.**种子实体生成**：通过主题建模提取出种子实体列表，这些实体列表将指导知识图谱包含最相关的实体。

2.**三元组提取**：设计了一个CoT的prompt，首先让LLMs提取领域内的实体，然后确定这些实体之间的可能关系，并发现新的三元组。

3.**知识图谱融合**：对多个局部子图进行全局合并和解决冲突，具体包括实体的合并、冲突的解决以及新三元组的发现，最终形成大的知识图谱。

#### AgentRE

>https://arxiv.org/abs/2409.01854
>
>AgentRE: An Agent-Based Framework for Navigating Complex Information Landscapes in Relation Extraction

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719203408990.png" alt="image-20250719203408990" style="zoom:45%;" />

AgentRE是一个包含检索和记忆模块的智能体框架，可以处理来自不同渠道的数据，借助检索和记忆模块等工具，辅助智能体进行推理。与传统的单轮“文本输入，文本输出”语言模型不同，AgentRE通过多轮交互和推理，拓宽了信息源的利用范围，克服了单轮提取的局限。

其次，在资源有限的情况下，AgentRE能够借助LLM的推理和记忆能力，在提取过程中进行动态总结和反思，从而精进其持续学习能力，通过不断积累经验与知识，提升提取效能，以下是AgentRE的主要三个模块：

**检索模块**（Retrieval Module）：负责维护静态知识库，便于存储和检索信息，这包括训练集中的标注样本以及相关的标注指南等资料。

**记忆模块**（Memory Module）：负责维护动态知识库，用于记录当前提取结果的短期记忆，以及用于总结和反思历史操作的长期记忆。通过在记忆模块中进行读写操作，记录并利用以往的提取经验。

**提取模块**（Extraction Module）：利用检索和记忆模块提供的信息，通过多种推理方法从输入文本中抽取三元组。

### 4.2、检索优化

#### LightRAG

>https://arxiv.org/abs/2410.05779
>
>LightRAG: Simple and Fast Retrieval-Augmented Generation

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719203506626.png" alt="image-20250719203506626" style="zoom:40%;" />

LightRAG对比微软的GraphRAG，它更多在信息召回层面做了优化。这里我们只看下LightRAG和GraphRAG的核心差异点：对图索引的构建和图信息召回。为了应对多样化的查询需求，LightRAG采用了两种不同的检索策略，主要包括以下两种方式：

- **Low-Level 检索**： 这一层次主要关注特定实体及其相关属性或关系。主要回答细节类的问题，例如谁写了傲慢与偏见，问题专注于具体实体，关系。
- **High-Level 检索**： 这一层次处理更广泛的主题和全局概念。包括全局类，概念类问题，需要掌握全局，抽象信息，例如人工智能如何影响当代教育。

通过将图结构与向量表示相结合，模型得以更全面地解析实体间的关系，这种协同机制使得检索算法能够灵活运用局部和全局关键词，优化搜索流程，进而提升结果的相关性。

### 4.3、多知识库索引

#### StructRAG

>https://arxiv.org/abs/2410.08815
>
>StructRAG: Boosting Knowledge Intensive Reasoning of LLMs via Inference-time Hybrid Information Structurization

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250719203628244.png" alt="image-20250719203628244" style="zoom:40%;" />

StructRAG借鉴了人类处理复杂推理任务时通常不会不同于简单阅读散乱的原始内容，而是会将这些信息信息汇总成结构化知识，再利用这些结构化信息进行思考推理。论文中设计了不同的知识库索引，例如：

1. **表索引**：提供传统的关系型数据查询与分析能力，实现基于表数据的过滤、分析、聚合等能力。
2. **图索引**：提供关联数据分析能力以及图迭代算法，实现基于图数据的高维分析与洞察。
3. **向量索引**：提供向量化存储与相似性查询能力，扩展数据检索的多样性。
4. **全文索引**：提供基于关键词的文档查询能力，扩展数据检索的多样性。

StructRAG最大创新点在于训练了**混合结构的路由器**，混合结构路由器根据任务需求灵活选择最佳知识结构形式，例如表格、图或算法，确保知识的呈现最大化满足推理需要。例如，当需要比较多家公司的财务数据时，混合结构路由器会优先选择表格这一形式，以便清晰展示数据对比。混合结构路由器采用混采用DPO训练，能够不依赖额外的奖励模型实现优良效果。这种方法通过生成高质量的偏好对来确保训练的有效性，结合“合成-模拟-判断”的方法来构建偏好数据。这种多知识库混合的方式也是未来RAG落地应用的方向。

## 五、总结

本文介绍了微软GraphRAG的主要流程，并分享了我在小说实战上的一些分析和经验，以及未来优化的方向。目前GraphRAG并不是非常成熟，未来还有很多问题需要解决，以下是给想要在自己领域内使用GraphRAG的一些建议：

1. 首先你要熟悉传统向量检索能解决什么问题以及不能解决什么问题，要有清晰的评判标准。
2. 要有高质量的数据源，可以是非结构化纯文本，也可以是其他结构化的能转换为知识图谱的数据。
3. 根据端到端的效果去优化中间组件，比如图谱构建质量较差就去优化图谱构建过程，检索效果较差就去优化查询过程，如果特殊领域比如需要数据分析的可以添加表格数据丰富知识库，如果时延要求比较宽松可以添加反思或记忆等。

👉目前[tRAG平台](https://km.woa.com/articles/show/605326?kmref=search&from_page=1&no=2)支持GraphRAG，并且检索性能比微软开源的GraphRAG快一倍，如有业务需求，请联系winniexli

👉 接口文档：[ https://iwiki.woa.com/p/4013015977](https://iwiki.woa.com/p/4013015977)

tRAG系列文章推荐：

[TRAG平台上线：助力业务敏捷落地RAG应用](https://km.woa.com/articles/show/605326?kmref=search&from_page=1&no=1)

[TRAG在NPC场景的落地实践](https://km.woa.com/articles/show/607303?kmref=search&from_page=1&no=2)

[AI搜索工具优化之道：时效性、改写技术的探索](https://km.woa.com/articles/show/612036?kmref=search&from_page=1&no=3)

[tRAG精解: 从文档解析到搜索召回多场景实操指南](https://km.woa.com/articles/show/613631?kmref=search&from_page=1&no=6)







