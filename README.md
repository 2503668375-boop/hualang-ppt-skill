# 华朗学校通用汇报

基于**佳兆业公司汇报规范**，使用华朗学校紫金品牌模板，制作可编辑 PPT 与配套 Word 一页纸。当前版本 **v2.0**。

内部汇报继承佳兆业的内容深度、论证、信息密度和验收要求。课堂、家长和对外展示再按用途调整，用图表、图解和组件承载信息。英文与双语版本分别组织语言和版面。

## 先按用途选择写法

| 用途 | 内容与排版重点 |
| --- | --- |
| 集团领导、校务会、经营及专项汇报 | 短业务标题、正式概论、完整依据；同页核对目标、实际、差额、原因及行动，保留费用、比较、责任和时点。正文黑字，重点红色，紫金用于华朗品牌。 |
| 学生课堂、复习和复读备考 | 概念图解、例题批注、错因对照、变式练习、任务与评价组件；保留题干、条件和推理。 |
| 家长沟通、招生说明 | 课程路径、同维度比较、学习反馈、家校行动；把家长需要判断和配合的内容讲清楚。 |
| 对外演讲、教学交流 | 清楚主线、真实案例、图文证据和数据可视化；按讲述节奏组织页面。 |
| 英文及双语 | 核对术语和事实，重新断行排版；用必要术语、图解和句式支架支持理解。 |

减少冗余文字后，信息应由图表、图解和组件承接。内部阅读型报告不会因“大字号、少字、留白”而变成提词卡；特殊展示也不能只剩几个口号。

## 看模板与实际页面

[![华朗学校通用汇报模板总览](demo/overview.jpg)](demo/example.pdf)

[阅读 15 页示例 PDF](demo/example.pdf) · [下载可编辑 PPTX](artifact-template-hualang-school/assets/reference.pptx?raw=true) · [阅读使用说明](docs/使用说明.pdf)

<a href="demo/internal.png"><img src="demo/internal.png" width="49%" alt="内部汇报示例：完整呈现经营依据、数据比较和后续行动"></a> <a href="demo/education.png"><img src="demo/education.png" width="49%" alt="教育展示示例：用图表、图解和学习任务组件组织信息"></a>

示例涵盖经营总览、招生转化、预算差异、方案比较、跨期排程、学情质量、开放日，以及课堂、复习、家长、英文和对外交流。**示例数据与安排用于展示版式，不代表华朗学校实绩或已批准计划。** 组件库的页数和顺序不构成每次汇报的固定提纲。

## 下载与安装

复制这句话，发给 **Codex 或 WorkBuddy**：

```text
请从 https://github.com/2503668375-boop/hualang-ppt-skill/tree/main/artifact-template-hualang-school 下载完整的「华朗学校通用汇报」技能，安装到当前工具的个人技能目录，并核对模板与参考文件完整。
```

也可[下载整个仓库 ZIP](https://github.com/2503668375-boop/hualang-ppt-skill/archive/refs/heads/main.zip)，按所用工具的技能安装方式，安装其中的 `artifact-template-hualang-school` 文件夹。

首次使用时附上材料，说明对象和用途即可，例如：

> 用华朗模板，把附件做成给集团高管看的月度经营汇报，展开招生差额、预算与实际、原因和责任节点。

> 用华朗模板，做一套高一数学复习课件，保留例题推导，增加错因对照和变式练习。

> 用华朗模板，做一份面向家长的课程说明，把选择路径、适用条件和家校配合可视化。

也可以直接调用 `$artifact-template-hualang-school`。已有要求和资料直接沿用，只补问影响结果的缺项。

## 技能内有什么

- [技能入口](artifact-template-hualang-school/SKILL.md)：按内部汇报与教育特殊场景选择流程。
- [佳兆业规范继承说明](artifact-template-hualang-school/references/kaisa-inheritance.md)：继承 v3.7 的哪些要求，以及华朗品牌和教育场景如何适配。
- [可编辑 PPT 模板](artifact-template-hualang-school/assets/reference.pptx?raw=true)：正文、表格、图表与关系图保持可编辑。
- [原始 2023 年模板](artifact-template-hualang-school/assets/source-original.pptx?raw=true)：保留校徽、字标和校园素材的原始参考。
- [Word 一页纸母版](artifact-template-hualang-school/assets/one-page-report.docx?raw=true)：用于独立简报或需配套的一页纸，具体内容按本次议题安排。

模板使用 PingFang SC 与 Arial。更换电脑或字体后需重新检查换行、图表和表格；PDF 用于阅读预览。

## 后续维护

后续优化在本仓库持续更新，记录在 [CHANGELOG](CHANGELOG.md)。每次修改同时核对技能规则、模板、样页和个人安装版；修改了版式或字体，就重新查看受影响的实际页面。

仓库校验可运行：

```bash
python3 scripts/validate_package.py --expected-slides 15
```

该检查核对文件、相对引用和原生对象结构；文案质量、有效信息密度、实际显示及数据含义仍需人工查看。

校徽、校名及校园素材不因本仓库公开而授予商标或其他使用权；本仓库不代表学校的正式对外发布。
