# 原生 PPT 制作辅助库

`scripts/hualang-kit.mjs` 固定华朗颜色、字体、页眉和表格样式，调用者决定议题、页序及主体构图。它不附带教学案例，也不替代内容审查。保留的封面来自 `assets/source-original.pptx` 第 1 页，原校园图、校徽、几何轮廓和画布保留，紫金底形统一为当前色值。新增页的原生文字、表格、图表和箭头均可编辑。

## 使用环境

在已具备 `@oai/artifact-tool` 的 Node.js 制作目录使用。若技能目录无法解析依赖，可把这个辅助文件复制到本次临时制作目录，让它复用该目录已配置的运行库；不要在技能包中加入依赖文件。`skillDir` 指向完整技能目录，所有输出路径由调用者传入，库内没有机器路径。

**先确认实际可用字体，再创建文件。** 默认中文 PingFang SC、英数 Arial。缺少字体时，把已核实可用的字体名传给 `createDeck` 的 `zhFont` / `latinFont`，无需修改库文件。它们统一作用于本稿封面、标题、页脚、文字、表格和图表；校徽图片保持原样。每个 deck 独立保留自己的选择，并行制作其他稿件不会受影响。换字体后须回看实际页面、换行和图表标签。

```js
import {createDeck, colors} from './hualang-kit.mjs';

const deck = await createDeck({
  skillDir, title: '本次实际题名', subtitle: '本次副题', presenter, date,
  zhFont: availableChineseFont, latinFont: availableLatinFont,
});
const page = deck.addPage({title: '本页事项', summary: '有依据的判断或安排', section: '所属章节'});
deck.text(page, '正文内容', {x: 48, y: 220, w: 720, h: 100, size: 28});
await deck.writeDraft({candidatePath, renderDir});
```

坐标与字号采用 96 dpi 的 CSS 像素，画布为原模板的 1280×720。数字 `fontSize: 24` 相当于 18 pt。标题右侧为校徽保留空间；常规正文区域从 y=210 至 y=660，省略概论时可以向上利用空余版面。调用者可以直接访问 `deck.presentation` 使用更多原生能力，主体不限定为两栏或卡片。

## 常用接口

| 接口 | 关键参数与返回 |
|---|---|
| `createDeck({skillDir,title,subtitle,presenter,date,zhFont,latinFont})` | 异步。保留原始封面图片与结构，填入本次文字，返回 deck；字体选项可省略 |
| `addPage({title,summary,section,titleSize})` | 返回常规浅底深紫字页面，固定左题名、右校徽 |
| `addStage({title,subtitle,section,imagePath,imageAlt,titleSize,subtitleSize,brandBacking})` | 异步。无图时为深紫底主张页；有图时上部 480 px 主图、下部深紫标题区。主图页默认主句 64 px、副句 38 px；深紫页默认主句 78 px、副句 40 px |
| `text(slide,value,{x,y,w,h,size,color,bold,font,zhFont,latinFont,align,name,lineSpacing})` | 返回可编辑文本形状。默认按中文/英数分配字体；`font` 可显式统一。不会自动缩小字号 |
| `image(slide,file,{x,y,w,h,alt,fit})` | 异步，PNG/JPEG，默认 `contain` 保留全图；`cover` 等比例裁切。`alt` 必填 |
| `nativeTable(slide,values,{x,y,w,h,columnWidths,rowHeights,size,numericColumns,focusRow,font,zhFont,latinFont})` | 返回原生表格。首行为深紫白字表头；指定数字列在表身右对齐；`focusRow` 按从 0 起的整表行号 |
| `chart(slide,type,options,fontOptions)` | 返回原生图表，沿用 Artifact Tool 的数据与坐标参数，并补统一字体及紫色系列。可选第 4 参数支持 `{font,zhFont,latinFont}` |
| `line(slide,{x,y,w,h,color,width})` | 返回无箭头的分隔线，默认水平；可用于图中必要的参考线 |
| `arrow(slide,{from,to,fromSide,toSide,kind,color,width})` | 两端依附已创建的文本框或形状，箭头由 from 指向 to，默认右侧接左侧 |
| `arrow(slide,{x,y,w,h,color,width})` | 创建独立的原生连接箭头；w/h 非负，方向从左上端指向右下端。反向关系请用明确的 from/to 形状 |
| `writeDraft({candidatePath,renderDir,scale})` | 异步。输出候选 PPTX、每页 PNG 和布局记录，返回路径与页数；默认 1.5 倍渲染 |

主图页的 `brandBacking` 默认开启，为右上金色校徽提供深紫小底托，避免浅色或复杂照片削弱对比。若遮住主体，先调整裁切或构图；只有图片本身已提供稳定对比时才设为 `false`。底托仅作用于主图页。主图页的主句和副句各以一行短句为默认，过长时先精简或改页型，也可以按实际长度传入 `titleSize` / `subtitleSize` 后查看渲染。深紫主张页为副句留出两行空间。

直接导入独立 `text` / `nativeTable` / `chart` 函数时，也可传上述字体选项；省略时仍使用默认字体。`deck.text` / `deck.nativeTable` / `deck.chart` 自动继承本稿字体，不必逐次重复。

### 表格

`columnWidths` 必填，总和等于 w。先按实际内容分配列宽：名称与说明列通常更宽，数字列以能容纳最长值和单位为准。每行列数一致；传入 `rowHeights` 时，其数量及总高须与表格一致。示例中的单元格值请换成本次材料，不能依赖自动缩字消除溢出。

```js
deck.nativeTable(page, [['项目', '数量 / 项'], ['实际项目名称', '8']], {
  x: 48, y: 220, w: 700, h: 180, columnWidths: [480, 220],
  rowHeights: [70, 110], size: 26, numericColumns: [1],
});
```

### 图表与箭头

数值轴上下限用 `min` / `max`，`majorUnit` 设置主刻度间隔。库会拒绝容易被忽略的 `minimumScale` / `maximumScale`。横向条形图 `barOptions.direction='bar'` 中，**xAxis 仍表示分类轴，yAxis 表示数值轴**；数值范围应写在 yAxis。默认横向条形图可能从下向上排列类别，若要与旁边的表格同序，应对应重排 categories 和每组 values 后查看渲染。散点图 xAxis、yAxis 都是数值轴，适用于函数关系，不能拿分类折线图代替数值横轴。

```js
deck.chart(page, 'bar', {
  position: {left: 48, top: 220, width: 700, height: 350},
  categories: ['项目甲', '项目乙'], series: [{name: '数量', values: [8, 5]}],
  barOptions: {direction: 'bar', grouping: 'clustered'},
  xAxis: {majorGridlines: {fill: 'none'}},
  yAxis: {min: 0, max: 10, majorUnit: 2},
});
const a = deck.text(page, '动作甲', {x: 800, y: 260, w: 170, h: 60});
const b = deck.text(page, '动作乙', {x: 1040, y: 260, w: 170, h: 60});
deck.arrow(page, {from: a, to: b});
```

连接箭头采用 `geometry:'connector'` 或 `shapes.connect`，目标端用 `tail`。不要给普通 `geometry:'line'` 传箭头参数，该运行库可能忽略它。关系的顺序与方向由资料决定。

## 输出后的检查

`writeDraft` 只负责导出和实际渲染，不宣称文件、教学内容或视觉已通过验收。查看每一页 PNG，检查文字、图片裁切、数轴、表格和可见箭头；再按成品流程核对可编辑对象与最终保存文件。舞台大图页须检查校徽对比和底托是否遮挡主体，必要时调整图片裁切或改用常规页。真实资料、示意、计划及实绩保持明确。
