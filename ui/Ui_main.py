"""
此模块实现了主窗口的 UI 界面，根据插件列表显示 Ui_item 实例。
"""
import os
import hashlib
import json
import requests
from datetime import datetime, timedelta
from PyQt5 import QtWidgets, QtCore, QtGui  # 已有导入
from PyQt5.QtCore import QObject, QThread, pyqtSignal  # 新增 QObject 导入
from ui.Ui_item import Ui_Form
from PIL import Image  # 导入 Pillow 库

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 构建图标文件的绝对路径
ICON_PATH = os.path.join(SCRIPT_DIR, "..", "img", "icon.png")
# 缓存目录
CACHE_DIR = os.path.join(SCRIPT_DIR, "..", "icon_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
# setting.json 文件路径
SETTING_PATH = os.path.join(SCRIPT_DIR, "..", "settings.json")


class IconLoader(QtCore.QThread):
    """
    图标加载线程类，负责从网络或缓存加载图标，同时移除 PNG 图像的 iCCP 信息。
    """
    icon_loaded = QtCore.pyqtSignal(QtGui.QPixmap, object)

    def __init__(self, icon_url, cache_file, ui, default_pixmap, proxy):
        super().__init__()
        self.icon_url = icon_url
        self.cache_file = cache_file
        self.ui = ui
        self.default_pixmap = default_pixmap
        self.proxy = proxy
        # print(f"IconLoader initialized with URL: {self.icon_url}, Cache file: {self.cache_file}")

    def remove_iccp_profile(self, image_path):
        """
        更彻底地移除 PNG 图像中的 iCCP 信息。

        :param image_path: 图像文件的路径
        """
        try:
            img = Image.open(image_path)
            # 转换图像模式为 RGB，避免保存时保留元数据
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 保存处理后的图像，明确指定参数以移除元数据
            img.save(image_path, "PNG", optimize=True, quality=95, icc_profile=b'')
            # print(f"Successfully removed iCCP profile from {image_path}")
        except Exception as e:
            # print(f"处理图像 {image_path} 时出错: {e}")
            pass

    def run(self):
        """
        线程执行的主要逻辑，优先从缓存加载图标，若缓存不存在则从网络或本地加载，
        保存图标时移除 iCCP 信息。
        """
        if os.path.exists(self.cache_file):
            # print(f"Loading icon from cache: {self.cache_file}")
            pixmap = QtGui.QPixmap(self.cache_file)
            if not pixmap.isNull():
                # print(f"Successfully loaded icon from cache: {self.cache_file}")
                self.icon_loaded.emit(pixmap, self.ui)
                return
            else:
                # print(f"Failed to load icon from cache: {self.cache_file}")
                pass

        # 检查是否为本地文件路径
        if os.path.exists(self.icon_url):
            # print(f"Loading local icon: {self.icon_url}")
            self._load_and_save_icon(self.icon_url)
            return

        try:
            # print(f"Downloading icon from {self.icon_url}")
            response = requests.get(self.icon_url, proxies=self.proxy, timeout=5)
            response.raise_for_status()
            with open(self.cache_file, 'wb') as f:
                f.write(response.content)
            # print(f"Successfully downloaded icon to {self.cache_file}")
            self._load_and_save_icon(self.cache_file)
        except requests.RequestException as e:
            # print(f"请求图片 {self.icon_url} 时出错: {e}")
            self.icon_loaded.emit(self.default_pixmap, self.ui)

    def _load_and_save_icon(self, image_path):
        """
        加载图标并保存到缓存，同时移除 iCCP 信息。

        :param image_path: 图像文件的路径
        """
        pixmap = QtGui.QPixmap(image_path)
        if not pixmap.isNull():
            # 保存到缓存
            pixmap.save(self.cache_file)
            if self.cache_file.lower().endswith('.png'):
                self.remove_iccp_profile(self.cache_file)
            # print(f"Successfully loaded and saved icon: {image_path}")
            self.icon_loaded.emit(pixmap, self.ui)
        else:
            # print(f"无法加载图片: {image_path}，可能是不支持的格式")
            self.icon_loaded.emit(self.default_pixmap, self.ui)


class PluginListUpdater(QThread):
    """
    用于在单独线程中获取和更新插件列表的类，继承自 QThread。
    带有缓存机制，程序启动时优先读取缓存，缓存过期或强制更新时从互联网拉取更新，
    并更新插件的收藏状态。
    """
    plugin_list_updated = pyqtSignal(list)

    def __init__(self, settings_fp="settings.json", force_update=False):
        super().__init__()
        self.settings_fp = settings_fp
        self.force_update = force_update

    def _get_cache_plugin_list(self, cache_plugin_fp, cache_plugin_time):
        """
        尝试从缓存文件中获取插件列表，若缓存未过期则返回缓存数据。

        :param cache_plugin_fp: 缓存插件文件的路径
        :param cache_plugin_time: 缓存有效时间，格式为 "%Y-%m-%d %H:%M:%S"
        :return: 缓存的插件列表或空列表
        """
        try:
            cache_time = datetime.strptime(cache_plugin_time, "%Y-%m-%d %H:%M:%S")
            if os.path.exists(cache_plugin_fp):
                now = datetime.now()
                if now - cache_time < timedelta(hours=24):
                    with open(cache_plugin_fp, "r", encoding="utf-8") as f:
                        return json.load(f)
        except FileNotFoundError:
            pass
        except ValueError:
            print("缓存时间格式错误，应使用 '%Y-%m-%d %H:%M:%S' 格式。")
        return []

    def _fetch_new_plugin_list(self, repo_index_fp, proxies):
        """
        从指定的仓库索引文件中读取 URL，请求这些 URL 并处理返回的数据，生成新的插件列表。

        :param repo_index_fp: 存储仓库索引的文件路径
        :param proxies: 代理配置，字典类型
        :return: 新的插件列表
        """
        try:
            with open(repo_index_fp, "r") as f:
                repo_index = f.readlines()
        except FileNotFoundError:
            print(f"文件 {repo_index_fp} 未找到。")
            return []

        plugin_list = []
        hash_set = set()
        for index, i in enumerate(repo_index):
            url = i.strip()
            if url.startswith("##"):
                continue
            try:
                response = requests.get(url, proxies=proxies, timeout=10).text
                data = json.loads(response)
                print(index)
                for j in data:
                    j["URL"] = url
                    # 使用 hashlib.md5 生成确定的哈希值
                    combined_str = (url + j["Name"]).encode('utf-8')
                    plugin_hash = hashlib.md5(combined_str).hexdigest()
                    if plugin_hash in hash_set:
                        continue
                    hash_set.add(plugin_hash)
                    j["Hash"] = plugin_hash
                    j["is_favorite"] = False
                    plugin_list.append(j)
            except requests.RequestException as e:
                print(f"请求 {url} 时出错: {e}")
            except json.JSONDecodeError as e:
                print(f"解析 {url} 的响应数据时出错: {e}")
        return plugin_list

    def _update_cache_and_settings(self, cache_plugin_fp, plugin_list):
        """
        将新获取的插件列表写入缓存文件，并更新设置文件中的缓存时间。

        :param cache_plugin_fp: 缓存插件文件的路径
        :param plugin_list: 新的插件列表
        """
        try:
            with open(cache_plugin_fp, "w", encoding="utf-8") as f:
                json.dump(plugin_list, f, ensure_ascii=False, indent=4)
            with open(self.settings_fp, "r", encoding="utf-8") as f:
                settings = json.load(f)
            settings["cache_plugin_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.settings_fp, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"写入缓存文件 {cache_plugin_fp} 时出错: {e}")

    def update_favorite_status(self, plugin_list, my_plugin_fp="MyRepo.json"):
        """
        读取 MyRepo.json 文件，如果文件不存在则创建，更新 plugin_list 里的 "is_favorite" 字段。

        :param plugin_list: 插件列表
        :param my_plugin_fp: MyRepo.json 文件的路径，默认为 "MyRepo.json"
        :return: 更新后的插件列表
        """
        favorite_dict = {}
        try:
            with open(my_plugin_fp, "r", encoding="utf-8") as f:
                favorite_dict = json.load(f)
        except FileNotFoundError:
            favorite_dict = {str(plugin["Hash"]): False for plugin in plugin_list}
            try:
                with open(my_plugin_fp, "w", encoding="utf-8") as f:
                    json.dump(favorite_dict, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"创建 {my_plugin_fp} 时出错: {e}")
        except Exception as e:
            print(f"读取 {my_plugin_fp} 时出错: {e}")

        for plugin in plugin_list:
            plugin_hash = str(plugin["Hash"])
            if plugin_hash in favorite_dict:
                plugin["is_favorite"] = favorite_dict[plugin_hash]
        return plugin_list

    def run(self):
        """
        线程执行的主要逻辑，从设置文件中读取配置，
        缓存过期或强制更新时从互联网拉取更新，完成后发送信号。
        """
        try:
            with open(self.settings_fp, "r", encoding="utf-8") as f:
                settings = json.load(f)
                proxies = settings.get("proxy", {})
                repo_index_fp = settings.get("repo_index_fp", "RepoIndex.txt")
                cache_plugin_fp = settings.get("cache_plugin_fp", "cache_plugin.json")
                my_plugin_fp = settings.get("my_plugin_fp", "MyRepo.json")
                cache_plugin_time = settings.get("cache_plugin_time", "2023-01-01 00:00:00")
        except FileNotFoundError:
            print(f"未找到设置文件 {self.settings_fp}")
            self.plugin_list_updated.emit([])
            return

        cache_plugin_list = []
        if not self.force_update:
            cache_plugin_list = self._get_cache_plugin_list(cache_plugin_fp, cache_plugin_time)

        if cache_plugin_list:
            plugin_list = cache_plugin_list
        else:
            plugin_list = self._fetch_new_plugin_list(repo_index_fp, proxies)
            self._update_cache_and_settings(cache_plugin_fp, plugin_list)

        plugin_list = self.update_favorite_status(plugin_list, my_plugin_fp)
        self.plugin_list_updated.emit(plugin_list)


class Git_Updater(QThread):
    """
    基于线程实现的 Git 更新类，负责读取 MyRepo.json 文件，
    去除自定义键值对，保存到 PluginMaster.json，最后推送到 GitHub。
    """
    update_finished = pyqtSignal(int, list)  # 信号，参数为更新数量和更新列表

    def __init__(self, plugin_list, my_repo_fp="MyRepo.json", git_repo_fp="PluginMaster.json"):
        super().__init__()
        self.plugin_list = plugin_list
        self.my_repo_fp = my_repo_fp
        self.git_repo_fp = git_repo_fp
        self.update_count = 0
        self.update_list = []

    def _read_my_repo(self):
        """
        读取 MyRepo.json 文件，如果文件不存在则创建空列表。
        """
        if not os.path.exists(self.my_repo_fp):
            return []
        try:
            with open(self.my_repo_fp, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"读取 {self.my_repo_fp} 时出错: {e}")
            return []

    def _process_repo_list(self, my_repo_list):
        """
        处理仓库列表，去除自定义键值对，更新计数和更新列表。
        """
        processed_list = []
        for hash_code,bool in my_repo_list.items():
            if bool:
                for item in self.plugin_list:
                    if "Hash" not in item:
                        if "URL" in item:
                            print(item["URL"])
                        if "Name" in item:
                            print(item["Name"])
                        if "URL" not in item or "Name" not in item:
                            continue
                        # 计算Hash值
                        combined_str = (item["URL"] + item["Name"]).encode('utf-8')
                        plugin_hash = hashlib.md5(combined_str).hexdigest()
                        item["Hash"] = plugin_hash
                    if item["Hash"] == hash_code:
                        self.update_count += 1
                        self.update_list.append(item["Name"])
                        # 假设要去除的键为 "URL", "Hash", "is_favorite"
                        data = item
                        # data.pop("URL", None)
                        # data.pop("Hash", None)
                        # data.pop("is_favorite", None)
                        processed_list.append(data)
        return processed_list

    def _save_to_plugin_master(self, processed_list):
        """
        将处理后的数据保存到 PluginMaster.json 文件。
        """
        try:
            with open(self.git_repo_fp, 'w', encoding='utf-8') as file:
                json.dump(processed_list, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"写入 {self.git_repo_fp} 时出错: {e}")

    def _commit_and_push(self):
        """
        执行 git 提交和推送操作。
        """
        # 执行 git 提交和推送操作
        os.system("git add .")
        os.system('git commit -m "update Repo"')
        os.system("git push")


    def run(self):
        """
        线程执行的主要逻辑，依次读取文件、处理数据、保存文件、提交推送，
        最后发送更新完成信号。
        """
        my_repo_list = self._read_my_repo()
        processed_list = self._process_repo_list(my_repo_list)
        self._save_to_plugin_master(processed_list)
        self._commit_and_push()
        self.update_finished.emit(self.update_count, self.update_list)

class Ui_MainWindow(QObject):  # 继承自 QObject
    def __init__(self):
        super().__init__()  # 调用父类构造函数
        self.plugin_list = []
        self.ui_items = []
        self.icon_loaders = []
        self.proxy_input = None
        self.scroll_area = None
        self.scroll_content = None
        self.scroll_layout = None
        self.spinner_label = None  # 新增旋转图标标签
        self.spinner_movie = None  # 新增旋转图标动画
        self.plugin_updater = None  # 新增插件更新线程实例
        self.MainWindow = None

    def _setup_proxy_layout(self):
        """
        创建代理输入框和按钮布局。
        """
        proxy_layout = QtWidgets.QHBoxLayout()

        # 代理输入框
        self.proxy_input = QtWidgets.QLineEdit()
        self.proxy_input.setText("127.0.0.1:7897")

        # 计算输入框合适的宽度
        font_metrics = self.proxy_input.fontMetrics()
        input_width = font_metrics.horizontalAdvance("127.0.0.1:7897") + 20
        self.proxy_input.setFixedWidth(input_width)
        proxy_layout.addWidget(self.proxy_input)

        # 第一个按钮
        button1 = QtWidgets.QPushButton("更新插件列表")
        proxy_layout.addWidget(button1)
        button1.clicked.connect(self.update_plugin_list)

        # 旋转图标标签
        self.spinner_label = QtWidgets.QLabel()
        self.spinner_movie = QtGui.QMovie(os.path.join(SCRIPT_DIR, "..", "img", "spin.gif"))
        self.spinner_label.setMovie(self.spinner_movie)
        # 缩放至30*30，scale
        self.spinner_label.setScaledContents(True)
        self.spinner_label.setFixedSize(30, 30)
        self.spinner_label.hide()  # 初始隐藏
        proxy_layout.addWidget(self.spinner_label)

        # 第二个按钮，重命名为 git 并绑定 Git 更新方法
        button2 = QtWidgets.QPushButton("git")
        proxy_layout.addWidget(button2)
        button2.clicked.connect(self.start_git_update)

        # 添加可伸展的水平占位符，将后续按钮推到右侧
        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        proxy_layout.addItem(spacer)

        # 右上角第一个按钮
        right_button1 = QtWidgets.QPushButton("右上按钮1")
        proxy_layout.addWidget(right_button1)

        # 右上角第二个按钮
        right_button2 = QtWidgets.QPushButton("右上按钮2")
        proxy_layout.addWidget(right_button2)

        return proxy_layout

    def _setup_scroll_area(self):
        """
        创建滚动区域。
        """
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QtWidgets.QWidget()
        scroll_content.setMinimumWidth(700)
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        return scroll_area, scroll_content, scroll_layout

    def setupUi(self, MainWindow, plugin_list = [], rebuild=False):
        """
        初始化或重新构建主窗口的 UI 界面。

        :param MainWindow: 主窗口实例
        :param plugin_list: 插件列表
        :param rebuild: 是否重新构建 UI，默认为 False
        """

        self.MainWindow = MainWindow

        if not rebuild:
            MainWindow.setWindowTitle("Item List Window")
            MainWindow.setGeometry(100, 100, 800, 600)

            layout = QtWidgets.QVBoxLayout(MainWindow)

            proxy_layout = self._setup_proxy_layout()
            layout.addLayout(proxy_layout)

            self.scroll_area, self.scroll_content, self.scroll_layout = self._setup_scroll_area()
            layout.addWidget(self.scroll_area)

            if isinstance(MainWindow, QtWidgets.QWidget):
                MainWindow.showEvent = self.handle_show_event

        if rebuild:
            # 清空现有插件项
            for i in reversed(range(self.scroll_layout.count())):
                item = self.scroll_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()

        self.plugin_list = plugin_list
        self.ui_items = []

        for plugin in plugin_list:
            item_widget = QtWidgets.QWidget()
            name = plugin.get("Name", "未知插件")
            info = plugin.get("Description", "暂无插件信息")
            icon = plugin.get("IconUrl")
            if not icon or not icon.startswith(('http://', 'https://')):
                icon = ICON_PATH

            default_pixmap = QtGui.QPixmap(ICON_PATH)

            ui = Ui_Form(plugin_list=plugin_list)
            ui.setupUi(item_widget, name, info, default_pixmap, plugin["Hash"], plugin)
            self.ui_items.append((ui, icon, default_pixmap))

            self.scroll_layout.addWidget(item_widget)

        # 当 rebuild 为 True 时，执行图标加载操作
        if rebuild:
            self.load_icons()

    def load_icons(self):
        """
        加载所有插件图标的方法。
        """
        for ui, icon, default_pixmap in self.ui_items:
            cache_file = self.get_cache_file(icon)
            proxy = self.get_proxy_from_input()
            loader = IconLoader(icon, cache_file, ui, default_pixmap, proxy)
            loader.icon_loaded.connect(self.update_icon)
            # print(f"Connecting icon_loaded signal for {icon}")
            loader.start()
            self.icon_loaders.append(loader)

    def handle_show_event(self, event):
        """
        处理窗口显示事件，窗口显示后开始加载图标。

        :param event: 显示事件
        """
        self.load_icons()
        event.accept()

    def get_proxy_from_input(self):
        """
        从输入框获取代理地址并转换为代理配置格式。
        """
        proxy_text = self.proxy_input.text()
        if proxy_text:
            return {
                "http": f"http://{proxy_text}",
                "https": f"https://{proxy_text}"
            }
        return None

    def get_cache_file(self, url):
        """
        根据 URL 生成缓存文件名。

        :param url: 图标的 URL
        :return: 缓存文件的路径
        """
        if url is None:
            url = ""
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        return os.path.join(CACHE_DIR, f"{url_hash}.png")

    def update_icon(self, pixmap, ui):
        """
        更新 UI 上的图标。

        :param pixmap: 要显示的图标
        :param ui: Ui_Form 实例
        """
        # print("Updating icon...")
        try:
            ui.update_icon(pixmap)
            # print("Icon updated successfully.")
        except Exception as e:
            print(f"Error updating icon: {e}")

    def __del__(self):
        # 停止所有图标加载线程
        for loader in self.icon_loaders:
            loader.quit()
            loader.wait()

    def update_plugin_list(self):
        """
        更新插件列表，包括更新代理设置、删除缓存文件和重新加载插件列表。
        """
        proxy_text = self.proxy_input.text()
        if proxy_text:
            proxy_config = {
                "https": proxy_text
            }
            try:
                with open(SETTING_PATH, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                settings['proxy'] = proxy_config
                with open(SETTING_PATH, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
            except FileNotFoundError:
                print("未找到 settings.json 文件")
            except Exception as e:
                print(f"更新 settings.json 出错: {e}")

        cache_plugin_fp = os.path.join(os.path.dirname(SETTING_PATH), 'cache_plugin.json')
        if os.path.exists(cache_plugin_fp):
            os.remove(cache_plugin_fp)

        # 显示旋转图标并开始动画
        self.spinner_movie.start()
        self.spinner_label.show()

        # 创建并启动插件更新线程
        self.plugin_updater = PluginListUpdater(SETTING_PATH)
        self.plugin_updater.plugin_list_updated.connect(self.on_plugin_list_updated)
        self.plugin_updater.start()

    def on_plugin_list_updated(self, new_plugin_list):
        """
        处理插件列表更新完成后的操作。

        :param new_plugin_list: 更新后的插件列表
        """
        # 隐藏旋转图标并停止动画
        self.spinner_movie.stop()
        self.spinner_label.hide()

        self.plugin_list = new_plugin_list
        self.setupUi(self.MainWindow, new_plugin_list, rebuild=True)

    def start_git_update(self):
        """
        启动 Git 更新线程。
        """
        plugin_list = self.plugin_list
        self.git_updater = Git_Updater(plugin_list)
        self.git_updater.update_finished.connect(self.on_git_update_finished)
        self.git_updater.start()

        # 显示旋转图标并开始动画
        self.spinner_movie.start()
        self.spinner_label.show()

    def on_git_update_finished(self, update_count, update_list):
        """
        处理 Git 更新完成后的操作，显示消息框。

        :param update_count: 更新的插件数量
        :param update_list: 更新的插件列表
        """
        # 隐藏旋转图标并停止动画
        self.spinner_movie.stop()
        self.spinner_label.hide()

        QtWidgets.QMessageBox.information(
            self.MainWindow,
            "上传",
            f"更新完成，共更新{update_count}个插件，更新列表：\n{update_list}"
        )