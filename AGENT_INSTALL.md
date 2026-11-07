# Agent 安装协议 · v0.3.0-alpha.1

[English](AGENT_INSTALL.en.md)


## 来源与校验
只从[本版本的 GitHub Release](https://github.com/osszhaoke/ptd-substrate/releases/tag/v0.3.0-alpha.1) 下载压缩包和同页 SHA256SUMS。下载后断开外网。在一个新的空目录运行 `shasum -a 256 -c SHA256SUMS`，再解压；在解压出的目录执行 `sh scripts/verify_release.sh`。核对所有文件才继续，缺项、多项或校验失败即停。包未签名；Hash 证明与取得的清单一致。完整性与发布者身份是两个检查。

## 环境
仅检查本机 `sw_vers`、`python3 --version` 与 Python 的 SQLite 导入。演练平台见[快速开始](README.md)。本版不需要 pip、npm、额外依赖、管理员权限或模型。缺依赖即说明差异并停止。

## 本人选择空间
让本人给出新数据根、实例标识、显示名、时区和配置输出位置。先用随包建库入口创建该空间，再由本人在终端完成随包安装器交互。安装器只接受已经初始化的目录。不要猜目标、枚举个人目录、改写已有配置或复用既有空间。公开示例配置只供阅读。按[快速开始](README.md)逐条执行两个 Python 命令，选 1 走虚构试用。配置写入是安装器唯一的首次创建操作。

## 启动与导入
执行 `python3 -B scripts/start_trial.py --root "$SPACE_ROOT" --config "$TRIAL_CONFIG"`。把终端给出的本机回环地址交给本人；随机端口仅供本次进程。首开语言由本人决定。到 CSV 表格入口打开 `data/sample-import.csv`，在待核对页停下。两个重复行应完整保留。保存按钮只由本人点击，退出使用 Ctrl+C。重新使用既有空间时直接启动，不重复建库。

## 可选 Oura 与边界
真实账号接入需要本人单独决定。见 [Oura 指南](docs/guides/oura.md)。本人在终端向本机钥匙串写入密钥，在浏览器授权。Agent 不查询钥匙串、不接收或回显密钥，不读取健康数值。不要安装依赖、改源码、手改配置、上传数据、启用被拒通道或读取用户其他文件。用虚构数据报错；遇到未知操作结果先停。

## 基因原始文件

由本人选择文件并声明数据性质。Agent 仅可按本人指示调用导入，不得打开、读取、复述或分析用户的基因文件内容。演练使用 app/fixtures/fictional-genotype-sample.txt。

虚构试用在建库时传入 `--accept SYNTHETIC`，安装时选 1。明确接收两种性质的本人空间在建库时传入 `--accept REAL SYNTHETIC` 和 `--kind REAL`，安装时选 2。遇到范围不一致请停下，安装器不会修改既有空间。
