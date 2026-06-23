# COA Converter — CLAUDE.md

## 项目简介

COA Converter 是一个 Windows/Mac 桌面工具，将供应商提供的原材料检验报告（PDF/Word）转换为企业品牌化、FDA 合规的 Certificate of Analysis（COA）文件，支持导出 PDF 和 Word 格式，100% 离线运行。

## 技术栈

| 层 | 选择 |
|---|---|
| GUI | PyQt6 |
| PDF 解析 | PyMuPDF (fitz) + pdfplumber |
| OCR 备选 | pytesseract + Tesseract |
| Word 解析 | python-docx |
| PDF 生成 | ReportLab platypus |
| Word 生成 | python-docx |
| 配置持久化 | JSON via platformdirs（写入 `%APPDATA%\COAConverter\`） |
| 打包 | PyInstaller --onedir |

## 项目结构

```
coa_converter/
├── main.py                    # QApplication 入口
├── requirements.txt
├── coa_converter.spec         # PyInstaller 打包配置
├── CLAUDE.md
│
├── core/
│   ├── coa_model.py           # COADocument + TestResult dataclass + validate()
│   ├── config_manager.py      # 读写 config.json，证书号自增，logo/header 保存
│   ├── pdf_parser.py          # PyMuPDF + pdfplumber + pytesseract OCR
│   ├── docx_parser.py         # python-docx 提取
│   └── field_mapper.py        # 正则/启发式映射原始文本 → COA 字段
│
├── generators/
│   ├── pdf_generator.py       # ReportLab COA PDF 生成器（行业标准布局）
│   └── docx_generator.py      # python-docx COA Word 生成器（镜像 PDF 布局）
│
├── views/
│   ├── main_window.py         # QMainWindow + QStackedWidget + 侧边栏导航
│   ├── setup_screen.py        # Screen 1：公司配置 + Logo + Header 上传
│   ├── upload_screen.py       # Screen 2：拖拽上传 + 提取预览
│   ├── review_screen.py       # Screen 3：COA 字段编辑 + 测试结果表格
│   ├── export_screen.py       # Screen 4：导出 PDF / Word
│   └── styles.py              # 全局 QSS 样式表
│
└── workers/
    └── extraction_worker.py   # QThread：后台 OCR 解析，保持 UI 流畅
```

## 运行方式

```bash
# 创建 venv（首次）
python -m venv venv

# 安装依赖
venv\Scripts\pip install -r requirements.txt

# 运行
venv\Scripts\python main.py
```

## 打包（Windows）

```bash
# 安装 PyInstaller
venv\Scripts\pip install pyinstaller

# 打包
cd coa_converter
venv\Scripts\pyinstaller coa_converter.spec --clean --noconfirm
```

输出在 `dist\COA_Converter\`，入口为 `COA_Converter.exe`。

**注意**：如需 OCR 功能，需先安装 Tesseract：
- 下载：https://github.com/UB-Mannheim/tesseract/wiki
- 默认路径 `C:\Program Files\Tesseract-OCR`（与 spec 文件一致）

## 数据存储位置

- 配置文件：`%APPDATA%\COAConverter\config.json`
- 用户 Logo：`%APPDATA%\COAConverter\user_logo.<ext>`
- 用户 Header：`%APPDATA%\COAConverter\user_header.<ext>`

## 核心数据模型

### COADocument（`core/coa_model.py`）
主文档 dataclass，包含所有 COA 字段：证书号、产品名、批号、生产商、日期、测试结果列表、签署人、公司信息等。

### TestResult（`core/coa_model.py`）
单条测试记录：`test_name`, `category`（Physical/Chemical/Microbiological/Other）, `specification`, `result`, `unit`, `method`, `pass_fail`。

### CompanyConfig（`core/config_manager.py`）
公司配置：名称、地址、联系方式、logo_path、header_path、QC 声明、签署人、证书编号前缀和计数器。

## COA 生成布局（行业标准）

两个生成器（PDF + Word）采用相同的 8 段布局（各段之间用水平线分隔）：

1. **公司 Header**：若有 header 图片则全宽显示；否则 3 列表格（联系人 | Logo/名称 | 地址）
2. **供应商信息块**：大字体居中供应商名称 + 地址
3. **货物信息**：ALL CAPS 加粗标签 + 值（无网格，无背景色）
4. **COA 标题**："CERTIFICATE OF ANALYSIS" + 斜体副标题
5. **测试结果表格**：4 列（Attribute | Method Reference | Specification | Test Results），类别作为跨列浅灰行；结果值绿色(PASS)/红色(FAIL)；单位合并入结果列
6. **QC 声明**：居中斜体段落
7. **签署块**：4 行 × 3 列（签名 | 职位 | 日期 → 标签 → 打印姓名 → 标签）
8. **页脚**：文件说明 + 日期（小字居中）

## 四屏流程

```
[Setup 公司配置] → [Upload 上传文件] → [Review 审核编辑] → [Export 导出]
        ↑                                                         ↓
    侧边栏可随时返回                                        PDF / Word 文件
```

## 当前完成状态

- [x] 全部 4 个界面功能完整
- [x] PDF / Word 生成器（行业标准 COA 布局）
- [x] 公司 Logo + Header 上传（Setup Screen）
- [x] OCR 备选路径（pytesseract）
- [x] PyInstaller spec 文件
- [ ] 待优化：字段提取准确率（field_mapper.py 正则可持续调优）
- [ ] 待优化：OCR 后处理（低置信度字段高亮）

## 已知设计决策

- `pdf_generator.py` 和 `docx_generator.py` 的布局参考了 SmartFoodSafe 行业样本（用户提供截图）
- 测试结果无独立 Pass/Fail 列，结果文字直接用颜色区分（绿/红）
- 单位合并入 "Test Results" 列（如 "4.0 %", "10 cfu/g"）
- `header_path` 优先于 3 列文字 header，设置后整行用图片替换
- 配置写入 `%APPDATA%\COAConverter\` 而非项目目录，便于打包后使用

## 下一步可做的功能

- 批量处理（一次上传多份供应商文件）
- 自定义 QSS 主题
- 中文界面语言包
- 字段提取置信度标黄（review_screen.py 已有骨架）
- Mac 版打包（已有 spec 骨架，需在 Mac 上测试）
