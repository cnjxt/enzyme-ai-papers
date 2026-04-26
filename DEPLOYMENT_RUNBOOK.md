# Deployment Runbook

这份文档是按步骤执行的简明部署和使用手册。完整背景说明见
[DEPLOYMENT.md](DEPLOYMENT.md)。

当前仓库实例：

- Repository: `https://github.com/cnjxt/enzyme-ai-papers`
- Website: `https://cnjxt.github.io/enzyme-ai-papers/`
- Pages source: GitHub Actions, not `main` + `/docs`

## 一、一次性部署流程

### 1. 准备 GitHub 仓库

创建或确认仓库存在：

```text
https://github.com/<owner>/enzyme-ai-papers
```

作用：GitHub 仓库承载 Issues、Pull Requests、Actions、Pages 和论文数据。

### 2. 推送本地代码

```bash
git remote add origin https://github.com/<owner>/enzyme-ai-papers.git
git branch -M main
git push -u origin main
```

作用：把项目代码、issue 模板、workflow、数据和站点源文件放到 GitHub。

如果 remote 已存在，检查即可：

```bash
git remote -v
```

### 3. 配置公开 URL

修改 `mkdocs.yml`：

```yaml
site_url: https://<owner>.github.io/enzyme-ai-papers/
repo_url: https://github.com/<owner>/enzyme-ai-papers
repo_name: <owner>/enzyme-ai-papers
```

作用：让网站导航、仓库链接和 Submit 页都指向真实仓库。

当前实例应为：

```yaml
site_url: https://cnjxt.github.io/enzyme-ai-papers/
repo_url: https://github.com/cnjxt/enzyme-ai-papers
repo_name: cnjxt/enzyme-ai-papers
```

### 4. 本地生成并校验

```bash
python3 scripts/build_docs.py
python3 scripts/validate_papers.py
python3 -m unittest discover -s tests
mkdocs build --strict
```

作用：

- `build_docs.py`: 从 `data/` 生成 `README.md` 和 `docs/`
- `validate_papers.py`: 检查论文 YAML 是否符合项目规则
- `unittest`: 跑项目测试
- `mkdocs build --strict`: 确认站点可构建

如果使用虚拟环境，可改成：

```bash
.venv/bin/python scripts/build_docs.py
.venv/bin/python scripts/validate_papers.py
.venv/bin/python -m unittest discover -s tests
.venv/bin/mkdocs build --strict
```

### 5. 提交并推送配置

```bash
git add mkdocs.yml README.md docs/
git commit -m "Configure public deployment URLs"
git push origin main
```

作用：把公开 URL 和生成后的站点源文件提交到 `main`。

### 6. 打开 GitHub Issues

GitHub 网页路径：

```text
Repository -> Settings -> Features -> Issues
```

作用：用户提交论文建议时会创建 GitHub issue。

### 7. 创建维护标签

需要这些 labels：

```text
needs-review
paper-suggestion
accepted
featured
needs-info
rejected
automated-curation
```

作用：

- `needs-review`: 新建议待审核
- `paper-suggestion`: 论文建议 issue
- `accepted`: 接收该论文并生成 curation PR
- `featured`: 标记为 Pick of the Week 候选
- `needs-info`: 要求投稿人补充信息
- `rejected`: 拒绝该建议
- `automated-curation`: 自动化创建的 PR

### 8. 开启 Actions 写权限

GitHub 网页路径：

```text
Repository -> Settings -> Actions -> General -> Workflow permissions
```

选择：

```text
Read and write permissions
Allow GitHub Actions to create and approve pull requests
```

作用：`issue-curation.yml` 需要评论 issue、写入分支、创建 PR。

### 9. 配置 GitHub Pages

GitHub 网页路径：

```text
Repository -> Settings -> Pages
Build and deployment -> Source: GitHub Actions
```

作用：让 `.github/workflows/deploy-pages.yml` 构建 MkDocs 的 `site/` 并发布。

不要选择：

```text
Deploy from a branch -> main -> /docs
```

原因：这样 GitHub 会用 Jekyll 渲染 `docs/`，不是 MkDocs Material 的正式站点。

