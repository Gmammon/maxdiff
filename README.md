# MaxDiff 问卷平台

一个完整的 **MaxDiff（最大差异量表）** 在线平台，支持实验设计生成、问卷作答、MLE 效用估计与数据分析。基于 Python + FastAPI 构建，单文件前端，开箱即用。

## 功能特性

- **实验设计生成**：BIBD（平衡不完全区组设计）自动生成，支持预计算查找表、循环构造、随机搜索 + 贪婪优化三种策略
- **问卷作答**：引导式逐轮作答界面，支持撤销操作、进度追踪
- **一致性检查**：自动插入重复任务，实时检测受访者作答一致性
- **MLE 效用估计**：基于多项逻辑模型（MNL）的最大似然估计，含解析梯度、Hessian 标准误、z 值显著性检验
- **计数模型**：Best-Worst 计数分析作为对照
- **数据导出**：一键导出 CSV

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/Gmammon/maxdiff.git
cd maxdiff

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

浏览器打开 http://localhost:8000 即可使用。

## 项目结构

```
├── run.py                  # 启动入口
├── requirements.txt        # Python 依赖
├── app/
│   ├── main.py             # FastAPI 应用入口 + 路由注册
│   ├── database.py         # SQLAlchemy + SQLite 配置
│   ├── models.py           # ORM 模型（Project, Design, Respondent, Response）
│   ├── schemas.py          # Pydantic 请求/响应模型
│   ├── algorithms.py       # BIBD 设计生成 + MLE 估计 + 标准误
│   └── routers/
│       ├── projects.py     # 项目 CRUD + 设计生成
│       ├── survey.py       # 问卷会话（开始/提交/撤销）
│       └── analysis.py     # MLE 分析 + 导出
├── templates/
│   └── index.html          # 前端 SPA（设计 / 问卷 / 分析三个页面）
└── data/
    └── maxdiff.db          # SQLite 数据库（自动创建）
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/projects` | 创建项目并生成实验设计 |
| `GET` | `/api/projects` | 列出所有项目 |
| `GET` | `/api/projects/{id}` | 获取项目详情 |
| `POST` | `/api/survey/start` | 开始问卷 |
| `POST` | `/api/survey/{rid}/submit` | 提交作答 |
| `POST` | `/api/survey/{rid}/undo` | 撤销上一轮作答 |
| `GET` | `/api/survey/{rid}/status` | 查询作答进度 |
| `GET` | `/api/analysis/{pid}` | MLE 分析结果 |
| `GET` | `/api/analysis/{pid}/count` | 计数模型结果 |
| `GET` | `/api/analysis/{pid}/export` | 导出 CSV |

启动后访问 http://localhost:8000/docs 查看交互式 API 文档。

## 算法说明

### 实验设计生成

采用三级策略自动选择最优构造方法：

1. **预计算 BIBD 查找表**：覆盖常见 `(v, k)` 组合的已知最优构造
2. **循环 BIBD**：对素数 `v`，搜索初始块并通过模旋转生成完整设计
3. **随机搜索 + 贪婪优化**：生成大量候选设计，通过交换去重并以配对平衡性为目标函数进行贪婪优化

设计质量通过覆盖率、最大配对偏差、D-efficiency、BIBD 达标判定等指标评估。

### MLE 效用估计

基于 `scipy.optimize.minimize`（SLSQP 方法）：

- log-sum-exp 数值稳定化，避免溢出
- 零和约束保证效用值可识别
- 解析梯度加速收敛
- Hessian 逆矩阵估计标准误，计算 z 值显著性
- RLH（Root Likelihood）拟合优度评估

### 一致性检查

在问卷设计中自动插入重复任务，通过比较受访者对相同任务的作答结果计算一致性分数，用于筛选低质量数据。

## 技术栈

- **后端**：Python 3.10+ / FastAPI / SQLAlchemy / SQLite
- **前端**：原生 HTML + CSS + JavaScript（单文件 SPA）
- **算法**：NumPy / SciPy

## License

MIT
