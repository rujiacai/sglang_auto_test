import json
import gzip
from collections import defaultdict

def analyze_kernel_events(trace_file):
    """
    解析JSON trace文件，统计cat为"kernel"的事件中每个kernel的执行时间
    
    参数:
        trace_file: JSON trace文件路径
    返回:
        按总耗时降序排序的kernel统计列表
    """
    # 用字典存储每个kernel的统计数据
    kernel_stats = defaultdict(lambda: {
        "total_duration_us": 0.0,  # 总耗时（微秒）
        "count": 0,                # 执行次数
        "avg_duration_us": 0.0     # 平均耗时（微秒）
    })

    try:
        # 加载JSON文件
        if trace_file.endswith("gz"):
            with gzip.open(trace_file, "rt", encoding="utf-8") as f:
                # 先解压得到文件对象，再用 json.load 解析
                trace_data = json.load(f)
        else:
            with open(trace_file, 'r', encoding='utf-8') as f:
                trace_data = json.load(f)

        # 检查是否包含traceEvents字段
        if "traceEvents" not in trace_data:
            print("错误：文件中未找到'traceEvents'字段")
            return []

        # 遍历所有事件
        for event in trace_data["traceEvents"]:
            # 筛选条件1：事件类别为"kernel"
            if event.get("cat") != "kernel":
                continue

            # 严格验证事件格式（避免类型错误）
            # 确保事件是字典类型，且包含必要字段
            if not isinstance(event, dict):
                continue  # 跳过非对象类型的事件
            if "name" not in event or not isinstance(event["name"], str):
                continue  # 跳过缺少kernel名称或名称不是字符串的事件
            if "dur" not in event or not isinstance(event["dur"], (int, float)):
                continue  # 跳过缺少耗时或耗时不是数值的事件

            # 提取kernel名称和耗时
            kernel_name = event["name"]
            duration = event["dur"]

            # 更新统计数据
            kernel_stats[kernel_name]["total_duration_us"] += duration
            kernel_stats[kernel_name]["count"] += 1

        # 计算平均耗时并整理结果
        result = []
        for kernel, stats in kernel_stats.items():
            if stats["count"] > 0:
                stats["avg_duration_us"] = round(
                    stats["total_duration_us"] / stats["count"], 3
                )
                result.append({
                    "kernel": kernel,
                    "total_duration_us": round(stats["total_duration_us"], 3),
                    "count": stats["count"],
                    "avg_duration_us": stats["avg_duration_us"]
                })

        # 按总耗时降序排序
        return sorted(result, key=lambda x: x["total_duration_us"], reverse=True)

    except FileNotFoundError:
        print(f"错误：文件 '{trace_file}' 不存在")
        return []
    except json.JSONDecodeError:
        print(f"错误：文件 '{trace_file}' 不是有效的JSON格式")
        return []
    except Exception as e:
        print(f"处理错误：{str(e)}")
        return []

if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) != 2:
        print("用法：python kernel_analyzer.py <trace_file.json>")
        sys.exit(1)

    # 执行分析
    trace_file = sys.argv[1]
    results = analyze_kernel_events(trace_file)

    # 输出结果
    if results:
        print(f"共统计到 {len(results)} 个kernel事件：")
        print("-" * 120)
        for i, item in enumerate(results, 1):
            # 截断过长的kernel名称（避免输出混乱）
            short_name = item["kernel"][:100] + "..." if len(item["kernel"]) > 100 else item["kernel"]
            print(f"{i}. Kernel: {short_name}")
            print(f"   总耗时：{item['total_duration_us']} 微秒")
            print(f"   执行次数：{item['count']}")
            print(f"   平均耗时：{item['avg_duration_us']} 微秒")
            print("-" * 120)
    else:
        print("未找到有效kernel事件或统计结果为空")