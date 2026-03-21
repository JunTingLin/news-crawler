#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EBSCO Newspaper Source Crawler

使用 Playwright 自動化爬取 EBSCO Newspaper Source 新聞
需要先連接台大 VPN

Usage:
    python scripts/crawl_ebsco_news.py --stock AAPL --start 2016-01-01 --end 2025-12-31 --headless
    python scripts/crawl_ebsco_news.py --all --start 2016-01-01 --end 2025-12-31 --headless
    python scripts/crawl_ebsco_news.py --all --start 2016-01-01 --end 2025-12-31 --headless --force

Requirements:
    pip install playwright pandas
    playwright install chromium
"""

import asyncio
import argparse
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from playwright.async_api import async_playwright


# EBSCO 基本設定
EBSCO_BASE_URL = "https://research.ebsco.com"
EBSCO_SEARCH_PATH = "/c/zley3o/search/results"
DATABASE = "nfh"  # Newspaper Source

# 道瓊 30 成分股關鍵字
US_STOCKS = {
    "AAPL": ["Apple", "蘋果", "AAPL-US"],
    "AMGN": ["Amgen", "安進", "AMGN-US"],
    "AMZN": ["Amazon", "亞馬遜", "AMZN-US"],
    "AXP": ["American Express", "美國運通", "AXP-US"],
    "BA": ["Boeing", "波音", "BA-US"],
    "CAT": ["Caterpillar", "開拓重工", "卡特彼勒", "CAT-US"],
    "CRM": ["Salesforce", "賽富時", "CRM-US"],
    "CSCO": ["Cisco", "思科", "CSCO-US"],
    "CVX": ["Chevron", "雪佛龍", "CVX-US"],
    "DIS": ["Disney", "迪士尼", "DIS-US"],
    "GS": ["Goldman Sachs", "高盛", "GS-US"],
    "HD": ["Home Depot", "家得寶", "HD-US"],
    "HON": ["Honeywell", "漢威聯合", "霍尼韋爾", "HON-US"],
    "IBM": ["IBM", "IBM-US"],
    "JNJ": ["Johnson & Johnson", "嬌生", "JNJ-US"],
    "JPM": ["JPMorgan", "摩根大通", "JPM-US"],
    "KO": ["Coca-Cola", "可口可樂", "KO-US"],
    "MCD": ["McDonald", "麥當勞", "MCD-US"],
    "MMM": ["3M", "MMM-US"],
    "MRK": ["Merck", "默克", "默沙東", "MRK-US"],
    "MSFT": ["Microsoft", "微軟", "MSFT-US"],
    "NKE": ["Nike", "耐吉", "耐克", "NKE-US"],
    "NVDA": ["NVIDIA", "輝達", "NVDA-US"],
    "PG": ["Procter & Gamble", "寶僑", "P&G", "PG-US"],
    "SHW": ["Sherwin-Williams", "宣偉", "SHW-US"],
    "TRV": ["Travelers", "旅行家", "TRV-US"],
    "UNH": ["UnitedHealth", "聯合健康", "UNH-US"],
    "V": ["Visa", "威士卡", "V-US"],
    "VZ": ["Verizon", "威瑞森", "VZ-US"],
    "WMT": ["Walmart", "沃爾瑪", "WMT-US"],
}

OUTPUT_DIR = Path("data/ebsco_news")
MAX_DOWNLOAD_PER_BATCH = 50  # EBSCO 下載限制


def build_search_query(keywords: list[str]) -> str:
    """建立 EBSCO 搜索查詢字串 (OR 邏輯)"""
    return " OR ".join(keywords)


def build_search_url(query: str) -> str:
    """建立 EBSCO 搜索 URL"""
    params = {"q": query, "db": DATABASE}
    return f"{EBSCO_BASE_URL}{EBSCO_SEARCH_PATH}?{urlencode(params)}"


def parse_date(date_str: str) -> str:
    """
    解析日期字串，返回 MM/YYYY 格式

    Args:
        date_str: YYYY-MM-DD 格式

    Returns:
        MM/YYYY 格式
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.month:02d}/{dt.year}"


