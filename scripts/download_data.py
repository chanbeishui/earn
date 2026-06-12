"""CLI: 数据下载脚本"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import storage, downloader


def main():
    print("=" * 60)
    print("  数据下载工具")
    print("=" * 60)

    print("\n[1/2] 下载股票列表...")
    count = downloader.download_all_stocks_basic()
    print(f"  已保存 {count} 只股票")

    codes = storage.get_stock_codes()
    print(f"\n[2/2] 下载日K线 (共 {len(codes)} 只)...")
    result = downloader.download_all_daily_kline(
        codes,
        progress_callback=lambda i, t, c: print(f"  [{i}/{t}] {c}") if i % 100 == 0 else None
    )
    print(f"  完成: {result['success']}/{result['total']}")
    if result["failed"]:
        print(f"  失败: {result['failed']}")

    print("\n数据下载完成!")


if __name__ == "__main__":
    main()
