1、执行graphrag初始化

```shell
graphrag init --root ./
```

2、配置.env文件，需要的对应的配置如下

```text
GRAPHRAG_API_BASE=<请求路径>
GRAPHRAG_API_KEY=<API-KEY>
GRAPHRAG_MODEL=<api-model>

EMBEDDING_API_BASE=<请求路径>
EMBEDDING_API_KEY=<API-KEY>
EMBEDDING_MODEL=<api-model>
```

3、进行graphrag索引indexing环节

```shell
graphrag index --root ./
```

4、检索环节

```python
context_builder = LocalSearchMixedContext(
    community_reports=reports,
    text_units=text_units,
    entities=entities,
    relationships=relationships,
    covariates=None,
    entity_text_embeddings=description_embedding_store,
    embedding_vectorstore_key=EntityVectorStoreKey.ID,
    text_embedder=text_embedder,
    token_encoder=token_encoder,
)
local_context_params = {
    "text_unit_prop": 0.5,
    "community_prop": 0.1,
    "conversation_history_max_turns": 5,
    "conversation_history_user_turns_only": True,
    "top_k_mapped_entities": 10,
    "top_k_relationships": 10,
    "include_entity_rank": True,
    "include_relationship_weight": True,
    "include_community_rank": True,
    "return_candidate_context": True,
    "embedding_vectorstore_key": EntityVectorStoreKey.ID,
    "max_tokens": 12_000,
}

llm_params = {
    "max_tokens": 2_000,
    "temperature": 0.0,
}

search_engine = LocalSearch(
    llm=llm,
    context_builder=context_builder,
    token_encoder=token_encoder,
    llm_params=llm_params,
    context_builder_params=local_context_params,
    response_type="multiple paragraphs",
)

result = await search_engine.asearch("请帮我介绍这个文章")
```