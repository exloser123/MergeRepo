from PyQt5 import QtWidgets, QtCore, QtGui
import json
import os
import hashlib
from datetime import datetime  # 将导入移到文件开头
import sys


# # 添加打包后路径处理
# if getattr(sys, 'frozen', False):
#     # 打包后环境
#     base_path = sys._MEIPASS
# else:
#     # 开发环境
#     base_path = os.path.dirname(os.path.abspath(__file__))
#     # 向上两级目录（因为Ui_item.py在ui子目录下）
#     base_path = os.path.dirname(os.path.dirname(base_path))

# ==== 修改路径基础目录定义 ====
# 判断是否为打包环境（exe运行）
if getattr(sys, 'frozen', False):
    # 打包后：获取 main_window.exe 所在目录
    exe_path = sys.executable
    BASE_DIR = os.path.dirname(exe_path)  # 正确定义为 BASE_DIR
else:
    # 开发环境：获取项目根目录（Ui_item.py 位于 ui 子目录，需向上两级）
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(SCRIPT_DIR)  # 项目根目录

# 构建图标文件的绝对路径（将 base_path 修正为 BASE_DIR）
# 新增：导入 importlib.resources
from importlib.resources import files

# ==== 删除原有 base_path/BASE_DIR 定义，使用资源包访问 ====
# 收藏图标通过 importlib.resources 访问
like_path = str(files("img").joinpath("like.png"))
notlike_path = str(files("img").joinpath("notlike.png"))

# 配置文件路径仍使用原逻辑
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MYREPO_PATH = os.path.join(BASE_DIR, "MyRepo.json")
SETTING_PATH = os.path.join(BASE_DIR, "settings.json")


