"""分析 lzbench baseline 数据，计算 Pareto 前沿并找出空位。

Pareto 支配定义：点 A 支配点 B 当且仅当：
  - A.cspeed >= B.cspeed (更快或一样快)
  - A.ratio <= B.ratio (压缩率更低或一样，即压缩更好)
  - 且至少一个维度严格优于
"""
import csv

def dominates(a: dict, b: dict) -> bool:
    return (a["cspeed"] >= b["cspeed"] and a["ratio"] <= b["ratio"]
            and (a["cspeed"] > b["cspeed"] or a["ratio"] < b["ratio"]))

def pareto_front(points: list[dict]) -> list[dict]:
    front: list[dict] = []
    for p in points:
        if not any(dominates(q, p) for q in points if p is not q):
            front.append(p)
    return front

def find_gaps(front: list[dict], all_points: list[dict],
              cspeed_range=(10, 600), ratio_range=(26, 50)) -> list[dict]:
    sorted_front = sorted(front, key=lambda p: p["cspeed"])
    filtered = [p for p in sorted_front
                if cspeed_range[0] <= p["cspeed"] <= cspeed_range[1]
                and ratio_range[0] <= p["ratio"] <= ratio_range[1]]

    gaps: list[dict] = []
    for i in range(len(filtered) - 1):
        a, b = filtered[i], filtered[i+1]
        cspeed_gap = b["cspeed"] - a["cspeed"]
        ratio_gap = a["ratio"] - b["ratio"]
        if cspeed_gap > 5 and abs(ratio_gap) > 0.5:
            target_cspeed = a["cspeed"] + cspeed_gap * 0.4
            target_ratio = b["ratio"] + ratio_gap * 0.4
            target = {"name": "GAP_TARGET", "cspeed": target_cspeed,
                       "ratio": target_ratio, "dspeed": 0}
            if not any(dominates(p, target) for p in all_points):
                gaps.append({
                    "between": (a["name"], b["name"]),
                    "cspeed_gap": cspeed_gap,
                    "ratio_gap": ratio_gap,
                    "target_cspeed": target_cspeed,
                    "target_ratio": target_ratio,
                    "size": cspeed_gap * abs(ratio_gap),
                })
    return sorted(gaps, key=lambda g: g["size"], reverse=True)

def load_points(filepath: str) -> list[dict]:
    points: list[dict] = []
    with open(filepath, newline="") as f:
        for row in csv.DictReader(f):
            points.append({
                "name": row["name"],
                "cspeed": float(row["cspeed"]),
                "dspeed": float(row["dspeed"]),
                "ratio": float(row["ratio"]),
            })
    return points

def main() -> None:
    all_points = load_points("results/baseline_data.csv")

    # 滤掉 memcpy（100% 压缩率，不是真正的压缩器）
    real_points = [p for p in all_points if p["name"] != "memcpy"]

    front = pareto_front(real_points)

    print(f"总数据点: {len(real_points)}")
    print(f"Pareto 前沿点: {len(front)}")
    print()

    print("=== Pareto 前沿（按压缩速度排序）===")
    for p in sorted(front, key=lambda x: x["cspeed"]):
        tag = " ← NEW" if "lizard" in p["name"].lower() else ""
        print(f"  {p['name']:25s} cspeed={p['cspeed']:8.1f} MB/s  ratio={p['ratio']:6.2f}%{tag}")

    print()
    gaps = find_gaps(front, real_points)

    print("=== 发现的空位（按面积排序）===")
    if not gaps:
        print("  未发现有效空位")
    for i, gap in enumerate(gaps[:5]):
        print(f"\n  空位 {i+1}: {gap['between'][0]} ↔ {gap['between'][1]}")
        print(f"    速度区间: {gap['between'][0].split()[-1] if ' ' in gap['between'][0] else ''} → {gap['between'][1]}")
        print(f"    速度差: {gap['cspeed_gap']:.1f} MB/s, 压缩率差: {gap['ratio_gap']:.2f} 百分点")
        print(f"    目标坐标: cspeed={gap['target_cspeed']:.1f} MB/s, ratio={gap['target_ratio']:.2f}%")

    print()
    if gaps:
        best = gaps[0]
        print(f"=== 推荐目标 ===")
        print(f"  压缩速度: {best['target_cspeed']:.0f} MB/s")
        print(f"  压缩率: {best['target_ratio']:.2f}%")
        print(f"  区域: {best['between'][0]} ↔ {best['between'][1]}")

if __name__ == "__main__":
    main()
