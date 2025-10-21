#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
from loguru import logger
from util.config import load_config


def split_question_answer(text: str, delimiter: str = "解答") -> tuple[str, str]:
    """テキストを最初に *delimiter* が出現する行で2分割する。

    戻り値は (問題, 解答) のタプル。
    *delimiter* が見つからなかった場合は、全文を問題とし、解答は空文字列とする。
    """
    lines = text.splitlines(keepends=False)
    answer_start_idx = next(
        (i for i, line in enumerate(lines) if delimiter in line), None
    )

    if answer_start_idx is None:
        return text.strip(), ""

    question_lines = lines[:answer_start_idx]
    answer_lines = lines[answer_start_idx:]

    question = "\n".join(question_lines).strip()
    answer = "\n".join(answer_lines).strip()

    return question, answer


def search_normalized_problems() -> list[Path]:
    """normalizedディレクトリから問題ファイルを検索する"""
    config = load_config()
    project_root = Path(__file__).parent
    normalized_dir = project_root / "output" / "normalized"
    
    assert normalized_dir.exists(), f"normalizedディレクトリが存在しません: {normalized_dir}"
    
    # テキストファイルの拡張子を取得
    text_extensions = config["file_extensions"]["text"]
    problem_files = []
    
    for ext in text_extensions:
        # globパターンから*.txt形式に変換
        pattern = ext.replace("*", "*")
        problem_files.extend(normalized_dir.glob(pattern))
    
    # 重複を除去してソート
    problem_files = sorted(set(problem_files))
    
    logger.info(f"発見されたnormalized問題ファイル数: {len(problem_files)}")
    return problem_files


def load_problem_text(problem_path: Path) -> str:
    """問題ファイルを読み込んでテキストを返す"""
    assert problem_path.exists(), f"問題ファイルが存在しません: {problem_path}"
    with open(problem_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return content


def main():
    """メイン処理：normalizedファイルからAnki形式のCSVを生成する"""
    # normalizedディレクトリ配下の *.txt ファイルを列挙
    problem_files = search_normalized_problems()
    
    if not problem_files:
        logger.error("normalizedディレクトリに問題ファイルが見つかりませんでした")
        return
    
    logger.info(f"{len(problem_files)} 件のnormalizedファイルを検出しました")

    data: list[dict[str, str]] = []

    for path in problem_files:
        logger.debug(f"読み込み開始: {path.name}")

        try:
            content = load_problem_text(path)
        except UnicodeDecodeError:
            logger.warning(
                f"UTF-8 デコードに失敗: {path.name} -> bytes デコードで再試行"
            )
            # 文字コードが合わない場合はバイナリ読み込みしてからutf-8でデコードを試みる
            content = path.read_bytes().decode("utf-8", errors="ignore")

        question, answer = split_question_answer(content)
        data.append({"問題": question, "解答": answer})
        logger.debug(
            f"抽出完了: {path.name} -> 問題 {len(question)} 文字 / 解答 {len(answer)} 文字"
        )

    df = pd.DataFrame(data, columns=["問題", "解答"])

    # outputディレクトリにanki.csvとして保存
    project_root = Path(__file__).parent
    output_path = project_root / "output" / "anki.csv"
    df.to_csv(output_path, index=False, header=False)

    logger.success(f"Anki形式のCSVを書き出しました: {output_path} (レコード数: {len(df)})")


if __name__ == "__main__":
    main()
