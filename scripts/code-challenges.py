"""
天锋PRO 代码挑战库 — 50+题目·5维度·4难度·难度自适应
=====================================================
2035视角: 题目不是静态的，而是从LGE基因库动态生成+人工精选
当前阶段: 手工精选50题，后续从基因库自动扩展

维度: 算法·数据结构·设计模式·系统设计·Bug修复
难度: easy·medium·hard·extreme

基因ID: GENE-CODE-CHALLENGES-V1
"""

CHALLENGES = {
    "algorithms": {
        "label": "算法",
        "icon": "⚡",
        "easy": [
            ("两数之和", "给定整数数组nums和目标target，返回两个数的索引使它们和为target。假设只有一个解", "O(n)"),
            ("回文判断", "判断字符串是否是回文，忽略大小写和标点符号", "O(n)"),
            ("二分查找", "在有序数组中查找目标值，返回索引，未找到返回-1", "O(log n)"),
            ("斐波那契", "返回第n个斐波那契数，使用迭代避免递归栈溢出", "O(n)"),
            ("数组去重", "移除排序数组中的重复元素，原地修改，返回新长度", "O(n)"),
            ("字符串反转", "反转字符串中的单词顺序，去除多余空格", "O(n)"),
            ("最大子数组和", "使用Kadane算法找到最大连续子数组和", "O(n)"),
            ("有效括号", "判断只含(){}[]的字符串是否有效", "O(n)"),
        ],
        "medium": [
            ("三数之和", "在数组中找到所有和为0的三元组，结果不重复", "O(n²)"),
            ("最长回文子串", "找到字符串中最长的回文子串，使用中心扩展法", "O(n²)"),
            ("LRU缓存", "实现LRU缓存，支持get/put操作，O(1)时间复杂度", "O(1)"),
            ("合并K个有序链表", "合并K个升序链表为一个升序链表，使用最小堆", "O(n log k)"),
            ("岛屿数量", "给定二维网格，1为陆地0为水，计算岛屿数量(DFS/BFS)", "O(mn)"),
            ("全排列", "给定无重复数字的数组，返回所有可能的全排列", "O(n!)"),
            ("最长递增子序列", "找到最长严格递增子序列的长度，使用DP+二分", "O(n log n)"),
            ("接雨水", "给定高度数组，计算能接多少雨水，双指针法", "O(n)"),
        ],
        "hard": [
            ("正则表达式匹配", "实现支持.和*的正则表达式匹配，动态规划", "O(mn)"),
            ("滑动窗口最大值", "在数组中找出每个大小为k的窗口的最大值，使用单调队列", "O(n)"),
            ("编辑距离", "计算两个单词之间的最短编辑距离(插入/删除/替换)", "O(mn)"),
            ("天际线问题", "给定建筑位置高度，输出天际线轮廓，使用扫描线+堆", "O(n log n)"),
        ],
        "extreme": [
            ("LFU缓存", "实现LFU(最不经常使用)缓存，O(1)时间所有操作", "O(1)"),
            ("单词搜索II", "在字符矩阵中找出所有字典单词，使用Trie+DFS剪枝", "O(mn*4^L)"),
        ],
    },
    "data_structures": {
        "label": "数据结构",
        "icon": "🏗️",
        "easy": [
            ("最小栈", "设计一个栈，支持push/pop/top/getMin操作，O(1)时间", "O(1)"),
            ("用栈实现队列", "用两个栈实现FIFO队列，支持push/pop/peek/empty", "O(1)均摊"),
            ("环形队列", "实现一个固定大小的环形队列，支持enqueue/dequeue", "O(1)"),
            ("哈希集合", "实现一个简单的HashSet，支持add/remove/contains", "O(1)"),
        ],
        "medium": [
            ("二叉搜索树迭代器", "实现BST中序遍历迭代器，next/hasNext O(1)均摊", "O(h)空间"),
            ("前缀树Trie", "实现Trie，支持insert/search/startsWith", "O(L)"),
            ("跳表SkipList", "实现跳表，支持insert/search/delete，概率平衡", "O(log n)期望"),
            ("并查集", "实现Union-Find，路径压缩+按秩合并", "O(α(n))"),
            ("优先队列", "基于二叉堆实现优先队列，支持push/pop/peek", "O(log n)"),
        ],
        "hard": [
            ("红黑树简化版", "实现自平衡二叉搜索树的插入和查找", "O(log n)"),
            ("B+树", "实现简化的B+树，支持范围查询和顺序遍历", "O(log n)"),
        ],
        "extreme": [
            ("并发HashMap", "实现分段锁的并发HashMap，支持高并发读写", "O(1)"),
        ],
    },
    "design_patterns": {
        "label": "设计模式",
        "icon": "🎨",
        "easy": [
            ("单例模式", "实现线程安全的单例模式，双重检查锁定", "-"),
            ("工厂方法", "实现工厂方法模式，创建不同类型的产品对象", "-"),
            ("建造者模式", "实现Builder模式构建复杂对象，支持链式调用", "-"),
            ("适配器模式", "实现适配器模式，将不兼容的接口转为兼容接口", "-"),
        ],
        "medium": [
            ("观察者模式", "实现发布-订阅模式的事件系统，支持多订阅者和取消订阅", "-"),
            ("策略模式", "实现策略模式，支持运行时切换算法策略(如不同排序算法)", "-"),
            ("装饰器模式", "实现Python装饰器框架，支持before/after/error钩子", "-"),
            ("责任链模式", "实现责任链审批流程，每个节点可批准或传递给下个节点", "-"),
            ("状态机模式", "实现有限状态机，支持状态转移和动作执行", "-"),
        ],
        "hard": [
            ("依赖注入容器", "实现简单的IoC容器，支持类型注册和自动注入", "-"),
            ("Actor模型", "实现简化的Actor并发模型，支持消息传递和状态隔离", "-"),
        ],
        "extreme": [
            ("CQRS+EventSourcing", "实现命令查询职责分离+事件溯源模式", "-"),
        ],
    },
    "system_design": {
        "label": "系统设计",
        "icon": "🏛️",
        "easy": [
            ("TTL缓存", "实现带TTL过期和最大容量的本地缓存", "-"),
            ("限流器", "实现令牌桶限流器，支持refill和consume", "-"),
            ("重试机制", "实现指数退避重试，支持最大重试次数和超时", "-"),
        ],
        "medium": [
            ("线程池", "实现简化的线程池，支持submit/shutdown/任务队列", "-"),
            ("连接池", "实现数据库连接池，支持borrow/return/健康检查", "-"),
            ("消息队列", "实现内存消息队列，支持pub/sub和持久化到文件", "-"),
            ("配置中心", "实现配置热加载系统，支持watch和回调通知", "-"),
        ],
        "hard": [
            ("分布式ID生成器", "实现雪花算法(Snowflake)的分布式唯一ID生成", "-"),
            ("一致性哈希", "实现一致性哈希环，支持虚拟节点和节点增删", "-"),
        ],
        "extreme": [
            ("微服务网关", "实现API网关，支持路由/限流/认证/日志", "-"),
        ],
    },
    "bug_fixing": {
        "label": "Bug修复",
        "icon": "🐛",
        "easy": [
            ("并发计数Bug", "修复非线程安全的计数器竞争问题，使用锁或原子操作", "-"),
            ("内存泄漏Bug", "修复循环引用导致的内存泄漏，使用weakref", "-"),
            ("索引越界Bug", "修复二分查找中整数溢出导致的索引越界", "-"),
        ],
        "medium": [
            ("死锁修复", "修复多锁获取顺序不一致导致的死锁", "-"),
            ("竞态条件Bug", "修复check-then-act模式的竞态条件", "-"),
            ("资源泄漏Bug", "修复文件/连接未正确关闭的资源泄漏", "-"),
        ],
        "hard": [
            ("并发Bug深度修复", "修复复杂并发场景下的ABA问题和活锁", "-"),
        ],
        "extreme": [
            ("分布式共识Bug", "修复分布式系统中的脑裂和一致性问题", "-"),
        ],
    },
}


