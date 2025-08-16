import pandas as pd
import numpy as np
from scipy import stats

# 费用表（更新后的 Table 9 数据）
# House | Standard | Original Economy 7 | Original Economy 10 | Optimized Economy 7 | Optimized Economy 10
data = [
    [1, 624.11, 462.22, 445.12, 438.74, 424.87],
    [2, 479.93, 451.59, 402.07, 379.43, 330.22],
    [3, 998.95, 939.04, 828.74, 804.08, 685.07],
    [4, 688.37, 609.21, 565.75, 590.96, 544.44],
    [5, 1127.77, 1019.59, 926.27, 976.74, 869.62],
    [6, 648.69, 580.18, 523.22, 555.85, 504.81],
    [7, 800.94, 757.62, 675.73, 617.57, 502.02],
    [8, 492.06, 391.79, 394.07, 389.28, 366.18],
    [9, 734.40, 673.30, 626.23, 571.21, 526.59],
    [10, 1211.50, 1069.32, 969.48, 1003.45, 903.88],
    [11, 171.88, 149.22, 137.88, 144.42, 134.07],
    # 12 缺失
    [13, 670.07, 620.48, 566.95, 569.03, 498.41],
    # 14 缺失
    [15, 299.32, 276.53, 240.86, 247.17, 214.44],
    [16, 665.04, 588.57, 535.29, 530.51, 482.75],
    [17, 513.98, 454.63, 416.15, 437.44, 400.63],
    [18, 704.04, 619.14, 564.15, 583.14, 535.64],
    [19, 269.39, 233.78, 219.56, 228.90, 214.59],
    [20, 524.15, 469.27, 432.77, 423.84, 387.54],
    [21, 495.20, 428.10, 389.52, 391.36, 352.66]
]

df = pd.DataFrame(data, columns=[
    "House", "Standard", "Orig_Eco7", "Orig_Eco10", "Opt_Eco7", "Opt_Eco10"
])

# 去掉缺失用户（12 和 14）
df = df.dropna()

# 计算节省百分比： (Standard - 某方案) / Standard * 100
df["Saving_Eco7"] = (df["Standard"] - df["Opt_Eco7"]) / df["Standard"] * 100
df["Saving_Eco10"] = (df["Standard"] - df["Opt_Eco10"]) / df["Standard"] * 100

# 统计显著性检验
def paired_ttest_and_effect(before, after):
    t_stat, p_val = stats.ttest_rel(before, after)
    diff = before - after
    cohen_d = diff.mean() / diff.std(ddof=1)
    mean_saving = np.mean((before - after) / before * 100)
    ci95 = stats.t.interval(
        0.95, len(diff)-1, loc=mean_saving, scale=stats.sem((before - after) / before * 100)
    )
    return mean_saving, ci95, p_val, cohen_d

# Economy-7 vs Standard
eco7_vs_std = paired_ttest_and_effect(df["Standard"], df["Opt_Eco7"])
# Economy-10 vs Standard
eco10_vs_std = paired_ttest_and_effect(df["Standard"], df["Opt_Eco10"])
# Economy-10 vs Economy-7
eco10_vs_eco7 = paired_ttest_and_effect(df["Opt_Eco7"], df["Opt_Eco10"])

eco7_vs_std, eco10_vs_std, eco10_vs_eco7
