# Render + Neon 免费部署指南

这个方案适合没有海外信用卡、需要一个公网可访问演示版本的场景：

- Render Free Web Service 跑 FastAPI 应用
- Neon Free Postgres 保存数据
- 不启用 Redis worker，使用当前表单默认的同步搜索模式

免费版限制要接受：

- Render 免费 Web Service 15 分钟无访问会休眠，首次访问可能等待约 1 分钟
- Render 免费服务没有持久本地磁盘，所以不能继续依赖 SQLite 文件
- Neon Free 有 0.5 GB 存储和月度计算额度限制
- 免费方案不适合作生产 SLA，只适合 MVP、内部试用和演示

## 1. 创建 Neon Postgres

1. 打开 `https://neon.com/`，用 GitHub 或邮箱注册。
2. 创建一个 Free 项目。
3. 在项目 Dashboard 复制数据库连接串。
4. 推荐使用 pooled connection string，并把协议改成 SQLAlchemy 兼容格式：

```text
postgresql://user:password@host/dbname?sslmode=require
```

如果连接报驱动问题，再改成：

```text
postgresql+psycopg2://user:password@host/dbname?sslmode=require
```

不要把连接串提交到 Git；只放到 Render 环境变量。

## 2. 准备 Git 仓库

Render 推荐从 GitHub 自动部署。把当前项目推到 GitHub 后，Render 可以直接读取仓库里的 `render.yaml` 和 `Dockerfile`。

确认仓库里有：

- `Dockerfile`
- `render.yaml`
- `pyproject.toml`
- `app/`

不要提交 `.env`、`data/`、`output/`。

## 3. 创建 Render Web Service

1. 打开 `https://render.com/` 注册。
2. 选择 New -> Blueprint 或 Web Service。
3. 连接 GitHub 仓库。
4. 如果使用 Blueprint，Render 会读取 `render.yaml`。
5. 如果手动创建 Web Service：
   - Runtime：Docker
   - Plan：Free
   - Branch：你的主分支
   - Root Directory：留空

## 4. 配置环境变量

在 Render 服务的 Environment 页面设置：

```env
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
ACCESS_USERNAME=admin
ACCESS_PASSWORD=replace-with-a-long-random-password
TAVILY_API_KEY=your-tavily-api-key
YOUTUBE_API_KEY=your-youtube-api-key
```

可选：

```env
SEARCH_ENGINE_API_KEY=
SEARCH_ENGINE_ID=
APP_NAME=Influencer Discovery
```

公网部署务必设置 `ACCESS_USERNAME` 和 `ACCESS_PASSWORD`。生成随机密码：

```bash
openssl rand -base64 24
```

## 5. 部署和访问

Render 首次部署会构建 Docker 镜像并启动应用。应用启动时会自动创建数据库表。

部署完成后，打开 Render 提供的 `.onrender.com` 地址。

如果浏览器弹出登录框，输入你设置的 `ACCESS_USERNAME` 和 `ACCESS_PASSWORD`。

## 6. 当前免费版运行方式

搜索表单默认会同步执行搜索任务，也就是请求会等待搜索完成再跳转结果页。这样可以避开免费方案里常驻 Redis worker 的成本。

如果以后需要后台队列，有两个选择：

- Render 付费 Web Service + Render Key Value + Background Worker
- 换成可运行 Docker Compose 的 VPS

## 7. 更新部署

以后推送代码到 GitHub，Render 会自动重新部署。也可以在 Render Dashboard 手动点 Manual Deploy。

## 8. 常见问题

### 部署成功但访问慢

免费 Web Service 休眠后的冷启动是正常现象。

### 数据没保存

确认 `DATABASE_URL` 指向 Neon，而不是 SQLite。Render 免费服务的本地文件系统会在重启或重新部署后丢失。

### 数据库连接失败

检查：

- Neon 连接串是否包含 `sslmode=require`
- 用户名、密码、host 是否完整
- `DATABASE_URL` 是否只配置在 Render 环境变量里
- 如果 `postgresql://` 报驱动错误，尝试 `postgresql+psycopg2://`

### 搜索卡住或失败

Render 免费实例资源较小，外部搜索也可能被目标站点限流。优先配置 `TAVILY_API_KEY`，比直接公开网页搜索稳定。
