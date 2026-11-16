# 无情老小儿 · FastAPI + Vue

FastAPI + Vue 3 博客，公开站参考 Casper / Prism 风格，后台提供登录、文章编辑、草稿与发布、标签、图片、站点设置及可选管理员邮件。界面、错误提示和系统邮件使用英文，文章内容及博客名称保留原文。

项目使用独立的新数据库。提供的 Ghost 数据库和其他项目仅作为设计参考，不包含数据导入或旧库兼容功能。

## 本地开发

要求 Python 3.12、Node.js 22。首次安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
Copy-Item .env.example .env
Push-Location frontend
npm ci
Pop-Location
```

创建管理员时交互输入密码，至少 12 个字符；没有内置默认密码：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m app.cli create-admin --username xionzhi
```

在两个终端分别启动后端和前端：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log --no-server-header
```

```powershell
cd frontend
npm run dev
```

- 博客：[http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- 后台：[http://127.0.0.1:5173/workspace/login](http://127.0.0.1:5173/workspace/login)
- API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Vite 将 API 和图片等请求代理到后端。开发时直接运行源码，不需要生产构建。默认数据库位于 `data/dev/blog.sqlite3`，图片位于 `data/dev/images/`；均不提交到源码仓库。

Linux 上原生运行后端：

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock.txt
cp .env.example .env
PYTHONPATH=backend .venv/bin/python -m app.cli create-admin --username xionzhi
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

## 工程结构

```text
backend/
  app/
    main.py                 # ASGI 入口
    application.py          # 生命周期、中间件和路由装配
    api.py                  # API 路由注册
    core/                   # 配置、依赖、安全和错误处理
    common/                 # ORM Base、数据库会话和公共契约
    modules/
      auth/                 # 登录、会话和密码找回
      post/                 # 文章、编辑冲突检测和内容处理
      tag/                  # 标签
      site/                 # 站点设置和导航
      mail/                 # SMTP 配置、发送和通知
      media/                # 图片校验和存储
      publishing/           # SEO、RSS 和 sitemap
      health/               # 健康检查
  migrations/               # Alembic 版本文件
frontend/src/
  api/                      # 类型化 API 和统一 HTTP transport
  stores/                   # 会话、站点和通知状态
  composables/              # 编辑器、导航和异步任务生命周期
  components/               # 展示组件及编辑器面板
  views/                    # 页面
  utils/                    # 纯格式化函数
```

后端参考 aimax_walmart 与 Netflix Dispatch，按业务组织 `models.py`、`service.py`、`views.py`，通过类型化依赖注入请求会话。业务查询和写入使用 SQLAlchemy 2 ORM；SQLite 连接参数及事务控制集中在数据库基础设施中。Alembic 管理表结构，应用启动时自动升级。

业务服务与 HTTP 层分离；API 使用输入、响应模型和稳定的英文错误契约。请求数据库事务在响应发送前提交或回滚，文章版本校验防止并发编辑覆盖。应用模块导入与应用装配不会创建数据库。

管理员密码使用 scrypt 哈希，会话使用 HttpOnly Cookie，并提供 CSRF、来源校验和登录限流。前端请求、共享状态与组件生命周期逻辑分别放在 API、store 和 composable 中。

需要运行后端测试与代码检查时，额外安装 `backend/requirements-dev.txt`；测试所用的 HTTP 客户端不进入生产镜像。检查与格式化：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
cd frontend
npm run format:check
```

不自动运行前端生产构建；需要时手动执行 `npm run build`。

运行 Vite 开发服务器后，可打开 `http://127.0.0.1:5173/tests/interactions.html` 执行前端交互回归检查。测试使用内存中的模拟请求，验证旧请求取消、刷新保留内容、失败重试、离开页面后的响应处理，以及嵌套弹窗的滚动锁恢复，不写入博客数据。测试页面不会进入生产构建。

## Linux Docker 部署

