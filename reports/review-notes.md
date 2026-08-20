## 人工维护记录

本节由 `reports/review-notes.md` 提供，不由 `scripts/simulate_routing.py` 生成，
因此测试不会对生成器自产的字符串做断言。内容需人工更新并对其准确性负责。

### 规则修正历史

0. 分组重构：取消独立 Meta/Telegram/YouTube 组，流媒体命名统一；
   新增哔哩哔哩组（Full 专属，默认直连、可切代理）、加密货币组（Full 专属）；
   通讯社交组扩充至 Telegram/WhatsApp/Instagram/Messenger/Signal/LINE/Discord 等，
   X、Threads、Facebook 主站等内容优先平台走节点选择。
   命名与广告精简：`📢 Google服务` → `📢 谷歌服务`，开发者 emoji 由 `🧑💻`
   改为单个 `💻`；成人广告网络并入 `ads-base.list`，广告拦截只保留一个分组一个文件。
1. 新增微信、抖音、小红书、微博、爱奇艺、优酷、腾讯视频及国产 AI 的显式直连规则；
2. 新增 Meta 家族规则，并在 Full 中建立独立 Meta 组、Standard 中归入通讯社交；
3. 补齐成人内容域名（含 xHamster、Pornhub Premium、RedTube、YouPorn、SpankBang 等），
   确保成人网站走代理而不是被广告规则拒绝；
4. 补充 Disney/BAMGrid、Netflix、Hulu、Prime Video 等流媒体依赖域名；
5. 扩充通用广告、成人广告和低价值行为跟踪器，同时保留成人网站主体；
6. 修正 Google/YouTube 与 Microsoft/GitHub 的规则抢占；
7. 将 GitHub Actions 第三方 Action 固定到不可变提交 SHA；
8. 移除过宽的 `byteimg.com` 直连。

### 成人内容与广告的设计理念（本轮修正）

`🔞 成人内容` 和 `🛑 广告拦截` 都是**分组**，不是强制策略。规则仓库只负责把域名
分到正确的组，是否 REJECT 由用户在 Clash 客户端里自行选择：

- `🔞 成人内容`：可选 `♻️ 自动选择 / 🚀 节点选择 / 🚀 手动切换 / DIRECT / REJECT`，
  默认走代理，用户可自行切到 REJECT；
- `🛑 广告拦截`：可选 `REJECT / DIRECT`，默认 REJECT，用户可自行放行。

因此 `validate_adult_site_separation` 的作用是**分类归属**，不是禁止拦截：
成人*站点*归 `adult-content.list`（用户可控组），成人*广告网络*与通用广告
合并为单一的 `ads-base.list`（广告拦截组）。护栏防止的是站点被广告规则
悄悄抢走、从而剥夺用户的选择权。

先前一版曾加入「禁止 reject 列表使用成人语义关键词」和「禁止成人 ruleset 指向拦截组」
两条护栏，这是对用户意图的越权限制——用户明确要求保留自行选择 REJECT 的能力，
两条护栏已移除。

### 护栏加固（本轮）

独立审查发现原成人内容护栏只做精确字符串比对，可被绕过。已修正：

- 保护域名集合改为直接从 `rules/proxy/adult-content.list` 派生，成为唯一事实源；
- 拦截判定扩展为后缀双向包含 + `DOMAIN-KEYWORD` 子串匹配，
  `DOMAIN-KEYWORD,porn`、`DOMAIN-SUFFIX,www.pornhub.com`、过宽父域 `DOMAIN-SUFFIX,tv`
  等手法均会被 `validate_repository.py` 拒绝；
- allowlist 与规则列表必须双向完全同步，任一侧漂移即报错；
- 新增 `china-services` 与 reject 列表互不遮蔽的不变量检查；
- 新增 profile ruleset 路径白名单校验，防止读取 `rules/` 之外的文件。

### 待完成事项

- 真实设备与账户验证（DRM、Apple Intelligence 资格、FCM 长连接、流媒体解锁）；
- IP-CIDR / `no-resolve` 语义的自动化验证；
- 固定 GeoIP 数据版本与长期更新机制。
