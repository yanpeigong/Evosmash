
## 1. 系统概览 (System Overview)

**EvoSmash** 是一个基于 **多模态视觉感知**、**物理推理** 与 **贝叶斯强化学习** 的垂直领域 AI 智能体。系统采用 **分层架构 (Layered Architecture)**，实现了从视频输入到战术进化闭环的全自动化流程。

### 核心能力
*   **全维感知**: 毫秒级球路追踪、无感场地标定、生物力学姿态分析。
*   **物理裁决**: 真实物理球速计算、单/双打自动胜负裁判 (Auto-Referee)。
*   **认知决策**: 基于汤普森采样 (Thompson Sampling) 的 RAG 战术推荐。
*   **自我进化**: 基于比赛结果自动更新战术权重的贝叶斯后验更新机制。

### 宏观架构：五层进化模型

| 层级 | 模块名称 | 核心职责 | 关键算法/技术 |
| :--- | :--- | :--- | :--- |
| **L1** | **视觉感知层** | "看清"：提取非结构化视频数据 | TrackNetV3, InpaintNet, YOLOv8-Pose |
| **L2** | **物理映射层** | "看懂"：映射物理世界，规则裁决 | Homography Matrix, Auto-Referee |
| **L3** | **贝叶斯记忆层** | "回忆"：存储战术，维护胜率分布 | ChromaDB, Beta Distribution |
| **L4** | **决策代理层** | "表达"：生成自然语言指导 | LLM (DeepSeek), Prompt Engineering |
| **L5** | **进化反馈层** | "成长"：策略权重自适应更新 | Thompson Sampling, Posterior Update |

---

## 2. 后端代码模块详解

### 目录结构
```text
EvoSmash_Backend/
├── config.py                     # [配置] 全局配置中心 (API Key, 物理常数)
├── main.py                       # [入口] FastAPI 服务与全流程编排
├── core/
│   ├── vision/                   # [L1 感知层]
│   │   ├── tracker.py            # 推理引擎 (27通道输入 + 高斯时序融合)
│   │   ├── court_detector.py     # 场地自动标定 (Canny + Hough变换)
│   │   └── pose.py               # 人体姿态评估 (YOLOv8-Pose)
│   ├── physics/                  # [L2 物理层]
│   │   ├── engine.py             # 物理映射与速度/事件计算
│   │   └── referee.py            # 自动裁判 (单/双打边界判定)
│   ├── memory/                   # [L3 记忆层]
│   │   └── rag_engine.py         # 贝叶斯 RAG 引擎 (汤普森采样检索)
│   ├── agent/                    # [L4 决策层]
│   │   └── llm.py                # LLM 教练代理接口
│   └── utils/                    # [L5 工具层]
│       └── fsm_segmenter.py      # 混合有限状态机 (长视频切片)
└── test.py          # [测试] 前端全自动模拟脚本
```

### 核心模块功能解析

#### 2.1 视觉感知 (`core/vision`)
*   **BallTracker**: 集成 TrackNetV3 与 InpaintNet。采用 **27通道张量输入**（序列帧+中值背景），结合 **高斯加权时序融合**，消除单帧预测抖动，解决遮挡问题。
*   **CourtDetector**: 实现 **无感标定**。利用几何约束算法自动提取球场 4 个角点，无需用户手动点击。
*   **PoseAnalyzer**: 计算膝盖角度（重心评估）和手肘角度（发力评估），生成结构化动作诊断数据。

#### 2.2 物理映射 (`core/physics`)
*   **PhysicsEngine**: 利用单应性矩阵将像素坐标 $(u,v)$ 转换为物理坐标 $(x,y)$，计算真实球速 ($km/h$)。
*   **AutoReferee**: **自动裁判**。根据轨迹 $Y$ 轴趋势判断击球方，根据落点判断界内界外。支持通过 `match_type` 切换单/双打判定规则。

#### 2.3 贝叶斯记忆 (`core/memory`)
*   **RAGEngine**: 系统的算法核心。
    *   **存储**: 维护战术的 Beta 分布参数 $(\alpha, \beta)$。
    *   **检索**: 实现 **汤普森采样**，解决探索与利用困境。
    *   **更新**: 实现 **贝叶斯后验更新**，根据 `AutoReferee` 的结果自动调整概率分布。

