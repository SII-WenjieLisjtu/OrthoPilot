# 国际化模块 (Internationalization Module)

## 概述 (Overview)

本模块为医学AI评测系统提供中英文双语支持。

This module provides bilingual support (Chinese and English) for the Medical AI Evaluation System.

## 文件结构 (File Structure)

```
i18n/
├── __init__.py          # 模块初始化文件
├── translations.py      # 翻译字典和核心函数
└── README.md           # 本文档
```

## 使用方法 (Usage)

### 导入模块 (Import Module)

```python
from i18n import get_text, get_language_name
```

### 获取翻译文本 (Get Translated Text)

```python
# 基本用法
text = get_text("page.title", lang="zh")  # 返回: "医学AI评测系统"
text = get_text("page.title", lang="en")  # 返回: "Medical AI Evaluation System"

# 带格式化参数
text = get_text("task_selection.welcome", lang="zh", name="张医生", title="主治医师")
# 返回: "欢迎，张医生 主治医师！"
```

### 获取语言名称 (Get Language Name)

```python
name = get_language_name("zh")  # 返回: "中文"
name = get_language_name("en")  # 返回: "English"
```

## 翻译键路径 (Translation Key Paths)

翻译键使用点分隔的路径格式：

Translation keys use dot-separated path format:

- `page.*` - 页面配置 (Page configuration)
- `sidebar.*` - 侧边栏 (Sidebar)
- `login.*` - 登录/注册页面 (Login/Register page)
- `task_selection.*` - 任务选择页面 (Task selection page)
- `evaluation.*` - 评价页面 (Evaluation page)
- `config.*` - 配置选项 (Configuration options)

## 添加新翻译 (Adding New Translations)

在 `translations.py` 的 `TRANSLATIONS` 字典中添加新的键值对：

Add new key-value pairs to the `TRANSLATIONS` dictionary in `translations.py`:

```python
TRANSLATIONS = {
    "zh": {
        "new_section": {
            "new_key": "中文文本"
        }
    },
    "en": {
        "new_section": {
            "new_key": "English text"
        }
    }
}
```

## 注意事项 (Notes)

1. 所有UI文本都应通过 `get_text()` 函数获取，避免硬编码
2. 格式化参数使用 Python 的 `str.format()` 语法
3. 默认语言为中文 (zh)
4. 语言偏好存储在 `st.session_state.language` 中

1. All UI text should be retrieved via `get_text()` function, avoid hardcoding
2. Format parameters use Python's `str.format()` syntax
3. Default language is Chinese (zh)
4. Language preference is stored in `st.session_state.language`
