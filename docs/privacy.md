# 隐私与发布检查

公开发布前建议检查：

```text
token
cookie
authorization
api_hash
api_id
session
password
secret
Bearer
sk-
ghp_
手机号
邮箱
身份证
真实群号
真实服务器 ID
真实工作区路径
```

不要提交：

```text
*.session
*.sqlite
*.sqlite3
*.db
*.jsonl
*.log
*.env
*.local.json
sessions/
outputs/
samples/
data/
```

建议只提交：

- `SKILL.md`
- 通用 `references/`
- 安装说明
- 安全说明
- `.gitignore`
- `LICENSE`

