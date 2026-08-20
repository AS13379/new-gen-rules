# 严格大陆网络路由模拟报告

## 模型假设

- 本机 DIRECT 出口只能可靠访问中国大陆服务；
- 代理出口只能可靠访问境外服务；
- 测试验证的是 Clash/Subconverter 首次匹配和策略归组，不模拟账户登录、DRM、设备地区或服务端风控；
- 国产服务域名必须在不借助 GEOIP 的情况下命中显式中国直连规则；
- 未分类中国大陆 IP 由 GEOIP,CN 直连，未分类境外流量由 FINAL 进入代理兜底。

## 结果摘要

- 场景-配置组合：732
- 通过：732
- 失败：0
- 通过率：100.00%

## 按类别

| 类别 | 通过 | 总数 | 通过率 |
|---|---:|---:|---:|
| Apple家族 | 54 | 54 | 100.00% |
| Google家族 | 78 | 78 | 100.00% |
| Meta家族 | 72 | 72 | 100.00% |
| 兜底行为 | 12 | 12 | 100.00% |
| 哔哩哔哩 | 12 | 12 | 100.00% |
| 国产AI | 54 | 54 | 100.00% |
| 国产社交 | 54 | 54 | 100.00% |
| 国产视频 | 48 | 48 | 100.00% |
| 弱跟踪器 | 36 | 36 | 100.00% |
| 微信生态 | 48 | 48 | 100.00% |
| 成人内容 | 102 | 102 | 100.00% |
| 成人广告 | 36 | 36 | 100.00% |
| 海外流媒体 | 72 | 72 | 100.00% |
| 通用广告 | 54 | 54 | 100.00% |

## 场景样本

| 类别 | 测试域名 |
|---|---|
| Apple家族 | `api.storekit.itunes.apple.com`、`apple-relay.apple.com`、`apple-relay.cloudflare.com`、`apple-relay.mask.apple-dns.net`、`apps.apple.com`、`courier.push.apple.com`、`gateway.icloud.com`、`icloud.com`、`me.com` |
| Google家族 | `alt8-mtalk.google.com`、`binance.com`、`coinbase.com`、`coinmarketcap.com`、`drive.google.com`、`fcm.googleapis.com`、`gemini.google.com`、`gmail.com`、`mail.google.com`、`maps.google.com`、`okx.com`、`redirector.gvt1.com`、`translate.google.com` |
| Meta家族 | `discord.com`、`facebook.com`、`instagram.com`、`line.me`、`messenger.com`、`scontent.xx.fbcdn.net`、`signal.org`、`static.xx.fbcdn.com`、`t.me`、`threads.com`、`threads.net`、`whatsapp.com` |
| 兜底行为 | `unknown-cn-service.example`、`unknown-overseas.example` |
| 哔哩哔哩 | `bilibili.com`、`hdslb.com` |
| 国产AI | `chat.deepseek.com`、`dashscope.aliyuncs.com`、`doubao.com`、`doubaocdn.com`、`kimi.com`、`moonshot.cn`、`tongyi.aliyun.com`、`tongyi.com`、`volcengine.com` |
| 国产社交 | `amemv.com`、`douyin.com`、`douyinvod.com`、`sinaimg.cn`、`wbimg.cn`、`weibo.com`、`xhscdn.com`、`xhsrcdn.com`、`xiaohongshu.com` |
| 国产视频 | `iqiyi.com`、`pps.tv`、`qiyi.com`、`qqvideo.tc.qq.com`、`v.qq.com`、`ykimg.alicdn.com`、`ykimg.com`、`youku.com` |
| 弱跟踪器 | `clarity.ms`、`fullstory.com`、`google-analytics.com`、`hotjar.com`、`mouseflow.com`、`quantserve.com` |
| 微信生态 | `qlogo.cn`、`qpic.cn`、`res.wx.qq.com`、`servicewechat.com`、`tenpay.com`、`weixin.qq.com`、`weixin110.qq.com`、`weixinbridge.com` |
| 成人内容 | `chaturbate.com`、`e-hentai.org`、`exhentai.org`、`hanime.tv`、`nhentai.net`、`phncdn.com`、`pornhub.com`、`pornhubpremium.com`、`redtube.com`、`spankbang.com`、`stripchat.com`、`xhamster.com`、`xhcdn.com`、`xnxx.com`、`xvideos-cdn.com`、`xvideos.com`、`youporn.com` |
| 成人广告 | `adsterra.com`、`exoclick.com`、`juicyads.com`、`popads.net`、`trafficjunky.com`、`trafficstars.com` |
| 海外流媒体 | `aiv-cdn.net`、`bamgrid.com`、`bamtech.net`、`disneyplus.com`、`hulu.com`、`max.com`、`netflix.com`、`nflxvideo.net`、`primevideo.com`、`spotify.com`、`spotifycdn.com`、`twitch.tv` |
| 通用广告 | `adservice.google.com`、`adsrvr.org`、`amazon-adsystem.com`、`criteo.com`、`doubleclick.net`、`googlesyndication.com`、`openx.net`、`pubmatic.com`、`rubiconproject.com` |

## 按配置

| 配置 | 通过 | 总数 | 通过率 |
|---|---:|---:|---:|
| Mini | 122 | 122 | 100.00% |
| Mini_Adblock | 122 | 122 | 100.00% |
| Standard | 122 | 122 | 100.00% |
| Standard_Adblock | 122 | 122 | 100.00% |
| Full | 122 | 122 | 100.00% |
| Full_Adblock | 122 | 122 | 100.00% |

## 失败明细

无。所有测试域名都命中预期策略。

## 覆盖范围

- 场景总数：122
- 配置档位：6
- 类别数：14
- 成人内容域名覆盖：`rules/proxy/adult-content.list` 全表由 `validate_repository.py` 强制与场景表和 allowlist 同步。

## 已知盲区

- 本模拟只对域名求值。`rules/direct/private.list` 与 `rules/proxy/messaging.list` 中的 IP-CIDR / IP-CIDR6 规则（含 `no-resolve`）不参与上述检查，其语义未被本报告验证；
- GEOIP,CN 仅按场景的 `cn_ip` 标记模拟，未使用真实 GeoIP 数据库，也未固定 GeoIP 数据版本；
- 不模拟账户登录、DRM、设备地区、服务端风控或流媒体解锁结果。

## 数据来源与限制

- Apple、Google FCM 和 Google Translation 以官方网络/开发文档为优先参考；
- Meta 和国产服务以官方主页、自有域名及固定提交的公开规则仓库交叉核对；
- 具体来源、检索日期、第三方许可证和不可变修订记录在 `policy/sources.toml`；
- 本报告证明规则层面的确定性分流，不证明流媒体解锁、Apple Intelligence 资格、FCM 长连接、成人网站可播放性或账户风控一定成功；
- 本轮严格遵守只修改本地仓库，未连接或修改远端服务器、GitHub 仓库和生产订阅。

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