### 10. 确认自动部署 workflow 存在

文件：

```text
.github/workflows/deploy-pages.yml
```

作用：每次 `main` 更新后：

1. 安装 Python 依赖
2. 运行 `scripts/build_docs.py`
3. 运行 `mkdocs build --strict`
4. 上传 `site/` artifact
5. 部署到 GitHub Pages

### 11. 验证线上部署

打开：

```text
https://<owner>.github.io/enzyme-ai-papers/
```

当前实例：

```text
https://cnjxt.github.io/enzyme-ai-papers/
```

检查点：

- 首页能打开
- 页面源码里能看到 `mkdocs-material`
- Submit 页链接指向真实仓库的 `/issues/new`
- GitHub Actions 里 `Deploy GitHub Pages` 成功

## 二、部署后的标准收录流程

标准流程：

```text
论文 URL -> GitHub issue -> 自动 metadata preview -> 维护者加 label -> 自动 PR -> 审核 PR -> merge -> 网站自动更新
```

### 1. 用户提交论文

用户进入网站 Submit 页：

```text
https://<owner>.github.io/enzyme-ai-papers/info/
```

填写：

- Paper URL: 必填
- Paper title: 可选
- Why this paper matters: 可选，但推荐填写
- Suggested tags: 可选
- Code or project link: 可选

作用：网站不会直接写仓库，只会打开一个预填好的 GitHub issue。

### 2. 自动生成预览评论

issue 创建后，`.github/workflows/issue-curation.yml` 会运行 preview job。

它会尝试解析：

- title
- source
- DOI
- authors
- suggested tags
- submitter note

作用：维护者先看 metadata 质量，不直接写入数据。

### 3. 维护者审核 issue

维护者根据情况加 label：

```text
accepted
featured
needs-info
rejected
```

作用：

- 加 `accepted`: 自动创建收录 PR
- 加 `featured`: 同时作为 Pick of the Week 候选
- 加 `needs-info`: 自动评论要求补充信息
- 加 `rejected`: 自动评论并关闭 issue

### 4. 自动创建 curation PR

给 issue 加 `accepted` 后，accept job 会：

1. 生成 `data/papers/YYYY/<paper-id>.yml`
2. 重新生成 `README.md`
3. 重新生成 `docs/`
4. 运行 metadata validation
5. 运行 tests
6. 创建 curation PR

作用：维护者不需要手写大部分 YAML 和站点页面。

### 5. 维护者审核 PR

重点检查：

- 标题是否正确
- 作者是否正确
- DOI / PDF / preprint URL 是否正确
- `topics` / `methods` / `evidence` / `applications` 标签是否合理
- `one_liner` 是否适合展示在首页
- `why_it_matters` 是否不是测试文字或空泛说明

作用：自动 metadata 是 best-effort，合并前必须人工把关。

### 6. 合并 PR

PR 合并到 `main` 后：

1. `Validate` 和 `Build static site` 在 `main` 上运行
2. `Deploy GitHub Pages` 重新部署网站
3. 线上页面更新

作用：数据和网站一起进入正式发布状态。

## 三、多种提交和 PR 方法

### 方法 A：网站 Submit 页提交

适合：普通读者、外部贡献者。

步骤：

1. 打开 `https://<owner>.github.io/enzyme-ai-papers/info/`
2. 填 Paper URL
3. 可选填写标题、说明、标签、代码链接
4. 点击提交，进入 GitHub issue 页面
5. 提交 issue

后续由维护者加 `accepted`，自动创建 PR。

### 方法 B：GitHub issue 模板提交

适合：用户直接从 GitHub 仓库提交。

步骤：

1. 打开 `https://github.com/<owner>/enzyme-ai-papers/issues/new/choose`
2. 选择 `Paper suggestion`
3. 填写 Paper URL 和可选字段
4. 提交 issue

作用：绕过网站页面，但走同一套 issue automation。

### 方法 C：维护者直接给 issue 加 label

适合：已经有待审核 issue。

步骤：

1. 打开 paper suggestion issue
2. 看自动 preview 评论
3. 合格则加 `accepted`
4. 如果要作为本周精选，同时加 `featured`
5. 等自动 PR 创建
6. 审核并合并 PR

