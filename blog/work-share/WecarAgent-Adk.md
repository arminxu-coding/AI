# 服务代码&ADK分享

## 一、背景

首先我们非常明确，目前座舱agent采用的架构是Google的ADK框架；

为了我们武汉团队同学，快速熟悉其业务代码&Agent框架原理，本次基于当前wecar-agent项目结合adk原理进行分析一下项目原理，帮助大家快速理解以及共同学习进步、集思广益。

## 二、目标

本次分享的核心目标是：

1.adk的代码运行原理（基于源码进行分享）

2.部分的wecar-agent代码业务

3.agent项目开发具备的内容

> 注意：本次内容并不是完全给大家讲明白adk的内容，仅仅是部分内容的初级分享，给大家做一个简单的启蒙分享，因为目前我们组内大部分同学还没有深入学习agent项目，更多深入的内容还需大家进行自行深入学习。

预计分享30～40分钟。

## 三、wecar-agent项目代码流程

首先，我们先看看wecar-agent项目源码，基于目前的代码一起过一下adk的执行流程；

#### 3.1、Agent入口

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707101426747.png" alt="image-20250707101426747" style="zoom:31%;" />



##### 核心功能

1. 初始化hostagent&runner运行器
2. 加载session会话（从redis&内存中共同加载）
3. 使用runner运行adk的框架代码，执行agent中的各种行为（调用大模型、处理模型返回结果、执行业务子sub_agent/tool代码）
4. 保存当前session会话到会话历史上下文中

##### HostAgent

先不管别的，我们先核心关注host_agent是什么个东西。

这里其实就是使用adk的Agent基类创建一个框架内不定义的agent实例对象，其中核心包括4个内容：

1. model
2. instruction + description
3. sub_agents
4. tool

看到这个大家应该非常清楚，这里我们简单回顾一下标准的调用llm的api格式：

```json
{
    "model": "Qwen/QwQ-32B",
    "messages": [
        {
            "role": "system",
            "content": "you are help full assiant."
        },
        {
            "role": "user",
            "content": "What opportunities and challenges will the Chinese large model industry face in 2025?"
        }
    ],
    "tools": [
        {
            "name": "get_weather",
            "description": "获取指定城市和日期的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称（支持中文/拼音/英文）",
                        "example": "上海"
                    }
                },
                "required": [ "city" ]
            }
        }
    ]
}
```

我们都知道，目前代表大模型核心的就是 `prompt` ，而在结构化程序当中就分为了`system_prompt` + `user_prompt`，在function_call的模式中新增的就是`tools`，这个在最后丢给llm的时候都会组装起来。

所以基于上面能够分析出，在 **host_agent** 中定义的这些内容，无非也就是一次标准调用llm的一个过程必备的参数，然后 **adk 中的 Agent** 定义包装成一个类，其中具备了其他的能力：上下文管理、状态管理、prompt组装、llm调用、工具tool调用、回调机制、事件驱动等等非常丰富合理的设计理念。

好的，我们再理解一遍，就是adk帮助我们封装了很多复杂又繁琐通用代码逻辑而已，帮助我们屏蔽了具体代码执行的细节，我们只需要关注于我们的业务代码即可，也就是 `prompt` + `tools`。

> 对的 这就是框架存在的本质和意义。

##### Runner

runner是adk的agent执行器，其中就是先决去执行agent的，会进行封装上下文content的前置后置处理、调用agent逻辑、会话处理等。

#### 3.2、Agent执行

##### 调用llm

经过base_agent的一通执行，各种的前置处理、参数封装、前置回调等等行为，最终进行调用llm：



<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707101500738.png" alt="image-20250707101500738" style="zoom:23.5%;" />



##### messages组装

最后就是封装messages列表，tools列表，交给llm进行推理，选择tool，然后代码进行执行tool。

那我们看看messages是怎么封装的：



<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707101543375.png" alt="image-20250707101543375" style="zoom:33%;" />



其中tool一般会是一个标准的function/agen_tool对象/mcp_tool等等在adk中定义的tool形式，会解析成一个标准的json格式。

##### 响应解析&调度执行

经过模型进行处理，那么其中响应，就是agent代码需要进行处理的，到最后我们的自己业务的代码执行；

为了简单理解起见：这里假设就是一个标准的function call的模式，模型经过本次处理之后，选择了一个tool，那么之后是如何执行的：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707101615826.png" alt="image-20250707101615826" style="zoom:24%;" />

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707101639760.png" alt="image-20250707101639760" style="zoom:30%;" />

