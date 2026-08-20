# 架构说明

## 边界

- CELERITY：用户、节点、流量、订阅 Token 和协议字段；
- Subconverter：策略组和规则排序；
- 合并侧车：把 CELERITY 节点注入 Subconverter 生成的完整配置；
- Mihomo：只作为配置解析和实际客户端验证器，不修改内核。

本仓库不保存 CELERITY 凭据、订阅 Token、服务器连接信息或私人节点。

## 单一策略源

六份配置由 `scripts/build_profiles.py` 生成。分档只决定用户可见策略组的粒度，不复制六套规则数据：

- Mini：规则统一映射到节点选择；
- Standard：高价值业务适度分组；
- Full：业务精细分组；
- `_Adblock`：在对应档位加入相同的唯一广告组。

## 首次匹配

Subconverter/Clash 使用首次匹配。业务规则必须位于 `GEOIP,CN` 前，`FINAL` 必须最后。这样明确境外服务不会因 CDN 或历史白名单被提前直连。

## 自动选择

`♻️ 自动选择`使用 `url-test` 和 HTTPS 204 探测，但只作为手动备选。所有代理业务组默认跟随 `🚀 节点选择`；该组先列真实节点，再列自动选择，避免新订阅默认使用测速最快节点。地区分组不在设计范围内。

## 严格大陆网络模拟

`scripts/simulate_routing.py`按 Subconverter INI 中的 ruleset 顺序执行确定性首次匹配。模拟假定 DIRECT 只能访问大陆服务、代理只能访问境外服务，并把每个域名在六种配置中的实际策略与预期策略比较。

国产服务必须显式命中 `rules/direct/china-services.list`；未知大陆 IP 才依赖 `GEOIP,CN`。该模拟不能替代真实账户、DRM、推送、Apple 地区资格或交易所风控测试。

## 发布模型

本地阶段使用相对规则路径。未来 GitHub 发布应生成绑定提交 SHA 的配置，经过：

1. 单元测试；
2. 严格大陆网络路由模拟；
3. 仓库校验；
4. Subconverter 转换；
5. Mihomo `-t`；
6. Canary 客户端；
7. 人工批准后发布。

GitHub Actions 使用完整提交 SHA 固定第三方 Action，避免可移动版本标签带来的供应链风险。
