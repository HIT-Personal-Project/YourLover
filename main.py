"""
YourLover 桌面助手启动入口

职责：
- 作为应用启动入口，创建 App 实例并运行。

设计说明：
- 应用核心逻辑（生命周期管理、组件初始化、EventBus 信号路由、AgentWorker
  工作线程管理）全部由 app.App 负责，本模块仅做最小化的启动封装。
- 保持 `python main.py` 启动方式不变。
"""

import sys

from app import App


def main() -> int:
    """启动桌面助手：创建 App 并进入事件循环。

    Returns:
        App.run() 返回的 Qt 退出码。
    """
    application = App()
    return application.run()


if __name__ == "__main__":
    sys.exit(main())
