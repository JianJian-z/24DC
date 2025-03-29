# 基本清理方法
import torch

# 1. 释放特定张量
tensor = torch.tensor([1, 2, 3]).cuda()
del tensor
torch.cuda.empty_cache()  # 关键步骤：释放缓存内存

# 2. 清理所有未引用的缓存
torch.cuda.empty_cache()

# 3. 强制回收所有缓存（包括仍在使用的内存）
torch.cuda.memory_snapshot()  # 获取内存快照
torch.cuda.synchronize()      # 等待所有GPU操作完成
torch.cuda.empty_cache()      # 释放缓存

# 4. 重置设备（慎用）
torch.cuda.reset_peak_memory_stats()  # 重置峰值内存统计
torch.cuda.reset_accumulated_memory_stats()  # 重置累计内存统计