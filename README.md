# 辛巴达社媒自动发布 · Xinbada Social Publisher

适用于 Codex 的 Facebook 产品推广技能：从 [Xinbada 官网产品目录](https://www.nutricdmo.com/product/) 随机或指定选品，生成英文 B2B 文案和四宫格配图，并通过已认证的浏览器发布到指定主页。

**固定发布目标：[Facebook 主页 61589310638473](https://www.facebook.com/profile.php?id=61589310638473)。**

## 功能与范围

- 遍历完整产品目录分页，去重后随机选品；支持指定产品链接。
- 只使用当前产品顶部概览中的标题、摘要、规格和主图；排除通用详情模板、FAQ、推荐产品中的其他产品信息。
- 保留原始页面和字段来源，校验提取范围；仅当当前产品允许使用的字段或主图之间存在冲突时拒绝候选，不用通用模板补全缺失信息。
- 生成 80–150 词英文 B2B 文案、关键词计划和一张四宫格图片；社媒文案不含网站链接或裸域名，产品来源链接仍保存在本地记录与发布清单中。
- 导出无 EXIF/XMP/ICC 元数据的 WebP 和临时上传 JPEG；尺寸为 960–1600 方形像素，每张不超过 750 KiB。
- 发布前核验主页身份、权限、文案、图片及预览；记录提交历史，发布结果不确定时先核查，最多重试一次。
- 支持 dry-run、明确指定批次的恢复和中文运行清单。
- Facebook 核验成功后，自动写入 [social-auto-upload](https://docs.google.com/spreadsheets/d/18iLpJ7bpDbJzxYtg0vsSOQxOR2e0KBuMI9C7LK0MhAw/edit#gid=0)，按 Facebook 链接去重，站内与 LinkedIn 两列留空；读回核验通过后才标记完成。

发布渠道仅包含 Facebook；Google Sheets 是必须的发布登记步骤。站内文章、LinkedIn、网站 API 和自动创建定时任务不在此技能范围内。写表失败仅修复登记，不重复发帖。

## 文件

- [`xinbada-social-publisher/SKILL.md`](xinbada-social-publisher/SKILL.md)：技能入口。
- [`references/`](xinbada-social-publisher/references/)：内容规范、选品规则和发布流程。
- [`scripts/`](xinbada-social-publisher/scripts/)：抓取、图片优化、批次校验、状态记录和离线测试。
- [`xinbada-social-publisher.zip`](xinbada-social-publisher.zip)：可分享安装包，包含完整技能目录。

## 安装

下载并解压 ZIP，将其中的 `xinbada-social-publisher` 文件夹放入 Codex 的用户技能目录，通常是 `~/.codex/skills/`。保留 `SKILL.md`、`agents/`、`references/` 和 `scripts/` 的相对位置。

已有同名技能时，先对比版本并备份现有修改，再决定是否替换。

运行依赖：

- Python 3.10+ 和 Pillow，脚本中的发布记录文件锁使用 Unix `fcntl`，适用于 macOS/Linux。
- Codex 可用的 `imagegen` 技能及图像生成工具。
- 实际发布需要可控制的已登录 Chrome 会话，或具备等效身份校验与发布能力的连接器，并拥有目标主页的发帖权限。
- 自动登记需要 Google Drive/Sheets 连接器及目标表格写入权限。

在选定的 Python 环境安装 Pillow：

```bash
python3 -m pip install Pillow
```

Python 脚本负责抓取、校验及记录；Facebook 操作和图像生成由 Codex 调用相应工具完成。这不是无需 Codex 的独立发帖程序。

## 使用

在 Codex 中明确请求运行，例如：

```text
使用 $xinbada-social-publisher，随机选择一个产品，完成预检后发布到指定 Facebook 主页，返回中文发布清单。
```

仅生成和检查素材，不实际发布：

```text
使用 $xinbada-social-publisher 执行 dry-run。
```

指定产品：

```text
使用 $xinbada-social-publisher 发布这个产品：[填写 nutricdmo.com 的完整产品详情链接]。
```

明确请求实际运行即授权通过预检后发布；创建、查看或修改技能不等于授权发布。登录、MFA、验证码、身份或权限不明确时会停止。需要定时运行时，请另外指定日期、时间和时区。

## 校验

从仓库根目录执行离线回归测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 xinbada-social-publisher/scripts/test_workflow.py
```

2026-11-12 更新：社媒文案不再包含网站链接；27 项离线回归测试通过，覆盖无链接发布、链接拦截、CTA 校验及旧批次登记兼容。

2026-10-15 的本地校验结果：

- 技能格式校验通过，24 项离线回归测试通过，包括模板污染排除、当前产品冲突识别、主图边界、旧提取数据拦截，以及写表去重、空列、读回证据和不重复发帖保护。
- 官网只读目录测试遍历 20 页，取得 238 个去重产品链接；目录数据会随网站更新变化。
- 源码与技能 ZIP 逐文件一致，ZIP 完整性检查通过。

测试中的 Facebook 状态与截图均为本地模拟。上述结果不表示已完成真实 Facebook 登录、生成素材或发帖验收。运行产物、网站抓取样本、账号会话和本地验收目录不随本仓库发布。