作用：这是维护者日常收录论文的主要动作。

### 方法 D：本地手动建分支提交 PR

适合：自动 metadata 不够好，或维护者想完全手动维护 YAML。

步骤：

```bash
git switch main
git pull origin main
git switch -c add-paper-short-name
```

新增或修改：

```text
data/papers/YYYY/<paper-id>.yml
```

然后生成和验证：

```bash
python3 scripts/build_docs.py
python3 scripts/validate_papers.py
python3 -m unittest discover -s tests
mkdocs build --strict
```

提交并推送：

```bash
git add data/papers README.md docs/
git commit -m "Add <paper title>"
git push origin add-paper-short-name
```

最后在 GitHub 网页创建 PR。

作用：适合更精细的人工整理；仍然保留 PR review 和 CI 流程。

### 方法 E：GitHub 网页直接编辑后开 PR

适合：小修 metadata，例如改标签、改摘要、改错别字。

步骤：

1. 在 GitHub 打开要编辑的 YAML 或文档
2. 点击编辑
3. 选择创建新 branch
4. 提交 change
5. 打开 PR

注意：如果改了 `data/papers/`，最好本地或 Actions 重新生成 `README.md` 和 `docs/`。
否则 `Validate` 里的 `git diff --exit-code` 可能失败。

### 方法 F：维护者直接合并自动 curation PR

适合：metadata preview 和 PR diff 都已经准确。

步骤：

1. 打开自动 PR
2. 检查 `data/papers/YYYY/*.yml`
3. 检查 README/docs diff
4. 合并 PR
5. 等 Pages 自动部署完成

注意：由 `GITHUB_TOKEN` 创建的 PR 不一定会递归触发额外的 `pull_request`
checks；但创建 PR 前的 `issue-curation` job 已经运行了生成、校验和测试。
如果要强制所有自动 PR 也显示 PR checks，需要改用单独 PAT 创建 PR，或调整
branch protection 规则。

## 四、用示例文章做一次端到端测试

示例 URL：

```text
https://www.biorxiv.org/content/10.64898/2026.04.22.720119v1
```

预期 preview 结果：

```text
Title: Improving AlphaFold3 by Engineering MSA and Template Inputs
Source: biorxiv
DOI: 10.64898/2026.04.22.720119
Authors: Neupane, P.; Liu, J.; Cheng, J.
```

测试步骤：

1. 用网站 Submit 页或 GitHub issue 模板提交该 URL
2. 等 GitHub Actions 评论 preview
3. 给 issue 加 `accepted`
4. 确认自动 PR 创建
5. 检查生成的 YAML
6. 修正不准确的标签或说明
7. 合并 PR
8. 等 Pages 部署完成
9. 打开网站确认文章出现在 Weekly 或 Archive

## 五、常见问题

### 线上页面像 GitHub 默认 Markdown 页面

原因：Pages 配成了 `Deploy from a branch -> main -> /docs`。

处理：改成：

```text
Settings -> Pages -> Build and deployment -> GitHub Actions
```

然后手动触发 `Deploy GitHub Pages` workflow。

### Submit 页跳到错误仓库

原因：`mkdocs.yml` 的 `repo_url` 还是占位值。

处理：改成真实仓库 URL，然后运行：

```bash
python3 scripts/build_docs.py
git add mkdocs.yml docs/
git commit -m "Fix public repository URLs"
git push
```

### 自动 PR 没创建

检查：

- issue 是否有 `accepted` label
- Actions workflow permissions 是否是 read/write
- 是否允许 GitHub Actions 创建 pull requests
- `.github/workflows/issue-curation.yml` 是否运行失败

### 自动标签不准确

这是正常情况。`infer_tags` 是关键词推断，合并 PR 前维护者应人工修正
`topics`、`methods`、`evidence`、`applications`。

### 改了 YAML 后 CI 说 docs 有 diff

原因：`README.md` 和 `docs/` 没重新生成。

处理：

```bash
python3 scripts/build_docs.py
git add README.md docs/
git commit -m "Regenerate docs"
```
