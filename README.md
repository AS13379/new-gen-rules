# Subconverter Modern Rules

面向 Subconverter 与 Mihomo/Clash 的现代分流规则仓库。

本项目保留 ACL4SSR 易用的策略分组思想，但不沿用其大量陈旧的直连、静态 IP 和服务域名数据。核心原则是：

- 中国大陆公网 IP 兜底直连；
- 明确的境外服务优先进入对应代理组；
- 未分类流量默认代理，不冒险直连；
- Apple 默认跟随“节点选择”，而不是独立自动测速；
- 不创建香港、新加坡等地区节点组；
- 所有广告（包括成人网站广告）只进入一个广告拦截组；
- 成人内容网站归独立分组，是否代理/拒绝由用户选择，绝不混入广告规则。

> [!WARNING]
> 当前是本地规则基线，已经具备生成、测试和仓库校验，但尚未接入生产 Subconverter，也未经过真实客户端 Canary 验证。不要直接替换现有生产订阅。

## 配置档位

仓库提供三档配置，每档都有普通版和广告拦截版：

| 配置 | 定位 | 策略组 |
|---|---|---|
| `Mini` | 接近原 ACL4SSR Mini 的极简体验 | 节点选择、自动选择、中国直连、漏网之鱼 |
| `Mini_Adblock` | Mini + 广告拦截 | Mini 全部 + 唯一广告组 |
| `Standard` | 日常够用的折中方案 | Google、Apple、AI、通讯社交、流媒体、Microsoft |
| `Standard_Adblock` | Standard + 广告拦截 | Standard 全部 + 唯一广告组 |
| `Full` | 需要精细控制的完整方案 | Standard 基础上细分哔哩哔哩、加密货币、游戏、开发者、成人内容等 |
| `Full_Adblock` | Full + 广告拦截 | Full 全部 + 唯一广告组 |

所有档位都没有地区节点组。

## 重要默认行为

### Mini

Mini 不设置 Google、Apple、加密货币等专组。服务规则仍会被维护，但统一指向 `🚀 节点选择`，从而保持界面简洁。

### Standard

Standard 是 Mini 和 Full 之间的折中档：保留高价值业务组，但不为每种网站创建单独组，也不单独显示加密货币、哔哩哔哩和成人内容。

### Full

Full 提供：

- `💹 加密货币`：OKX、Binance、Coinbase、KuCoin、Gate、Bybit、Bitget 等主流交易所与行情站；
- `📺 哔哩哔哩`：默认直连，可切代理看港澳台/海外番剧；
- `🔞 成人内容`：成人视频、漫画/本子、直播站本身走代理（可选拒绝）；
- Google、Apple、AI、通讯社交、流媒体、游戏、Microsoft、开发者等专组。

### Apple

`🍎 Apple服务`的第一候选是 `🚀 节点选择`，之后才提供 `♻️ 自动选择`、手动和 DIRECT。这样 Apple 默认继承用户选择的稳定出口，避免每次测速导致地区变化。

规则初步覆盖 Apple Account、iCloud、App Store、APNs、Apple Intelligence、Siri 和 Private Cloud Compute 相关域名。网络分流无法绕过设备销售地区、Apple Account 地区或 Apple 服务端资格限制。

### Google 和 FCM

Google Translate、Google APIs 和 Firebase Cloud Messaging 统一归入 `📢 谷歌服务`。FCM 长连接可能对 VPN/代理敏感，因此 Full/Standard 中保留 DIRECT 作为最后的人工排错选项，但默认仍走代理策略。

### 广告与成人内容

广告版只有一个用户可见组：

```text
🛑 广告拦截 = REJECT / DIRECT
```

通用广告和成人广告网络合并进这个组（单一 `ads-base.list`）。成人网站主域只允许出现在 `rules/proxy/adult-content.list`，测试会阻止这些域名进入任何 REJECT 列表。

## 路由顺序

1. localhost、LAN 和私有地址；
2. 微信、国产社交、国产视频、国产 AI 等显式大陆服务；
3. 广告和跟踪（仅 Adblock 配置）；
4. Apple；
5. Google、Translate、FCM；
6. 通讯社交和加密货币；
7. AI、通讯、视频、游戏、开发者和成人内容；
8. `GEOIP,CN` 中国大陆公网 IP；
9. `FINAL` 到漏网之鱼，默认自动选择代理。

明确业务规则位于 `GEOIP,CN` 之前，因此 Google、Apple、OKX 等不会因为历史直连列表而误判。

## 仓库结构

