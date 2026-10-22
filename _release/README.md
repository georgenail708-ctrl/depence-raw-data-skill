# Depence Raw-Data Skill — 喷泉全帧原始数据 skill / Fountain Frame-Level Raw Data Skill

**中文** | [English below](#english)

这是给 AI 用的 **Depence 喷泉软件原始数据技能包**：210 首真实喷泉节目的**逐帧 DMX 输出原语、原始增量链、全套设备布局与配接、逐音符 MIDI 与音乐深度分析**，全部带来源哈希、校验和与"未知项声明"。配合 **Depence MCP** 接入后，AI 可以在真实工程数据上理解"编曲如何逐帧随音乐发生"，显著提升对真实项目的操控与编排能力。

> **定位声明**：本 skill 是原始证据库与查询工具，**不包含编曲审美规则**。它要求 AI 通读原始数据自行内化——冲突时以原始数据为准。

## 数据规模

| 层 | 歌曲数 | 说明 |
|---|---|---|
| rendered_output | 46 | .oss 渲染缓存真实帧（60fps 稠密 + 零推导增量原语链） |
| rendered_output_raw_variant | 3 | 旧录制器流（字节零损失，编解码开放） |
| saved_clip_facts | 9 | DMXT frames_blob 逐 clip 录制帧（地址自描述） |
| saved_scene_facts | 138 | Scene 保存事实（源文件无渲染帧，如实标注） |
| derived_scene_render_v1 | 14 | Scene 事实推导帧（v1 语义，明确标注非 DP 渲染） |
| **合计** | **210** | 音乐匹配 204/210 |

每首歌四件套：`<id>.npz`（帧）+ `<id>.record.json`（音乐逐音符对齐/深度分析/溯源 SHA/未知项声明）+ `<id>.project.json`（全套设备布局/DMX 配接/模式通道定义/通道-ID 映射表）+ QA 报告；渲染层另有 `<id>.raw.npz`（原始增量链）。

## 快速开始

1. 把整个仓库放进你的 AI 工作目录（或作为 skill 安装）。
2. 读 `SKILL.md` —— 这是给 AI 的总入口：遍历纪律、数据健康、查询指南、18 个外部数据分卷的 Drive 定位与 SHA-256。
3. 用 `scripts/` 里的查询工具按歌/按帧/按设备取数（详见 `references/query-guide.md`）。
4. 原始 18 分卷（约 3.4 GB）不在仓库内：`catalog/archive_parts.json` 有每个分卷的文件名、长度、SHA-256 与获取方式。

## 这套数据怎么来的

- 直接解包 Depence 工程归档（.depence = project.xml + .oss 渲染缓存 + .show 时间线）与 .dmxt 时间线 JSON；
- .oss = Depence 渲染缓存（每帧真实输出的增量链，frame_index 主轴），格式经独立字节级逆向并双源互证；
- 音乐层 = 逐音符修正解析器 + 逐秒统计 + librosa 实测（tempo/beat/和弦/结构）+ 转写产物；
- 全程哈希溯源，未知/缺失逐项声明，**不做任何插值伪造**。

## 适配的 AI 工作流

配合 [wubaiji DMX512 FOUNTAIN FRONTIER CONTROLLER](https://github.com/georgenail708-ctrl/wubaiji-ultra-DMX512-FOUNTAIN-FRONTIER-CONTROLLER)（DMX512 喷泉主控源码）与 **Depence MCP** 使用：AI 通过 MCP 连接真实 Depence 工程 → 用本数据集理解真实编曲的逐帧结构 → 对新音乐产出可落地的编曲。

## English

A skill package giving AI access to **frame-level raw DMX output, primitive delta chains, full device layouts/patching, and note-level MIDI with deep music analysis** for 210 real fountain shows (18 external 200MB data shards, SHA-256 indexed). Built by unpacking Depence project archives (.depence/.dmxt), byte-level reverse-engineering the .oss render-cache format for interoperability, and cross-validating against .dmxt timelines. Designed for use over **Depence MCP**: the AI reads real per-frame choreography data and learns how shows actually follow music — no aesthetic priors, raw data first. Code: MIT. Show data: CC-BY-4.0. Third-party formats belong to their owners; no proprietary code included.

## License

- 代码/工具：MIT
- 喷泉节目数据（本人作品）：CC-BY-4.0
- 引用的第三方格式与商标归各自所有者
