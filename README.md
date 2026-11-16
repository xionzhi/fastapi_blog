# 无情老小儿 · FastAPI + Vue

基于 FastAPI、Vue 3 和 SQLite 的个人博客，面向 Linux 单实例部署。

- Markdown / HTML 文章编辑、草稿、发布、标签和图片上传。
- 全文搜索、归档、RSS 和 sitemap。
- 站点设置、匿名浏览统计，以及可选的管理员邮件找回密码。
- 原生 JSON 内容导入导出，图片文件单独复制。

管理界面及系统提示使用英文，文章内容保持原文。项目使用独立数据库，默认不包含文章、图片或管理员账号。

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
.\.venv\Scripts\python.exe -m app.cli create-admin --username admin
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
PYTHONPATH=backend .venv/bin/python -m app.cli create-admin --username admin
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

## 工程结构与检查

```text
backend/
  app/
    main.py                 # ASGI 入口
    application.py          # 生命周期、中间件和路由装配
    api.py                  # API 路由注册
    core/                   # 配置、依赖、安全和错误处理
    common/                 # ORM Base、数据库会话和公共契约
    modules/                # 文章、标签、账号、媒体、统计等业务模块
  migrations/               # Alembic 版本文件
  tests/                    # 后端功能与安全回归检查
frontend/src/
  api/                      # 类型化 API 和统一 HTTP transport
  stores/                   # 会话、站点和通知状态
  composables/              # 编辑器、导航和异步任务生命周期
  components/               # 展示组件及编辑器面板
  views/                    # 页面
  utils/                    # 纯格式化函数
```

后端按业务组织 `models.py`、`service.py` 和 `views.py`，业务读写使用 SQLAlchemy 2 ORM。Alembic 管理表结构，应用启动时自动升级。前端请求、共享状态及生命周期逻辑分别位于 `api/`、`stores/` 和 `composables/`。贡献代码时遵循 [AGENTS.md](AGENTS.md)。

安装开发依赖后运行测试和格式检查：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\ruff.exe format --check backend
cd frontend
npm run format:check
```

生产构建手动执行 `npm run build`。

Vite 启动后，访问 `http://127.0.0.1:5173/tests/interactions.html` 可执行异步请求和弹窗交互检查。检查使用模拟请求，不写入博客数据，不进入生产构建。

## Linux Docker 部署