def generate_monthly_ranges(start_date: str, end_date: str) -> list[tuple[str, str]]:
    """
    將日期範圍分割成月份區間

    Args:
        start_date: YYYY-MM-DD 格式
        end_date: YYYY-MM-DD 格式

    Returns:
        [(from_date, to_date), ...] 格式為 MM/YYYY
    """
    from dateutil.relativedelta import relativedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    ranges = []
    current = start.replace(day=1)

    while current <= end:
        # 該月的最後一天
        next_month = current + relativedelta(months=1)
        month_end = next_month - relativedelta(days=1)

        # 確保不超過結束日期
        if month_end > end:
            month_end = end

        from_date = f"{current.month:02d}/{current.year}"
        to_date = f"{month_end.month:02d}/{month_end.year}"

        ranges.append((from_date, to_date))

        current = next_month

    return ranges


class EBSCOCrawler:
    def __init__(self, headless: bool = False, slow_mo: int = 50):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        """啟動瀏覽器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-TW",
            accept_downloads=True
        )
        self.page = await self.context.new_page()

    async def close(self):
        """關閉瀏覽器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def close_popups(self):
        """關閉各種彈窗"""
        popup_selectors = [
            ".osano-cm-close",  # Cookie 同意
            'button:has-text("Got it")',  # Got it 按鈕
            '[data-auto="bulk-record-coachmark-button"]',  # 批次選擇提示
            'button:has-text("知道了")',  # 中文版 Got it
            '.bulk-record-coachmark button',  # coachmark 關閉按鈕
        ]
        for sel in popup_selectors:
            try:
                el = self.page.locator(sel)
                if await el.count() > 0:
                    await el.first.click()
                    await asyncio.sleep(0.3)
            except:
                pass

        # 額外嘗試按 Escape 關閉任何 overlay
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
        except:
            pass

    async def get_result_count(self) -> int:
        """取得搜索結果數量"""
        try:
            el = self.page.locator('[data-auto="result-count"]')
            if await el.count() > 0:
                text = await el.first.text_content()
                match = re.search(r'[\d,]+', text)
                if match:
                    return int(match.group().replace(',', ''))
        except:
            pass
        return 0

    async def set_date_filter(self, from_date: str, to_date: str) -> bool:
        """
        設定日期篩選

        Args:
            from_date: 格式 MM/YYYY
            to_date: 格式 MM/YYYY
        """
        try:
            print(f"    設定日期篩選: {from_date} ~ {to_date}")

            # 點擊日期下拉選單
            all_dates_btn = self.page.locator(
                'button:has-text("All dates"), button:has-text("所有日期"), '
                'button:has-text("Date range"), button:has-text("日期範圍")'
            ).first
            await all_dates_btn.click()
            await asyncio.sleep(0.8)

            # 點擊 Date range 選項
            date_range_option = self.page.locator(
                '[role="option"]:has-text("Date range"), button:has-text("Date range"), '
                '[role="option"]:has-text("日期範圍"), button:has-text("日期範圍")'
            )
            if await date_range_option.count() > 0:
                await date_range_option.first.click()
                await asyncio.sleep(0.8)

            # 輸入日期 (支援英文和中文介面)
            from_input = self.page.locator('input[placeholder="YYYY or MM/YYYY"], input[placeholder="YYYY 或 MM/YYYY"]')
            to_input = self.page.locator('input[placeholder*="Today"], input[placeholder*="今日"]')

            if await from_input.count() > 0:
                await from_input.click(click_count=3)
                await from_input.fill("")  # 清空
                await from_input.type(from_date, delay=80)
                await asyncio.sleep(0.5)
                entered_from = await from_input.input_value()
                print(f"      起始日期已輸入: {entered_from}")

            if await to_input.count() > 0:
                await to_input.click(click_count=3)
                await to_input.fill("")  # 清空
                await to_input.type(to_date, delay=80)
                await asyncio.sleep(0.5)
                entered_to = await to_input.input_value()
                print(f"      結束日期已輸入: {entered_to}")

            # 點擊 Apply/套用
            apply_btn = self.page.locator('button:has-text("Apply"):not([disabled]), button:has-text("套用"):not([disabled])')
            if await apply_btn.count() > 0:
                await apply_btn.first.click()
                print(f"      已點擊套用，等待頁面載入...")
                await asyncio.sleep(3)
                await self.page.wait_for_load_state("networkidle", timeout=60000)
                await asyncio.sleep(3)
                print(f"      頁面載入完成")
                return True
            else:
                print(f"      找不到可用的套用按鈕")

        except Exception as e:
            print(f"    日期篩選失敗: {e}")
        return False

    async def load_all_results(self, max_results: int = 10000) -> int:
        """
        使用 Show More 載入所有結果

        Returns:
            int: 載入的結果數量
        """
        loaded_count = await self.page.locator('[data-auto="result-item-title"]').count()
        no_change_count = 0
        clicks = 0

        while loaded_count < max_results:
            # 滾動到底部
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.2)

            # 找 Show More 按鈕
            show_more = self.page.locator('button[data-auto="show-more-button"][aria-controls="result-list"]')
            if await show_more.count() == 0:
                show_more = self.page.locator('section.eb-pagination button[data-auto="show-more-button"]')

            if await show_more.count() == 0 or not await show_more.first.is_visible():
                break

            try:
                # 使用 JavaScript 點擊（更可靠）
                await self.page.evaluate('''() => {
                    const btn = document.querySelector('button[data-auto="show-more-button"][aria-controls="result-list"]');
                    if (btn) btn.click();
                }''')
                await asyncio.sleep(1.5)
                clicks += 1
            except:
                break

            new_count = await self.page.locator('[data-auto="result-item-title"]').count()

            if clicks % 10 == 0:  # 更頻繁地輸出進度
                print(f"      載入中: {new_count} 筆...")

            if new_count == loaded_count:
                no_change_count += 1
                if no_change_count >= 3:
                    break
            else:
                no_change_count = 0
                loaded_count = new_count

        return await self.page.locator('[data-auto="result-item-title"]').count()

    async def close_download_modal(self):
        """關閉下載 modal"""
        try:
            # 等待 modal 消失或點擊關閉按鈕
            modal = self.page.locator('.nuc-bulk-download-modal__overlay, .eb-modal__overlay')
            for _ in range(10):
                if await modal.count() == 0:
                    break
                # 嘗試按 Escape 關閉
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.5)
        except:
            pass

    async def deselect_all(self):
        """取消所有選擇"""
        try:
            # 使用 Select All checkbox 來取消全選
            select_all = self.page.locator('[aria-label*="取消選定所有"], [aria-label*="選定所有顯示的記錄"]').first
            if await select_all.count() > 0:
                # 如果已經有選擇，點擊兩次（全選再取消）
                is_checked = await select_all.is_checked()
                if is_checked:
                    await select_all.click()
                    await asyncio.sleep(0.3)
        except:
            pass

    async def download_batch(self, start_idx: int, batch_size: int, output_path: Path) -> bool:
        """
        下載一批結果

        Args:
            start_idx: 起始索引（0-based）
            batch_size: 批次大小
            output_path: 輸出路徑
        """
        try:
            # 先關閉所有彈窗
            await self.close_popups()
            await asyncio.sleep(0.3)

            # 滾動到該批次的位置
            if start_idx > 0:
                await self.page.evaluate(f"""
                    const items = document.querySelectorAll('[data-auto="result-item-title"]');
                    if (items[{start_idx}]) {{
                        items[{start_idx}].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                """)
                await asyncio.sleep(0.5)
            else:
                # 滾動到頁面頂部
                await self.page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.3)

            # 再次關閉可能出現的彈窗
            await self.close_popups()

            checkboxes = self.page.locator('input[type="checkbox"][aria-label*="選定記錄"]')
            total = await checkboxes.count()
            print(f"        找到 {total} 個 checkbox")

            if total == 0:
                print(f"        沒有可選的 checkbox")
                return False

            # 選擇指定範圍的 checkbox（從 start_idx 開始，最多選 batch_size 個）
            end_idx = min(start_idx + batch_size, total)
            selected_count = 0

            for i in range(start_idx, end_idx):
                try:
                    cb = checkboxes.nth(i)
                    if await cb.count() > 0:
                        is_disabled = await cb.get_attribute("disabled")
                        if is_disabled:
                            # EBSCO 限制：已選 50 個後其他會被 disabled
                            if selected_count >= 50:
                                break
                            continue
                        if not await cb.is_checked():
                            # 滾動到 checkbox 可見位置
                            await cb.scroll_into_view_if_needed()
                            await asyncio.sleep(0.02)
                            await cb.click(force=True)  # 使用 force=True 強制點擊
                            selected_count += 1
                            await asyncio.sleep(0.02)

                            # 每選 10 個關閉一次可能出現的 coachmark
                            if selected_count % 10 == 0:
                                await self.close_popups()

                            # EBSCO 限制最多 50 個
                            if selected_count >= 50:
                                break
                except Exception as e:
                    continue

            if selected_count == 0:
                print(f"        沒有選中任何項目")
                return False

            print(f"        已選 {selected_count} 個")
            await asyncio.sleep(0.5)
            await self.close_popups()

            # 下載
            download_btn = self.page.locator('button[aria-label="下載"]:not([disabled])')
            if await download_btn.count() == 0:
                print(f"        找不到下載按鈕")
                return False

            await download_btn.first.click()
            await asyncio.sleep(1)

            # 點擊「書目格式」標籤以顯示 CSV 選項
            bib_tab = self.page.locator('[role="tab"]:has-text("書目格式"), button:has-text("書目格式"), button:has-text("Citation")')
            if await bib_tab.count() > 0:
                await bib_tab.first.click()
                await asyncio.sleep(0.8)

            # 選擇 CSV 格式（找包含 CSV 文字的 label 或 radio）
            csv_label = self.page.locator('label:has-text("CSV")')
            if await csv_label.count() > 0:
                await csv_label.first.click()
                await asyncio.sleep(0.3)
            else:
                # 嘗試用 value 找 radio
                csv_radio = self.page.locator('input[type="radio"][value*="csv" i]')
                if await csv_radio.count() > 0:
                    await csv_radio.first.click()
                    await asyncio.sleep(0.3)

            # 點擊 modal 中的下載按鈕
            dialog_download = self.page.locator('.eb-modal button:has-text("下載"), .eb-modal button:has-text("Download")')
            if await dialog_download.count() == 0:
                dialog_download = self.page.locator('button:has-text("下載"):not([disabled])')

            if await dialog_download.count() > 0:
                async with self.page.expect_download(timeout=60000) as download_info:
                    await dialog_download.last.click()
                download = await download_info.value
                await download.save_as(output_path)

                # 等待 modal 關閉
                await asyncio.sleep(1)
                await self.close_download_modal()

                # 取消所有選擇
                await self.deselect_all()
                await asyncio.sleep(0.5)

                return True

        except Exception as e:
            print(f"      批次下載失敗: {e}")
            # 嘗試關閉 modal 和取消選擇
            await self.close_download_modal()
            await self.deselect_all()
        return False

    async def crawl_month(self, stock_code: str, keywords: list[str],
                          from_date: str, to_date: str, temp_dir: Path) -> list[Path]:
        """
        爬取單月的新聞

        Args:
            from_date: MM/YYYY 格式
            to_date: MM/YYYY 格式
            temp_dir: 臨時目錄

        Returns:
            list[Path]: 下載的 CSV 檔案列表
        """
        query = build_search_query(keywords)
        url = build_search_url(query)

        csv_files = []

        # 前往搜索頁面
        await self.page.goto(url, timeout=30000)
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(2)

        for _ in range(3):
            await self.close_popups()
            await asyncio.sleep(0.3)

        # 設定日期篩選
        if not await self.set_date_filter(from_date, to_date):
            return csv_files

        # 等待頁面完全穩定
        await asyncio.sleep(5)
        await self.page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(2)
        await self.close_popups()

        # 取得結果數量
        total_results = await self.get_result_count()

        if total_results == 0:
            return csv_files

        print(f"      {from_date}: {total_results:,} 筆")

        # 分批下載
        batch_num = 0
        num_batches = (total_results + MAX_DOWNLOAD_PER_BATCH - 1) // MAX_DOWNLOAD_PER_BATCH

        while batch_num < num_batches:
            target_load = min((batch_num + 1) * MAX_DOWNLOAD_PER_BATCH, total_results)
            start_idx = batch_num * MAX_DOWNLOAD_PER_BATCH

            current_loaded = await self.page.locator('[data-auto="result-item-title"]').count()

            # 載入更多結果
            load_attempts = 0
            no_change_count = 0
            while current_loaded < target_load and load_attempts < 50:
                load_attempts += 1

                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.3)

                show_more = self.page.locator('button[data-auto="show-more-button"][aria-controls="result-list"]')
                if await show_more.count() == 0:
                    show_more = self.page.locator('section.eb-pagination button[data-auto="show-more-button"]')
                if await show_more.count() == 0:
                    break

                try:
                    if await show_more.first.is_visible():
                        await self.page.evaluate('''() => {
                            const btn = document.querySelector('button[data-auto="show-more-button"][aria-controls="result-list"]');
                            if (btn) btn.click();
                        }''')
                        await asyncio.sleep(2)
                        await self.page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    await asyncio.sleep(1)
                    continue

                new_loaded = await self.page.locator('[data-auto="result-item-title"]').count()
                if new_loaded == current_loaded:
                    no_change_count += 1
                    if no_change_count >= 3:
                        break
                    await asyncio.sleep(1)
                else:
                    no_change_count = 0
                    current_loaded = new_loaded

            current_loaded = await self.page.locator('[data-auto="result-item-title"]').count()

            if start_idx >= current_loaded:
                break

            # 下載這一批
            month_str = from_date.replace("/", "_")
            batch_file = temp_dir / f"{month_str}_batch_{batch_num:04d}.csv"

            success = await self.download_batch(start_idx, MAX_DOWNLOAD_PER_BATCH, batch_file)

            if success and batch_file.exists():
                csv_files.append(batch_file)
                with open(batch_file, 'r', encoding='utf-8') as f:
                    batch_count = len(f.readlines()) - 1
                print(f"        批次 {batch_num + 1}: {batch_count} 筆")

            batch_num += 1
            await asyncio.sleep(1)
            await self.close_popups()
            await self.close_download_modal()

            if start_idx + MAX_DOWNLOAD_PER_BATCH >= total_results:
                break

        return csv_files

    async def crawl_stock(self, stock_code: str, keywords: list[str],
                          start_date: str, end_date: str, output_dir: Path) -> int:
        """
        爬取單一股票的所有新聞（使用月份分區）

        Args:
            start_date: YYYY-MM-DD 格式
            end_date: YYYY-MM-DD 格式

        Returns:
            int: 下載的新聞數量
        """
        print(f"\n  {stock_code} ({start_date} ~ {end_date}):")

        # 生成月份區間
        monthly_ranges = generate_monthly_ranges(start_date, end_date)
        print(f"    分為 {len(monthly_ranges)} 個月份區間")

        # 建立臨時目錄
        temp_dir = output_dir / f".temp_{stock_code}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        all_csv_files = []

        for i, (from_date, to_date) in enumerate(monthly_ranges):
            print(f"    [{i+1}/{len(monthly_ranges)}] {from_date}...")

            try:
                csv_files = await self.crawl_month(stock_code, keywords, from_date, to_date, temp_dir)
                all_csv_files.extend(csv_files)
            except Exception as e:
                print(f"      ✗ 錯誤: {e}")
                continue

            await asyncio.sleep(2)

        # 合併 CSV
        if all_csv_files:
            output_file = output_dir / f"{stock_code}.csv"
            dfs = [pd.read_csv(f, encoding='utf-8') for f in all_csv_files]
            merged_df = pd.concat(dfs, ignore_index=True)
            merged_df.drop_duplicates(subset=['an'], inplace=True)
            merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')

            # 清理臨時檔案
            for f in all_csv_files:
                f.unlink()
            try:
                temp_dir.rmdir()
            except:
                pass

            final_count = len(merged_df)
            print(f"    ✓ 完成: {output_file.name} ({final_count:,} 筆)")
            return final_count

        return 0


