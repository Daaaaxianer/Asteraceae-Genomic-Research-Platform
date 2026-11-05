# AGRP API 限流、IP 白名单与 API Key 配置说明（操作员版）

> 2026-10-29 安全加固更新：现行入口、可信代理链、跨 worker 计数、查询预算与日志规则见 [SECURITY.md](SECURITY.md)。下文旧的“无条件优先信任 CF 请求头”和“LocMemCache 限流”描述已被替换。合作访问额度配置方法继续适用。生产 API 经可信代理与 Cloudflare，以 HTTPS 访问；public 分页上限 100，`limit=all/none/0` 也受限；JSON 单文件和 TE 单次选择合计默认最多 16 MiB，超过返回 413。

本文档用于维护 AGRP / Asteraceae 网站的公开 API 访问限制与合作团队高通量访问配置。主要面向服务器操作员，不是面向普通 API 用户的公开文档。

## 1. 基本信息

项目路径：

```bash
/wangjp/Asteraceae/Asteraceae
```

关键文件：

```text
/wangjp/Asteraceae/Asteraceae/LGBP/settings.py
/wangjp/Asteraceae/Asteraceae/api/access_control.py
/wangjp/Asteraceae/Asteraceae/api/throttles.py
/wangjp/Asteraceae/Asteraceae/api/middleware.py
/wangjp/Asteraceae/Asteraceae/api/views.py
/wangjp/Asteraceae/Asteraceae/templates/api_documentation.html
```

运行检查命令时必须带：

```bash
PYTHONNOUSERSITE=1
```

标准检查命令：

```bash
cd /wangjp/Asteraceae/Asteraceae
PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python manage.py check
```

正常结果应为：

```text
System check identified no issues
```

每次修改 `settings.py`、`api/throttles.py`、`api/middleware.py`、`api/access_control.py`、`api/views.py` 后，都需要重启宝塔 Python 项目 `Asteraceae`。

---

## 2. 当前访问等级设计

API 访问分为三个等级：

| 等级 | 适用对象 | 识别方式 |
|---|---|---|
| `public` | 普通公开用户 | 默认按真实 IP 识别 |
| `partner` | 合作团队 | 有效 API Key |
| `trusted` | 高信任合作团队或固定服务器 | IP 白名单，或 API Key 配置为 `trusted` |

普通用户不需要登录、不需要 key。合作团队可以通过固定 IP 或 API Key 获得更高额度。

---

## 3. 当前默认限流规则

### 3.1 public 普通用户

| 范围 | 限制 |
|---|---|
| `/api/download/` | 每 IP 每分钟 5 次 |
| `/api/files/` | 每 IP 每分钟 60 次 |
| `/api/genomics/`、`/api/genosyn/`、`/api/multiomics/` | 每 IP 每分钟 120 次 |
| `/api/ping/` | 每 IP 每分钟 60 次 |
| 下载并发 | 每 IP 同时最多 2 个下载请求 |
| 查询 `limit` | 默认 20，最大 100 |

### 3.2 partner 合作用户

| 范围 | 限制 |
|---|---|
| `/api/download/` | 每分钟 60 次 |
| `/api/files/` | 每分钟 600 次 |
| 查询类 API | 每分钟 1000 次 |
| `/api/ping/` | 每分钟 120 次 |
| 下载并发 | 同时最多 10 个下载请求 |
| 查询 `limit` | 最大 1000 |

### 3.3 trusted 高信任用户

| 范围 | 限制 |
|---|---|
| `/api/download/` | 每分钟 120 次 |
| `/api/files/` | 每分钟 1200 次 |
| 查询类 API | 每分钟 2000 次 |
| `/api/ping/` | 每分钟 300 次 |
| 下载并发 | 同时最多 20 个下载请求 |
| 查询 `limit` | 最大 2000 |

---

## 4. IP 是如何识别的

系统优先按以下顺序识别用户真实 IP：

```text
1. HTTP_CF_CONNECTING_IP
2. HTTP_X_FORWARDED_FOR 的第一个 IP
3. REMOTE_ADDR
```

因为网站前面有 Cloudflare，所以优先使用 `CF-Connecting-IP`。如果不这样处理，Django 可能只能看到 Cloudflare 节点 IP，容易把多个真实用户误判成同一个 IP。

### 4.1 让用户查看 AGRP 实际识别到的公网 IP

建议新增并启用：

```text
/api/whoami/
```

用户可以在浏览器访问：

```text
https://asteraceae.cgrpoee.top/api/whoami/
```

但浏览器可能优先走 IPv6。用于申请 IPv4 白名单时，应要求用户在“实际访问 AGRP 的服务器或计算节点”上使用命令行强制 IPv4：

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