1. 如果本次模型返回的是一个tool，那么就会走选择好tool（本身自己的业务tool）进行执行
2. 如果本次模型返回的是一个sub_agent，那么就会走sub_agent进行执行，那么又会回到agent执行的流程，因为他们都是属于ADK定义的标准Agent逻辑，那么就是如此往复执行
3. 然后再交由模型进行处理tool的响应结果

到目前也执行好了tool之后，那么会如何调用呢？

首先第一步，会把tool执行的结果response返回；

其次，如果选择的tool是需要分给sub_agent的，也就是当前host_agent配置的tools列表无法满足，llm推理出选择sub_agent进行执行，会走LlmAgent中默认配置的`transfer_to_agent_tool`执行，加一个 function_response_event.actions.transfer_to_agent 字段，然后执行模型选择好的子agent；

最后，如何进行退出整个执行流程呢?

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707105714371.png" alt="image-20250707105714371" style="zoom:29%;" />



这段代码中就会判断当前响应是否为最后一个响应，核心判断就是是否为**function_call_response**，如果是了那么就结束了流程，也就是本次对话处理完毕了；2

#### 3.3、其他能力

Adk中间封装的能力不仅仅有这套代码框架流程的调用，也有很多高级功能，例如：

1. 各个关键流程的前置、后置回调机制（agent执行前/后、model执行前/后、tool执行前/后...）：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707110232469.png" alt="image-20250707110232469" style="zoom:35%;" />

2. session上下文的状态值管理，会讲一些临时状态变量放置在当前的调用上下文中，类似于thread_local：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707111012827.png" alt="image-20250707111012827" style="zoom:27%;" />

3. event事件机制
4. 其他高级特性：planner、code_executor、自定义llm实现、自定义session管理（默认基于内存、我们会实现基于redis、mysql等）、agent工作流、artifacts组件信息等等...

#### 3.4、总结

基于上面的几块内容，以及基本把google的内容讲解完毕了；

## 四、回到wecar-agent业务逻辑

#### 4.1、业务流程图

总结流程大概就是：

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707143022088.png" alt="image-20250707143022088" style="zoom:50%;" />

#### 4.2、业务代码

下面结合代码进行查看一下：

1. 初始化agent，假设这里就只有一个agent，**也就是零售agent**（简单来看），_host_agent = supported_agents[0]，retail_agent()

```python
def init_agents(self, channel_id: str = "009000"):
        channel_config: ChannelConf = get_channel_rainbow_config().get_channel_config().get(channel_id, {})
        logger.info(f"当前渠道{channel_id}的配置信息: {channel_config}, ID: {id(channel_config)}")
        supported_agents = support_agents_by_channel(channel_config)

        if len(supported_agents) == 0:
            raise Exception(f"当前渠道{channel_id}没有支持的agent")

        _host_agent = None
        if len(supported_agents) == 1:
            # 只有一个agent，则不需要host agent 进行分发，直接将这个agent 作为host agent
            _host_agent = supported_agents[0]
        else:
            sub_agents = supported_agents
            llm_conf = base.get_llm_config(LLmKey.LLM_CONF_TAIJI_HUNYUAN_FUNCALL)
            _host_agent = TxBaseAgent(
                model=llm_conf.llm,
                name='host_agent',
                description="Main coordinator.",
                instruction="Handoff to the appropriate agent based on user needs.",
                sub_agents=sub_agents,
                before_agent_callback=before_agent,
                after_agent_callback=after_agent,
                before_model_callback=before_model_callback,
            )

        _runner = Runner(
            app_name=self.app_name,
            agent=_host_agent,
            artifact_service=self.artifact_service,
            session_service=self.session_service,
        )
        return _host_agent, _runner

def retail_agent() -> Agent:
    # 初始化零售API接口,需要提前加载
    manager = RetailOrderManager()
    # 设置回调函数
    manager.set_client_info_callback(get_client_info)
    llm_conf = base.get_llm_config(LLmKey.LLM_CONF_OPENAI_DEFAULT)
    retail_detail_agent = retail_goods_detail_agent()
    return Agent(
        model=llm_conf.llm,
        name='retail_agent',
        instruction="",
        description=RETAIL_AGENT_DESC,
        after_agent_callback=after_agent_callback,
        after_tool_callback=after_tool_modifier,
        before_model_callback=before_model_modifier,
        after_model_callback=after_model_modifier,
        tools=[select_brands_tool,
               AgentTool(agent=retail_detail_agent),
               pay_retail_order,
               cancel_retail_order,
               common_select_tool,
               show_search_goods,
               show_search_stores,
               turn_page]
    )
```