async def main():
    parser = argparse.ArgumentParser(description='EBSCO Newspaper Source Crawler')
    parser.add_argument('--stock', type=str, help='指定股票代碼 (e.g., AAPL)')
    parser.add_argument('--all', action='store_true', help='爬取所有成分股')
    parser.add_argument('--start', type=str, default='2016-01-01', help='開始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2025-12-31', help='結束日期 (YYYY-MM-DD)')
    parser.add_argument('--force', action='store_true', help='強制重新爬取（忽略已存在的檔案）')
    parser.add_argument('--headless', action='store_true', help='使用無頭模式')
    parser.add_argument('--output', type=str, default=str(OUTPUT_DIR), help='輸出目錄')

    args = parser.parse_args()

    if not args.stock and not args.all:
        parser.error("請指定 --stock 或 --all")

    stocks_to_crawl = US_STOCKS if args.all else {args.stock: US_STOCKS.get(args.stock, [])}
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("╔" + "="*50 + "╗")
    print("║" + " "*10 + "EBSCO News Crawler" + " "*22 + "║")
    print("╚" + "="*50 + "╝")
    print(f"\n股票數: {len(stocks_to_crawl)}")
    print(f"日期範圍: {args.start} ~ {args.end}")
    print(f"強制重爬: {'是' if args.force else '否'}")
    print(f"輸出目錄: {output_dir}")
    print("\n⚠️  請確保已連接台大 VPN\n")

    crawler = EBSCOCrawler(headless=args.headless)

    try:
        await crawler.start()
        total_news = 0
        skipped = 0

        for stock_code, keywords in stocks_to_crawl.items():
            if not keywords:
                print(f"跳過未知股票: {stock_code}")
                continue

            # 檢查是否已存在
            output_file = output_dir / f"{stock_code}.csv"
            if output_file.exists() and not args.force:
                existing_count = len(pd.read_csv(output_file)) if output_file.stat().st_size > 0 else 0
                print(f"\n  {stock_code}: 已存在 ({existing_count} 筆)，跳過")
                skipped += 1
                continue

            print(f"\n{'='*50}")
            print(f"股票: {stock_code}")
            print(f"關鍵字: {keywords}")
            print('='*50)

            count = await crawler.crawl_stock(
                stock_code, keywords, args.start, args.end, output_dir
            )
            total_news += count
            await asyncio.sleep(2)

        print(f"\n{'='*50}")
        print(f"完成！")
        print(f"  下載: {total_news:,} 筆")
        print(f"  跳過: {skipped} 支股票")
        print('='*50)

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
