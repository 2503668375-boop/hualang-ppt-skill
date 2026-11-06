# 原生制作工具 V8.3

常规华朗内容页使用`addPage`；`addSchoolScene`同样只保留页眉、校徽、分隔线与正文底。混合场景创建时指定`sceneMode:'mixed'`，通用入口漏传`purpose`会报错；单一场景可用`defaultPurpose`整稿指定。为兼容旧稿，未传这些参数仍保留report默认。用途参数只设置字号起点，不决定主体和构图，也不证明场景设计已经完成。

`scripts/hualang-kit.mjs` 使用当前可用的 `@oai/artifact-tool`，封面与封尾均从原始模板保留。调用者决定内容、学科与具体构图，工具提供用途对应的默认值。

## 运行环境

`addPage`只提供品牌框架，没有默认卡片网格。`addReportPage(...).areas.content`给出完整正文区；历史`evidence/note`保留兼容，调用者无需将一页切成证据块和底备注块。内容选择见[内容与版式](report-layouts.md)。

桌面环境读取 `load_workspace_dependencies` 返回的运行库。可将辅助库复制到本次临时制作目录，并让该目录解析已有依赖；不要把依赖目录打入技能包。字体先核实，中文默认PingFang SC，英数Arial，简单分式默认Times New Roman；缺失时用 `zhFont / latinFont / mathFont` 传入实际可用字体。

```js
import {createDeck,renderSavedDeck,colors,profiles} from './hualang-kit.mjs';
const deck=await createDeck({skillDir,title:'本次题名',presenter,date,sceneMode:'mixed'});
const report=deck.addPage({title:'招生差额',purpose:'report'});
// 在主比较旁安排结论与条件，不先加同款分栏。
const lesson=deck.addPage({title:'区间最值',purpose:'classroom'});
// 完整题干、图形与关键推理；教师教案另用lessonPlan。
// 新页自动插在固定封尾之前；不要自拟最后一页替代原模板。
const preview=await deck.writeDraft({candidatePath,renderDir});
// preview.reviewStatus始终为unreviewed；按实际预览继续审查。
```

概论可省略。`summary`的固定文本区及旧`evidence/note`区域仅为兼容便捷入口，不把所有页都推成“题名＋长概论＋分栏”。内容需要概论时确定真实行数和位置，短概论不预留无用高度；也可在完整正文区用`deck.text`自行安排。文字高度不等于实际字形边界，需检查最终换行和末行。

封面不传subtitle。确有独立范围或用户明确要求时同时传 `subtitlePurpose:'scope'` 或 `'user_request'`；这表示已有语义依据，不要求额外审批。不要把版本、使用介绍或演示标签当成副题。

## 用途与默认字号

坐标/字号单位为CSS像素，24px=18pt。画布1280×720。标题区约y=30—73，分隔线y=86，主体可从y=108至650。不要复制V5的第二个大标题或y=210才开始正文的布局。

| purpose | 题名px | 正文px | 概论px | 典型用途 |
|---|---|---|---|---|
| report | 28 | 21 | 22 | 正式内部阅读汇报 |
| lessonPlan | 28 | 20 | 21 | 教师教案/备课 |
| classroom | 30 | 25 | 25 | 学生课堂 |
| worksheet | 28 | 24 | 24 | 练习题组 |
| parent | 28 | 28 | 28 | 家长现场/招生 |
| stage | 28 | 30 | 30 | 舞台表达 |

`deck.text` 对通过入口创建的页面采用对应正文起点，可按真实材料显式调整。正文默认 `colors.ink`，标题和教学组件用 `colors.purple` / `colors.pale`，重点 `colors.red`，分析图形 `colors.blue`。字号起点不等于配额，见[教学设计](teaching-design.md)及[视觉规范](design.md)。

## 主要入口

### 开放式组件

下列方法返回可编辑原生对象数组，可以登记揭示；它们不创建背景面板，也不决定整页布局。

