# codex-memory-scope-patch

针对 `openai/codex` 的最小补丁仓库。

目标是只修正 `codex-rs/core/templates/memories/read_path.md` 中 memory 提示词的作用域边界，保留官方“当前会话不要直接改 Codex 自管 memory”这一限制，但把限制收窄到 `{{ base_path }}` 对应的 Codex home memory root，不再误伤其他 MCP-managed state 或项目目录。

## 设计原则

- 不 fork `openai/codex`
- 不复刻 upstream 全量 release 流程
- 只在 GitHub Actions 中临时 clone upstream
- 只应用一个 patch
- 只产出最小可用的 patched `codex` 二进制

## 当前 patch 行为

当前 patch 会把这句过宽的限制：

```md
Never update memories. You can only read them.
```

替换为仅作用于 Codex 自管 memory root 的版本：

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

## 产物说明

当前 workflow 默认构建：

- Linux x64: `x86_64-unknown-linux-gnu`
- Windows x64: `x86_64-pc-windows-msvc`

这是为了降低失败面，优先保证能稳定产出 patched binary。

如果后续需要完全贴近 upstream 发布资产，可以再扩成 musl/macOS 矩阵。

## 风险说明

- 这个仓库不是官方发布渠道
- upstream 一旦调整 `read_path.md` 上下文或构建流程，patch 可能需要同步更新
- 该 patch 只解决 memory 提示词的“作用域外溢”问题，不尝试恢复旧版的 live memory editing 机制
