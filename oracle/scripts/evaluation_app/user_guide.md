# 医学AI评测系统 - 使用说明

## 启动应用

### 方法 1：使用启动脚本（推荐）
```bash
cd /path/to/orthopilot/gen_validation/evaluation_app
./start.sh
```

### 方法 2：直接使用 Python 命令
```bash
cd /path/to/orthopilot/gen_validation/evaluation_app
python -m streamlit run app.py
```

## 访问应用

应用启动后，在浏览器中访问：
- 本地访问：http://YOUR_HOST:YOUR_PORT
- 如果在远程服务器上，需要配置端口转发或使用服务器的公网IP

## 语言切换功能

### 切换语言
1. 查看侧边栏右上角
2. 点击语言切换按钮：
   - 中文模式下显示 "EN" 按钮
   - 英文模式下显示 "中" 按钮
3. 点击后页面会自动刷新并切换语言

### 默认语言
- 系统默认使用中文界面
- 语言偏好在会话期间保持

## 功能说明

### 1. 登录/注册
- 首次使用需要注册账号
- 填写基本信息（姓名、职称、专科等）
- 已注册用户可直接选择账号登录

### 2. 任务选择
- 查看可用的评测任务
- 显示每个任务的进度
- 选择任务开始评价

### 3. 病例评价
- 阅读患者病历信息
- 查看不同AI模型的回答
- 对模型回答进行评分
- 提交评价后自动进入下一个病例

## 停止应用

在终端中按 `Ctrl+C` 停止应用

## 故障排除

### 问题：streamlit: command not found
**解决方案**：使用 `python -m streamlit run app.py` 代替 `streamlit run app.py`

### 问题：端口被占用
**解决方案**：
```bash
# 查找占用端口的进程
lsof -i :8501
# 或
netstat -tulpn | grep 8501

# 停止进程
kill -9 <PID>
```

### 问题：依赖缺失
**解决方案**：
```bash
pip install -r requirements.txt
```

## 技术支持

如遇到问题，请检查：
1. Python 版本（需要 Python 3.7+）
2. 依赖是否正确安装
3. 数据文件是否存在（data/samples/ 目录）
4. 端口 8501 是否被占用

## 更新日志

### 2026-03-04
- ✅ 添加中英文切换功能
- ✅ 创建国际化模块 (i18n)
- ✅ 更新所有UI文本支持双语
- ✅ 添加语言切换按钮
- ✅ 创建启动脚本
