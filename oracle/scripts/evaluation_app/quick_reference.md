# 快速参考 - 医学AI评测系统

## 🚀 启动应用

```bash
cd /path/to/orthopilot/gen_validation/evaluation_app
./start.sh
```

或者：

```bash
python -m streamlit run app.py --server.headless=true --server.port=8502
```

## 🌐 访问地址

- **本地**: http://YOUR_HOST:YOUR_PORT
- **外网**: http://YOUR_HOST:YOUR_PORT

## 🔄 语言切换

1. 打开应用
2. 查看侧边栏右上角
3. 点击 **"EN"** → 切换到英文
4. 点击 **"中"** → 切换回中文

## 🛠️ 常用命令

### 停止应用
```bash
ps aux | grep streamlit | grep -v grep
kill <PID>
```

### 查看日志
```bash
tail -f /tmp/streamlit_fixed.log
```

### 检查健康状态
```bash
curl http://YOUR_HOST:YOUR_PORT
```

## ✅ 已修复的问题

1. **AttributeError: 'list' object has no attribute 'values'**
   - 原因: doctors.json 是列表格式
   - 解决: 自动转换为字典格式

2. **KeyError: 'experience'**
   - 原因: 字段名不匹配 (experience vs experience_years)
   - 解决: 使用兼容性访问方式

## 📁 重要文件

- `app.py` - 主应用
- `i18n/translations.py` - 翻译字典
- `config.py` - 配置文件
- `utils/storage.py` - 数据存储
- `start.sh` - 启动脚本

## 🎯 功能特性

- ✅ 中英文双语界面
- ✅ 即时语言切换
- ✅ 医生登录/注册
- ✅ 任务选择
- ✅ 病例评价
- ✅ 数据持久化

## 📞 故障排除

### 端口被占用
```bash
# 查找占用端口的进程
netstat -tulpn | grep 8502
# 或
ss -tulpn | grep 8502

# 停止进程
kill -9 <PID>
```

### 依赖缺失
```bash
pip install -r requirements.txt
```

### 数据格式问题
- 确保 `data/doctors.json` 存在
- 确保 `data/samples/` 目录存在

---

**最后更新**: 2026-03-04
**版本**: v1.0 with i18n support
**状态**: ✅ 运行正常
