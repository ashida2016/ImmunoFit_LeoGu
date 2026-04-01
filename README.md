# ImmunoFit 🧬

**ImmunoFit** is a Multimodal Healthcare & Bioinformatics Platform designed to quantify patients' "Immune Readiness" and utilize exercise as a physiological perturbation to reveal underlying immune capacity.

[中文说明请见下方](#immunofit-中文说明)

## 🎯 Core Purpose (English)
The core objective of this system is to bridge lifestyle interventions (exercise) with underlying molecular biological changes (gene expression and immune status). By quantifying "Immune Readiness", the system predicts and optimizes a patient’s clinical response to immunotherapy (e.g., anti-PD-1 therapy), particularly in the pre-treatment phase. It serves not only as a data monitoring tool but also as a decision-support system for proactive intervention.

## 🚀 Key Features
1. **Dual-Role Architecture**: 
   - **Patient Mode**: Provides simple, actionable feedback and behavioral incentives (e.g., "Today's exercise improved your immune readiness").
   - **Clinician/Research Mode**: Displays raw molecular data, IRS calculation processes, probability prediction curves, and gene pathway explanations. Supports data anonymization.
2. **Multi-Modal Data Integration**: Aggregates baseline characteristics, clinical physiological markers (NLR, CRP), molecular/gene expression (DCN, IFNG, CD8A), and exercise behavior.
3. **Core Assessment Engine**:
   - **Baseline IRS**: Reflects the current immune state.
   - **ΔIRS (Delta IRS)**: Reflects immune adaptability and potential in response to perturbation (exercise).
4. **Actionable Outputs & Predictions**: 3D immune state space tracking, anti-PD-1 response probability prediction, and personalized exercise recommendations for pre-conditioning.
5. **Bilingual Support & Responsive Design**: Seamless switching between English and Chinese languages. Mobile, tablet, and PC cross-device scalability via Bootstrap 5.

## 🛠️ Tech Stack
- **Backend**: Python 3, Flask, SQLite / Flask-SQLAlchemy
- **Frontend**: HTML5, Bootstrap 5 CSS
- **Visualization**: Google Charts
- **i18n**: Custom Session-based Dictionary Translation

## ⚙️ Installation & Usage
1. **Clone the repository and enter the directory**:
   ```bash
   cd ImmunoFit_LeoGu
   ```
2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Generate mock clinical & molecular data based on industry conventions**:
   ```bash
   python mock_data.py
   ```
4. **Run the application**:
   ```bash
   python app.py
   ```
5. **Access the platform**: Open your browser and navigate to `http://127.0.0.1:5000`

---

# ImmunoFit 中文说明 🧬

**ImmunoFit** 是一个多模态医疗健康与生物信息学平台，旨在量化患者的“免疫准备度（Immune Readiness）”，并利用运动作为一种生理扰动，揭示潜在的免疫能力。

## 🎯 核心目的
该系统的核心目标是打通生活方式干预（运动）与底层分子生物学变化（基因表达与免疫状态）之间的联系。通过量化“免疫准备度”，从而预测并优化患者对免疫治疗（如抗PD-1治疗）的临床反应，尤其是在治疗前阶段。它不仅是一个数据监测工具，更是一个主动干预的临床决策支持系统。

## 🚀 核心特性
1. **双视角与安全架构**：
   - **患者模式 (Patient Mode)**：提供简洁易懂的反馈，强调行为引导与激励（例如：“今天的运动提升了您的免疫准备度”）。
   - **临床/研究模式 (Clinician Mode)**：展示原始分子数据、IRS计算过程、疗效概率预测曲线及基因通路机制层面的解释。数据呈标准化加密展示。
2. **多模态数据采集体系**：整合多方数据输入，包括患者基线特征、临床生理指标（NLR、CRP等）、分子与特定基因表达（核心如 DCN, IFNG, CD8A）以及详细的运动行为输入。
3. **核心算法引擎**：
   - **基线 IRS (Baseline IRS)**：表征患者当前的免疫状态。
   - **ΔIRS (Delta IRS)**：表征免疫系统对外部扰动（运动操作）的动态响应潜能（即潜在免疫能力）。
4. **疗效预测与可视化干预**：构建3D免疫状态空间（激活/衰竭/增殖），预测免疫治疗响应概率，并反向推导出实现理想状态的人性化运动处方（Pre-conditioning运动预处理）。
5. **多语言与自适应设计**：内置原生中英文语言无缝切换机制，并由 Bootstrap 5 驱动实现跨端（手机、平板、桌面屏）屏幕尺寸的自适应缩放。

## 🛠️ 技术栈
- **后端引擎**: Python 3, Flask 微框架, SQLite / Flask-SQLAlchemy (ORM)
- **前端页面**: HTML5, Bootstrap 5 CSS
- **图表渲染**: Google Charts 动态组件
- **国际化 (i18n)**: 基于会话级字典映射方案机制

## ⚙️ 安装与启动
1. **进入项目目录**:
   ```bash
   cd ImmunoFit_LeoGu
   ```
2. **安装运行所需的依赖库**:
   ```bash
   pip install -r requirements.txt
   ```
3. **初始化数据库并生成拟真的多模态与实验数据种子**:
   ```bash
   python mock_data.py
   ```
4. **启动 Flask 平台原型**:
   ```bash
   python app.py
   ```
5. **访问平台主页**: 在浏览器中打开 `http://127.0.0.1:5000` 即可开始体验测试。
