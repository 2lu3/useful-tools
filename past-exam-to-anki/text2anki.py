import pandas as pd
from pathlib import Path
from loguru import logger


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


if __name__ == "__main__":
    # text ディレクトリ配下の *.txt ファイルを列挙
    text_dir = Path(__file__).parent / "text"
    txt_files = sorted(text_dir.glob("*.txt"))

    logger.info(f"{len(txt_files)} 件のテキストファイルを検出しました: {text_dir}")

    data: list[dict[str, str]] = []

    for path in txt_files:
        logger.debug(f"読み込み開始: {path.name}")

        try:
            content = path.read_text(encoding="utf-8")
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

    output_path = Path(__file__).parent / "anki" / "qa_pairs.csv"
    df.to_csv(output_path, index=False, header=False)

    logger.success(f"CSVを書き出しました: {output_path} (レコード数: {len(df)})")