2. model调用前值回调，进行判断是否为手动点击 则执行对应事件、**初始化system_prompt**、根据不同步骤选择对应的tools

```python
def before_model_modifier(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    request = callback_context.state.get(MemoryManager.SESSION_STATE_REQUEST)
    isManual = request.extra_info.get('manual_click', False)
    logger.info(f'before_agent_callback request isManual: {isManual}')
    # 如果是手动点击，则直接处理结果,不走模型
    if isManual:
        handle_manual_result(callback_context, request.query)
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="")], ))
    brands_desc = get_brand_desc(callback_context)
    current_step = _get_current_step(callback_context)
    confirm_items = _get_confirm_items(callback_context)
    un_confirm_items = _get_un_confirm_items(callback_context)
    llm_request.config.system_instruction = RETAIL_AGENT_INSTR.format(
        brand_list=brands_desc,
        confirm_items=confirm_items,
        un_confirm_items=un_confirm_items,
        current_step=current_step)

    # 规格修改界面，需要限制工具使用
    cache: RetailCacheManger = RetailCacheManger()
    step = cache.get_current_step(callback_context)
    if step == RetailStep.RETAIL_GOODS_DETAIL_CHANGE:
        filter_functions = []
        tools = [GOODS_DETAIL_AGENT_NAME, 'cancel_retail_order']
        origin_functions = llm_request.config.tools[0].function_declarations
        for function in origin_functions:
            if function.name in tools:
                filter_functions.append(function)
        llm_request.config.tools[0].function_declarations = filter_functions
    return None
```

3. 假设当前 **query="帮我点个咖啡"**，这里目前支持`麦当劳`、`瑞幸`都支持点咖啡，目前步骤就应该是先 **选择品牌（select_brands_tool）**；这里的大致流程就是根据llm推理出来的brand_names（也就是llm选择的tool对应的args），获取当前品牌选择页渲染的h5内容 + tts内容

```python
def select_brands_tool(brand_names: list[str], product_keyword: str, store_keyword: str, tool_context: ToolContext):
    """
    处理用户发起的点餐请求，推荐品牌列表，并尽量提取产品关键字和门店关键字。

    Args:
        brand_names (list[str]): 品牌名称列表，需要严格匹配[品牌列表]中的品牌，优先匹配品类，其次是描述。
        product_keyword (str): 商品关键词（具体商品、品类等），如果不存在，则为空字符串 `""`
        store_keyword (str): 门店关键词（店名、位置、所在区域等），如果不存在，则为空字符串 `""`
    """
    logger.info(f"brand_names: {brand_names}, product_keyword: {product_keyword}, store_keyword: {store_keyword}")
    brand_list = get_brands(tool_context)
    filter_brands = [brand for brand in brand_list if brand.name in brand_names]
    if not filter_brands:
        tool_context.actions.skip_summarization = False
        return None
    tool_context.actions.skip_summarization = True
    cache: RetailCacheManger = RetailCacheManger()
    cache.save_prodcut_keyword(tool_context, product_keyword)
    cache.save_store_keyword(tool_context, store_keyword)
    cache.save_brand_list(tool_context, filter_brands)
    cache.save_current_step(tool_context, RetailStep.RETAIL_BRAND)
    if len(filter_brands) == 1:
        cache.save_brand(tool_context, filter_brands[0])
        handle_show_stores(tool_context, store_keyword)
    else:
        cache.save_response_type(tool_context, RetailResponseType.TTS,
                                 f"已为您找到多个可点{product_keyword}的品牌，请问要帮您选择哪个品牌呢?")
        # UI 模板回复
        h5_output = get_branch_html(filter_brands)
        cache.save_response_type(tool_context, RetailResponseType.TEMPLATE, h5_output)
```

#### 4.3、总结

好了到这里其实也就把整个流程过完了，基本就是这样子的，整体逻辑其实和整体的agent架构还是非常类似的，大家上次如果听过wmpf-agent的架构分享的话，应该是有所领悟；

- agent四大模块

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250505214523754.png" alt="image-20250505214523754" style="zoom:25%;" />

- agent执行流程

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250505214329460.png" alt="image-20250505214329460" style="zoom:50%;" />

- agent架构设计

<img src="/Users/xuchen/Library/Application Support/typora-user-images/image-20250707202443374.png" alt="image-20250707202443374" style="zoom:40%;" />