```js
deck.metricInline(slide,'500','年度新增学生',{
  x:48,y:200,w:350,unit:'人',context:'模拟数据；同一招生年度',size:64
});
deck.dotComparison(slide,[
  {label:'初中',before:180,after:165},
  {label:'高中',before:240,after:225},
  {label:'国际高中',before:130,after:110}
],{x:48,y:210,w:1184,h:340,min:0,max:260,unit:'人',beforeLabel:'目标',afterLabel:'实际'});
deck.milestoneTimeline(slide,[
  {date:'2027-01-15',label:'复核需求',detail:'模拟安排'},
  {date:'2027-04-20',label:'阶段复测',detail:'同标准检验'}
],{x:48,y:220,w:1184,h:330,start:'2027-01-01',end:'2027-06-30'});
deck.evidenceNote(slide,'解释这个具体转折及其条件。',{
  x:900,y:260,w:300,h:150,anchor:{x:850,y:360},title:'变化依据'
});
```

- `metricInline`：开放数字、含义与口径，`unit/context`可省略；检查长值与单位是否适配宽度。不同群体与期间分开标明，不暗示可加总。
- `dotComparison`：相同指标、单位和口径的成对值，共用`min/max`数轴；端点、数值和差额直接标注。`labelWidth/size`可调，留出必要行高。它是按数值定位的可编辑图形，不是含数据工作簿的原生chart；多系列图表可用`deck.chart`。
- `milestoneTimeline`：`start/end`和每项`date`为有效ISO日期，节点依真实间距定位。事件可带`width/labelX/labelY`调整文字，近邻日期须实看避免重叠。若日期未定或只有季度，不虚构具体日期；改用阶段文字或责任关系。
- `evidenceNote`：正文可加`title`和指向证据的`anchor`，无需底框；锚点须在注释文字区外。检查引线端点与对象对应；不能让引线穿过重要文字。

数据图导出后另查图表部件与数值是否保留，以及是否包含嵌入工作簿。含原生chart和数值字面量不自动证明PowerPoint的“编辑数据”已可用；需要该功能时按实际工具补工作簿并验证，交付不声称未做的应用编辑测试。

色块接口如`focusPanel/numberFlag/stepBands`仍可使用，但只在内容关系适合时调用。不要循环同款组件填满整稿；组件名称不同也可能产生相同的等分面板。

先按实际对象组合小组件。表格接口只在真实行列查阅需要时使用；教案、推理、方法、反馈和文本并不因接口方便而默认套表。内容完整与密度由关系、条件及完整解释保证，不能靠删网格、缩字或等宽卡片替代组织。

| 方法 | 返回与用途 |
|---|---|
| `addPage({title,purpose,summary,section,titleSize})` | 普通页，单题名；summary为正文层级概论 |
| `addSchoolScene({title,summary,section,purpose})` | 保留固定正文框架，用于家长、招生与对外交流 |
| `addReportPage({title,summary,section})` | 题名、概论、依据与落实区域，内部完整论证 |
| `addLessonPlanPage({title,section})` | 历史分区便捷入口，不代表所有教案固定三块；按实际活动与反馈重组 |
| `addMathPage({title,mode,purpose,section})` | mode为single/pair/proof，分别给完整题干+推导/图形、双题或通栏推导 |
| `addLessonPage({title,task,section})` | 观察对象与任务页，只适用于相应观察任务 |
| `addPhotoEssay({title,orientation,section})` | 主次照片区域，left/right按真实素材选择 |
| `await addEditorial({title,dark,section})` | 开放画布；题名不应再与大口号重复 |
| `await addStage({title,subtitle,imagePath,imageAlt,section})` | 旧的局部特殊画布；常规演讲用addPage保留既定品牌框架，再组合主句与主图 |
| `text / image / nativeTable / chart / line / arrow` | 原生文字、图片、表格、数据图与关系图，具体坐标由内容决定 |
| `fraction(slide,num,den,{x,y,w,size,color})` | 简单可编辑分式：分子/横线/分母；复杂数学对象按数学专项 |

`deck.nativeTable` 的默认size跟随当前页面profile.table，显式size仍优先；底层独立nativeTable按自身默认值。原生表格必须给按内容分配的columnWidths且合计为w，可给rowHeights。表头默认紫底白字，可选headerStyle=tint为浅紫深紫字；表身黑色，数字列右对齐。cellPadding控制内边距，按真实换行确定rowHeights，不能让自动增高压住后续内容。图表数值轴使用min/max；函数采用scatter与xValues。默认蓝/灰系列，重点需要时才显式用红。

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

图片按具体场景选择contain或cover，并实看人物、动作、关键证据和原图署名；图像裁切不能破坏内容。常规对外页面使用addSchoolScene保留原模板。

