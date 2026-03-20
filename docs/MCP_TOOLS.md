# CapCut Mate：REST 接口与 MCP Tool 对照

MCP 服务在启动时读取仓库根目录的 `openapi.yaml`，为每个 `POST` 路径注册一个与 `operationId` 同名的 tool；下列三个接口在 OpenAPI 中未收录，由桥接服务单独注册。

## 环境变量

| 变量名 | 含义 | 默认 |
|--------|------|------|
| `CAPCUT_MATE_BASE_URL` | API 根地址（含 `/openapi/capcut-mate/v1`，无末尾斜杠） | `http://127.0.0.1:30000/openapi/capcut-mate/v1` |
| `CAPCUT_MATE_OPENAPI_PATH` | 自定义 OpenAPI 文件绝对或相对路径 | 仓库根目录 `openapi.yaml` |
| `CAPCUT_MATE_HTTP_TIMEOUT` | 转发 HTTP 超时（秒） | `120` |

## 运行方式

安装可选依赖后，以 stdio 方式启动（供 Cursor、Claude Desktop、支持 stdio 的 n8n MCP 社区节点等使用）：

- 包内入口：`capcut-mate-mcp`
- 模块方式：`python -m mcp_server`

## Tool 与 HTTP 映射

| MCP tool 名（operationId） | HTTP | 路径 | 说明（来自 OpenAPI summary） |
|----------------------------|------|------|------------------------------|
| add_audios | POST | /add_audios | 批量添加音频 |
| add_captions | POST | /add_captions | 批量添加字幕 |
| add_effects | POST | /add_effects | 添加特效 |
| add_images | POST | /add_images | 批量添加图片 |
| add_keyframes | POST | /add_keyframes | 添加关键帧 |
| add_masks | POST | /add_masks | 添加蒙版 |
| add_sticker | POST | /add_sticker | 添加贴纸 |
| add_text_style | POST | /add_text_style | 添加文本样式 |
| add_videos | POST | /add_videos | 添加视频 |
| audio_infos | POST | /audio_infos | 音频信息相关 |
| audio_timelines | POST | /audio_timelines | 音频时间线 |
| caption_infos | POST | /caption_infos | 字幕信息 |
| create_draft | POST | /create_draft | 创建草稿 |
| easy_create_material | POST | /easy_create_material | 简易创建素材 |
| effect_infos | POST | /effect_infos | 特效信息 |
| gen_video | POST | /gen_video | 提交云端渲染（OpenAPI 外补充） |
| gen_video_status | POST | /gen_video_status | 查询渲染状态（OpenAPI 外补充） |
| get_audio_duration | POST | /get_audio_duration | 获取音频时长 |
| get_draft | GET | /get_draft | 获取草稿文件列表（OpenAPI 外补充） |
| get_image_animations | POST | /get_image_animations | 获取图片动画 |
| get_text_animations | POST | /get_text_animations | 获取文本动画 |
| get_url | POST | /get_url | 获取 URL |
| imgs_infos | POST | /imgs_infos | 图片信息 |
| keyframes_infos | POST | /keyframes_infos | 关键帧信息 |
| objs_to_str_list | POST | /objs_to_str_list | 对象转字符串列表 |
| save_draft | POST | /save_draft | 保存草稿 |
| search_sticker | POST | /search_sticker | 搜索贴纸 |
| str_list_to_objs | POST | /str_list_to_objs | 字符串列表转对象 |
| str_to_list | POST | /str_to_list | 字符串转列表 |
| timelines | POST | /timelines | 自定义创建时间线列表 |
| video_infos | POST | /video_infos | 根据时间线制作视频数据 |

各 tool 的请求体 JSON Schema 与 OpenAPI 中对应路径的 `requestBody` 一致；`get_draft` 使用查询参数 `draft_id`，与后端 `GET /get_draft` 一致。

## 与 n8n 的配合方式

- **直接调 REST**：工作流中使用 HTTP Request 节点指向同一 `CAPCUT_MATE_BASE_URL` 下的路径，与 MCP 转发行为一致，不依赖 MCP 运行时。
- **通过 MCP Client（stdio）**：在支持「启动子进程 + stdio」的 MCP Client 中配置启动命令为已安装的 `capcut-mate-mcp`，并设置上述环境变量；由客户端拉起桥接进程后，即可在 Agent 工具列表中看到全部 tool。

若后续需要 **仅 HTTP/SSE 的 MCP 传输**（部分托管环境无法使用 stdio），可在本仓库基础上增加基于 MCP Streamable HTTP 的入口或单独部署网关，与当前 stdio 桥接并列维护。
