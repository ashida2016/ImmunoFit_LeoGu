# ImmunoFit — 多模态医疗健康和生物信息学平台

**ImmunoFit** 是一个面向癌症免疫治疗的决策支持系统，通过量化患者的"免疫准备度（Immune Readiness）"，并利用运动干预作为生物学刺激手段，预测并优化患者对免疫疗法（如抗PD-1治疗）的临床反应。

> *Bridging lifestyle interventions (exercise) with underlying molecular biology changes (gene expression and immune status) to deliver personalised guidance for clinical treatment.*

---

## 核心功能

| 模块 | 功能 |
|------|------|
| **免疫准备度评分引擎** | 综合CD8+ T细胞、PD-L1、TMB、运动能力等维度，输出0–100分的免疫准备度评分 |
| **运动干预推荐** | 基于患者当前状态，生成个性化运动处方（有氧、阻力训练、HIIT、综合方案） |
| **免疫治疗响应预测** | 预测患者对抗PD-1检查点阻断疗法的客观响应概率，并给出临床建议 |
| **基因表达分析** | 分析RNA-seq/芯片数据，评估肿瘤微环境（TME）表型及免疫基因签名 |
| **REST API** | 通过Flask API将所有功能暴露为标准JSON接口 |

---

## 系统架构

```
immunofit/
├── models.py             # 核心数据模型
├── immune_readiness.py   # 免疫准备度评分引擎
├── exercise.py           # 运动干预推荐模块
├── gene_expression.py    # 基因表达分析模块
├── predictor.py          # 免疫治疗响应预测模块
└── api.py                # Flask REST API
tests/
├── conftest.py
├── test_models.py
├── test_immune_readiness.py
├── test_exercise.py
├── test_gene_expression.py
├── test_predictor.py
└── test_api.py
```

---

## 快速开始

### 安装依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 启动 API 服务

```bash
python -m immunofit.api
```

---

## API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/health` | GET | 服务健康检查 |
| `/api/v1/assess` | POST | 计算免疫准备度评分 |
| `/api/v1/exercise` | POST | 生成个性化运动干预处方 |
| `/api/v1/predict` | POST | 预测免疫治疗响应概率 |
| `/api/v1/gene-expression` | POST | 分析基因表达数据及TME表型 |

### 请求示例

```json
{
  "patient_id": "P001",
  "age": 58,
  "sex": "male",
  "cancer_type": "NSCLC",
  "immune_markers": {
    "cd8_t_cell_count": 500,
    "nk_cell_activity": 45,
    "pd_l1_expression": 55,
    "tumor_mutation_burden": 12,
    "il6": 3,
    "crp": 2,
    "tnf_alpha": 5,
    "ifn_gamma": 30
  },
  "exercise_data": {
    "vo2_max": 38,
    "weekly_minutes_moderate": 150,
    "weekly_minutes_vigorous": 30,
    "steps_per_day": 8000,
    "exercise_type": "aerobic"
  }
}
```

---

## 免疫准备度评分模型

| 维度 | 权重 | 主要生物标志物 |
|------|------|--------------|
| T细胞激活 | 25分 | CD8+ T细胞计数、IFN-γ、NK细胞活性 |
| 检查点/PD-L1状态 | 25分 | PD-L1 TPS（KEYNOTE阈值：1%/50%） |
| 肿瘤突变负荷 (TMB) | 25分 | mut/Mb（FDA阈值：10 mut/Mb） |
| 运动能力 | 25分 | VO₂max、每周MET-min |
| 炎症惩罚 | -10分 | IL-6、CRP、TNF-α |

**评分分级：**
- Low (0–39): 免疫准备度不足，建议先实施运动干预
- Moderate (40–69): 建议运动干预提升后再启动免疫治疗
- High (70–100): 具备良好的免疫准备度，可启动抗PD-1治疗

---

## Python 直接调用示例

```python
from immunofit import ImmuneReadinessCalculator, ImmunotherapyResponsePredictor
from immunofit.models import Patient, ImmuneMarkers, ExerciseData, Sex

patient = Patient(
    patient_id="P001",
    age=58,
    sex=Sex.MALE,
    cancer_type="NSCLC",
    immune_markers=ImmuneMarkers(
        cd8_t_cell_count=500, nk_cell_activity=45,
        pd_l1_expression=55, tumor_mutation_burden=12,
        il6=3, crp=2, tnf_alpha=5, ifn_gamma=30,
    ),
    exercise_data=ExerciseData(
        vo2_max=38, weekly_minutes_moderate=150,
        weekly_minutes_vigorous=30, steps_per_day=8000,
    ),
)

calculator = ImmuneReadinessCalculator()
score = calculator.calculate(patient)
print(score.interpretation)

predictor = ImmunotherapyResponsePredictor()
response = predictor.predict(patient, score)
print(f"Response probability: {response.response_probability:.1%}")
```

---

## 科学依据

- Pedersen et al., *Cell* 2016 — 运动通过肾上腺素介导的T细胞肿瘤归巢
- Campbell & Turner, *Nat Rev Immunol* 2019 — 运动与免疫监视
- Ayers et al., *JCI* 2017 — 18基因IFN-γ IO预测签名
- Herbst et al., *Nature* 2014 — PD-L1与抗PD-1疗效相关性

---

## 许可证

MIT License
