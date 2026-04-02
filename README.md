# codex-memory-scope-patch

针对 `openai/codex` 的最小替换仓库。

目标是只修正 `codex-rs/core/templates/memories/read_path.md` 中 memory 提示词的作用域边界，保留官方“当前会话不要直接改 Codex 自管 memory”这一限制，但把限制收窄到 `{{ base_path }}` 对应的 Codex home memory root，不再误伤其他 MCP-managed state 或项目目录。

## 设计原则

- 不 fork `openai/codex`
- 不复刻 upstream 全量 release 流程
- 只在 GitHub Actions 中临时 clone upstream
- 只执行一个文本替换脚本
- 只产出最小可用的 patched `codex` 二进制

## 当前替换行为

当前脚本会把这句过宽的限制：

```md
Never update memories. You can only read them.
```

直接替换为仅作用于 Codex 自管 memory root 的版本：

```md
Do not directly modify Codex-managed memory artifacts under {{ base_path }} in this session.
Treat only that Codex memory root as read-only.
This restriction does not apply to unrelated project directories or other MCP-managed state unless separately instructed.
```

## 使用方式

1. 打开 GitHub Actions
2. 手动运行 `build-patched-codex`
3. 按需填写 `upstream_ref`
4. 下载对应平台产物

默认 `upstream_ref` 建议填写稳定 tag，例如：

```text
rust-v0.116.0
```

也可以填写具体 commit SHA。

## Release 成品 Patch

如果不想 clone upstream 再重新编译，也可以直接运行 `patch-release-binary` workflow。

这条 workflow 会：

1. 接受上游 release 名称（例如 `0.119.0-alpha.3`）或原始 upstream tag（例如 `rust-v0.119.0-alpha.3`），并统一解析成真实 upstream release tag
2. 下载同 tag 的 `codex-rs/core/templates/memories/read_path.md`
3. 下载 Windows x64 成品 `codex-x86_64-pc-windows-msvc.exe`
4. 下载 Linux x64 成品包 `codex-x86_64-unknown-linux-gnu.tar.gz`，解出其中的 `codex-x86_64-unknown-linux-gnu`
5. 先做一层提示词 patch：只改 4 处目标文本，并要求 patch 前后归一化后的模板字节长度完全一致
6. 再做一层制成品 patch：用原始 `read_path.md` 定位内嵌 block，再用 patched 模板按原偏移覆盖，并校验 patch 前后的二进制字节长度完全一致
7. 上传 patched Windows x64 可执行文件与 patched Linux x64 tarball
8. 两个平台都成功后，自动发布 `patched-<release>` 命名的 GitHub pre-release

这条路径的重点不是“硬编码一整份完整提示词”，而是尽量用最小锚点做等长替换。这样 upstream 只要没有大改 `read_path.md`，即使有少量无关文本变化，我们仍然大概率可以继续 patch；一旦关键锚点缺失或等长条件失效，workflow 会直接失败，而不是猜测性地继续改。

当前默认输入已经对齐到新的 upstream pre-release 命名方式：

```text
0.119.0-alpha.3
```

如果你更想显式传原始 upstream tag，也可以直接填：

```text
rust-v0.119.0-alpha.3
```

## 产物说明

当前 workflow 默认构建：

- Linux x64: `x86_64-unknown-linux-gnu`
- Windows x64: `x86_64-pc-windows-msvc`

这是为了降低失败面，优先保证能稳定产出 patched binary。

如果后续需要完全贴近 upstream 发布资产，可以再扩成 musl/macOS 矩阵。

## 风险说明

- 这个仓库不是官方发布渠道
- upstream 一旦改掉这句精确原文，脚本会明确失败，需要同步更新目标文本
- 该替换只解决 memory 提示词的“作用域外溢”问题，不尝试恢复旧版的 live memory editing 机制
