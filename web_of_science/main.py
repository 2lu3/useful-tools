from typing import Dict
import pyautogui as ag
import argparse
import math
import time
import toml
from alive_progress import alive_bar

def wait():
    pass

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("paper_num", type=int)

    return parser.parse_args()

def wait_to_select_browser():
    for i in range(3):
        print(i)
        time.sleep(1)


def load_config():
    with open("config.toml", "r") as f:
        return toml.load(f)


def open_tabs(num):
    with alive_bar(num) as bar:
        for _ in range(num):
            ag.keyDown("alt")
            ag.keyDown("d")
            ag.keyDown("enter")
            ag.keyUp("alt")
            ag.keyUp("d")
            ag.keyUp("enter")
            bar()

def open_tabs_again(num):
    """明示的に開かないと、ページのロードが遅延してしまうことがある"""
    ctrl_tab_nums = num +1 
    # 一番うしろのタブに移動するため

    with alive_bar(ctrl_tab_nums) as bar:
        for _ in range(ctrl_tab_nums):
            ag.hotkey("ctrl", "tab")
            bar()

def download(config: Dict, num):
    write_interval = 1 / 10
    def _click(x, y):
        ag.moveTo(x, y)
        ag.click() 

    with alive_bar(num * 9) as bar:
        for i in range(num):
            start, end = (500 * i + 1, 500 * (i + 1))

            ag.hotkey("ctrl", "tab")
            bar()

            _click(config["range_selector"]["x"], config["range_selector"]["y"])
            bar()

            ag.press("tab")
            bar()
            ag.write(str(start), interval=write_interval)
            bar()

            ag.press("tab")
            bar()
            ag.write(str(end), interval=write_interval)
            bar()

            _click(config["export_kind_selector"]["x"], config["export_kind_selector"]["y"])
            bar()

            _click(config["export_kind"]["x"], config["export_kind"]["y"])
            bar()

            _click(config["export_button"]["x"], config["export_button"]["y"])
            bar()


def main():
    args = parse_args()

    download_times = math.ceil(args.paper_num / 500)

    WINDOW_WIDTH, WINDOW_HEIGHT = ag.size()
    print("window size:", WINDOW_WIDTH, WINDOW_HEIGHT)

    config = load_config()

    wait_to_select_browser()

    print('open new tabs')
    open_tabs(download_times)
    print('open tabs again')
    open_tabs_again(download_times)

    print('waiting to load')
    with alive_bar(100) as bar:
        for _ in range(100):
            time.sleep(0.1)
            bar()

    print('download')
    download(config, download_times)


if __name__ == "__main__":
    main()
