# 原生制作工具 V6

`scripts/hualang-kit.mjs` 使用当前可用的 `@oai/artifact-tool`，封面与封尾均从原始模板保留。调用者决定内容、学科与具体构图，工具提供用途对应的默认值。

## 运行环境

桌面环境读取 `load_workspace_dependencies` 返回的运行库。可将辅助库复制到本次临时制作目录，并让该目录解析已有依赖；不要把依赖目录打入技能包。字体先核实，中文默认PingFang SC，英数Arial，简单分式默认Times New Roman；缺失时用 `zhFont / latinFont / mathFont` 传入实际可用字体。

```js
import {createDeck,colors,profiles} from './hualang-kit.mjs';
const deck=await createDeck({skillDir,title:'本次题名',presenter,date});
const page=deck.addPage({title:'本页议题',purpose:'report',summary:'有依据的判断或安排。'});
// 新页自动插在固定封尾之前；不要自拟最后一页替代原模板。
await deck.writeDraft({candidatePath,renderDir});
```

封面不传subtitle。确有独立范围或用户明确要求时同时传 `subtitlePurpose:'scope'` 或 `'user_request'`；这表示已有语义依据，不要求额外审批。不要把版本、使用介绍或演示标签当成副题。

## 用途与默认字号

坐标/字号单位为CSS像素，24px=18pt。画布1280×720。标题区约y=30—73，分隔线y=86，主体可从y=108至650。不要复制V5的第二个大标题或y=210才开始正文的布局。

| purpose | 题名px | 正文px | 概论px | 典型用途 |
|---|---|---|---|---|
| report | 28 | 21 | 22 | 正式内部阅读汇报 |
| lessonPlan | 28 | 20 | 21 | 教师教案/备课 |
| classroom | 30 | 25 | 25 | 学生课堂 |
| worksheet | 28 | 24 | 24 | 练习题组 |
| parent | 34 | 28 | 28 | 家长现场/招生 |
| stage | 52 | 30 | 30 | 舞台表达 |

`deck.text` 对通过入口创建的页面采用对应正文起点，可按真实材料显式调整。正文默认 `colors.ink`，标题和教学组件用 `colors.purple` / `colors.pale`，重点 `colors.red`，分析图形 `colors.blue`。字号起点不等于配额，见[教学设计](teaching-design.md)及[视觉规范](design.md)。

## 主要入口

| 方法 | 返回与用途 |
|---|---|
| `addPage({title,purpose,summary,section,titleSize})` | 普通页，单题名；summary为正文层级概论 |
| `addReportPage({title,summary,section})` | 题名、概论、依据与落实区域，内部完整论证 |
| `addLessonPlanPage({title,section})` | context、sequence、assessment三个区域；可以按具体学科改变安排 |
| `addMathPage({title,mode,purpose,section})` | mode为single/pair/proof，分别给完整题干+推导/图形、双题或通栏推导 |
| `addLessonPage({title,task,section})` | 观察对象与任务页，只适用于相应观察任务 |
| `addPhotoEssay({title,orientation,section})` | 主次照片区域，left/right按真实素材选择 |
| `await addEditorial({title,dark,section})` | 开放画布；题名不应再与大口号重复 |
| `await addStage({title,subtitle,imagePath,imageAlt,section})` | 舞台主句/主图；默认不加小场景标题，舞台字号不传给课堂 |
| `text / image / nativeTable / chart / line / arrow` | 原生文字、图片、表格、数据图与关系图，具体坐标由内容决定 |
| `fraction(slide,num,den,{x,y,w,size,color})` | 简单可编辑分式：分子/横线/分母；复杂数学对象按数学专项 |

原生表格必须给按内容分配的columnWidths且合计为w，可给rowHeights。表头默认紫底白字，可选headerStyle=tint为浅紫深紫字；表身黑色，数字列右对齐。cellPadding控制内边距，按真实换行确定rowHeights，不能让自动增高压住后续内容。图表数值轴使用min/max；函数采用scatter与xValues。默认蓝/灰系列，重点需要时才显式用红。

## 点击揭示

```js
const {slide}=deck.addMathPage({title:'导数应用',mode:'single'});
const step=deck.text(slide,'完整的关键推理',{x:48,y:240,w:720,h:70});
deck.registerReveal(slide,[step],{label:'关键转化'});
await deck.writeRevealManifest(manifestPath);
```

先确定页序并排出完整末态，再登记对象。后续重排页序需重新登记/导出清单。对象可为原生shape；图表/图片可传已核实且唯一的导出对象名，例如单图表页面的 `Chart`。

```text
python3 scripts/apply_reveals.py base.pptx reveals.json animated.pptx
python3 scripts/apply_reveals.py base.pptx reveals.json state0.pptx --state 0
```

基础稿先完成图表数据、文件和视觉检查，再写入原生时间线。写入后不要用会丢失动画的工具重存。已有动画、缺失或重复对象、覆盖输出会报错。状态图只能证明各步内容与位置，不能代替PowerPoint应用内放映。

图表再导出须核对嵌入数据文件。运行库丢失已有工作簿时回到保留的源稿恢复，不凭缓存伪造来源；新制图表可从完整字面量数据创建快照并保留明确精度。


## 功能组件

- `lessonBand(slide,label,body,{x,y,w,h,size,labelWidth})`：统一任务带，紫色短标签与浅紫完整题干区域，返回原生对象组。
- `methodStrip(slide,label,body,{x,y,w,h,size})`：方法、关键条件或支持提示，浅紫底/紫色边界、黑色正文。
- `stepMarker(slide,label,{x,y,w,size})`：稳定的紫色步骤编号，与实际推理同时出现。

任务/步骤/方法是内容组织，不能代替完整题目、论证或活动。组件只在对应信息存在时使用。可将返回对象登记为同一揭示步骤。场景选择决定组合，不强制全稿套一套条带。

演讲图文默认stageLayout=split、imageFit=contain，优先完整保留人物与动作。只有适合宽幅裁切的素材才用banner/cover，必须实看人脸、手部和证据未被裁掉。

`createDeck`用于完整稿。单页或局部任务可从品牌正文页起稿并按用户指定页数导出，保留正文品牌；不强加完整稿的封面封尾。
