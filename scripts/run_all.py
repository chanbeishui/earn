"""一键全流程脚本"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 60)
    print("  Earn 量化交易系统 — 全流程执行")
    print("=" * 60)

    print("\n[Phase 1] 数据下载...")
    from scripts.download_data import main as download_main
    download_main()

    print("\n[Phase 2] 策略选股...")
    print("  (将在 Phase 2 中实现)")

    print("\n[Phase 3] 回测...")
    print("  (将在 Phase 3 中实现)")

    print("\n[Phase 4] AI 优化...")
    print("  (将在 Phase 4 中实现)")

    print("\n[Phase 5] 股票池更新...")
    print("  (将在 Phase 5 中实现)")

    print("\n全流程完成!")


if __name__ == "__main__":
    main()
