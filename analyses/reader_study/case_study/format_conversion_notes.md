# 如何将.docx转换为.doc格式

## 生成的文件

✅ **医生评测问卷_按患者.docx** (95.5 KB)
- 已按患者组织，每个患者的所有诊断任务放在一起
- 格式：Word 2007+ (.docx)

## 转换为.doc格式的方法

### 方法1：使用Microsoft Word（推荐）

1. 在Word中打开 `医生评测问卷_按患者.docx`
2. 点击 `文件` → `另存为`
3. 在"文件类型"下拉菜单中选择 `Word 97-2003 文档 (*.doc)`
4. 点击 `保存`

### 方法2：使用LibreOffice（免费）

如果没有Microsoft Word，可以使用免费的LibreOffice：

```bash
# 安装LibreOffice（Ubuntu/Debian）
sudo apt-get install libreoffice

# 转换命令
libreoffice --headless --convert-to doc:"MS Word 97" \
    "医生评测问卷_按患者.docx" \
    --outdir .
```

### 方法3：在线转换（无需安装软件）

可以使用以下在线转换服务：
- CloudConvert: https://cloudconvert.com/docx-to-doc
- Zamzar: https://www.zamzar.com/convert/docx-to-doc/
- Online-Convert: https://document.online-convert.com/convert-to-doc

## 关于文件格式

- **.docx** (推荐)
  - Word 2007及以上版本
  - 基于XML，文件更小，兼容性更好
  - 支持更多现代功能
  
- **.doc** (旧版)
  - Word 97-2003版本
  - 二进制格式，文件较大
  - 仅在需要兼容非常老的Word版本时使用

**建议**：除非有特殊兼容性需求，否则直接使用.docx格式即可。

## 文档内容组织

新生成的文档已按您的要求组织：

```
患者1
├── 入院诊断（判断/选择/开放 共3题）
├── 术前诊断（判断/选择/开放 共3题）
├── 术后诊断（判断/选择/开放 共3题）
└── 出院诊断（判断/选择/开放 共3题）

患者2
├── 入院诊断
├── 术前诊断
├── 术后诊断
└── 出院诊断

...（共10个患者）
```

每个患者12个案例（4个诊断阶段 × 3种题型），完整体验从入院到出院的诊疗流程。