典型返回：

```json
{
  "status": "ok",
  "detected_ip": "203.0.113.10",
  "ip_source": "CF-Connecting-IP",
  "is_private_or_local": false,
  "message": "This is the client IP address detected by the AGRP API for this request."
}
```

其中：

```text
detected_ip：AGRP API 实际识别到的当前请求来源 IP
ip_source：IP 来自哪个请求头，Cloudflare 环境下通常是 CF-Connecting-IP
is_private_or_local：是否为内网/本机/链路本地地址
```

如果合作团队申请 IPv4 白名单，应让他们从“实际下载数据的服务器或计算节点”执行 `curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"`，然后把返回的 `detected_ip` 发给 AGRP 团队。不要让他们从个人电脑、宿舍网、公共 Wi-Fi 或手机热点随便查一个 IP 来申请白名单。

### 4.2 校园网公网 IP 的处理原则

校园网、公用 Wi-Fi、宿舍网、手机热点、运营商动态宽带，通常可能是多人共享同一个公网出口 IP。把这类 IP 加入白名单后，可能导致同一出口下的其他无关用户也获得高额度访问权限。

因此：

```text
固定服务器 / 固定计算节点 IP：可以考虑 IP 白名单
校园网公共出口 IP：一般不建议加入白名单
公网 IP 不稳定或多人共享：优先使用 API Key
全量大规模下载：优先提供 bulk package 或 manifest
```

操作员在收到 IP 白名单申请时，应先确认：

```text
1. 该 IP 是否来自固定服务器或稳定计算环境；
2. 该 IP 是否为多人共享的校园网/公共网络出口；
3. 对方是否真的需要 IP 白名单，还是 API Key 更合适；
4. 是否已经和 AGRP 团队沟通并获得同意。
```

---

## 5. 添加 IP 白名单

适用场景：合作团队有固定服务器 IP、固定机构服务器出口 IP，或者稳定计算集群出口 IP。

在添加白名单前，必须先确认对方已经和 AGRP 团队取得联系，并说明访问目的、数据范围、预计请求量、使用周期和联系人信息。不要直接根据一条口头 IP 或普通校园网公网 IP 放行。

打开配置文件：

```bash
cd /wangjp/Asteraceae/Asteraceae
vim LGBP/settings.py
```

找到：

```python
AGRP_API_TRUSTED_IPS = set()
```

改成：

```python
AGRP_API_TRUSTED_IPS = {
    '203.0.113.10',      # 单个固定 IP
}
```

如果对方提供的是网段，例如 `203.0.113.0/24`，可以这样写：

```python
AGRP_API_TRUSTED_IPS = {
    '203.0.113.10',
    '203.0.113.0/24',
}
```

保存后检查：

```bash
cd /wangjp/Asteraceae/Asteraceae
PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python manage.py check
```

检查无误后，重启宝塔 Python 项目 `Asteraceae`。

### 5.1 验证 IP 白名单是否生效

先让合作团队从他们的服务器执行 IPv4 查询，确认返回的 `detected_ip` 与白名单配置一致：

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

然后从同一台服务器访问：

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000"
```

如果返回 JSON 中显示：

```json
"limit": 1000
```

说明已经走高权限访问。普通 public 用户请求 `limit=1000` 时会被压到 `limit=100`。

### 5.1.1 告知用户使用 `-4`

如果加入白名单的是 IPv4 地址，操作员在通知用户“白名单已添加”时，必须同时说明：

```text
AGRP 白名单匹配的是你提交的 IPv4 地址。后续用 curl 进行高通量查询或下载时，请在命令中加入 -4，确保请求实际从该 IPv4 发出；否则系统或网络可能自动选择 IPv6，导致白名单不生效。
```

可以直接给用户这样的示例：

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000"

curl -4 -L -o Aann.cds "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

注意：

```text
-4 不是 AGRP API 参数，而是 curl 的 IPv4 强制选项。
只有 IPv4 白名单访问需要特别提醒用户使用 -4。
如果用户使用的是 API Key，一般不需要加 -4，只需要带 X-AGRP-API-Key 请求头。
浏览器访问无法方便地加 -4，因此浏览器或个人电脑用户通常更适合 API Key。
```

---

## 5.2 高通量访问申请建议收集的信息

当用户或合作团队申请高通量访问时，建议要求他们提供：

```text
1. 联系人姓名、单位、邮箱；
2. 使用目的，例如批量下载基因组文件、自动化查询注释数据等；
3. 预计访问的数据范围；
4. 预计请求频率或下载规模；
5. 访问方式：固定服务器 IP、API Key、bulk package / manifest；
6. 如果申请 IPv4 白名单，需要提供从实际访问服务器执行 `curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"` 返回的 `detected_ip`；
7. 计划使用时间，例如临时测试、1 周、1 个月、长期合作。
```

推荐判断：

```text
固定服务器且下载量中等：可以使用 IP 白名单
校园网/公共网络/动态 IP：优先 API Key
全量数据镜像：优先 bulk package 或 manifest
不清楚访问规模：先给 partner API Key，暂不直接 trusted
```

---

## 5.3 `/api/whoami/` 接口部署说明

本次建议在 `api/views.py` 中增加 `whoami` 视图，并在 `api/urls.py` 中增加路由：

```python
path('whoami/', views.whoami, name='whoami'),
```

部署后，用户访问：

```text
https://asteraceae.cgrpoee.top/api/whoami/
```

可以看到 AGRP API 当前识别到的请求来源 IP。这个接口不发放权限，只用于帮助用户和操作员确认 IP。用于 IPv4 白名单申请时，应优先让用户执行 `curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"`，不要只依赖浏览器结果。

