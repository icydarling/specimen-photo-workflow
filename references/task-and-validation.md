# 任务记录与验收

从请求生成计划。单图记录足以复核的内容；批量、断点恢复及完整流程验证按图保存清单。可沿用这些字段：

| 字段 | 内容 |
|---|---|
| `sample_id`, `purpose`, `modules` | 样本、用途、本次开关 |
| `source`, `reference` | 首次编辑前的路径、SHA256、尺寸，参照及验证依据 |
| `scale`, `brightness`, `parameters` | 启用模块的测量、方法、曲线、保护区及变换 |
| `state`, `output`, `checks`, `issues` | 进度、实际文件和哈希、自动及视觉检查、待复核项 |

`planned → editing → exported → checked`。编辑后记录步骤、文档 ID。导出后核对实际文件与哈希，完成本次要求的检查才记 `checked`。未解决的必要检查记 `needs_review`，确实受阻记 `blocked`。

## 批量与断点恢复

核对 Photoshop 连接、工具限制、文档路径/ID、输出位置。分批处理，现有环境每批以 10 个工作文档为上限；视内存和图像大小继续减批。核验后关闭本任务已保存的工作文档，用户打开的其他文档保持原状。超时后先按工具规则恢复连接，确认它是否仍在执行，再对照文档、状态和输出哈希续做，防止重复缩放或叠加曲线。

## 检查与导出

- **分离与几何**。对照原片查全图，按原生像素查看关键轮廓、基部与末行末列。细线残留只精确遮盖已确认的背景，保护真实触边组织。改后重新导出并复查。边界、物理尺度与新尺线按[尺度与居中](scale-and-centering.md)核对，保留既有尺时记本次未重校准。
- **仅亮度**。保持尺寸、构图、标记和 alpha；依源图与任务核对背景、打印 PPI 和 ICC。用实际 PNG 核对保护区、像素与元数据。普通 PNG 保存优先，网页导出可能省略 PPI 或 ICC。若 DPI 仅有小数差异，检查 pHYs 和实际要求。
- **文件与来源**。重算来源哈希并核对文件名、类别与样本清单。参考图需原样提供或成品需复制到其他目录时，核对相应文件哈希。
- **交付**。按要求另存 PSD、PNG、透明 PNG 或 JPEG 预览；只检查时按要求提供结果。派生缩略图与联系表注明预览用途。说明自动检查、视觉检查覆盖范围与待复核项。

## 只读检查脚本

`audit_image.py` 和原像素核验需要 Pillow 与 NumPy，其余算术与策略脚本只需 Python 3。依赖缺失时说明具体包。脚本不编辑图像，报告写入新路径。

```text
python scripts/audit_image.py --source SOURCE --output OUTPUT --expected-source-sha256 HASH --expect-same-size --protect 0,960,418,1100 --preserve-black --preserve-alpha --expect-metadata --report NEW.json
```

- `--protect` 使用当前图的实际像素矩形 `[left,top,right,bottom)`，比较同几何下的标记区 RGBA。只调整亮度时使用 `--preserve-alpha`（普通 RGB 按 alpha 255 处理）。`--expect-metadata` 核对来源已有的 DPI/ICC，`--expect-identical` 核对 RGBA 像素完全一致。文件哈希和像素相等分别记录。
- `--preserve-black` 默认比较源图全部不透明纯黑像素。全流程成图可比较同排版的亮度层关闭版与成品，半透明边缘的 8 位舍入可使局部 RGB 从 0 变为 1–2。若只检查真背景，从 Photoshop 导出独立同变换的样本 alpha，传 `--mask ALPHA.png --background-only-black --preserve-black`。蒙版须是同尺寸 L 模式，来源必须独立于亮度阈值。
- 样本统计优先用已核实蒙版；缺蒙版时是排除保护区后的可见非黑候选。0/255 通道比例增加及 alpha 触边提示复核。换底、抠图、几何任务按实际改动选择检查项。

`pass` 表示所要求的自动检查成立，`fail` 表示不变量失败，`needs_review` 表示有提示或证据不足。未执行项标明覆盖范围。组织完整性与拍摄尺度依据分别人工核对。