一台 Linux 主机即可运行整个项目：宿主机安装 [Docker Engine 与 Compose 插件](https://docs.docker.com/engine/install/)、Nginx 和 logrotate，Nginx 使用现有的 HTTPS 证书。域名的 A/AAAA 记录需要指向该主机；只有提供 IPv6 服务时才保留 AAAA。公网仅开放 80/443，SSH 限制为管理来源，应用 8000 端口只绑定本机。

Dockerfile 在你手动构建时编译 Vue，最终镜像以 UID/GID 10001 的非 root 用户运行，由 FastAPI 提供前端、API 和图片。主机不需要额外安装 Node.js 或 Python，也不需要 MySQL、Redis 或第三方统计服务。Compose 将生产数据独立保存到 `data/production/`。

### 准备源码和已有内容

把源码放到服务器目录，例如 `/opt/ghost_blog`，后续命令都在这个目录执行。不要上传 Windows 的 `.venv`、`node_modules`、缓存目录或开发 `.env`。数据库、上传图片和备份已被 Git 忽略，单独拉取源码不会带上本地文章。

如果需要保留当前本项目中的文章、标签、站点设置和图片，暂停编辑与上传，在 Windows 项目根目录生成一致性快照。`data/deployment` 必须是新目录，防止覆盖已有备份：

```powershell
$env:PYTHONPATH='backend'
New-Item -ItemType Directory -Path .\data\deployment -ErrorAction Stop
.\.venv\Scripts\python.exe -m app.cli backup .\data\deployment\blog.sqlite3
if ($LASTEXITCODE -ne 0) { throw 'Database backup failed.' }
Copy-Item -LiteralPath .\data\dev\images -Destination .\data\deployment\images -Recurse -ErrorAction Stop
tar -czf .\data\blog-data.tar.gz -C .\data\deployment blog.sqlite3 images
```

通过 SSH/SFTP 等私有通道把 `data/blog-data.tar.gz` 传到服务器。它包含管理员密码哈希等私有数据，不要提交到 Git 或放进公开下载目录。运行中的 SQLite 可能还在 `-wal` 文件中写数据，不能只复制主数据库文件；上述命令使用 SQLite 备份接口取得完整快照。这是本项目数据的部署备份，不涉及 Ghost 导入或旧库兼容。

首次部署时，在**空的** `data/production/` 中解压：

```bash
mkdir -p data/production
tar -xzf /path/to/blog-data.tar.gz -C data/production
sudo chown -R 10001:10001 data/production
sudo chmod 0700 data/production
sudo chmod 0600 data/production/blog.sqlite3
```

如需从空站开始，跳过解压，只创建 `data/production/images` 并设置 UID/GID 10001 的所有权。应用启动时会自动运行 Alembic，创建独立的新数据库。

### 配置与启动

```bash
cp .env.production.example .env
chmod 0600 .env
```

在 `.env` 填写正式域名，例如：

```dotenv
BLOG_URL=https://xionzhi.com
BLOG_SECURE_COOKIES=true
BLOG_ALLOWED_ORIGINS=https://xionzhi.com
```

SMTP 可留空，登录、写作和站内统计不依赖邮件。先验证配置并手动构建；在服务对公网开放前设置生产密码。`--reset-password` 对已有账号重设密码并撤销会话，也可以创建尚不存在的账号：

```bash
docker compose config --quiet
docker compose build --pull
docker compose run --rm --no-deps blog python -m app.cli create-admin --username xionzhi --reset-password
docker compose up -d --wait
docker compose ps
curl --fail http://127.0.0.1:8000/api/health
```

生产密码在服务器终端交互输入，不使用聊天中创建的测试密码。部署时的 CPU/内存限制是运行上限；构建前端和安装依赖还需要额外可用内存及镜像缓存空间。若服务器访问 npm、PyPI 或镜像仓库很慢，可在相同目标架构的构建机生成镜像后传到服务器。

生产配置必须启用 HTTPS 与安全 Cookie，否则应用拒绝启动。生产环境关闭 `/docs`、`/redoc`、`/openapi.json`，验证 Host，后台位于 `/workspace/login`，所有管理接口均验证服务端会话和 CSRF。生产 Cookie 使用 `__Host-` 前缀；密码使用带工作参数的 scrypt。

### HTTPS 反向代理

参考 `deploy/nginx.conf.example`，把所有 `xxx.com` 换为实际域名，并保留现有证书路径和 ACME webroot。配置中的 `limit_req_zone` 必须位于 `http` 上下文；不要把整个示例直接嵌入已有的 `server` 中。`http2 on` 需要 Nginx 1.25.1 或更新版本，较旧版本需按其支持的语法配置。

`BLOG_TRUSTED_PROXY_NETWORKS` 默认留空，应用不相信传入的代理头。**上线前必须确认并设置代理来源**，否则应用限流会把经过代理的访客当作同一来源。宿主机 Nginx 通常对应 Docker 网络的 bridge gateway，可用 `docker network inspect <project>_default` 查看 gateway，再核对实际网络路径并填写其 `/32` 地址。原生运行可填写 `127.0.0.1/32,::1/128`。不要设置 `0.0.0.0/0` 或 `::/0`。更改 `.env` 后执行 `docker compose up -d --wait` 重建容器配置。

示例 Nginx 覆盖外部传入的代理头，并对总请求、每个来源和登录请求分别限流。如果 Nginx 本身位于 CDN 或其他反向代理之后，还需只信任该上游提供的来源地址，不能直接相信任意公网 `X-Forwarded-For`。如果现有 Nginx 也在容器里，`127.0.0.1:8000` 的宿主机方案需要调整为共享 Docker 网络中的服务地址。

```bash
sudo nginx -t
sudo systemctl reload nginx
curl --fail https://xionzhi.com/api/health
```

最后通过正式 HTTPS 地址检查首页、文章、图片、后台登录、草稿保存与匿名统计，并在浏览器网络面板确认资源来自本站。安装下文的日志轮转，配置数据库和图片的定期异机备份，验证一次恢复流程。先验证新站再切换现有站点反向代理，保留旧服务作为切换回退。应用和反向代理的限流不能替代网络边缘对大规模 DDoS 的防护。

当前开发机没有 Docker 和 Nginx，尚未执行镜像构建、容器运行或 `nginx -t`；这些是部署到 Linux 时仍须完成的验证。

## 公网日志与资源上限

- Uvicorn 和 Nginx 默认不逐条记录访问日志；常见扫描路径、无效请求和 4xx 不打印业务异常堆栈。
- 应用警告及错误共用每进程每分钟 10 条的预算，超出部分计数，下一窗口附带抑制数量。每行最多 2 KB；不打印请求体、查询参数、凭据或异常中的原始业务数据。
- Compose 使用 Docker `local` 日志驱动：每个文件 10 MB、最多 3 个文件、压缩轮转，缓冲区 1 MB；日志积压时丢弃缓冲区溢出部分，不阻塞请求。
- Nginx 的限流拒绝记录使用 notice 级别，错误日志阈值为 warn，避免每次被拒绝的请求写日志。`deploy/logrotate.conf` 对博客专用错误日志按 10 MB 轮转，保留两个旧文件。需在服务器安装并按分钟检查大小，轮转间隔内允许短暂超出阈值。
- 容器使用只读根文件系统、64 MB 临时目录及进程、内存、CPU 上限，只有应用数据卷可持久写入。

安装博客专用 Nginx 日志轮转，不修改其他站点的日志配置：

```bash
sudo install -d /etc/ghost-blog
sudo install -m 0644 deploy/logrotate.conf /etc/ghost-blog/logrotate.conf
# 在 root crontab 中添加以下一行；使用独立 state 文件。
* * * * * /usr/sbin/logrotate -s /var/lib/logrotate/ghost-blog.status /etc/ghost-blog/logrotate.conf
```

## 匿名浏览统计

后台 `/workspace/analytics` 提供今日浏览量、今日访客估算、每日趋势和热门页面。客户端只在公开页面可见时提交事件，忽略 query/hash；后台拒绝不存在的页面，并过滤常见机器人、预取、DNT/GPC 和已登录管理员。

访客使用浏览器每天新建的随机标识，不使用 IP 或 User-Agent 指纹。服务端只保存当日标识的哈希用于去重，每小时清理前一天的标识。聚合数据默认保留 90 天，单日最多接收 50,000 次有效浏览，避免被滥用写入无界数据。可通过 `BLOG_ANALYTICS_ENABLED`、`BLOG_ANALYTICS_RETENTION_DAYS`、`BLOG_ANALYTICS_MAX_DAILY_VIEWS` 调整。

这些是浏览器端估算：禁用脚本、拦截统计、浏览器存储受限或伪装成浏览器的机器人都会影响准确度；不作为计费或完整安全审计依据。平均每日访客包含零访问日期，不表示跨天去重人数。统计不会发送真实邮件。

## 弱网访问

页面路由按需加载，归档每次加载 25 条摘要；列表数据库查询不读取正文和 HTML。图片原生懒加载并异步解码，代码块接近视口时再加载高亮语言；高亮模块加载失败时仍保留可读代码。

文本响应启用 gzip；图片、字体和 Range 请求跳过重复压缩。生产环境的带指纹资源与 UUID 图片长期缓存，固定名称图片短期缓存并支持 ETag、Last-Modified、304 和字节范围读取。公开 API 使用短期缓存，后台和会话数据禁止缓存。开发环境公开数据重新验证，方便手动实测。

站点样式、Open Sans / Merriweather 字体、图标和代码高亮均从本站提供，不请求 Google Fonts 或第三方脚本 CDN。中文使用设备已有字体，不额外下载大型中文字库。字体许可证随源码和生产镜像提供。文章中的参考链接不属于自动加载资源；作者手动填写的外部图片或音视频 URL 仍会发起外部请求，需要先上传为本站资源才能消除依赖。

API 在 20 秒无读取进展时超时；收到数据分块会重置超时。读取请求遇到网络中断或 408/502/503/504 时最多重试一次并退避，写入请求不自动重试，避免重复发布。取消的搜索和页面请求不会重试。当前未构建前端生产产物；构建仍由用户手动执行。

## 管理员邮件

SMTP 默认关闭，不影响登录和写作。确定服务商后填写 `.env`，无需把凭据发到聊天中：

```dotenv
BLOG_SMTP_HOST=smtp.your-provider.example
BLOG_SMTP_PORT=587
BLOG_SMTP_SECURITY=starttls
BLOG_SMTP_USERNAME=your-account
BLOG_SMTP_PASSWORD=your-secret
BLOG_MAIL_FROM=blog@example.com
```

仅支持加密 SMTP：`starttls`（通常 587）或 `ssl`（通常 465）。重启后绑定管理员找回邮箱：

```bash
docker compose exec blog python -m app.cli set-admin-email --username xionzhi --email you@example.com
```

邮件启用后登录页提供密码找回入口。找回令牌以哈希形式保存，15 分钟过期且只能使用一次；密码修改后使已有会话失效并发送通知。开发测试模拟邮件传输，不发送真实邮件。

## 备份与密码重置

运行中使用 SQLite 一致性备份命令，图片目录独立备份：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m app.cli backup .\data\blog-backup.sqlite3
```

管理员可在可信服务器终端重置密码，该账号已有会话会失效：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m app.cli create-admin --username xionzhi --reset-password
```

生产环境在容器内执行对应命令，备份目标必须位于可写的数据卷，使用新的文件名，例如：

```bash
docker compose exec blog python -m app.cli backup /app/data/backup-2026-11-13.sqlite3
```

同时备份图片目录；恢复时停止容器，在保留现状副本后，把完整快照和对应图片放入 `data/production/` 并恢复 UID/GID 10001 所有权，再启动并验证。项目约定见 `AGENTS.md`。
