# 规则维护规范

## 来源优先级

1. 服务官方网络或开发文档；
2. 活跃维护的公开规则仓库；
3. 实际应用与浏览器网络请求；
4. DoH、证书、ASN 和 HTTP 可达性验证；
5. ACL4SSR 旧规则只作待核对候选。

所有来源登记在 `policy/sources.toml`。

## 直连

直连只接受：

- localhost、LAN、私有和链路本地地址；
- 经验证的中国大陆公网 IP；
- 少量有充分证据且确有必要的国内业务例外。

未知境外域名默认代理。禁止把 Google Translate、OKX 等受阻或地区敏感服务加入泛直连列表。

微信、抖音、小红书、微博、国产视频和国产 AI 使用独立的 `china-services.list`。优先收录服务自有域名；共享 CDN 和整个厂商根域需要额外证据，避免把境外业务误导向 DIRECT。

## Apple

Apple 清单应按月对照官方企业网络文档，重点关注：

- Apple Account；
- iCloud 和 iCloud Content；
- App Store 与模型/软件分发；
- APNs；
- Apple Intelligence、Siri、Search；
- Private Cloud Compute 和第三方 relay 主机。

共享 CDN 域名必须使用精确主机，不得把整个 Cloudflare/Fastly 域名后缀归入 Apple。

## Google 与 FCM

Google Translate、Google API 和 FCM 归 Google。FCM 域名和端口以 Firebase 官方网络说明为基线，并通过 Android 通知延迟实测。

## 加密货币

交易所需要覆盖网页、登录、REST、WebSocket、静态资源和验证服务。测试只做只读访问，不进行交易。出口地区应稳定，避免频繁切换触发风控。

## 成人内容与广告

- 成人内容站点归 `adult-content.list`（独立分组，默认代理、可选 REJECT）；
- 成人广告网络与通用广告合并为单一 `ads-base.list`，统一进入广告拦截组；
- 成人站点不得被广告规则捕获（分类归属护栏，见 `validate_repository.py`）；
- 修改广告规则后必须运行 `tests/fixtures/adult-sites-allow.txt` 保护检查；
- 实际 Canary 要验证主页、登录、图片、视频和直播功能。

行为分析类域名只屏蔽明显不承担登录、支付、验证码、深链和媒体传输职责的低价值跟踪器。AppsFlyer、Adjust、Branch 等可能承担归因和深链功能的域名默认不进入基础拒绝表。

## 更新门禁

以下情况禁止自动发布：

- 上游条目数量异常增减；
- 来源不可访问；
- 格式变化；
- 规则目标组不存在；
- 成人内容主域进入 REJECT；
- 生成配置过期；
- 测试或 Mihomo 校验失败。
