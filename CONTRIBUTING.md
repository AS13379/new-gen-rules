# Contributing

1. 不提交凭据、订阅 Token、私人节点或服务器信息。
2. 为行为变化先写失败测试，再修改生成器或规则。
3. 规则新增必须说明来源、目标策略组和理由。
4. 运行：

```bash
make build
make check
```

5. `profiles/*.ini` 必须由生成器产生，禁止手工修改。
6. 成人内容主域不得出现在 REJECT 规则中。
7. 外部规则复制或派生前先确认许可证并更新 `NOTICE.md`。
