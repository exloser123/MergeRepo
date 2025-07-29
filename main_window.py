"""
此模块负责调用 fetch_plugin_list 函数获取插件列表，并初始化主窗口。
"""
import sys
from PyQt5 import QtWidgets
from ui.Ui_main import Ui_MainWindow, PluginListUpdater, SETTING_PATH
import time


class MainWindow(QtWidgets.QWidget):
    """
    主窗口类，负责初始化 UI 界面。
    """
    def __init__(self):
        super().__init__()
        self.plugin_list = []
        self.ui = Ui_MainWindow()
        self.show()
        self.start_time = time.time()
        # 程序启动时读取缓存
        self.plugin_updater = PluginListUpdater(settings_fp=SETTING_PATH, force_update=False)
        self.plugin_updater.plugin_list_updated.connect(self.on_plugin_list_updated)
        self.plugin_updater.start()

    def on_plugin_list_updated(self, new_plugin_list):
        """
        处理插件列表更新完成后的操作。

        :param new_plugin_list: 更新后的插件列表
        """
        self.plugin_list = new_plugin_list
        # 调用 Ui_MainWindow 的 setupUi 方法更新界面
        self.ui.setupUi(self, new_plugin_list)

    def manual_update(self):
        """
        处理手动更新操作，强制从互联网拉取更新。
        """
        self.plugin_updater = PluginListUpdater(settings_fp=SETTING_PATH, force_update=True)
        self.plugin_updater.plugin_list_updated.connect(self.on_plugin_list_updated)
        self.plugin_updater.start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # 将 plugin_list 传递给 MainWindow 构造函数
    window = MainWindow()
    sys.exit(app.exec_())