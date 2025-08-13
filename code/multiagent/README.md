# 编写一个agent相关的技术code

## 环境准备
1、首先得再根目录下添加 .env 文件，包含一下内容
```shell
MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=<你的 deepseek api-key>
DEEPSEEK_API_KEY=<你的 deepseek api-key>

GOOGLE_API_KEY=<你的 google api-key> # 建议去官方申请 
TAVILY_API_KEY=<你的 tavily api-key> # 建议去官方申请 https://app.tavily.com/home
```