def get_all_challenges():
    """获取所有题目，展平为列表"""
    result = []
    for dim_key, dim_data in CHALLENGES.items():
        for difficulty in ["easy", "medium", "hard", "extreme"]:
            for title, desc, complexity in dim_data.get(difficulty, []):
                result.append({
                    "dimension": dim_key,
                    "dim_label": dim_data["label"],
                    "dim_icon": dim_data["icon"],
                    "difficulty": difficulty,
                    "title": title,
                    "description": desc,
                    "target_complexity": complexity,
                })
    return result


def count_challenges():
    """统计题目数量"""
    total = 0
    for dim_key, dim_data in CHALLENGES.items():
        for diff in ["easy", "medium", "hard", "extreme"]:
            count = len(dim_data.get(diff, []))
            if count:
                total += count
    return total


def get_challenge_stats():
    """题目统计"""
    stats = {}
    for dim_key, dim_data in CHALLENGES.items():
        dim_stats = {}
        for diff in ["easy", "medium", "hard", "extreme"]:
            dim_stats[diff] = len(dim_data.get(diff, []))
        stats[f"{dim_data['icon']} {dim_data['label']}"] = dim_stats
    return stats


if __name__ == "__main__":
    print(f"代码挑战库: {count_challenges()}题")
    print(f"维度: {len(CHALLENGES)}")
    print(f"难度: easy/medium/hard/extreme")
    print()
    for k, v in get_challenge_stats().items():
        total = sum(v.values())
        parts = [f"{d}:{c}" for d, c in v.items() if c > 0]
        print(f"  {k}: {total}题 ({', '.join(parts)})")