建议保留该接口，因为它可以减少用户申请白名单时填错 IP 的情况。

---

## 6. 创建 API Key

适用场景：合作团队没有固定 IP，或者希望临时授予高通量访问权限。

API Key 的使用方式为请求头：

```text
X-AGRP-API-Key: agrp_xxxxxxxxx
```

不要把 API Key 放进 URL，例如不要使用 `?api_key=xxx`。URL 更容易进入浏览器历史、访问日志和分享链接。

### 6.1 生成 API Key 和 hash

在服务器执行：

```bash
PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python - <<'PY'
import secrets
import hashlib

key = "agrp_" + secrets.token_urlsafe(32)
key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()

print("API key, send this to collaborator:")
print(key)
print()
print("SHA-256 hash, paste this into settings.py:")
print(key_hash)
PY
```

输出中会有两部分：

```text
API key, send this to collaborator:
agrp_xxxxxxxxxxxxxxxxxxxxxxxxx

SHA-256 hash, paste this into settings.py:
一长串 hash
```

操作原则：

```text
原始 API key：只发给合作团队，不写进代码。
hash：写进 settings.py，用于服务端验证。
```

---

## 7. 配置 API Key

打开：

```bash
cd /wangjp/Asteraceae/Asteraceae
vim LGBP/settings.py
```

找到：

```python
AGRP_API_KEY_HASHES = {}
```

配置为：

```python
AGRP_API_KEY_HASHES = {
    '这里粘贴刚才生成的SHA256_HASH': {
        'name': 'Example Lab',
        'tier': 'partner',
        'enabled': True,
    },
}
```

如果要给更高权限，可以把 `tier` 改成 `trusted`：

```python
AGRP_API_KEY_HASHES = {
    '这里粘贴刚才生成的SHA256_HASH': {
        'name': 'Important Collaborator',
        'tier': 'trusted',
        'enabled': True,
    },
}
```

多个团队示例：

```python
AGRP_API_KEY_HASHES = {
    '第一个团队的hash': {
        'name': 'Lab A',
        'tier': 'partner',
        'enabled': True,
    },
    '第二个团队的hash': {
        'name': 'Lab B',
        'tier': 'trusted',
        'enabled': True,
    },
}
```

保存后检查：

```bash
cd /wangjp/Asteraceae/Asteraceae
PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python manage.py check
```

检查无误后，重启宝塔 Python 项目 `Asteraceae`。

---

## 8. 合作团队如何使用 API Key

查询示例：

```bash
curl -H "X-AGRP-API-Key: agrp_xxxxxxxxx"   "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000"
```

下载示例：

```bash
curl -H "X-AGRP-API-Key: agrp_xxxxxxxxx"   -L -o Aann.cds   "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

Python 示例：

```python
import requests

headers = {
    "X-AGRP-API-Key": "agrp_xxxxxxxxx"
}

