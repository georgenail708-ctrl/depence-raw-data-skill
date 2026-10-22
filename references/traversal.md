# 原始资料遍历与覆盖账本

## 范围

全库初始账本包含全部 517 个 source_song_id，不以 supplier selection 或 claimed duplicate 筛掉任何组。每组列出其 record/project/NPZ/分析等实际成员，以及目录能建立的 MIDI/音频候选关系；这些关系本身不是音乐身份或同步证明。未关联到具体曲目的安全目录成员放在 __archive_supplement__，也必须给出读取/审阅处置，不能因未归类而遗漏。初始账本覆盖全部 2,551 个可分发原始数据成员；不收录私密交接、密钥工具或旧艺术规则。

如果用户只问明确子范围，先记录该范围，仍报告未覆盖的关联上下文；不要把局部结论扩展成全库结论。任何审美决定由使用本库的 AI 结合音乐知识与需求作出，不从统计共性硬套成规则。

## 实际命令

在 skill 根目录创建账本（不会覆盖已有文件）：

    python scripts/traversal.py init --out coverage-000.json
    python scripts/traversal.py next --ledger coverage-000.json --limit 10
    python scripts/traversal.py summary --ledger coverage-000.json

init、next 和 record-window 本身不会读取音频、帧或其他原始内容；它们只是导航和覆盖记录。实际读取/解析必须通过原始成员读取器及对应格式的解析过程完成，并留下可回查证据。

next 的 limit 只是工作队列分页，不是“只检查十个就算完成”。初始化不会把任何成员标为已校验、已读或已理解；已接受的 127 Scene 帧缺失会独立显示。零读取状态也不能宣称已完成全库审阅。

选择单成员后，用 archive_reader 的本地/有界云端读取通路获取原始字节，先验证：

    python scripts/traversal.py verify-member --ledger coverage-000.json --song a1_1035 --member '01_数据集_songs/a1_1035.analysis.json' --path /path/to/verified/a1_1035.analysis.json --out coverage-001.json

读取完整 2,352 字节的这个成员、确认解析完整而非终端截断之后，才能记录原始读取：

    python scripts/traversal.py record-window --ledger coverage-001.json --song a1_1035 --member '01_数据集_songs/a1_1035.analysis.json' --stage raw_read --start 0 --end 2352 --evidence /path/to/read-receipt.json --scope-note '完整解析此源分析JSON；其中音乐结论仍是待回查的分析主张' --out coverage-002.json

semantic_reviewed 使用同样命令，但仅在确实回查并逐项审阅后记录。evidence 应指向具体读取/解析/比较产物，scope-note 必须说明曲目、时间/帧/样本区间、设备/通道范围、原始来源和仍未知内容。该字段是可审计的工作记录，不是自动证明 AI 理解正确。

账本窗口为提取后的原始字节半开区间 [start,end)，并不把字节位置当作音乐时间。对于 NPZ、MIDI、音频、项目 XML 等容器，读完整容器字节仍须另外遍历实际数组/事件/样本/设备树；不能仅看文件头、统计值或一个样本就把整个容器标为语义已审阅。用证据产物记录这些实际语义区间，账本只负责保留指向与未完成状态。

## 控制帧和音乐对应的原始顺序

1. 原始成员的身份/CRC/SHA与来源先固定；按源 ID 关联，不能按相似文件名随意换曲。
2. dense 数据逐时间窗遍历全部应检通道，first-write 之前和从未写入是 UNKNOWN。纠正数组优先，但回查 raw/source 才能建立来源真实性；保留零写入与事件顺序。
3. opaque 数据完整头/事件/payload/尾部逐条保留，未解码就明确未解码；Scene 为保存事实而不是实测输出。9 clips 无原生时间字段，整数桶不能自动变成原始均匀时间轴。
4. 设备树、显式 slot 起点及地址多候选都读取。缺 width/fine/historical patch 证据时不强行指定控制值归属。
5. 音频本身与 MIDI 的实际事件都可单独读取；分析/QA仅导航。对齐必须区分保存 offset、估算 lag、独立验证值，缺身份或 native clock 时不能声称精确对应。
6. 每个窗口完成后保存新账本版本；中断后 next/summary 继续。发现缺失、歧义、未解码或无音频时写明处置，不默认跳过、不虚构数据。对全部可用资料报告完整覆盖前，检查 pending 为零且语义证据真正覆盖所称范围；来源限制仍单独保留。

