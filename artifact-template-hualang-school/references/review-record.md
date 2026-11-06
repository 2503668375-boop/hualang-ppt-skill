# 审查记录与签收条件

记录是制作者和审查者的实际观察，不能由导出脚本代写。`review_gate.py`只阻止记录自相矛盾、版本不一致、漏页和问题未关闭；不能判断观察是否真实、图像内容是否与页面相符，也不能认证审美。

## 从最终预览建立记录

`renderSavedDeck` / `writeDraft`返回的`renderManifestPath`包含源文件及PNG摘要，状态为`unreviewed`。复制这份清单作为审查记录：

- 保留`schemaVersion:1`、`artifact.path/sha256`、`renderSourceSha256`和各页`render/renderSha256`，相对路径以记录文件所在目录为基准。
- 每页补`scene`、`subject`与实际`verdict`。`subject`写共同数轴、匿名作答修订、实验装置等具体主体，不能只写“两栏”或“丰富组件”。逐页结论为`pass`、`revise`或`unverified`。
- 补以下四项`gates`与`issues`。没有实际观察时保持待核，不为运行脚本填“通过”。

```json
{
  "gates": {
    "content": {"verdict": "unverified", "evidence": []},
    "expression": {"verdict": "unverified", "evidence": []},
    "visual": {"verdict": "unverified", "evidence": []},
    "file": {"verdict": "unverified", "evidence": []}
  },
  "issues": []
}
```

每项`evidence`是`{"slides":[页码],"observation":"具体对象、阅读关系及实际发现"}`数组。内容、表达与场景、视觉、文件各自作结论，不能互相抵消。先看成品，再核任务；跨场景稿须看实际用途差异与整稿联排。没有发现问题时不编造缺陷，证据仍需指向实际对象。

## 问题怎样关闭

每项问题包含`id`、`slide`、`area`、`problem`、`status`，`area`使用四项gate键名。未解决为`open`，记录中仍有任何`open`问题就退回。修复后用`fixed`，补`resolution`及对应新图的`checkedRenderSha256`；复查摘要必须与当前记录的预览一致；实际修改是否完成、图片是否对应修复结果，仍须通过实际页面审查确认。脚本没有修复前图像历史，不能单凭一个摘要证明真实修改。

自动几何提示未必是真实缺陷。经实页判断应保留的同题推理或必要比较，在相应gate观察中记录具体理由；不要将明显越框、不可读或场景同构降级为无关建议。若已确认为缺陷，就必须修复后复查。

完整新稿默认覆盖全部页。局部修订可用`scope:[页码]`，图片与观察只覆盖这一范围；未受影响项可用`not_applicable`并写明理由。完整审查四项均须`pass`，局部结论不能称全稿重新通过。

```text
python scripts/review_gate.py 审查记录.json --output 审查状态.json
```

`return_for_revision`表示仍需修改记录所指问题或补核验；`ready_for_human_signoff`只表示文件与记录条件齐全，待制作者按实际内容、表达、视觉决定是否交付。退出0不代表美观或现场可用。新文件、补附件或动画后源摘要改变，应从最终版本重新建立对应预览；只检查实际受影响范围，不能沿用旧版本图充当复查。

## 实际字形辅助检查

若已有最终PDF且环境有`pdfplumber`，可运行`audit_rendered_pdf.py`检查实际字形是否跨页面或有色面板底边。它只测有限几何，不能识别所有文本溢出、合理叠层或场景表达；`no_measured_issue`也不表示视觉通过。发现项仍须看实页，确认为问题后进入上述问题记录。没有可测字形的页面会列为`unmeasured_pages`并返回需人工复核，不按无问题处理。缺少此依赖时继续实际页面审查，不为检查工具安装无关环境。
