# 文件与查询

## 离线依赖和版本

打包组件必须先通过 python scripts/verify_bundle.py；该检查逐文件核对冻结长度/SHA，并拒绝未冻结版本或缺失文件。它不重新验证音乐对齐或来源完整性。

运行脚本只需 Python 3 标准库，不需要模型、SDK、NumPy 或设备。命令中的路径由使用者明确提供。skill 文件夹可放在任意工作目录，不必安装到软件配置目录。

catalog/components.json 固定各组件版本。发布包的组件数据位于 data/registry、data/dmx、data/music。若组件路径不存在，报告缺失，不声称结果已加载。没有整个 3.65GB 原始归档时，嵌入组件仍可查询，但未嵌入原始文件不可读取。完整原始 ZIP 解压体积更大，不需全量展开。

如需整包本地校验，原始18分片需保持 catalog/archive_parts.json 中 filename 名称，放到一个外部目录。先验证：

    python scripts/archive_reader.py --parts-dir /path/to/original-parts verify

验证逐一计算 SHA-256 并比较串接 SHA。extract 的 CRC/长度检查不等于当次校验了全部本地分片；返回字段明确区分历史完整性收据和本次校验。

## 原始文件

精确查询源组：

    python scripts/query.py assets --song glimmers_end
    python scripts/query.py search --text tothemoon

推荐先联合读取当前作用域与证据：

    python scripts/query.py song --song glimmers_end

它将 registry v3、policy overlay v4、最终 DMX 和音乐目录按精确 ID 关联；overlay 的本轮 Scene 接受范围优先，最终 DMX 优先于旧 registry frame_evidence。各证据分别输出，不据此升级音乐对齐或历史设备归属。audio v3 若已安装，另外输出按源 ID 匹配的音频字节/文件头校验；它不意味着已听辨全曲、控制帧已同步或所有音频关联已证明。

也可查看单组件 source ID 的工程、record、音乐或 DMX 审核事实：

    python scripts/query.py row --file data/registry/canonical_registry_v3.jsonl --song glimmers_end
    python scripts/query.py row --file data/dmx/dmx_manifest_v1.jsonl --song pengquan124_blk8_118s
    python scripts/query.py row --file data/music/song_music_catalog.jsonl --song glimmers_end

如果最终 registry 版本更高，使用 components.json 中冻结路径。每一组件保留原文件内容；里面的历史工作目录路径不是可移植地址。context_evidence.normalized_path 取 basename 后从 data/registry/normalized_contexts 读取；DMX recommended_npz 取 corrected/ 或 restored/ 相对路径后从 data/dmx 读取。不得尝试依赖原机器绝对路径。

精确取单个原始成员（输出父目录需已存在；拒绝覆盖）：

    python scripts/archive_reader.py --parts-dir /path/to/original-parts extract --member '01_数据集_songs/glimmers_end.record.json' --out /path/to/output/glimmers_end.record.json

默认最大单成员输出 1GiB，可用 --max-bytes 缩小。按目录元数据核对所需可用空间；脚本仅流式提取所选成员，不恢复整个 ZIP。CRC 与长度必须通过，存在固定成员 SHA 时一并验证；否则计算 SHA 留作来源记录，但不称其为预期 SHA 验证。只有目录允许的成员可通过 CLI 提取。

## 一个已知 DMX 单元

在 DMX manifest 选定 recommended_npz 及 sha256 后，用准确路径与该哈希：

    python scripts/dmx_value.py --npz data/dmx/corrected/pengquan124_blk8_118s.corrected.npz --sha256 96fb7b1768a6bc878150bd182906e591c9b9895fe82c6d69e0b80fd110246bc3 --frame 174 --channel 783

这是 0 基帧号、0 基扁平源通道 ID，不自动换算物理设备或秒。此例纠正值为 0，旧数组为 220。脚本读取完整 NPZ SHA 并检查 first-write 遮罩；未写通道返回 value:null、status:UNKNOWN。它不替代原链重放证明，不把任意未经审核数组升级为真实性已验证。

## MIDI 与音乐事实