统计完成率不替代原始审阅。总 SHA、单文件 SHA、行数和覆盖账本只是完整性与工作范围工具，不是艺术判断，也不是“全部原始项目已恢复”的证明。

## 顺序读取，而不是单点采样

MIDI 事件与音符有有界游标，保留每条原始 track/order/tick/source_byte_offset 等字段：

    python scripts/music_query.py --song a1_1035 --source reference --kind events --cursor 0 --limit 50
    python scripts/music_query.py --song a1_1035 --source transcription --kind notes --cursor 0 --limit 50

每页返回 cursor、end_cursor、total_records、next_cursor、eof 和原样记录。按 next_cursor 连续续读，不得跳页或只看计数。eof 仅证明这一页已到末尾，只有连续覆盖 [0,total_records) 并审阅每条记录才能称该集合已遍历。没有参考 MIDI 的 glimmers_end 应显式使用 --source record-only --kind notes，不能替换成另一首 MIDI。需要完整程序化对象时使用 --all 并重定向到文件，不能依赖被截断的终端输出。

DMX 连续帧窗输出包含每个扁平通道，不按活跃度筛掉零或静态设备：

    python scripts/dmx_window.py --npz data/dmx/corrected/pengquan124_blk8_118s.corrected.npz --sha256 96fb7b1768a6bc878150bd182906e591c9b9895fe82c6d69e0b80fd110246bc3 --start 0 --count 60 --out window-000000.jsonl

每次最多 120 帧，文件为一行元数据加逐帧 values 数组；数组下标就是源扁平通道 ID，null 表示 UNKNOWN，0 保留为已写零。按返回 next_frame 连续续读，直到 eof，并核对窗口没有空隙或重叠漏记。它输出选定派生数组的所有通道，不证明物理 patch 或音乐时间正确。opaque、Scene 和 cN clips 格式不能伪装成 dense 传给此脚本。

账本还分别列出最终 DMX manifest 的 26 个纠正/恢复组件。用完整键例如 component:data/dmx/corrected/pengquan124_blk8_118s.corrected.npz 记录其验证与覆盖；这些键不是原归档成员，不能用它们冒充旧 NPZ 的 CRC或覆盖证据。原始成员和派生组件都保留各自条目。

summary 同时显示引用次数和 distinct unique member 数。一个 MIDI 被多首资料引用时，验证一次可为多个关联提供同一字节证据，但不能把 300 个实际成员说成 740 个不同成员已经审阅；曲目关系与上下文审阅仍各自有记录。

## 时钟域核验

参考 MIDI、转写 MIDI、DMX 分块帧索引和工程/音频全局时间是独立时钟域。目录保存的 offset 及 frame/FPS-offset 公式只是来源或旧派生主张，不是已验证对应。必须先核对局部分块原点、工程原点、符号、速率、素材身份与时长覆盖，不能因存在公式就套用。例如水仙十字_blk2_240s 的保存偏移用于字面换算会超出两套 MIDI 时间范围，应记录冲突和 UNKNOWN，不延伸音乐或控制值。music_query.py 支持 --base 指向完整解包根目录；分页本身不会建立时钟对应。

## v2 关系与低优先级观察

先读逐源coverage矩阵和独立pair gate。旧mode字典、首个重叠音频offset和名字/时长匹配都可能是错误关系，必须用当前版本来源修复，不能因字段存在就信任。完整原始遍历仍为必需步骤。

用户允许经过反复验证的艺术观察成为低优先级可选参考，但必须有证据、适用范围、条件和反例，不能把一次试读推广成普遍规律，不能替代原始资料遍历；冲突时原始数据优先。本版本没有将本轮个案解释登记为已验证艺术规律。