class Ui_Form(QtCore.QObject):
    icon_loaded = QtCore.pyqtSignal(QtGui.QPixmap)

    def __init__(self, parent=None, plugin_list=None):
        super().__init__(parent)
        self.icon_loaded.connect(self.update_icon)
        self.plugin_list = plugin_list if plugin_list else []
        self.Form = None

    def setupUi(self, Form, name, info, pixmap, plugin_hash, plugin_json=None):
        Form.setObjectName("Form")
        Form.resize(600, 80)

        self.Form = Form

        # 创建垂直布局
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)

        # 创建 widget_item
        self.widget_item = QtWidgets.QWidget(Form)
        self.widget_item.setStyleSheet("background-color: #f0f0f0;")
        self.widget_item.setMinimumSize(600, 82)

        # 为 widget_item 安装事件过滤器
        self.widget_item.installEventFilter(self)

        # 创建 widget_item 的水平布局
        item_horizontal_layout = QtWidgets.QHBoxLayout(self.widget_item)

        # 左边添加一个固定 64*64 大小的 label 用于显示图标
        self.label_icon = QtWidgets.QLabel(self.widget_item)
        self.label_icon.setFixedSize(64, 64)
        self.label_icon.setAlignment(QtCore.Qt.AlignCenter)
        # 设置图标
        self.label_icon.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio))
        item_horizontal_layout.addWidget(self.label_icon)

        # 创建中间内容的垂直布局
        middle_vertical_layout = QtWidgets.QVBoxLayout()

        # 中间上方添加一个 label 用来显示插件名字
        self.label_plugin_name = QtWidgets.QLabel(self.widget_item)
        self.label_plugin_name.setText(name)
        # 字体加粗,字体大小为 14px
        self.label_plugin_name.setStyleSheet("font-weight: bold;font-size: 14px;")
        middle_vertical_layout.addWidget(self.label_plugin_name)

        # 中间下方添加一个 label 用来显示一些 info
        self.label_plugin_info = QtWidgets.QLabel(self.widget_item)
        self.label_plugin_info.setText(info)
        middle_vertical_layout.addWidget(self.label_plugin_info)

        item_horizontal_layout.addLayout(middle_vertical_layout)

        # 创建用于收藏切换的 widget
        self.favorite_widget = QtWidgets.QWidget(self.widget_item)
        favorite_layout = QtWidgets.QVBoxLayout(self.favorite_widget)
        favorite_layout.setContentsMargins(0, 0, 0, 0)

        # 创建用于显示收藏状态的 label
        self.favorite_label = QtWidgets.QLabel(self.favorite_widget)
        self.favorite_label.setFixedSize(32, 32)
        # 初始化收藏状态
        self.is_favorite = self.get_plugin_favorite_status(plugin_hash)
        self.favorite_label.setPixmap(
            QtGui.QPixmap(like_path if self.is_favorite else notlike_path).scaled(32, 32, QtCore.Qt.KeepAspectRatio)
        )
        favorite_layout.addWidget(self.favorite_label)

        # 将收藏 widget 添加到最右边
        item_horizontal_layout.addWidget(self.favorite_widget, alignment=QtCore.Qt.AlignRight)

        self.verticalLayout.addWidget(self.widget_item)

        # 创建 widget_details
        self.widget_details = QtWidgets.QWidget(Form)
        self.widget_details.setStyleSheet("background-color: white;")
        self.widget_details.setMinimumSize(600, 300)
        self.widget_details.setVisible(False)

        # 创建滚动区域
        scroll_area = QtWidgets.QScrollArea(self.widget_details)
        scroll_area.setWidgetResizable(True)

        # 创建用于显示 JSON 内容的标签
        self.json_label = QtWidgets.QLabel(scroll_area)
        self.json_label.setWordWrap(True)
        self.json_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        if plugin_json:
            # 格式化 JSON 内容，使用不同颜色显示键和值
            formatted_html = self._format_json_to_html(plugin_json)
            self.json_label.setText(formatted_html)

        # 将标签设置为滚动区域的 widget
        scroll_area.setWidget(self.json_label)

        # 将滚动区域添加到 widget_details 的布局中
        details_layout = QtWidgets.QVBoxLayout(self.widget_details)
        details_layout.addWidget(scroll_area)

        self.verticalLayout.addWidget(self.widget_details)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

        # 为 widget_item 绑定点击事件
        self.widget_item.mousePressEvent = lambda event: self.toggle_widget_details(name)

        # 为收藏 label 绑定点击事件
        self.favorite_label.mousePressEvent = lambda event: self.toggle_favorite(plugin_hash)

    def get_plugin_favorite_status(self, plugin_hash):
        """
        获取插件的收藏状态。

        :param plugin_hash: 插件的哈希值
        :return: 插件的收藏状态
        """
        for plugin in self.plugin_list:
            if plugin.get("Hash") == plugin_hash:
                return plugin.get("is_favorite", False)
        return False

    def eventFilter(self, obj, event):
        if obj == self.widget_item:
            if event.type() == QtCore.QEvent.Enter:
                # 鼠标进入时改变背景颜色为淡灰色
                self.widget_item.setStyleSheet("background-color: white;")
                return True
            elif event.type() == QtCore.QEvent.Leave:
                # 鼠标离开时恢复原始背景颜色
                self.widget_item.setStyleSheet("background-color: #f0f0f0;")
                return True
        return False

    def _format_json_to_html(self, data, indent=0):
        """
        将 JSON 数据转换为带有不同颜色的 HTML 格式。

        :param data: JSON 数据
        :param indent: 缩进级别
        :return: 格式化后的 HTML 字符串
        """
        html = ""
        space = "  " * indent
        if isinstance(data, dict):
            html += "<div>"
            for key, value in data.items():
                html += f"{space}<span style='color: blue;'>{key}:</span> "
                html += self._format_json_to_html(value, indent + 1)
                html += "<br>"
            html += "</div>"
        elif isinstance(data, list):
            html += "<div>"
            for item in data:
                html += f"{space}- "
                html += self._format_json_to_html(item, indent + 1)
                html += "<br>"
            html += "</div>"
        else:
            html += f"<span style='color: green;'>{data}</span>"
        return html

    def toggle_widget_details(self, name):
        # 切换 widget_details 的显示状态
        self.widget_details.setVisible(not self.widget_details.isVisible())
        print(f"widget_item 被点击，名称为 {name}，widget_details 显示状态已切换")

    def toggle_favorite(self, plugin_hash):
        """
        切换插件的收藏状态，并实时更新 UI，同时修改 MyRepo.json 文件，更新 settings.json 中的时间戳。

        :param plugin_hash: 插件的哈希值
        """
        print("当前程序目录:", BASE_DIR)
        print("MyRepo.json 路径:", MYREPO_PATH)
        for plugin in self.plugin_list:
            if plugin["Hash"] == plugin_hash:
                # 切换收藏状态
                plugin["is_favorite"] = not plugin["is_favorite"]
                self.is_favorite = plugin["is_favorite"]
                print(self.is_favorite)
                # 更新图标显示
                icon_path = like_path if self.is_favorite else notlike_path
                self.favorite_label.setPixmap(
                    QtGui.QPixmap(icon_path).scaled(32, 32, QtCore.Qt.KeepAspectRatio)
                )

                # 读取并更新 MyRepo.json 文件
                favorite_dict = self._read_favorite_dict()
                favorite_dict[str(plugin_hash)] = self.is_favorite
                self._write_favorite_dict(favorite_dict)

                # 更新 settings.json 中的 my_plugin_time 字段
                self._update_settings_timestamp()

                return
        print(f"未找到 Hash 值为 {plugin_hash} 的插件")

    def _read_favorite_dict(self):
        """读取 MyRepo.json 文件内容"""
        favorite_dict = {}
        if os.path.exists(MYREPO_PATH):
            try:
                with open(MYREPO_PATH, "r", encoding="utf-8") as f:
                    favorite_dict = json.load(f)
            except FileNotFoundError:
                print(f"{MYREPO_PATH} 文件未找到")
            except json.JSONDecodeError as e:
                print(f"解析 {MYREPO_PATH} 时出错: {e}")
        return favorite_dict

    def _write_favorite_dict(self, favorite_dict):
        """写入 MyRepo.json 文件"""
        try:
            with open(MYREPO_PATH, "w", encoding="utf-8") as f:
                json.dump(favorite_dict, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"写入 {MYREPO_PATH} 时出错: {e}")

    def _update_settings_timestamp(self):
        """更新 settings.json 中的 my_plugin_time 字段"""
        if os.path.exists(SETTING_PATH):
            print("settings.json 存在")
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(SETTING_PATH, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                settings["my_plugin_time"] = current_time
                with open(SETTING_PATH, "w", encoding="utf-8") as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
            except FileNotFoundError:
                print(f"{SETTING_PATH} 文件未找到")
            except json.JSONDecodeError as e:
                print(f"解析 {SETTING_PATH} 时出错: {e}")
            except Exception as e:
                print(f"更新 {SETTING_PATH} 时出错: {e}")

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))

    def update_icon(self, pixmap):
        """
        更新图标显示。

        :param pixmap: 新的图标 QPixmap 对象
        """
        self.label_icon.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio))

    def get_favorite_plugins(self):
        """
        返回所有收藏的插件。

        :return: 包含所有收藏插件的列表
        """
        return [plugin for plugin in self.plugin_list if plugin.get("is_favorite", False)]
    
    def set_visible(self, visible):
        """
        设置插件项的可见性。

        :param visible: 布尔值，True 表示可见，False 表示不可见
        """
        self.Form.setVisible(visible)
        self.widget_details.setVisible(False)