`createDeck`用于完整稿。单页或局部任务可从品牌正文页起稿并按用户指定页数导出，保留正文品牌；不强加完整稿的封面封尾。

## 连续稿与封尾

`createDeck({...,closingText:"感谢聆听，期待同行"})`保留封尾原底图并叠加培养目标与结束语。连续稿登记实际构图并调用序列审查脚本；重复是实看提示，清单缺漏/重复页码仍失败。合理同题推理保留题干与对象，不为通过检查换版式或改标签。低层开放画布与舞台接口只为用户明确要求的局部特殊设计保留，不作为常规页入口。


## 紫金组件接口

所有接口接受slide并返回可编辑对象（或对象数组）。

```js
deck.purpleRibbon(slide,'课程体验',{x:48,y:200,w:330,h:64,size:28});
deck.lightFrame(slide,{x:440,y:120,w:790,h:520});
deck.focusPanel(slide,{x:48,y:350,w:440,h:260,kicker:'实际事件',main:'核心主张',detail:'具体支持'});
deck.numberFlag(slide,'50+','参展高校',{x:48,y:220,w:315,h:324,caption:'统计范围与时间'});
deck.starOrbit(slide,{cx:960,cy:410,r:165,main:'每生\n一案',nodes:[{angle:-90,text:'成长目标',tx:850,ty:195}]});
deck.stepBands(slide,[{title:'阶段一',body:'具体内容'},{title:'阶段二',body:'具体内容'}],{x:48,y:500,w:1184,rise:50});
deck.evidenceStrip(slide,'事实类别','完整的关键事实',{x:48,y:610,w:1184,h:52});
deck.facetCorner(slide,{x:48,y:540,w:220,h:100});
```

数值和示例词替换成本次真实内容，不复制示例事件作当期事实。浅色内容与深紫组件要保持对比；画布边界、标签和原图署名仍逐页检查。

## 编号、图标与图文组合

| 接口 | 用途 |
|---|---|
| `schoolIcon(slide,kind,{x,y,size,color,badge,fill})` | 原生线性图标；kind为book/people/target/globe/chart/cap/case/calendar/science |
| `numberBadge(slide,label,{x,y,size,fill,color})` | 圆形编号或短符号，不代表占比 |
| `iconLabel(slide,kind,title,body,{x,y,w,iconSize,fill})` | 图标、短标题和必要说明就近组合 |
| `photoLabel(slide,label,{x,y,w,h,fill})` | 图片图注或主题色标 |
| `pointBand(slide,items,{x,y,w,h,fill})` | 横向主题组，items包含icon/text |
| `sectionRule(slide,label,{x,y,w,size})` | 无既定页眉的局部标题工具；常规正文不重复添加第二标题区 |

复杂关系可用原生customPaths、连接线、表图及上述组件组合。文字、图形和线条保持可编辑，不能以组件数量代替信息完整和实际页面检查。

## 题名与草稿

`writeDraft`保存候选PPTX后，调用`renderSavedDeck`从保存文件重新导入。每次使用新的run目录，返回PNG、实际layout及`render-manifest.json`，记录源文件和各页图片SHA-256，状态始终为`unreviewed`。不再渲染保存前的内存对象充当最终证据。

对已有或随后补附件/动画的最终文件，只读重渲染，不重新导出PPT：

```js
const preview=await renderSavedDeck({candidatePath:finalPptx,renderDir,scale:1.5});
// 局部修复可传slides:[受影响页码]；只声明该范围复查。
```

预览成功后按[四项验收](review.md)看实际页面，并按[记录格式](review-record.md)补真实观察。混合场景若全部页使用同一用途，应复核选择是否合理；即使不同用途参数齐全，主体仍同构也需修改。`addParentPage`等历史便捷布局只适合其特定照片材料，不替代家长作品反馈的构图选择。

自动中文题名用具体议题短语，课堂问句放任务区；四、六、八字是编辑偏好。正常英文与学科专名不按12字位硬截，长中文由保存后检查提示实看实际换行。用户给定正式题名可用userSuppliedTitle保留，并在验收时对应原要求。

署名或日期缺失时可先准备完整主体内容与页面底稿；需要构建时传明确的待填草稿值，不虚构真实身份或日期。正式验收仍拒绝未补字段。