推荐 python scripts/music_query.py --song glimmers_end --source record-only --kind notes；它按曲目和来源分页返回原始事件或音符，并保留来源目录；沿 next_cursor 遍历至 EOF 才覆盖该来源的全部记录，逐一核对 catalog、原始 MIDI、派生事件及额外 record 音符文件的冻结 SHA。data/music/load_music_v2.py 是已加固的底层辅助入口，使用前需完成包级验证；音乐来源目录、原始 .mid、events/*.json.gz、notes/*.json.gz、deterministic_note_facts.jsonl.gz 均分层保留。任何 offset 必须同时报告是保存 offset、QA 最优 lag 还是独立验证值。

原始音频依赖外部 archive_parts，而不是此 skill 的附件内嵌音频。用 query.py search 找精确成员后通过 archive_reader.py 提取；不能只因名称一样就判定它和 record 中的音频是同一版本。

## 云端按范围取原始成员（不需保留所有分片）

单成员读取只需要它实际涉及的分片；上面的 verify 才需要全 18 个本地分片。空间不足时，用 scripts/range_source.py 的 RangeParts(manifest, fetch) 接入调用方已有的授权 Drive 连接。fetch(part_index, local_start, byte_count, expected_part_size) 返回恰好 byte_count 个 bytes；part_index 与 start 都是 0 基。RangeParts.read 可直接传给 archive_reader.extract 所需的 source 对象。

使用方协议：
1. 由 catalog/archive_parts.json 中的 drive_file_id 读取官方元数据，核对 ID、filename、size、modified_time（及可用的 created_time）；不得凭同名文件替换。
2. 只为需要的分片请求新鲜官方下载引用；签名 URL 和授权头只在内存中保留，不写到参数日志、文件或输出。库不携带登录、SDK 或私有令牌，也不自行刷新授权。
3. 可用 EphemeralHTTP(grant) 作为 fetch。grant(part_index) 返回内存里的 url 与 expires_at_epoch；剩余有效期不足60秒时拒绝请求。调用前再次核对元数据，失败后核查而非盲目重试。
4. 必须使用 Range: bytes=start-end、HTTP206、精确 Content-Range: bytes start-end/part_size；HTTP200、重定向、长度不符、压缩传输和过量响应均拒绝。默认单次读不超过1MiB，跨片由 adapter 分段。
5. 成员解压后校验长度、CRC、已有成员 SHA。下载引用并不证明本次验证了整个归档；保持历史整包收据与当前成员校验分开。若源元数据改变，停止使用冻结目录并重新验证来源。

只有调用方在当前运行环境确实有授权 Drive 连接时，该可选路径才可使用；没有连接时报告依赖缺失。现有原始数据仍是外部依赖，不会因提供 adapter 而变成内嵌附件。

## 空间、设备组和当前地址候选

python scripts/context_query.py --song 水仙十字_blk2_240s --section groups --limit 50

python scripts/context_query.py --song 水仙十字_blk2_240s --group '42x 2-Axis Jet  - 15m ' --out group-page.json

精确组名包括原始空格。该入口校验 registry 与 context 的冻结哈希，保留成员顺序、GUID、原始位置字符串、rot、mode slot 及同一候选地址上的全部冲突。支持 --base、--cursor、--limit；必须沿 next_cursor 读完，不能把一页说成全部。它将来源中的旧绝对路径按源 SHA 定位到包内文件，不依赖制作时的目录。

pos_*_cm 是源字段单位标签；旋转轴顺序、舞台/观众视角及历史 patch 不能自行补齐。slot 起点与 channel-to-action（高度、角度、流量等）转换不是一回事。只有独立确认历史对应后才可将组的候选地址投向控制帧；否则报告候选与碰撞，不输出“某设备实际动作”的断言。

对已证实的映射做组间同步或反例比较时，应遍历每个选定成员的每个帧窗口，保存完整索引范围及不相符的具体索引和值；0、1、UNKNOWN 分别保留。dmx_window 输出全通道原值可用于这一步，不能只比较起止帧就断言整段对称。另列控制块帧范围、各 MIDI 的 EOF/原点和已知缺段；块名、保存偏移或 EOF 都不能自动证明“完整原曲”。

音频字节/头信息见 data/music/audio_verification_v3/audio_catalog.jsonl，音频与 record 的来源关联主张见 audio_record_associations.jsonl；query.py song 同时返回两者。191项头信息成功不等于全音频解码或聆听，1项格式未建立，不能以扩展名猜测。目录中已加入192项实际成员 SHA，提取时会自动核对。

## 私有备份分片定位

catalog/archive_parts.json 保留经校验的原始 Drive 来源；catalog/archive_parts_backup.json 提供私有备份的独立 ID 和元数据时间。18个备份分片均已完整读取，逐片及串接 SHA 与原始来源一致，收据见 catalog/source_copy_integrity_receipt.json。云端调用 RangeParts 时可显式传入任一定位表；必须使用所选表中的 ID/时间验证，不能混用原始文件与副本元数据。本地文件名及字节布局相同。备份仍是外部依赖，不代表内嵌了3.65GB归档。

## v2 检索与功能修复

先运行 python scripts/verify_bundle.py。

- 全库逐源矩阵：python scripts/query.py coverage --song 水仙十字_blk2_240s
- 独立配对闸门：python scripts/query.py pair-status --song 水仙十字_blk2_240s
- 实例模式与几何：python scripts/context_query.py --song 水仙十字_blk2_240s --group '42x 2-Axis Jet  - 15m ' --out group.json
- 完整实例特征/物理对象/profile来源：python scripts/device_semantics.py --song 水仙十字_blk2_240s --fixture b4d7a937-ff25-4f8f-852b-49fbfff8e9ee --out fixture.json
- 指定所返回的source_profile_index可追加 --profile-index N --x 0.5：精确结点保留全部值；只有明确非spline且严格递增结点才返回标记为数学派生的分段线性值。重X、spline及域外值不猜解，不自动变成水压/角度/高度。
- 全组连续帧：python scripts/group_trace.py --song 水仙十字_blk2_240s --group '42x 2-Axis Jet  - 15m ' --npz 具体推荐NPZ路径 --sha256 对应冻结哈希 --start 0 --count 120 --out trace.jsonl
- 独立音乐窗口：python scripts/music_compare.py --song tothemoon_blk0_0s --reference-start 180 --reference-end 184 --transcription-start 180 --transcription-end 184
- 创作时间块：python scripts/clock_query.py --song 水仙十字_blk2_240s --local-seconds 4.8
- 名义帧检查：python scripts/clock_query.py --song 水仙十字_blk2_240s --nominal-frame 11965

group_trace校验NPZ必须是该源ID推荐件，保留每次组成员出现、原始order、GUID及全部槽；不得按相同order去重。首槽由逐fixture字段计算，不假定等间距。输出全部所选成员/槽对应的原始列，0、1、before_first_write、never_written、out_of_capture分别保留。每窗最多120帧，沿next_frame完成指定范围；输出仅为当前地址候选下的原值，不证明历史设备归属或水形可见。DMXT宇宙标签若尚不能绑定捕获列则拒绝此路线，不猜0/1基。

music_compare要求两套来源各自明确窗口，保留跨边界音符、原索引和原始事件指针；每个来源独立分页。它展示精确元组差异，不自动选“参考真值”，也不合并音符或假设两时钟已同步。原始未配对note-on/off依旧通过music_query --all访问，不发明声学持续时间。

DMXT资料用context_query的fixture_defs/fixture_groups/splines入口读取，组名歧义时用组ID。python scripts/dmxt_channel.py --song 精确源ID --fixture 原始fixtureID --channel-index 0 --value 255 按该源定义的dmx_min/max返回所有匹配区间；省略value表示UNKNOWN。重叠/未覆盖区间不强选，返回原定义和来源；此值由调用者提供，不声称已从录制帧观察到。*_fine名称和motor_ranges原样保留，不猜字节顺序或物理变换。

clock_query同时返回配对闸门；现有结果均不允许同步使用。只看authoring对象位置时可用分段查询，但不得把它当已确认音频sample位置。data/music/clock_bridge_v4原manifest保留收集清单，本包排除两个制作期build脚本，以components实际清单为准。