#### 2.4 长视频处理 (`core/utils`)
*   **BadmintonFSM**: **混合有限状态机**。识别 `IDLE` (死球) $\leftrightarrow$ `RALLY` (回合) 状态流转，引入冷却缓冲机制，实现整场比赛的精准切片。

---

## 3. API 接口规范

### 3.1 单回合分析 (Short Clip Analysis)
**场景**: 用户上传 5-15秒 的单球视频。

*   **URL**: `/analyze_rally`
*   **Method**: `POST`

**请求参数 (Form Data)**:
*   `file`: 视频文件 (Binary)。
*   `match_type`: 字符串，`singles` (单打) 或 `doubles` (双打)。

**响应结果 (JSON)**:
```json
{
  "physics": {
    "event": "Smash",
    "max_speed_kmh": 214.5,
    "description": "对手重杀... [动作评价: 重心过高]"
  },
  "advice": "重心太高了！根据贝叶斯推断，下一球建议反手挡网前。", 
  "auto_result": "WIN",               // 自动裁判结果: WIN, LOSS, UNKNOWN
  "auto_reward": 10.0,                // 自动进化的奖励值
  "match_type": "singles",
  "session_id": "T001",               // 推荐的战术ID
  "tactics": [ ... ]                  // 包含 Alpha/Beta 参数的战术列表
}
```

### 3.2 整场比赛分析 (Full Match Analysis)
**场景**: 用户上传 30分钟+ 的长视频，后台自动切片并批量进化。

*   **URL**: `/analyze_match`
*   **Method**: `POST`

**响应结果 (JSON)**:
```json
{
  "status": "success",
  "match_summary": {
    "total_rallies_found": 12,
    "valid_rallies_analyzed": 8
  },
  "timeline": [
    {
      "rally_index": 1,
      "duration_sec": 5.2,
      "physics": { "event": "Smash", ... },
      "auto_result": "WIN",
      "auto_reward": 10.0
    },
    // ... 更多回合
  ]
}
```

### 3.3 人工反馈修正 (Manual Feedback)
**场景**: 当自动裁判无法判定或判定错误时，用户手动修正。

*   **URL**: `/feedback`
*   **Method**: `POST`

**请求参数**: `tactic_id`, `result` (`WIN`/`LOSS`)。

---

## 4. 用户使用流程 (User Journey)

### 阶段一：赛前设置
1.  **启动 APP**: 打开 EvoSmash。
2.  **模式选择**: 点击切换 **【单打 Singles】** 或 **【双打 Doubles】** (影响裁判逻辑)。
3.  **架设机位**: 将手机固定在场边，无需人工校准。

### 阶段二：实战录入
1.  **击球**: 用户进行回合对抗。
2.  **上传**:
    *   **单球模式**: 每次死球后点击“分析上一球”。
    *   **整场模式**: 比赛结束后上传整段录像。

### 阶段三：智能反馈 (HUD)
APP 弹出战术面板，展示：
*   **仪表盘**: 真实球速 (例如 `205 km/h`)。
*   **裁判判决**: 绿色徽章 **【判定：WIN】**。
*   **教练指导**: “好球！战术有效，模型置信度已提升。”

### 阶段四：自动进化
*   **后台逻辑**: 系统检测到 WIN，自动更新该战术的 Beta 分布 ($\alpha+1$)。
*   **用户感知**: 在【进化】页面看到该战术的能量槽变满，下次遇到类似局面，AI 会更坚定地推荐此战术。

### 阶段五：人工修正 (Human-in-the-loop)
*   如果 AI 判错了 (例如压线球判出界)，用户点击结果图标，手动改为正确的胜负。系统立即回滚并更新模型。

---

## 5. 数据流转图 (Data Pipeline)

1.  **Input** (Video + MatchType)
    $\downarrow$
2.  **Vision** (TrackNet + Pose + CourtDetector)
    $\downarrow$ *[提取像素轨迹 & 骨骼 & 场地角点]*
3.  **Physics** (Homography + AutoReferee)
    $\downarrow$ *[计算真实球速 & 自动判定胜负 (WIN/LOSS)]*
4.  **Memory** (Thompson Sampling RAG)
    $\downarrow$ *[检索 Top-3 战术 & 采样得分]*
5.  **Agent** (LLM)
    $\downarrow$ *[生成自然语言建议]*
6.  **Evolution** (Auto-Update)
    $\downarrow$ *[若裁判结果有效 -> 自动更新数据库 $\alpha, \beta$]*
7.  **Output** (JSON Response to Frontend)