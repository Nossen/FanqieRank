# Codex 自动化任务说明

这个项目采用和 `Nossen/gitPopular` 类似的双层自动化：

- GitHub Actions 每天北京时间 16:10 采集番茄男频/女频新书榜，并用规则兜底生成可发布页面。
- Codex 自动化每天北京时间 16:30 在本地仓库做双频道深度分析，分别写入 `data/channels/male/analysis/YYYY-MM-DD.json` 和 `data/channels/female/analysis/YYYY-MM-DD.json`，再运行 `finalize` 覆盖为 Codex 分析结果。

Codex 自动化必须先执行硬门禁：

```sh
git status --short
git fetch origin main
```

如果工作区不干净，或者 `git fetch origin main` 失败，必须立即停止。不要生成文件，不要提交，不要推送，避免基于过期本地数据发布。

成功后的命令顺序：

```sh
report_date="$(TZ=Asia/Shanghai date +%F)"

git pull --rebase origin main
python -m fanqierank collect --channel all --date "$report_date" --timezone Asia/Shanghai --sleep-seconds 3
python -m fanqierank fallback-finalize --channel all --date "$report_date"

# Codex 读取：
# - data/channels/male/codex_context/$report_date.json
# - data/channels/female/codex_context/$report_date.json
# 并分别写入：
# - data/channels/male/analysis/$report_date.json
# - data/channels/female/analysis/$report_date.json

python -m fanqierank finalize --channel all --date "$report_date"
python -m compileall fanqierank tests
pytest
git diff --check
git add README.md data api reports
git commit -m "chore: add Codex analysis for $report_date"
git push
```

每个频道的 analysis JSON 必须覆盖该频道所有分类和 `7 / 14 / 30 / all` 四个全站摘要周期。缺任何分类时，`finalize` 会失败。
