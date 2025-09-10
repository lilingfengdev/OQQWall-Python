# Docker 部署

## docker-compose

```bash
cp config/config.example.yaml config/config.yaml
docker-compose up -d
docker-compose logs -f | cat
```

默认暴露 8082，并通过 `/health` 提供健康检查。

## 手动构建

```bash
docker build -t oqqwall .
docker run -d \
  --name oqqwall \
  -p 8082:8082 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -e LLM_API_KEY=your-api-key \
  oqqwall
```

注：容器内已安装 Chromium 与字体，Playwright 可直接用于渲染。

