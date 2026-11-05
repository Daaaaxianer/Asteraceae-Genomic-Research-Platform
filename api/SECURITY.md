# API 安全配置与验证

本次加固兼容现有 Django 3.2.8、DRF 3.14.0 和 MySQL 5.7，不安装新依赖，不改变数据库结构。

用户下载行为及结果访问规则见 [DOWNLOADS.md](DOWNLOADS.md)。不建立账号系统，不增加手工输入步骤。

## 请求入口

生产 API 要求经本机反向代理和 Cloudflare，通过 HTTPS 访问 `asteraceae.cgrpoee.top` 或 `asteraceae.cgrpoee.cn`。
IP 从可信代理链右侧逐跳解析，直接连接方不可信时忽略转发头；只有验证到 Cloudflare 节点后才使用 CF-Connecting-IP。
Cloudflare 网段来自官方 https://www.cloudflare.com/ips/ ，在 `access_control.py` 中注明核对日期。代理拓扑或网段变化时应更新配置并回归。

`AGRP_API_REQUIRE_EDGE` 与 `AGRP_API_REQUIRE_HTTPS` 控制 API、结果状态与下载入口。
源服务的 8457、8222、8515 端口限制为本机访问；应用层也校验可信代理链。使用域名 HTTPS 地址进行健康检查；测试环境可以关闭这两个开关。

## 查询预算

- public / partner / trusted 的分页上限分别来自 `AGRP_API_QUERY_MAX_LIMITS`。接口另有更小上限时取较小值。
- `limit=all/none/0` 兼容旧参数，但规范化为当前身份的有限上限，不再无限返回。
- offset 默认最大 100000；查询串默认最大 8192 字符，q/keyword 最大 512 字符，拒绝控制字符。
- JSON 单文件默认最大 16 MiB，实际读取也有字节上限。
- TE 查询读取任何内容前，先检查完整选择范围：最多 64 个文件、合计 16 MiB；过大返回 413。大 TE 目录不再直接整目录在线查询，应使用预算内小文件。网页图表的数据读取通过受控文件 API 流式返回。

## 限流与下载

`shared_limits.py` 使用服务器本地文件锁与原子文件替换，在当前单主机的多个 worker/thread 间共享限流。
不依赖 LocMemCache，也不增加 Redis 或数据库。状态目录 `AGRP_API_STATE_DIR` 不得放在 static/media 中，必须为所有 worker 共用的本地目录，由运行用户拥有。
频率记录使用固定 256 个分片，每片最多保留 256 个未过期身份；达到容量时拒绝请求，不挤掉已有额度。
下载并发使用持续到响应关闭的操作系统锁，进程退出会自动释放，不依赖会中途过期的计数器。
默认全局下载并发 8，单身份仍使用原有 public=2 / partner=10 / trusted=20；最终受两个上限共同约束。

公开科研数据目录、旧下载入口与 `/file_keep/` 直链返回 404；下载按钮、表单、图表导出、示例和分析结果统一使用 API。预览使用 `/api/files/`，下载使用 `/api/download/`。新任务创建时记录自动访问标记，文件链接可跨浏览器使用；不新增用户表。
文件代理关闭响应缓存和缓冲，并传递 Range，以便分段读取及应用并发控制生效；请求编号与审计记录统一由 API 生成。页面图片、CSS、JS 和字体等界面资源继续由 static 提供。
如果以后在 Nginx/CDN 上新增直接文件映射或缓存规则，必须同步实施相同下载控制，不能绕过应用检查。已有 CDN 缓存应另行检查。
沿用 FileResponse 与有界流式读取，支持 GET、HEAD 和单段 Range；不引入 Nginx 内部文件发送架构。

## 错误与审计

API 输入、路径、数据库和未知异常均返回简短 JSON，不返回绝对路径、数据库原始异常或 HTML 调试页。
API 404/400 等框架错误也会规范化。全站 DEBUG 设置保持原样；非 API 页面的调试风险仍需单独整改。
API 响应携带 `X-Request-ID` 和 `Cache-Control: private, no-store`。

审计文件为项目根目录下 `.api_security_logs/api_audit.log`，日志目录权限须为 0700；单文件 10 MiB，保留 5 份轮转备份。记录时间、请求 ID、方法、路径、IP、身份摘要、等级、状态、响应生成耗时及声明内容长度；不记录原始 API Key、查询串、查询正文或下载内容。受控服务端错误日志可能包含堆栈，仅允许运维访问。
`declared_bytes` 是响应声明长度，不代表客户端实际收到的字节数；请求日志也不声称客户端已完成下载。
Nginx 常规访问日志记录请求方法、路径、状态、实际传输字节数和请求编号，不记录查询串及 Referer。uWSGI 请求日志使用 PATH_INFO，避免记录结果链接中的随机标记。错误日志仅供运维排查。

## 回归检查

使用隔离设置运行，无生产配置凭据，不创建或访问生产数据库：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python -B -m django test api browse tools --settings=api.security_test_settings
```

覆盖公开/可信访问分页、IP 伪造、空字节、内部异常隐藏、JSON/TE 预算、文件内容与 Range、跨进程限流和并发、下载路由、结果访问隔离、自动结果链接、导出预算、HTTPS/代理入口及审计脱敏。

此文件记录当前单服务器方案。多主机部署时，必须更换真正跨主机的原子限流存储。
