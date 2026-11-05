# 华朗学校汇报与教学 Skill

当前版本 **v6.0**。按华朗固定品牌制作内部汇报，以及初中、高中、国际高中的分学科教案与课件；家长招生和对外演讲采用对应的图文表达。

## V6重点

- **先研究、审改技能，再生成案例**：依据真实教案与教学资料，结合用户要求和已验证的公司汇报方法，重审规则、工具及验收。见[调研与全局审查](docs/v6-research-and-review.md)。
- **学段×学科×用途**：教师教案、课堂讲解、练习、内部审议和对外展示分别组织。教案写清目标、具体活动、预期回应、评价和调整。
- **完整内容与合适密度**：短题可以成组，常规例题可保留完整解答与变式。一页放多少由题长、图形、推理与观看方式决定，不统一成大字号提词页。
- **紫色搭配、黑色阅读**：紫色用于标题、任务带、方法提示、步骤与表头；普通正文和公式黑色，少量红色强调，深蓝用于分析图形。
- **可调用教学组件与原生揭示**：任务带、步骤、方法条、原生表图及图文区域可复用；答案、曲线和批注按点击出现。
- **固定首尾与全局检查**：封面默认一个主标题，汇报人与时间左下同组；保留原模板封尾。检查真实行高、断行、符号、裁切与动画各状态。

## 分学科规则

| 范围 | 参考 |
|---|---|
| 教师教案、课堂、练习、说课 | [教学设计与单页容量](artifact-template-hualang-school/references/teaching-design.md) |
| 初中 | [语数英、理化生、史地道法、技术与艺体](artifact-template-hualang-school/references/junior-subjects.md) |
| 高中 | [完整推理、综合材料、模型与证据](artifact-template-hualang-school/references/senior-subjects.md) |
| 国际高中 | [课程体系、层级、考试年与各学科表达](artifact-template-hualang-school/references/international-subjects.md) |
| 数学题库 | [给题、给章节、题库整理与解答揭示](artifact-template-hualang-school/references/math-teaching.md) |
| 学校内部汇报 | [概论、依据、图表、条件与落实](artifact-template-hualang-school/references/internal-report.md) |
| 家长与对外 | [照片、作品、数字与适用条件](artifact-template-hualang-school/references/parent-admissions.md) |

## 介绍与示例

[![V6介绍预览](demo/overview.jpg)](demo/hualang-skill-introduction.pptx?raw=true)

[下载18页介绍PPT](demo/hualang-skill-introduction.pptx?raw=true) · [下载教学点击预览HTML](demo/teaching-preview.html?raw=true)

第4页为教师教案；第5—10页为初中数学、高中数学、语文、物理、生物及国际数学；第11页为国际经济材料分析；第13—14页为内部管理/资源汇报；第15—16页为家长与演讲。最后一页为原固定封尾。

HTML下载后用浏览器打开，可前进、返回和重置。它展示对应PPT的逐步画面，不等于PowerPoint应用内放映测试。现行场景库保留同一完整演示，避免在裁取页面时丢失动画或图表数据。

![现行场景](demo/scene-comparison.png)

## 安装与调用

首次在支持本地技能的Codex环境发送：

> 从 https://github.com/2503668375-boop/hualang-ppt-skill 安装 artifact-template-hualang-school，保留完整模板和素材。

[下载完整仓库ZIP](https://github.com/2503668375-boop/hualang-ppt-skill/archive/refs/heads/main.zip) · [安装说明](artifact-template-hualang-school/references/getting-started.md)

调用示例：

> 用华朗学校汇报技能，按附件设计高三导数复习课。先给教师的课时教案，再制作学生课件。完整题干、解答和函数图尽量同页，答案按关键推理点击出现，署名与日期按附件。

> 用华朗学校汇报技能，把方案与报价做成校务会审议稿。保留正式概论、同口径依据、图表、费用范围与责任节点，不改变已定和待定状态。

## 规则和验证

[技能入口](artifact-template-hualang-school/SKILL.md) · [视觉规范](artifact-template-hualang-school/references/design.md) · [制作API](artifact-template-hualang-school/references/production-api.md) · [固定首尾](artifact-template-hualang-school/references/cover-layout.md) · [本轮验证](tests/v6-validation.md) · [研究依据](artifact-template-hualang-school/references/research-basis.md)

公开题例和业务数据均有示例标识，生成情境图不代表学校实际活动或成果。实际课程体系、教材与考试年须按任务核实。已检查最终文件、页面与动画状态，未完成Microsoft PowerPoint应用内放映或真实教室投影测试。历史V4/V5记录保留，但当前规范以V6为准。
