import csv
from typing import List, Tuple, Dict
from tkinter import filedialog
from dataclasses import dataclass
import toml
from time import sleep
import pyautogui as ag
from alive_progress import alive_bar
import pyperclip as clip


def file_selector():
    file_type = [("csvファイル", "*.csv")]
    return filedialog.askopenfilename(filetypes=file_type)


def read_csv(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)


def wait_with_bar(description: str, time: float):
    split_num = 100
    split_time = time / split_num
    print(description)
    with alive_bar(split_num) as bar:
        for _ in range(split_num):
            sleep(split_time)
            bar()


@dataclass
class CoordinateConfig:
    sleep_time: float
    add_problem_button: Tuple[int, int, int]
    problem_statement: Tuple[int, int]
    answer: Tuple[int, int]
    auto_generate_button: Tuple[int, int]
    ok_button: Tuple[int, int]
    save_button: Tuple[int, int]


def read_config(config_file_path: str = "./coordinate.toml") -> CoordinateConfig:
    def name2tuple(config: Dict, name: str) -> Tuple[int, int]:
        return (config[name]["x"], config[name]["y"])

    config = toml.load(config_file_path)
    return CoordinateConfig(
        config["sleep_time"]["time"],
        name2tuple(config, "add_problem_button"),
        name2tuple(config, "problem_statement"),
        name2tuple(config, "answer"),
        name2tuple(config, "auto_generate_button"),
        name2tuple(config, "ok_button"),
        name2tuple(config, "save_button"),
    )


def register_a_problem(config: CoordinateConfig, problem: List):
    print(problem)

    def _wait(repeat=1):
        sleep(config.sleep_time * repeat)

    _wait()
    ag.click(config.add_problem_button)

    # 問題の入力
    _wait()
    ag.click(config.problem_statement)
    clip.copy(problem[0])

    _wait()
    ag.hotkey("ctrl", "v")

    # 回答の入力
    _wait()
    ag.click(config.answer)
    clip.copy(problem[1])

    _wait()
    ag.hotkey("ctrl", "v")

    # 選択肢の自動生成
    _wait()
    ag.click(config.auto_generate_button)
    _wait()
    ag.click(config.ok_button)

    # 保存
    _wait(5)
    ag.click(config.save_button)
    _wait(3)
    ag.click(config.ok_button)


def main():
    file_path = file_selector()
    problems = read_csv(file_path)

    wait_with_bar("waiting to start", 2)

    config = read_config()
    for problem in problems:
        register_a_problem(config, problem)


if __name__ == "__main__":
    main()
