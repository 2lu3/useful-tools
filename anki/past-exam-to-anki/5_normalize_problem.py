#!/usr/bin/env python3
from pathlib import Path
from loguru import logger
from util.config import load_config, load_prompt
from util.llm import ask_llm
from concurrent.futures import ThreadPoolExecutor, as_completed
from alive_progress import alive_bar


def search_problems() -> list[Path]:
    """single_problemディレクトリから問題ファイルを検索する"""
    config = load_config()
    project_root = Path(__file__).parent
    single_problem_dir = project_root / "output" / "single_problem"
    
    assert single_problem_dir.exists(), f"single_problemディレクトリが存在しません: {single_problem_dir}"
    
    # テキストファイルの拡張子を取得
    text_extensions = config["file_extensions"]["text"]
    problem_files = []
    
    for ext in text_extensions:
        # globパターンから*.txt形式に変換
        pattern = ext.replace("*", "*")
        problem_files.extend(single_problem_dir.glob(pattern))
    
    # 重複を除去してソート
    problem_files = sorted(set(problem_files))
    
    logger.info(f"発見された問題ファイル数: {len(problem_files)}")
    return problem_files


def load_problem_text(problem_path: Path) -> str:
    """問題ファイルを読み込んでテキストを返す"""
    assert problem_path.exists(), f"問題ファイルが存在しません: {problem_path}"
    with open(problem_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return content


def modify_problem(problem: str) -> str:
    """与えられた問題文・解答文に対して、LLMによる修正を行い、修正後の文章を返す"""
    assert problem.strip(), "空の問題文が渡されました"

    result_remove_combination_choices = ask_llm(load_prompt("remove_combination_choices"), text_content=problem)
    logger.debug("############ remove_combination_choices ############\n")
    logger.debug("--- before ---\n")
    logger.debug(problem)
    logger.debug("--- after --\n")
    logger.debug(result_remove_combination_choices)
    logger.debug("####################################################\n")

    result = ask_llm(load_prompt("format_for_anki"), text_content=result_remove_combination_choices)
    logger.debug("############ format_for_anki ############\n")
    logger.debug("--- before ---\n")
    logger.debug(result_remove_combination_choices)
    logger.debug("--- after --\n")
    logger.debug(result)
    logger.debug("####################################################\n")

    return result

def parallel_modify_problem(problems: list[str]) -> list[str]:
    """複数の問題を並列で修正する"""
    assert problems, "修正する問題がありません"
    max_workers = load_config()["general"]["max_workers"]
    logger.info(f"並列処理で{len(problems)}個の問題を修正します (ワーカー数: {max_workers})")
    
    results = [""] * len(problems)  # 結果を格納するリスト
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 各問題の修正タスクを並列で実行
        future_to_index = {
            executor.submit(modify_problem, problem): i 
            for i, problem in enumerate(problems)
        }
        
        # 完了したタスクから結果を取得（プログレスバー付き）
        with alive_bar(len(problems), title="問題修正中") as bar:
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                result = future.result()
                results[index] = result
                bar()
    
    return results

def save_normalized_problem(problem_path: Path, normalized_content: str) -> bool:
    """修正された問題をnormalizedディレクトリに保存する"""
    project_root = Path(__file__).parent
    normalized_dir = project_root / "output" / "normalized"
    output_path = normalized_dir / problem_path.name
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(normalized_content)
    return True

def main():
    """メイン処理：問題の正規化を実行する"""
    problem_files = search_problems()
    assert problem_files, "修正対象の問題ファイルが見つかりませんでした"
    
    # 2. 問題ファイルを読み込み
    problems = []
    problem_paths = []
    
    for problem_path in problem_files:
        problem_text = load_problem_text(problem_path)
        if problem_text:
            problems.append(problem_text)
            problem_paths.append(problem_path)
        else:
            logger.warning(f"問題ファイルの読み込みをスキップしました: {problem_path}")
    
    if not problems:
        logger.error("有効な問題ファイルがありませんでした")
        return
    
    logger.info(f"{len(problems)}個の問題を処理します")
    
    # 3. 並列で問題を修正
    normalized_problems = parallel_modify_problem(problems)
    
    # 4. 修正された問題を保存
    success_count = 0
    for i, (problem_path, normalized_content) in enumerate(zip(problem_paths, normalized_problems)):
        if save_normalized_problem(problem_path, normalized_content):
            success_count += 1
    
    logger.info(f"問題正規化処理が完了しました。成功: {success_count}/{len(problems)}")


if __name__ == "__main__":
    main()