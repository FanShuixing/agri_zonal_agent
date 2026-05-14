agri-deep-agent/
│
├── README.md
├── requirements.txt
├── .env
│
├── app/                        # 应用入口
│   ├── main.py                # 启动入口（CLI / API）
│   ├── api.py                 # FastAPI（可选）
│
├── agent/                     # Deep Agent核心
│   ├── builder.py            # create_deep_agent 封装
│   ├── planner.py            # 任务拆解（核心）
│   ├── executor.py           # 执行调度
│   ├── reflection.py         # 结果校验（关键加分点）
│   ├── state.py              # Agent状态管理（类似LangGraph State）
│
│   ├── nodes/                # 各个推理节点（重点）
│   │   ├── climate_node.py
│   │   ├── soil_node.py
│   │   ├── terrain_node.py
│   │   ├── suitability_node.py
│   │   ├── yield_node.py
│   │   ├── risk_node.py
│   │   ├── decision_node.py
│   │   ├── map_node.py
│   │
│   ├── graph.py              # Agent执行流程（强烈建议用图结构）
│
├── tools/                    # 工具层（外部能力）
│   ├── weather_api.py
│   ├── soil_api.py
│   ├── geo_tool.py
│   ├── map_renderer.py
│   ├── price_api.py
│
├── models/                   # 数据模型 & 计算逻辑
│   ├── climate_model.py
│   ├── crop_model.py
│   ├── yield_model.py
│   ├── risk_model.py
│   ├── suitability_model.py
│
├── memory/                   # 长期记忆（Deep Agent关键）
│   ├── cache.py             # 区域分析缓存
│   ├── vector_store.py      # 向量记忆（可选）
│   ├── history.py           # 用户历史
│
├── data/                     # 数据（本地 or mock）
│   ├── crops.json
│   ├── soil.json
│   ├── counties.geojson
│
├── prompts/                  # Prompt管理（很重要）
│   ├── planner_prompt.txt
│   ├── decision_prompt.txt
│   ├── reflection_prompt.txt
│
├── utils/
│   ├── logger.py
│   ├── config.py
│
└── tests/
    ├── test_agent.py