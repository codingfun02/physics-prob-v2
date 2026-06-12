# 주사위 시뮬레이션의 물리·수학

> 미적분학을 이수한 고등학생 대상.  
> 프로젝트 코드(`config.py`, `physics/`, `simulation/`)와 대응되는 수식 정리.

---

## 0. 문제의 수학적 정식화

연속 밀도 $\rho(\mathbf{r})$ ($\mathbf{r}=(x,y,z)$)가 주어진 정육면체 $\Omega = [-a,a]^3$ ($a=0.5\,\mathrm{m}$)에 대해:

$$
M = \int_\Omega \rho(\mathbf{r})\,dV, \qquad
\mathbf{r}_{\mathrm{cm}} = \frac{1}{M}\int_\Omega \rho(\mathbf{r})\,\mathbf{r}\,dV
$$

코드에서는 이를 $6\times6\times6$ 격자로 **리만 합** 근사합니다:

$$
M \approx \sum_{i,j,k} \rho_{ijk}\,\Delta V, \qquad
\mathbf{r}_{\mathrm{cm}} \approx \frac{1}{M}\sum_{i,j,k} \rho_{ijk}\,\mathbf{r}_{ijk}\,\Delta V
$$

한 시행의 결과는 **확률변수** $X \in \{1,2,3,4,5,6\}$ (위쪽 면 번호)이고, 목표는:

$$
p_k = \mathbb{P}(X = k), \quad k=1,\ldots,6
$$

몬테카를로는 $\hat{p}_k$로 $p_k$를 추정합니다.

---

## 1. 무게중심이 확률을 바꾸는 이유

### 1.1 강체의 운동방정식 (6자유도)

주사위를 **강체(rigid body)**로 보면, 상태는 위치 $\mathbf{r}(t)$, 자세 $R(t)\in SO(3)$, 선속도 $\mathbf{v}$, 각속도 $\boldsymbol{\omega}$로 기술됩니다.

**병진:**

$$
M\,\ddot{\mathbf{r}} = \mathbf{F}_{\mathrm{ext}} = M\mathbf{g} + \mathbf{F}_{\mathrm{contact}}
$$

**회전 (무게중심 기준):**

$$
\mathbf{I}_{\mathrm{cm}}\,\dot{\boldsymbol{\omega}} + \boldsymbol{\omega}\times(\mathbf{I}_{\mathrm{cm}}\boldsymbol{\omega}) = \boldsymbol{\tau}_{\mathrm{ext}}
$$

$\mathbf{I}_{\mathrm{cm}}$: 무게중심 기준 관성텐서. `physics/inertia.py`의 `compute_inertia()`가 격자 합으로 계산:

$$
I_{\alpha\beta} = \sum_i m_i\Big[|\mathbf{r}_i'|^2\delta_{\alpha\beta} - r'_{i\alpha}\, r'_{i\beta}\Big], \qquad \mathbf{r}_i' = \mathbf{r}_i - \mathbf{r}_{\mathrm{cm}}
$$

### 1.2 중력 토크 — $\mathbf{r}_{\mathrm{cm}} \neq 0$일 때

중력 $\mathbf{g}=(0,0,-g)$의 합력은 무게중심에 $M\mathbf{g}$로 작용합니다. 기하학적 중심 $O$가 원점이고 $\mathbf{r}_{\mathrm{cm}}\neq 0$이면 원점 기준 중력 토크:

$$
\boldsymbol{\tau}_{\mathrm{grav}} = \mathbf{r}_{\mathrm{cm}} \times (M\mathbf{g})
$$

자세가 $R$일 때 body 좌표의 $\mathbf{r}_{\mathrm{cm}}$은 월드에서 $R\mathbf{r}_{\mathrm{cm}}$이므로:

$$
\boldsymbol{\tau}_{\mathrm{grav}} = (R\mathbf{r}_{\mathrm{cm}}) \times (M\mathbf{g})
$$

**핵심:** $\mathbf{r}_{\mathrm{cm}}=0$ (균일 밀도)이면 중력만으로는 정역학 토크가 0입니다. $\mathbf{r}_{\mathrm{cm}}\neq 0$이면 자세마다 토크가 달라집니다.

### 1.3 포텐셜 에너지

중력 포텐셜 (무게중심 높이 $z_{\mathrm{cm}}$):

$$
U = M g\, z_{\mathrm{cm}}(\mathbf{r}, R)
$$

한 면이 바닥에 닿은 자세 $R$에서 $z_{\mathrm{cm}}$이 작을수록 에너지가 낮습니다.

- **균일 정육면체:** 6가지 “면이 바닥” 자세에서 $z_{\mathrm{cm}}$ 동일 → 에너지 대칭 → $p_k \approx 1/6$
- **비균일:** 6자세마다 $z_{\mathrm{cm}}(R)$ 다름 → 안정 자세(basin of attraction)의 크기가 달라짐 → $p_k$ 편향

### 1.4 안정 평형과 2차 미분

작은 각변위 $\delta\boldsymbol{\theta}$에 대해:

$$
U(\delta\boldsymbol{\theta}) \approx U_0 + \frac{1}{2}\,\delta\boldsymbol{\theta}^\top \mathbf{H}\,\delta\boldsymbol{\theta}, \qquad \mathbf{H} = \nabla^2 U
$$

$\mathbf{H}$ 양정치 → 안정 평형, 음의 고유값 방향 → 불안정.

### 1.5 코드와의 연결 — 위쪽 면 판정

정지 후 자세 $R$에서 위쪽 면:

$$
k^* = \arg\max_{k} \;\hat{\mathbf{n}}_k^\top R^\top \hat{\mathbf{z}}
$$

(`physics/faces.py`: $R\hat{\mathbf{n}}_k$와 $\hat{\mathbf{z}}$의 내적 최대)

**주의:** $p_k$는 정적 에너지만이 아니라 초기 $\boldsymbol{\omega}_0$, 반발 $e=0.3$, 마찰 $\mu=0.5$, 낙하 높이 $h=1.5\,\mathrm{m}$을 포함한 **전체 동역학**의 종단 분포입니다.

---

## 2. PyBullet이 매 스텝마다 하는 계산

### 2.1 연속 시간 문제 (ODE)

$$
\frac{d\mathbf{q}}{dt} = \mathbf{v}, \qquad M\frac{d\mathbf{v}}{dt} = \mathbf{F}(\mathbf{q}, \mathbf{v}, t)
$$

$$
\frac{d\boldsymbol{\Phi}}{dt} = \boldsymbol{\omega}, \qquad \mathbf{I}\dot{\boldsymbol{\omega}} = \boldsymbol{\tau} - \boldsymbol{\omega}\times\mathbf{I}\boldsymbol{\omega}
$$

$\mathbf{q}$: 위치, $\boldsymbol{\Phi}$: 회전(쿼터니언), $\mathbf{F},\boldsymbol{\tau}$: 중력 + 접촉력.

### 2.2 시간 이산화

```python
PHYSICS_DT = 1/240  # 초, Δt ≈ 4.17 ms
```

매 `stepSimulation()`마다 $t \to t+\Delta t$. PyBullet은 **constraint-based rigid body solver** (sequential impulse / PGS류) 사용:

1. **예측:** $\mathbf{v},\boldsymbol{\omega}$로 $\Delta t$ 동안 자유 운동
2. **충돌 검출:** 관통 깊이 $d>0$
3. **제약 해결:** 법선 임펄스 $J_n$, 마찰 임펄스 $J_t$

**법선 (뉴턴 회복 계수 $e$):**

$$
v_n^+ = -e\, v_n^-, \qquad e = 0.3 \;(\texttt{RESTITUTION})
$$

**마찰 (쿨롱, $\mu$):**

$$
|J_t| \le \mu |J_n|, \qquad \mu = 0.5 \;(\texttt{FRICTION})
$$

### 2.3 수치적분 (오일러와의 비교)

연속 ODE $\dot{\mathbf{x}}=f(\mathbf{x},t)$의 **오일러법:**

$$
\mathbf{x}_{n+1} = \mathbf{x}_n + \Delta t\, f(\mathbf{x}_n, t_n), \qquad \text{오차 } O(\Delta t)
$$

PyBullet은 semi-implicit Euler + constraint projection에 가깝습니다.

**스텝 크기 타당성:** 낙하 속도 $v\sim\sqrt{2gh}$, $h=1.5\,\mathrm{m}$:

$$
v \approx \sqrt{2 \times 9.8 \times 1.5} \approx 5.4\,\mathrm{m/s}
$$

한 스텝 이동 $\Delta x \sim v\Delta t \approx 5.4/240 \approx 0.022\,\mathrm{m}$ (주사위 한 변 $1\,\mathrm{m}$의 약 2%).

### 2.4 한 시행 알고리즘

| 단계 | 수학 | 코드 |
|------|------|------|
| 초기화 | $\mathbf{r}_0=(0,0,h)$, $h=1.5$; $R_0$ 균일; $\mathbf{v}_0=0$; $\boldsymbol{\omega}_0\sim\mathrm{Unif}([-5,5]^3)$ | `single_trial.py` |
| 반복 | $n=1,\ldots,2400$: solver step | `p.stepSimulation()` |
| 정지 | $\|\mathbf{v}\|<0.01$, $\|\boldsymbol{\omega}\|<0.05$ 가 $0.1\,\mathrm{s}$ 연속 | `VEL_THRESHOLD` 등 |
| 출력 | $X = \arg\max_k \hat{\mathbf{n}}_k^\top R^\top \hat{\mathbf{z}}$ | `get_top_face()` |

### 2.5 비균일 밀도의 PyBullet 표현

216개 body 대신 **단일 box** + 무게중심 오프셋 + 주관성 모멘트 (`physics/bodies.py`):

- `baseMass = M`
- `baseInertialFramePosition = r_cm`
- `localInertiaDiagonal = [I_1, I_2, I_3]` (주축 분해)

---

## 3. 몬테카를로 오차

### 3.1 추정량

면 $k$의 진짜 확률 $p_k$, $N$회 시행 횟수 $C_k$:

$$
C_k \sim \mathrm{Binomial}(N, p_k), \qquad \hat{p}_k = \frac{C_k}{N}
$$

### 3.2 기댓값과 분산

$$
\mathbb{E}[\hat{p}_k] = p_k, \qquad \mathrm{Var}(\hat{p}_k) = \frac{p_k(1-p_k)}{N}
$$

**표준오차:**

$$
\mathrm{SE}(\hat{p}_k) = \sqrt{\frac{p_k(1-p_k)}{N}}
$$

$p_k\approx 1/6$일 때:

$$
\mathrm{SE} \approx \sqrt{\frac{5/36}{N}} = \sqrt{\frac{5}{36N}}
$$

### 3.3 $N = 50{,}000$일 때

$$
\mathrm{SE} \approx \sqrt{\frac{5}{36 \times 50000}} \approx 0.00167 \;(0.17\%\mathrm{p})
$$

95% 신뢰구간 (정규 근사, $z=1.96$):

$$
\hat{p}_k \pm 1.96 \times \mathrm{SE} \approx \hat{p}_k \pm 0.0033
$$

균일 주사위 $p_k=1/6\approx 0.1667$ → 95% CI 폭 약 $\pm 0.33\%\mathrm{p}$.

### 3.4 $N=200$과 비교 (검증 실험)

$$
\mathrm{SE}_{200} \approx \sqrt{5/(36\times 200)} \approx 0.026 \;(2.6\%\mathrm{p})
$$

200회에서 면별 14%–20%는 **통계적 변동으로 충분히 설명**됩니다.

### 3.5 표본 크기별 오차 (참고)

| $N$ | 대략 $\mathrm{SE}$ ($p\approx 1/6$) | 95% CI 폭 |
|-----|-----------------------------------|-----------|
| 200 | 2.6% | $\pm 5\%$ |
| 5,000 | 0.52% | $\pm 1\%$ |
| 50,000 | 0.17% | $\pm 0.33\%$ |
| 500,000 | 0.053% | $\pm 0.1\%$ |

$N$을 4배 늘리면 $\mathrm{SE}$는 약 $1/2$로 감소합니다.

### 3.6 중심극한정리

$N$이 크면:

$$
\frac{\hat{p}_k - p_k}{\mathrm{SE}(\hat{p}_k)} \xrightarrow{d} \mathcal{N}(0,1)
$$

`main.py`의 오차막대 $\sqrt{\hat{p}(1-\hat{p})/N}$가 이 $\mathrm{SE}$의 추정입니다.

### 3.7 통계적 오차 vs 체계적 오차 (bias)

몬테카를로 $\mathrm{SE}$는 **샘플링 오차**만 반영합니다. $N\to\infty$에도 남을 수 있는 **체계적 오차**:

1. $6\times6\times6$ 격자 이산화
2. $\Delta t = 1/240$ 및 constraint solver 근사
3. 정지 임계값 (`VEL_THRESHOLD`, `ANG_VEL_THRESHOLD`)
4. 초기 각속도 분포가 실제 던지기와 다를 수 있음

진짜 확률을 $p_k$, 시뮬 결과를 $\hat{p}_k$라 하면:

$$
\hat{p}_k \xrightarrow{N\to\infty} p_k + b
$$

$b$: bias. $b$를 줄이려면 $\Delta t$ 감소, 격자 세분화, 파라미터 민감도 검사가 필요합니다.

---

## 4. 전체 흐름 (요약)

```mermaid
flowchart LR
    rho["rho -> r_cm, I"] --> dyn["ODE + contact solver"]
    dyn --> settle["종단 자세 R"]
    settle --> face["X in 1..6"]
    face --> mc["N회 -> p_hat"]
    mc --> err["SE ~ sqrt(p(1-p)/N)"]
```

1. $\mathbf{r}_{\mathrm{cm}}$이 토크·포텐셜 $U=Mgz_{\mathrm{cm}}$를 비대칭으로 만들어 **종단 자세 분포**를 바꾼다.
2. **PyBullet**은 $\Delta t=1/240$으로 ODE+접촉 제약을 반복 풀어 궤적 $\mathbf{r}(t), R(t)$를 구한다.
3. **몬테카를로**는 $X$의 표본평균으로 $p_k$를 추정하며, $N=50{,}000$이면 통계 오차는 약 $\pm 0.33\%\mathrm{p}$ (95%) 수준이다.

---

## 5. 관련 코드 파일

| 파일 | 역할 |
|------|------|
| `density/grid.py` | $M$, $\mathbf{r}_{\mathrm{cm}}$ 격자 합 |
| `physics/inertia.py` | $\mathbf{I}_{\mathrm{cm}}$, 주축 분해 |
| `physics/bodies.py` | PyBullet 강체 생성 |
| `simulation/single_trial.py` | 1회 낙하·회전 적분 |
| `physics/faces.py` | 위쪽 면 판정 |
| `simulation/monte_carlo.py` | $N$회 $\hat{p}_k$ 추정 |
| `config.py` | $h$, $\mu$, $e$, $\Delta t$, 임계값 |

---

## 6. 확장 주제 (추후)

- 초기 조건 $(\mathbf{q}_0, \boldsymbol{\omega}_0)$에 대한 push-forward measure로 $p_k$ 적분 표현
- 균일 $\rho$에서 $p_k=1/6$ 대칭성 증명
- bias $b$ 수치 실험 ($N$, $\Delta t$ 수렴)
