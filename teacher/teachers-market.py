#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List, Dict
import csv
from datetime import datetime

import requests  # HTTP リクエスト用

from bs4 import BeautifulSoup
import time
from loguru import logger


# サーバーへのリクエスト間隔（秒）
REQUEST_INTERVAL: int = 1


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
    """Teachers-Market の検索結果を API から取得し ``JobListing`` のリストを返す。

    サイトは AngularJS で動的に求人データを取得しており、通常の ``GET`` では
    プレースホルダ（ ``<% ... %>``） しか得られない。
    そこで以下の手順で API へ直接アクセスする。

    1. 検索ページを ``GET`` して CSRF トークンを取得（Cookie も保持）
    2. 取得したトークンを付与して ``/api/katekyo`` へ ``POST``
    3. 返ってきた JSON を ``JobListing`` に整形

    Parameters
    ----------
    page : int
        1 以上のページ番号

    Returns
    -------
    List[JobListing]
        求人情報リスト
    """

    SEARCH_URL = (
        "https://teachers-market.com/teacherjobs/tutor/search"
        f"?page={page}&wage=3&prefecture=%E6%9D%B1%E4%BA%AC%E9%83%BD"
    )
    API_URL = "https://teachers-market.com/api/katekyo"

    ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    session = requests.Session()

    # --- 1. CSRF トークン取得 -------------------------------------------
    # 過剰なリクエストを避けるため待機
    time.sleep(REQUEST_INTERVAL)
    resp = session.get(SEARCH_URL, headers={"User-Agent": ua}, timeout=10)
    resp.raise_for_status()

    import re

    m = re.search(r'name="csrf-token" content="([^"]+)"', resp.text)
    if not m:
        raise RuntimeError("CSRF トークンが取得できませんでした")

    csrf_token = m.group(1)

    # --- 2. API へ POST --------------------------------------------------
    # NOTE: API 側は CSRF ヘッダと Cookie の両方を要求するため、
    #       ``session`` を使って Cookie を共有する。
    payload = {
        "page": str(page),
        "wage": "3",  # '時給2000円〜' に対応
        "prefecture": "東京都",
    }

    api_headers = {
        "User-Agent": ua,
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN": csrf_token,
        "Accept": "application/json, text/plain, */*",
    }

    # API へのリクエスト前にも待機
    time.sleep(REQUEST_INTERVAL)
    api_resp = session.post(API_URL, data=payload, headers=api_headers, timeout=10)
    api_resp.raise_for_status()

    data = api_resp.json().get("data", [])

    listings: List[JobListing] = []

    for item in data:
        # --- 基本フィールド -------------------------------------------
        name = (
            item.get("offerer", {}).get("nickname")
            or item.get("_name", "")
        )

        job_id = int(item["id"])
        catch_copy = item.get("catch_copy", "")

        # --- タグ -----------------------------------------------------
        tags = [t.strip() for t in item.get("option", []) if t.strip()]

        # --- 詳細テーブル相当 ---------------------------------------
        wage_val = item.get("wage")  # 数値 or None
        wage = f"時給{wage_val}円" if wage_val else ""

        working_days = item.get("working_days", "")
        target = item.get("teaching_target", "")
        location = item.get("work_address", "")

        stations = []
        for idx in (1, 2, 3):
            if item.get(f"station{idx}_enabled"):
                line = item.get(f"station{idx}_line") or ""
                station = item.get(f"station{idx}_station") or ""
                walk = item.get(f"station{idx}_walktime")
                if line and station:
                    s = f"{line} {station} 駅から徒歩 {walk}分" if walk else f"{line} {station}"
                    stations.append(s)

        detail_url = f"https://teachers-market.com/teacherjobs/tutor/detail/{job_id}"

        listings.append(
            JobListing(
                name=name,
                job_id=job_id,
                catch_copy=catch_copy,
                tags=tags,
                wage=wage,
                working_days=working_days,
                target=target,
                location=location,
                stations=stations,
                in_review_list=False,  # API では取得不可のため False 固定
                detail_url=detail_url,
            )
        )

    return listings


if __name__ == "__main__":
    logger.info("スクレイピングを開始します")
    job_list = []
    for i in range(1, 1000):
        logger.info(f"ページ {i} を取得中")
        try:
            jobs = get_job_list(i)
            if len(jobs) == 0:
                logger.info(f"ページ {i}: 取得 0 件")
                break
            logger.info(f"ページ {i}: 取得 {len(jobs)} 件")
            job_list.extend(jobs)
        except Exception as e:
            logger.exception(f"ページ {i} の取得でエラーが発生: {e}")
            break

    logger.info(f"総求人件数: {len(job_list)}")
    
    # CSVファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"teachers_market_jobs_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'job_id', 'name', 'catch_copy', 'wage', 'working_days', 
            'target', 'location', 'stations', 'tags', 'detail_url'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for job in job_list:
            writer.writerow({
                'job_id': job.job_id,
                'name': job.name,
                'catch_copy': job.catch_copy,
                'wage': job.wage,
                'working_days': job.working_days,
                'target': job.target,
                'location': job.location,
                'stations': '; '.join(job.stations),
                'tags': '; '.join(job.tags),
                'detail_url': job.detail_url
            })
    
    logger.info(f"CSVファイルに保存しました: {csv_filename}")
    print(f"取得した求人情報を {csv_filename} に保存しました")