一台 Linux 主机即可运行整个项目：宿主机安装 [Docker Engine 与 Compose 插件](https://docs.docker.com/engine/install/)、Nginx 和 logrotate，Nginx 使用现有的 HTTPS 证书。域名的 A/AAAA 记录需要指向该主机；只有提供 IPv6 服务时才保留 AAAA。公网仅开放 80/443，SSH 限制为管理来源，应用 8000 端口只绑定本机。

Docker 构建会编译 Vue，最终镜像以 UID/GID 10001 的非 root 用户运行，由 FastAPI 提供前端、API 和图片。宿主机无需安装 Node.js 或 Python。生产数据保存在 `data/production/`，通过卷挂载持久化。

### 准备源码和已有内容

把源码放到服务器目录，例如 `/opt/ghost_blog`，后续命令都在这个目录执行。不要上传 Windows 的 `.venv`、`node_modules`、缓存目录或开发 `.env`。数据库、上传图片和备份已被 Git 忽略，单独拉取源码不会带上本地文章。

首次部署先准备独立的数据目录：

```bash
mkdir -p data/production/images
sudo chown -R 10001:10001 data/production
sudo chmod 0700 data/production
```

首次启动自动创建数据库。迁移内容见下文“JSON 数据迁移”；完整数据库恢复见“备份与密码重置”。

### 配置与启动

```bash
cp .env.production.example .env
chmod 0600 .env
```

在 `.env` 填写正式域名，例如：

```dotenv
BLOG_URL=https://blog.example.com
BLOG_SECURE_COOKIES=true
BLOG_ALLOWED_ORIGINS=https://blog.example.com
```

SMTP 默认关闭。服务对公网开放前创建管理员并设置密码。

如果构建时 PyPI 下载较慢，可以在服务器 `.env` 中设置清华镜像，仅影响 Docker 构建期间的 pip 安装：

```dotenv
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

地址使用 HTTPS，并保留 `/simple`，参见[清华镜像说明](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)。不设置时使用官方 PyPI，也可以仅为一次构建传参：`docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple blog`。修改宿主机的 pip 配置不会自动改变镜像构建中的 pip 配置。

```bash
docker compose config --quiet
docker compose build --pull
docker compose run --rm --no-deps blog python -m app.cli create-admin --username admin
docker compose up -d --wait
docker compose ps
curl --fail http://127.0.0.1:8000/api/health
```

密码在服务器终端交互输入，不应使用开发或测试密码。构建需要额外可用内存及镜像缓存空间；也可在相同目标架构的构建机生成镜像后传到服务器。

生产配置必须启用 HTTPS 与安全 Cookie，否则应用拒绝启动。生产环境关闭 `/docs`、`/redoc`、`/openapi.json`，验证 Host，后台位于 `/workspace/login`，所有管理接口均验证服务端会话和 CSRF。生产 Cookie 使用 `__Host-` 前缀；密码使用带工作参数的 scrypt。

### HTTPS 反向代理

使用 `deploy/nginx.conf.example`，把所有 `xxx.com` 换为实际域名，并设置证书路径和 ACME webroot。配置中的 `limit_req_zone` 必须位于 `http` 上下文；不要把整个示例直接嵌入已有的 `server` 中。`http2 on` 需要 Nginx 1.25.1 或更新版本，较旧版本需按其支持的语法配置。

`BLOG_TRUSTED_PROXY_NETWORKS` 默认留空，应用不相信传入的代理头。**上线前必须确认并设置代理来源**，否则应用限流会把经过代理的访客当作同一来源。宿主机 Nginx 通常对应 Docker 网络的 bridge gateway，可用 `docker network inspect <project>_default` 查看 gateway，再核对实际网络路径并填写其 `/32` 地址。原生运行可填写 `127.0.0.1/32,::1/128`。不要设置 `0.0.0.0/0` 或 `::/0`。更改 `.env` 后执行 `docker compose up -d --wait` 重建容器配置。

示例 Nginx 覆盖外部传入的代理头，并对总请求、每个来源和登录请求分别限流。如果 Nginx 本身位于 CDN 或其他反向代理之后，还需只信任该上游提供的来源地址，不能直接相信任意公网 `X-Forwarded-For`。如果现有 Nginx 也在容器里，`127.0.0.1:8000` 的宿主机方案需要调整为共享 Docker 网络中的服务地址。

```bash
sudo nginx -t
sudo systemctl reload nginx
curl --fail https://blog.example.com/api/health
```

通过正式 HTTPS 地址验证首页、文章、图片、后台登录、草稿保存与匿名统计；配置日志轮转、数据库及图片的异机备份，并验证恢复流程。迁移现有网站时，验证新站后再切换反向代理，保留原服务以便回退。

## JSON 数据迁移

后台 **Settings → Export and import data** 提供原生 JSON 导出和导入，单个文件上限 16 MB。暂停编辑和图片上传后导出，再复制对应图片，保持两者一致。

1. 在源站点击 **Export JSON**。导出包含文章、独立页面、草稿与发布状态、原始正文、时间、标签、旧链接跳转和站点设置；不包含管理员账号、密码、会话、统计、SMTP 或部署配置。草稿也属于私有内容，JSON 不要放进公开目录或 Git。
2. 单独复制图片。`files[].path` 是相对源项目根目录的 POSIX 路径，例如 `data/dev/images/file/logo-1.png`；`media_root` 标明源图片目录。目标站使用自身配置的图片目录，加上去掉 `media_root/` 后的路径。因此这个例子在 Compose 宿主机中应放到 `data/production/images/file/logo-1.png`，容器中对应 `/app/data/images/file/logo-1.png`。无需修改 JSON；正文里的 `/content/images/…` 是公开 URL，保持原样。
3. 目标站登录后，在同一位置选择 JSON，查看 **Import preview**。服务器检查路径、记录关系、冲突和图片大小、SHA-256；缺少图片时先上传再重新选择 JSON。也可以明确勾选允许缺图导入，之后补传图片。
4. 按需勾选 **Also import site settings and navigation**（默认不勾选），确认预览后点击 **Import data**。新增文章和标签，相同记录跳过；内容冲突或已有图片校验不一致时阻止整个导入。失败时数据库事务回滚，不覆盖现有内容。重复导入同一份数据可安全跳过相同记录，服务器管理员账号与密码保持不变。

例如在 Windows 项目根目录打包图片（归档根目录下直接是 `file/` 等图片子目录）：

```powershell
tar -czf .\data\site-images.tar.gz -C .\data\dev\images .
```

通过 SFTP 上传后，在 Linux 项目根目录解压到目标图片目录。已有同名文件时先比较并保留副本，避免覆盖目标站正在使用的图片；预检会报告导出包与目标文件的差异。

```bash
mkdir -p data/production/images
tar -xzkf /path/to/site-images.tar.gz -C data/production/images
sudo chown -R 10001:10001 data/production/images
sudo chmod -R u+rwX data/production/images
```

`-k` 保留已有文件，同名文件导致 tar 报错时应先检查内容。JSON 导入只写数据库，不解压文件，仅接受本项目原生格式。

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

统计属于浏览器端估算，会受到脚本拦截、浏览器存储限制和伪装机器人的影响，不适合作为计费或安全审计依据。平均每日访客包含零访问日期，不表示跨天去重人数。

## 弱网访问

页面路由按需加载，归档每次加载 25 条摘要；列表数据库查询不读取正文和 HTML。图片原生懒加载并异步解码，代码块接近视口时再加载高亮语言；高亮模块加载失败时仍保留可读代码。

文本响应启用 gzip；图片、字体和 Range 请求跳过重复压缩。生产环境的带指纹资源与 UUID 图片长期缓存，固定名称图片短期缓存并支持 ETag、Last-Modified、304 和字节范围读取。公开 API 使用短期缓存，后台和会话数据禁止缓存。开发环境公开数据重新验证，方便手动实测。

样式、字体、图标和代码高亮均从本站提供，中文使用设备已有字体。文章中手动填写的外部图片或音视频 URL 仍会发起外部请求，可上传为本站资源。

API 在 20 秒无读取进展时超时；收到数据分块会重置超时。读取请求遇到网络中断或 408/502/503/504 时最多重试一次并退避，写入及已取消的请求不自动重试。

## 管理员邮件

需要邮件找回密码时，在服务器 `.env` 配置 SMTP：

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
docker compose exec blog python -m app.cli set-admin-email --username admin --email you@example.com
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
.\.venv\Scripts\python.exe -m app.cli create-admin --username admin --reset-password
```

生产环境在容器内执行对应命令，备份目标必须位于可写的数据卷，使用新的文件名，例如：

```bash
docker compose exec blog python -m app.cli backup /app/data/backup-001.sqlite3
```

同时备份图片目录；恢复时停止容器，在保留现状副本后，把完整快照和对应图片放入 `data/production/` 并恢复 UID/GID 10001 所有权，再启动并验证。完整数据库恢复包含管理员账号和密码哈希；只迁移文章且保留目标账号时，使用上文 JSON 导入。运行中的 SQLite 可能仍有未合并的 WAL 数据，不要只复制主数据库文件，应使用上述一致性备份命令。项目约定见 `AGENTS.md`。

## 第三方许可

随项目分发的样式和字体许可证见 [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES/)。再分发时请保留对应版权及许可声明。
