# 软件操作依据与尺度助手

## 软件选择

Photoshop 足以完成整个流程：用标尺工具测原图像素长度，用图层蒙版保留样本，最后绘制数值宽度的矩形比例尺。Fiji/ImageJ 适合做独立校准/复核，不是强制依赖。Python 助手只负责确定性的换算。

实际菜单按已安装版本与语言核对：

- Photoshop 标尺工具：在工具栏选择 Ruler Tool，沿明确刻线中心拖动，读选项栏/信息面板的距离与坐标；不要将屏幕缩放百分比乘入图像像素距离。
- Photoshop 蒙版：选图层蒙版缩略图，黑画笔隐藏、白画笔恢复；Select and Mask 可局部细化边缘。保留蒙版以便恢复茎基和少量盆痕。
- Photoshop 缩放：Image > Image Size 中关联宽高比例；区分改变像素数的 Resample 与仅改变打印 ppi 的设置。改变 ppi 本身不能建立照片的物理长度校准。
- Fiji/ImageJ：先在原图直线连接已知距离的刻线中心，再用 Analyze > Set Scale 设置 Known Distance 和单位。若已设物理单位，后续读数可能不再是像素，要同时核对原始像素端点。对不同照片不要随意开启 Global 共用尺度。

以上操作核对于 2026-11-15，参考官方文档：

- [Adobe：编辑和细化图层蒙版](https://helpx.adobe.com/photoshop/desktop/create-masks/layer-masks/edit-and-refine-layer-masks.html)
- [Adobe：标尺工具](https://helpx.adobe.com/photoshop/desktop/use-grids-measurement-guides/measure-scale/measure-and-position-with-the-ruler-tool.html)
- [Adobe：图像大小、分辨率和重新采样](https://helpx.adobe.com/photoshop/desktop/crop-resize-transform/resize-adjust-resolution/image-size-resolution-and-resampling.html)
- [ImageJ：Analyze / Set Scale](https://imagej.net/ij/docs/guide/146-30.html)

## 尺度助手

`scripts/scale_bar.py` 仅依赖 Python 3 标准库。输入同一原图坐标系上的已确认刻线端点及实际毫米数；可重复传多个区间。倍率为小数，25% 输入 0.25；多次等比缩放重复传 `--scale`，脚本相乘。纯裁切/平移倍率为 1。

以下是**人为构造的算术例子，不是附图的测量值**：三个区间均为 100 mm 对应 600 px，最终缩小到 25%，20 cm 白线应长 300 px。

```powershell
python scripts/scale_bar.py --interval 0,0,0,600,100 --interval 0,600,0,1200,100 --interval 0,1200,0,1800,100 --scale 0.25 --bar-mm 200 --source-id example-only --output example-scale.json
```

脚本使用各区间 px/mm 的中位数汇总，并报告极差/中位数、每段测量和取整误差；原始数据保留供复核，不能只看汇总值。默认差异提示阈值为 1%，是操作复核提示，不是测量准确度认证。区间不足三个、分布差异较大或比例尺太短时产生警告。

无论是否警告，输出都标为 `arithmetic_only`：工具未识别刻度，没有验证单位、平面、倍率来源、蒙版或真实导出线长。后续需把来源文件、原图尺寸/哈希、坐标截图、变换依据、物理适用范围和实际导出核验结果加入交付记录。
