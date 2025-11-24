# 📦 GitHub Pages 部署文件夹

这个文件夹包含所有需要上传到 GitHub Pages 的文件。

## 📁 文件结构

```
github-deploy/
├── index.html              # 网站主页
├── app.js                  # 前端JavaScript逻辑
├── .nojekyll              # 禁用Jekyll处理
├── fetch_data.py          # 数据获取脚本
├── requirements.txt       # Python依赖
├── data/                  # 数据文件夹
│   ├── schedule_2025-26.json
│   ├── player_stats_season.json
│   ├── player_stats_l7.json
│   ├── player_stats_l14.json
│   └── defensive_ratings.json
└── .github/
    └── workflows/
        └── daily_update.yml  # GitHub Actions自动更新配置
```

## 🚀 部署步骤

### 方法1: 通过GitHub网页上传

1. 访问你的GitHub仓库: https://github.com/OrangeCatan/My-NBA-Tool
2. 将这个文件夹中的所有文件上传到仓库根目录
3. 进入 Settings → Pages，配置发布源为 `main` 分支

### 方法2: 使用Git命令行

```bash
# 进入这个文件夹
cd github-deploy

# 初始化Git仓库
git init

# 添加远程仓库
git remote add origin https://github.com/OrangeCatan/My-NBA-Tool.git

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: Fantasy NBA Tool"

# 推送到GitHub
git push -u origin main
```

## ✅ 部署完成后

访问: https://orangecatan.github.io/My-NBA-Tool/

## 🔄 自动更新

GitHub Actions会每天美东时间早上9点自动更新数据。

## 📝 注意事项

- 所有文件已经测试完成，可以直接上传
- 保持文件夹结构不变
- `.nojekyll` 文件很重要，不要删除
