# 🎙️ Voice Timer Assistant

一个轻量级中文桌面语音助手，支持**按住说话（Push-to-Talk）**、语音转文字、大模型理解、倒计时提醒与系统托盘运行。

---

## ✨ Features

- 🎤 按住说话（Push-to-Talk）：默认快捷键 Alt + \`
- 🧠 大模型理解：基于科大讯飞 Spark Ultra-32K
- 🎧 语音识别：使用讯飞录音文件转写 API
- ⏱️ 倒计时提醒：支持自然语言表达
- 💬 聊天问答：自动识别并调用大模型回答
- 🔊 语音播报：支持倒计时与聊天回复
- 🖥️ 系统托盘：后台常驻运行
- 📜 日志窗口：可选查看运行日志

---

## 📁 项目结构

```text
voice_timer/
├── main.py              # 主程序：热键、托盘、日志窗口、主流程
├── config.py            # 配置与路径管理
├── audio_recorder.py    # 录音模块
├── speech_to_text.py    # 科大讯飞录音文件转写
├── intent_router.py     # 意图识别与时间解析
├── spark_client.py      # Spark API 调用封装
├── tts.py               # 语音播报
├── requirements.txt     # 依赖列表
├── .env.example         # 环境变量示例
├── skills/
│   ├── __init__.py
│   ├── timer.py         # 倒计时功能
│   └── chat.py          # 聊天功能
└── README.md
```

---

## 🚀 安装依赖

```bash
pip install -r requirements.txt
```

---

## 🔧 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
```

填写你的 API Key：

```env
# 讯飞录音文件转写
XFYUN_APPID=你的录音转写APPID
XFYUN_SECRET_KEY=你的录音转写SecretKey

# 讯飞 Spark 大模型
XFYUN_SPARK_APPID=你的Spark APPID
XFYUN_SPARK_API_KEY=你的Spark APIKey
XFYUN_SPARK_API_SECRET=你的Spark APISecret
XFYUN_SPARK_MODEL=spark-ultra-32k

LLM_PROVIDER=spark
```

---

## ▶️ 运行项目

```bash
python main.py
```

程序启动后会常驻系统托盘。

---

## 🎮 使用方式

1. 按住 Alt + \` 开始录音
2. 松开 ` 结束录音并自动处理

---

## 🧪 使用示例

| 语音输入 | 执行效果 |
| --- | --- |
| 倒数十秒 | 启动 10 秒倒计时 |
| 5秒后提醒我喝水 | 5 秒后语音提醒“喝水” |
| 一分钟后提醒我休息 | 60 秒后语音提醒“休息” |
| 哈基米是什么梗 | 调用 Spark 生成回答 |

---

## 📦 打包为 exe

安装 PyInstaller：

```bash
python -m pip install pyinstaller
```

先打包调试版本：

```bash
python -m PyInstaller --onefile main.py
```

确认无误后再打包正式版本：

```bash
python -m PyInstaller --onefile --noconsole main.py
```

打包完成后，将 `.env` 放在 exe 同目录：

```text
dist/
├── main.exe
└── .env
```

---

## ⚠️ 注意事项

- `.env` 不要上传到 GitHub
- 建议关闭 VPN 使用讯飞 API（否则可能出现 SSL 错误）
- 热键无效时建议使用管理员权限运行
- 无控制台模式下可通过托盘打开日志窗口
- 录音文件保存在 `recordings/` 目录

---

## ✅ TODO List

只是存在一个TODO List，很难说我会不会做（生死不明就是死了）

- [ ] 对其他云服务提供商的支持（有人提或者我的免费额度用完后会做）（也是为什么大模型和STT都用了讯飞作为提供商的原因）
- [ ] 让程序可以理解“一分半”为1分30秒（居然不支持吗？）
- [ ] 用户主动修改呼出的组合键（居然也不支持吗？）
- [ ] 开机自启动
- [ ] 托盘状态显示（监听中 / 已关闭）
- [ ] 更多语音指令（打开软件、执行命令）
- [ ] UI 界面
- [ ] 更自然的语音播报

---

## 📄 License

MIT License
