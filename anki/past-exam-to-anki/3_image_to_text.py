#!/usr/bin/env python3
import glob
from pathlib import Path
from loguru import logger
from util.config import load_config, load_prompt
from util.llm import ask_llm
from typing import Literal
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from alive_progress import alive_bar


@dataclass
class ImageFile:
    path: Path
    type: Literal["image"]


def search_image_files(input_dir: Path) -> list[ImageFile]:
    """inputディレクトリから画像ファイルを検索する"""
    config = load_config()
    results = []
    
    # 画像ファイルの拡張子を取得
    image_extensions = config["file_extensions"]["image"]
    
    for ext in image_extensions:
        globbed_files = glob.glob(str(input_dir / ext))
        files = [ImageFile(path=Path(path), type="image") for path in globbed_files]
        results.extend(files)
    
    logger.info(f"見つかった画像ファイル数: {len(results)}")
    return results


def image_to_text(image_file: ImageFile) -> str:
    """画像ファイルをテキスト化する"""
    assert image_file.path.exists(), f"画像ファイルが存在しません: {image_file.path}"
    
    # プロンプトを読み込み
    prompt = load_prompt("image_to_text")
    
    # LLMに画像を送信してテキスト化
    result = ask_llm(prompt, image_paths=[image_file.path])
    
    logger.debug(f"画像テキスト化完了: {image_file.path}")
    logger.debug(f"結果: {result}")
    
    return result


def save_textualized_image(image_file: ImageFile, text_content: str, output_dir: Path):
    """テキスト化された画像をtxtファイルとして保存"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ファイル名を生成（拡張子を.txtに変更）
    output_filename = f"{image_file.path.stem}.txt"
    output_path = output_dir / output_filename
    
    # テキスト内容をファイルに保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    
    logger.info(f"保存完了: {image_file.path} -> {output_path}")


def process_single_image(image_file: ImageFile, output_dir: Path) -> bool:
    """単一の画像ファイルを処理する（並列処理用）"""
    try:
        logger.info(f"処理中: {image_file.path}")
        
        # 画像をテキスト化
        text_content = image_to_text(image_file)
        
        if text_content and text_content.strip():
            # テキスト化結果を保存
            save_textualized_image(image_file, text_content, output_dir)
            return True
        else:
            logger.warning(f"テキスト化に失敗しました: {image_file.path}")
            return False
            
    except Exception as e:
        logger.error(f"画像処理中にエラーが発生しました: {image_file.path} - {e}")
        return False


def parallel_process_images(image_files: list[ImageFile], output_dir: Path) -> int:
    """複数の画像ファイルを並列で処理する"""
    assert image_files, "処理する画像ファイルがありません"
    max_workers = 4  # 固定で4ワーカー
    logger.info(f"並列処理で{len(image_files)}個の画像を処理します (ワーカー数: {max_workers})")
    
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 各画像の処理タスクを並列で実行
        future_to_image = {
            executor.submit(process_single_image, image_file, output_dir): image_file 
            for image_file in image_files
        }
        
        # 完了したタスクから結果を取得（プログレスバー付き）
        with alive_bar(len(image_files), title="画像テキスト化中") as bar:
            for future in as_completed(future_to_image):
                image_file = future_to_image[future]
                success = future.result()
                if success:
                    success_count += 1
                bar()
    
    return success_count


def main():
    """メイン処理"""
    # 設定ファイルを読み込み
    config = load_config()
    
    # 入力ディレクトリと出力ディレクトリを設定
    input_dir = Path(__file__).parent / "input"
    output_dir = Path(__file__).parent / "output" / "single_problem"
    
    # 画像ファイルを検索
    image_files = search_image_files(input_dir)
    
    if not image_files:
        logger.warning("画像ファイルが見つかりませんでした。")
        return
    
    # 並列で画像ファイルをテキスト化して保存
    success_count = parallel_process_images(image_files, output_dir)
    
    logger.info(f"\n処理完了: {success_count}/{len(image_files)}個の画像ファイルを処理しました。")


if __name__ == "__main__":
    main()