url = "https://asteraceae.cgrpoee.top/api/genomics/kegg/"
params = {
    "species": "Aann",
    "limit": 1000,
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
```

---

## 9. 验证 API Key 是否生效

用带 key 的请求测试：

```bash
curl -H "X-AGRP-API-Key: agrp_xxxxxxxxx"   -s "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000" | head
```

如果返回 JSON 中有：

```json
"limit": 1000
```

说明该 key 正在使用 `partner` 或 `trusted` 高权限。

再用不带 key 的请求测试：

```bash
curl -s "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000" | head
```

普通 public 用户应被压到：

```json
"limit": 100
```

---

## 10. 禁用或删除 API Key

### 10.1 临时禁用

```python
AGRP_API_KEY_HASHES = {
    '某个团队的hash': {
        'name': 'Example Lab',
        'tier': 'partner',
        'enabled': False,
    },
}
```

### 10.2 彻底删除

直接从 `AGRP_API_KEY_HASHES` 中删除对应 hash。

修改后执行：

```bash
cd /wangjp/Asteraceae/Asteraceae
PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python manage.py check
```

检查无误后重启宝塔 Python 项目 `Asteraceae`。

---

## 11. 修改限流额度

额度集中配置在：

```bash
/wangjp/Asteraceae/Asteraceae/LGBP/settings.py
```

相关配置：

```python
AGRP_API_RATE_LIMITS = {
    'public': {
        'download': (5, 60),
        'files': (60, 60),
        'query': (120, 60),
        'ping': (60, 60),
    },
    'partner': {
        'download': (60, 60),
        'files': (600, 60),
        'query': (1000, 60),
        'ping': (120, 60),
    },
    'trusted': {
        'download': (120, 60),
        'files': (1200, 60),
        'query': (2000, 60),
        'ping': (300, 60),
    },
}

AGRP_API_DOWNLOAD_CONCURRENCY_LIMITS = {
    'public': 2,
    'partner': 10,
    'trusted': 20,
}

AGRP_API_QUERY_MAX_LIMITS = {
    'public': 100,
    'partner': 1000,
    'trusted': 2000,
}
```

含义：

```python
'download': (5, 60)
```

表示 60 秒内最多 5 次。

修改后必须：

```bash
cd /wangjp/Asteraceae/Asteraceae
PYTHONNOUSERSITE=1 /www/server/pyporject_evn/Asteraceae_venv/bin/python manage.py check
```

然后重启宝塔 Python 项目 `Asteraceae`。

---

## 12. 常用测试命令

### 12.1 测普通下载限流

```bash
for i in {1..8}; do
  curl -s -o /dev/null -w "%{http_code}
" "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=lens"
done
```

正常情况下，连续高频请求后会出现：

```text
429
```

### 12.2 测普通查询 limit 上限

```bash
curl -s "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=999999" | head
```

普通用户应显示：

```json
"limit": 100
```

### 12.3 测 API Key 高权限 limit

```bash
curl -H "X-AGRP-API-Key: agrp_xxxxxxxxx"   -s "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000" | head
```

`partner` 用户应显示：

```json
"limit": 1000
```

---

## 13. 注意事项

1. 当前默认使用 `LocMemCache`，多 uWSGI worker 之间计数不是完全共享，所以限流不是全局绝对精确。当前阶段可接受；如果访问量明显增大，建议换 Redis 或 Nginx / Cloudflare 前置限流。
2. 不要把原始 API Key 写进 `settings.py`，只写 SHA-256 hash。
3. 不要把校园网、公共 Wi-Fi、宿舍网、手机热点这类共享公网 IP 轻易加入 IP 白名单；这类场景优先使用 API Key。
4. 如果给用户加入的是 IPv4 白名单，通知用户时必须说明后续 `curl` 请求要使用 `-4`，否则请求可能走 IPv6 而无法命中白名单。
5. 不要让合作团队把 key 放进 URL，只能放在 `X-AGRP-API-Key` 请求头。
6. 如果是全站级大批量下载，优先提供 bulk package 或 manifest 文件，不建议让对方用 API 高频循环下载全部文件。
7. 修改配置后必须 `manage.py check`，并重启宝塔 Python 项目。
8. 回滚前要确认备份文件时间，避免回滚到过旧版本。

---

## 14. 推荐操作流程

### 添加 IP 白名单

```text
收到合作团队固定 IP
→ 先确认对方已联系 AGRP 团队并说明用途
→ 让对方从实际下载服务器执行 curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
→ 确认 detected_ip 不是校园网/公共网络共享出口
→ 修改 AGRP_API_TRUSTED_IPS
→ manage.py check
→ 重启宝塔 Python 项目
→ 通知对方：后续 curl 高通量访问要加 -4，确保走已登记的 IPv4
→ 让对方用 curl -4 测试 limit=1000 或下载接口
```

### 发放 API Key

```text
确认对方不适合 IP 白名单或 IP 不固定
→ 生成 API Key 和 hash
→ 把原始 key 发给合作团队
→ 把 hash 写入 AGRP_API_KEY_HASHES
→ manage.py check
→ 重启宝塔 Python 项目
→ 用 X-AGRP-API-Key 测试
```

### 禁用 API Key

```text
enabled 改为 False 或删除 hash
→ manage.py check
→ 重启宝塔 Python 项目
→ 确认该 key 不再获得高权限
```
