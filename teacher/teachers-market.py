from dataclasses import dataclass, field
from typing import List, Dict

import requests  # HTTP リクエスト用

from bs4 import BeautifulSoup


@dataclass
class JobListing:
    """家庭教師マーケットの 1 求人を表現するデータクラス"""

    # --- 画面上の主要フィールド ---
    name: str  # 講師／依頼者名
    job_id: int  # 案件 ID
    catch_copy: str  # キャッチコピー（仕事内容の一言）
    tags: List[str] = field(default_factory=list)  # 特徴タグ

    # 詳細テーブル内の項目
    wage: str = ""
    working_days: str = ""
    target: str = ""
    location: str = ""
    stations: List[str] = field(default_factory=list)

    # その他
    in_review_list: bool = False  # 検討リストに既に入っているか
    detail_url: str = ""  # "詳しく見る" のリンク


# ------------------------------------------------------------
#  HTML 1 ページをパースして JobListing の list を返す
# ------------------------------------------------------------

def parse_page(html: str) -> List[JobListing]:
    """Teachers-Market の検索結果ページ HTML から JobListing を抽出する。

    Parameters
    ----------
    html : str
        get_page() などで取得した HTML 文字列

    Returns
    -------
    List[JobListing]
        ページに表示されている求人一覧
    """

    soup = BeautifulSoup(html, "html.parser")
    listings: List[JobListing] = []

    # 1 案件は <div class="search-box" …> がルート
    for box in soup.select("div.search-box"):
        # -------------- 基本情報 --------------
        name_tag = box.select_one("span.search-list-jobname")
        job_id_tag = box.select_one("span.search-list-id")
        catch_tag = box.select_one("h2.search-catch")

        if not (name_tag and job_id_tag and catch_tag):
            # 想定外の DOM 変化はスキップ
            continue

        name = name_tag.get_text(strip=True)

        # job_id_tag テキスト例: "/ ID: 202486" → 数値部分だけ取得
        job_id_text = job_id_tag.get_text(strip=True)
        try:
            job_id = int(job_id_text.split(":")[-1])
        except ValueError:
            job_id = -1

        catch_copy = catch_tag.get_text(strip=True)

        # -------------- タグ一覧 --------------
        tag_list = [li.get_text(strip=True) for li in box.select("ul.search-box-tag li")]

        # -------------- 詳細テーブル --------------
        wage = working_days = target = location = ""
        stations: List[str] = []

        for row in box.select("div.search-box-info table tr"):
            th = row.find("th")
            td = row.find("td")
            if not (th and td):
                continue
            label = th.get_text(strip=True)
            value = td.get_text(" ", strip=True)
            if label == "給与":
                wage = value
            elif label == "勤務日数":
                working_days = value
            elif label == "指導対象":
                target = value
            elif label == "勤務地":
                location = value
            elif label == "最寄り駅":
                # 中に <span> が複数入るケースがあるので改めて抽出
                stations = [span.get_text(" ", strip=True) for span in td.select("span")]

        # -------------- 検討リスト状態 --------------
        review_btn = box.select_one(".search-box-bt a[ng-click^='addReviewList']")
        in_review_list = False
        if review_btn:
            # クラスに solid-bt-newpink があればすでに登録済み
            if "solid-bt-newpink" in review_btn.get("class", []):
                in_review_list = True

        # -------------- 詳細ページ URL --------------
        detail_link = box.select_one(".search-box-bt a.solid-bt-newgreen")
        detail_url = detail_link["href"] if detail_link and detail_link.has_attr("href") else ""

        # data class 作成
        listings.append(
            JobListing(
                name=name,
                job_id=job_id,
                catch_copy=catch_copy,
                tags=tag_list,
                wage=wage,
                working_days=working_days,
                target=target,
                location=location,
                stations=stations,
                in_review_list=in_review_list,
                detail_url=detail_url,
            )
        )

    return listings


# ------------------------------------------------------------
#  get_page() と合わせて使うユーティリティ関数
# ------------------------------------------------------------

def get_job_list(page: int) -> List[JobListing]:  # noqa: D401  pylint: disable=invalid-name
    """指定ページを直接リクエストし、JobListing のリストを返す。

    Teachers-Market の検索結果 URL は検索条件を含めて固定長パラメータにしている。
    例：給与「2000円〜」(wage=3)・都道府県「東京都」
    必要に応じて URL を変更してください。
    """

    url = (
        "https://teachers-market.com/teacherjobs/tutor/search"
        f"?page={page}&wage=3&prefecture=%E6%9D%B1%E4%BA%AC%E9%83%BD"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    return parse_page(resp.text)
    


