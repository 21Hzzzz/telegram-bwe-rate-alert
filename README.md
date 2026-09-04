# Telegram BWE Rate Alert

以 root 身份运行的 Ubuntu/Debian 常驻服务：监控 `https://t.me/BWE_pricechange_monitor`，当滚动 60 秒内收到至少 5 条消息时，对指定 webhook URL 发起一次 HTTP GET 请求。同一波高频消息只通知一次；消息速率恢复后，下一波会重新通知。

## 一键部署

使用 root 登录服务器后执行：

```bash
curl -fsSL https://raw.githubusercontent.com/21Hzzzz/telegram-bwe-rate-alert/main/install.sh | bash
```

安装器会从当前终端读取交互输入，因此可安全使用上述 `curl | bash` 命令。

安装过程会交互式要求输入：Telegram 手机号、[API ID 与 API Hash](https://my.telegram.org/apps)、告警 webhook 完整 URL、Telegram 验证码；如账户启用两步验证，还会安全地要求输入密码。

输入 webhook 后，安装器会立即以 HTTP GET 探测它；只有收到成功响应才会继续。服务每次启动也会再次检查并写入日志。由于 webhook 的协议是“访问即告警”，这两次检查都可能产生测试通知。

该 Telegram 账号必须能访问目标频道。安装程序不会自动加入频道。

对于内存小于 768 MiB 且没有至少 256 MiB swap 的服务器，安装器会自动创建并启用一个持久化的 512 MiB `/swapfile`，以避免 Python 依赖安装时触发 OOM。

## 运维命令

```bash
systemctl status telegram-bwe-rate-alert
journalctl -u telegram-bwe-rate-alert -f
systemctl restart telegram-bwe-rate-alert
systemctl stop telegram-bwe-rate-alert
```

卸载服务及其凭据：

```bash
systemctl disable --now telegram-bwe-rate-alert
rm -f /etc/systemd/system/telegram-bwe-rate-alert.service
systemctl daemon-reload
rm -rf /opt/telegram-bwe-rate-alert /etc/telegram-bwe-rate-alert /var/lib/telegram-bwe-rate-alert
```

## 安全与行为

- Telegram 配置和 session 均以 root-only 权限保存，不会提交到仓库。
- webhook 直接以 HTTP GET 访问；程序不向 URL 增加消息正文或查询参数。
- webhook 失败会写入 systemd 日志，但 Telegram 监听会继续运行。
