# DeepSeek Balance Widget

一个 Windows 桌面浮动插件，实时显示 DeepSeek API 账户余额。

## 功能

- 浮动置顶面板，显示总余额、赠送余额、充值余额
- 每 5 分钟自动刷新（可在设置中调整）
- 系统托盘驻留，右键菜单可手动刷新、修改设置、退出
- 余额低于 ¥1 时数字变红提醒
- 首次运行输入 API Key，后续自动记住

## 使用方式

### 下载 exe（无需 Python）

从 [Releases](https://github.com/hkdatahub/deepseek-balance-widget/releases) 下载 `DeepSeek-Balance-Widget.exe`，双击运行。

### 从源码运行

```bash
git clone https://github.com/hkdatahub/deepseek-balance-widget.git
cd deepseek-balance-widget
pip install -r requirements.txt
python main.py
```

### 打包

```bash
python build.py
# 输出: dist/DeepSeek-Balance-Widget.exe
```

## 截图

运行后效果：

- 标题栏显示 "DeepSeek"，右侧 × 按钮关闭窗口（程序仍在托盘运行）
- 大字体显示总余额，下方分列赠送余额和充值余额
- 底部显示最后更新时间
- 右键系统托盘图标可打开设置、手动刷新、退出

## 技术栈

Python 3.11+ / PySide6 / requests / PyInstaller

## License

MIT