```text
policy/                  规则来源登记
profiles/                自动生成的 Subconverter 外部配置
rules/direct/            本地和私网直连
rules/proxy/             业务代理规则
rules/reject/            统一广告拒绝规则
scripts/build_profiles.py 生成六份配置
scripts/validate_repository.py 仓库和引用完整性校验
scripts/simulate_routing.py 严格大陆/海外出口路由模拟
tests/                   行为和回归测试
reports/                 自动生成的测试报告
docs/                    架构与维护说明
```

## 生成与验证

项目只使用 Python 标准库；本地已用 Python 3.9 验证，GitHub Actions 配置为 Python 3.11。

```bash
make build
make test
make simulate
make check
```

等价命令：

```bash
python3 scripts/build_profiles.py
python3 -m unittest discover -s tests -v
python3 scripts/build_profiles.py --check
python3 scripts/validate_repository.py
python3 scripts/simulate_routing.py --report reports/mainland-strict-routing-report.md
```

`profiles/*.ini` 是生成文件，不应手工修改。修改策略时编辑 `scripts/build_profiles.py` 和规则源，再重新生成。

## 接入 Subconverter

当前 INI 使用相对规则路径，例如：

```ini
ruleset=📢 谷歌服务,rules/proxy/google.list
```

部署时有两种选择：

1. 将整个仓库挂载到 Subconverter 可读取的目录，保持相对路径；
2. 上传 GitHub 后，在发布流程中把路径转换为固定提交的 Raw URL。

生产环境应固定到提交 SHA 或版本标签，不应直接追踪 `main`，避免上游变更未经验证进入订阅。

## 规则维护原则

- 官方网络文档优先；
- 活跃第三方规则只作候选来源，不整包盲目导入；
- 静态 IP 规则必须说明来源和更新时间；
- 无法确认的境外服务默认代理；
- 不使用 `DOMAIN-KEYWORD,porn,REJECT` 等宽泛成人内容封锁；
- 不把订阅 Token、SSH 凭据、服务器地址和生成后的私人订阅提交到 Git。

详见 [`docs/rule-maintenance.md`](docs/rule-maintenance.md)。

## 当前状态

已经完成：

- 六份配置生成；
- Mini / Standard / Full 分档；
- 单一广告拦截组；
- Apple 默认节点选择；
- Full 专属哔哩哔哩、加密货币、游戏、开发者和成人内容组；
- 通讯社交统一覆盖 Telegram、WhatsApp、Instagram、Messenger、Signal、LINE、Discord 等；
- 流媒体统一覆盖 YouTube、Netflix、Disney+、Spotify、Twitch 等；
- Google Translate / FCM 基础规则；
- Apple/iCloud/Apple Intelligence 基础规则；
- 微信、抖音、小红书、微博、爱优腾、哔哩哔哩、DeepSeek、Kimi、千问和豆包显式直连；
- 中国大陆 IP 最终直连；
- 规则语法、重复项、策略引用和成人站误拦截测试。
- 使用 Subconverter v0.9.0 将六份 INI 转换为真实 Clash YAML；
- 六份转换结果均通过 Mihomo v1.19.30 `-t` 配置校验。
- 122 个代表场景 × 6 种配置，共 732 个确定性路由检查全部通过；
- 分组即选择权：`🔞 成人内容` 可选 `自动选择 / 节点选择 / 手动切换 / DIRECT / REJECT`
  （默认代理），`🛑 广告拦截` 可选 `REJECT / DIRECT`（默认拦截），
  是否拦截由用户在 Clash 客户端自行决定，规则仓库不代替用户做这个决定；
- 校验只保证**分类归属**：成人站点归 `adult-content.list`（用户可控组），
  成人广告网络归 reject 列表，防止站点被广告规则悄悄抢走而剥夺选择权；
- 报告由模拟结果生成并经 `scripts/check_report_current.py` 校验新鲜度，
  详见 [`reports/mainland-strict-routing-report.md`](reports/mainland-strict-routing-report.md)。

已知盲区（未被自动化覆盖）：

- IP-CIDR / IP-CIDR6 规则与 `no-resolve` 语义不参与路由模拟；
- GEOIP,CN 按场景标记模拟，未使用真实 GeoIP 数据库，也未固定数据版本；
- 未验证流媒体解锁、DRM、Apple Intelligence 资格、FCM 长连接或账户风控。

后续仍需：

- 对原 Subconverter 直连列表逐条迁移审计；
- 从官方资料补全并验证 Apple、Google、交易所；
- 引入可信 CN GeoIP/MRS 数据并固定版本；
- 接入真实 CELERITY 节点并进行 Canary 客户端测试。

## 许可证

本仓库原创代码采用 MIT License。外部规则来源及派生数据可能适用其各自许可证，参见 [`NOTICE.md`](NOTICE.md) 和 `policy/sources.toml`。
