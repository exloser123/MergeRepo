import json
import requests
import tkinter as tk
from tkinter import messagebox
import os

repo_index_fp = "RepoIndex.txt"
repo_index = open(repo_index_fp, "r").readlines()

plugin_list = []
for i in repo_index:
    url = i.split("\n")[0]
    if url.startswith("##"):
        continue
    response = requests.get(url).text
    data = json.loads(response)
    print(repo_index.index(i))
    for j in data:
        api_level = 0
        if "DalamudApiLevel" in j.keys():
            api_level = int(j["DalamudApiLevel"])
        if "TestingDalamudApiLevel" in j.keys() and int(j["TestingDalamudApiLevel"]) < api_level:
            api_level = int(j["TestingDalamudApiLevel"])
        if "DalamudApiLevel" not in j.keys() and "TestingDalamudApiLevel" not in j.keys():
            api_level = 0
        Plugin_dict = {
            "URL":url,
            "Name":j["Name"],
            "APILevel":api_level,
            "Dict":j
        }
        plugin_list.append(Plugin_dict)

def list_select(evt):
    cur = list_Repo.curselection()[0]
    # 删除目前TEXT里的文字
    Repo_Description.delete(1.0, tk.END)
    Repo_Description.insert(tk.END, filter_plugin_list[cur]["URL"] + "\n")
    global current_select
    current_select = filter_plugin_list[cur]
    for key, value in current_select["Dict"].items():
        temp_str = f"{key}\t:\t{value}\n"
        Repo_Description.insert(tk.END, temp_str)

def my_list_select(evt):
    cur = list_My_Repo.curselection()[0]
    Repo_Description.delete(1.0, tk.END)
    Repo_Description.insert(tk.END, filter_my_repo_list[cur]["URL"] + "\n")
    global current_select
    current_select = filter_my_repo_list[cur]
    for key, value in current_select["Dict"].items():
        temp_str = f"{key}\t:\t{value}\n"
        Repo_Description.insert(tk.END, temp_str)


def filter_list(event):
    search_string = Repo_Search.get().lower()
    global filter_plugin_list
    filter_plugin_list = [_item for _item in plugin_list if search_string in _item["Name"].lower()]
    global filter_my_repo_list
    filter_my_repo_list = [_item for _item in my_Repo_list if search_string in _item["Name"].lower()]
    list_Repo.delete(0, tk.END)
    list_My_Repo.delete(0, tk.END)
    for _item in filter_plugin_list:  # 第一个小部件插入数据
        list_Repo.insert(tk.END, _item["Name"])
    for _item in filter_my_repo_list:
        list_My_Repo.insert(tk.END, _item["Name"])

def ADD_TO_LIST(event):
    if current_select in my_Repo_list:
        return
    my_Repo_list.append(current_select)
    filter_my_repo_list.append(current_select)
    list_My_Repo.delete(0, tk.END)
    for _item in filter_my_repo_list:
        list_My_Repo.insert(tk.END, _item["Name"])

def DELETE_FROM_LIST(event):
    my_Repo_list.remove(current_select)
    filter_my_repo_list.remove(current_select)
    list_My_Repo.delete(0, tk.END)
    for _item in filter_my_repo_list:
        list_My_Repo.insert(tk.END, _item["Name"])

def UPDATE_REPO():
    global filter_my_repo_list
    UPDATE_COUNT = 0
    UPDATE_LIST = []
    for _item in filter_plugin_list:
        for _item_my in filter_my_repo_list:
            if _item["Name"] == _item_my["Name"] and _item["URL"] == _item_my["URL"]:
                if _item == _item_my:
                    continue
                else:
                    _item_my["Dict"] = _item["Dict"]
                    UPDATE_COUNT += 1
                    UPDATE_LIST.append(_item["Name"])
    with open(my_Repo_fp, 'w') as _file:
        json.dump(filter_my_repo_list, _file,indent=2)
    _temp_list = []
    for _item in filter_my_repo_list:
        _temp_list.append(_item["Dict"])
    with open(git_Repo_fp, 'w') as _file:
        json.dump(_temp_list, _file,indent=2)
    os.system("git commit --all -m 'update'")
    os.system("git push origin master")
    messagebox.showinfo("上传", f"更新完成，共更新{UPDATE_COUNT}个插件，更新列表：\n{UPDATE_LIST}")

my_Repo_fp = "MyRepo.json"
git_Repo_fp = "PluginMaster.json"
# 如果文件不存在，则创建
if not os.path.exists(my_Repo_fp):
    with open(my_Repo_fp, 'w') as file:
        json.dump([], file,indent=2)
else:
    with open(my_Repo_fp, 'r') as file:
        my_Repo_list = json.load(file)

filter_plugin_list = plugin_list
filter_my_repo_list = my_Repo_list
current_select = plugin_list[0]

root = tk.Tk()
# root.geometry("1200x500+200+200")

list_Repo = tk.Listbox(root,selectmode=tk.SINGLE)
Repo_scrollbar = tk.Scrollbar(root)
Repo_Description = tk.Text(root)
Repo_Search = tk.Entry(root)
UPDATE_BUTTON = tk.Button(root, text="更新", command=UPDATE_REPO)
list_My_Repo = tk.Listbox(root,selectmode=tk.SINGLE)
My_Repo_scrollbar = tk.Scrollbar(root)

list_Repo.grid(row=0, column=0, sticky=tk.N+tk.W+tk.S)
Repo_scrollbar.grid(row=0, column=1, sticky=tk.N+tk.S)
Repo_Search.grid(row=1, sticky=tk.S+tk.W)
Repo_Description.grid(row=0, column=2, sticky=tk.N)
UPDATE_BUTTON.grid(row=1, column=3, sticky=tk.S+tk.W)
list_My_Repo.grid(row=0, column=3, sticky=tk.N+tk.E+tk.S)
My_Repo_scrollbar.grid(row=0, column=4, sticky=tk.N+tk.S)



for item in filter_plugin_list:  # 第一个小部件插入数据
    list_Repo.insert(tk.END, item["Name"])
list_Repo.bind("<ButtonRelease-1>", list_select)
list_Repo.bind("<ButtonRelease-3>", ADD_TO_LIST)
Repo_Search.bind("<Return>", filter_list)
Repo_Search.bind("<Return>", filter_list)
list_Repo.config(yscrollcommand = Repo_scrollbar.set)
Repo_scrollbar.config(command = list_Repo.yview)

if len(filter_my_repo_list) > 0:
    for item in filter_my_repo_list:
        list_My_Repo.insert(tk.END, item["Name"])
list_My_Repo.bind("<ButtonRelease-1>", my_list_select)
list_My_Repo.bind("<ButtonRelease-3>", DELETE_FROM_LIST)
list_My_Repo.config(yscrollcommand = Repo_scrollbar.set)
My_Repo_scrollbar.config(command = list_Repo.yview)

root.mainloop()