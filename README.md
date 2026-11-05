# 华朗学校汇报 Skill

当前版本 **v5.0**。根据材料与使用现场制作可编辑PPT，覆盖学校内部汇报、中学学科教学、家长招生和对外演讲。保留原始校徽、固定封面与紫金配色。

## 本次更新

- **题目决定分区**：支持两道短题同屏、综合题的题干/推导/函数图分区，长题按设问续页。
- **答案点击揭示**：提供PowerPoint原生出现动画工具，题干先显示，推导与答案按步骤出现；函数图可以随等价转化揭示。
- **章节与题库**：给章节时按学段拟题并校核，给题库时保留题号与条件，组织诊断、例题、变式与检测。原创题明确标注。
- **学科表达**：数学用公式与数值坐标，英语与语文用文本证据和批注，理科按装置、变量、方程与现象安排。
- **家长招生**：照片采用主次关系，数字带单位与口径，演讲、活动说明和留阅材料分别编排。
- **五个尺度**：同时检查整稿、整页、分区、组件和字与细节，实际看动画初始态、中间态及末态。

[完整复盘与改进对应](docs/v5-review.md) · [构图方法](artifact-template-hualang-school/references/composition.md) · [数学与题库](artifact-template-hualang-school/references/math-teaching.md)

## 使用介绍

[![18页介绍预览](demo/overview.jpg)](demo/hualang-skill-introduction.pptx?raw=true)

[下载18页介绍PPT](demo/hualang-skill-introduction.pptx?raw=true) · [下载教学点击预览HTML](demo/teaching-preview.html?raw=true)

PPT第6、7页为数学点击揭示，第10页为英语证据句揭示。HTML下载到本地后用浏览器打开，可查看同一页面的逐步状态；它用于展示揭示节奏，不等于PowerPoint兼容性测试。

![教学、图文与演讲实页](demo/scene-comparison.png)

## 开始使用

首次可在支持本地技能的 Codex 环境发送：

> 从 https://github.com/2503668375-boop/hualang-ppt-skill 安装 artifact-template-hualang-school，保留完整模板和素材。

已安装时要求更新并保留旧版。之后附上材料并点名调用，例如：

> 用华朗学校汇报技能，把附件两道导数题做成高三复习课件。保留完整题干，按题目划分页面。答案按关键推理逐次点击出现，函数图与公式对应。署名和日期按附件。

> 用华朗学校汇报技能，把这些校园照片与课程材料做成家长开放日介绍。面向首次到访的家庭，用图片和关键数字讲清学习体验与课程选择，保留全部适用条件。

> 用华朗学校汇报技能，把方案与报价做成校务会费用审议稿，保留已定安排、费用明细、比较依据与责任节点。

[下载完整仓库ZIP](https://github.com/2503668375-boop/hualang-ppt-skill/archive/refs/heads/main.zip) · [安装说明](artifact-template-hualang-school/references/getting-started.md)

## 规则与工具

- [技能入口](artifact-template-hualang-school/SKILL.md)
- [固定封面](artifact-template-hualang-school/references/cover-layout.md)与[文案](artifact-template-hualang-school/references/writing.md)
- [组件索引](artifact-template-hualang-school/references/component-index.md)与[场景版式](artifact-template-hualang-school/references/scene-layouts.md)
- [学科对象](artifact-template-hualang-school/references/subject-layouts.md)与[家长招生](artifact-template-hualang-school/references/parent-admissions.md)
- [制作API](artifact-template-hualang-school/references/production-api.md)与[出现动画工具](artifact-template-hualang-school/scripts/apply_reveals.py)
- [实际检查范围](tests/v5-validation.md)与[研究依据](artifact-template-hualang-school/references/research-basis.md)

需要现有PPT制作运行库。教学文字、简单公式、原生图表与关系图保持可编辑；复杂公式在不同环境中的实现与编辑限制须按实际工具说明。本版未完成Microsoft PowerPoint应用内放映；原生时间线与逐步状态已检查。示例题、虚构预算与活动安排均有标识，生成情境图不代表学校真实活动或办学成果。

V4历史测试保留在[历史记录](tests/README.md)，不作为V5现行版式。原始品牌资产保留，不扩大其授权使用范围。
