# MINI RESEARCH MLOPS PLATFORM

> **Project specification / tài liệu định hướng triển khai**  
> Phiên bản: `v1.2` — 04/11/2026
> Đối tượng: người mới học backend, Linux, networking, Docker và Kubernetes; đã có kiến thức cơ bản về Python/ML.  
> Môi trường chính: **Ubuntu 24.04, laptop CPU-only, Docker, GitHub**.  
> Mục tiêu: dự án **cá nhân, public trên GitHub**, dùng **dữ liệu tổng hợp**, không sử dụng tài nguyên hoặc dữ liệu nội bộ của công ty.

---

## 0. Đọc phần này trước: project này thực sự là gì?

**Mini Research MLOps Platform** là một nền tảng nhỏ mô phỏng cách nhóm nghiên cứu ML làm việc với hệ thống MLOps dùng chung:

1. Researcher viết một command cho workload và file YAML mô tả experiment; sau bài `hello` ngắn để học Docker, chạy ngay một CPU classifier nhỏ, rồi mở rộng sang job có state và toy PyTorch.
2. Researcher chạy CLI `mini-ml submit configs/hello.yaml`, về sau dùng config cho toy ML/mock prompt.
3. Platform kiểm tra config, gắn định danh cho run và chuẩn bị môi trường thực thi.
4. Platform khởi chạy một **job biệt lập** trong Docker (giai đoạn đầu), sau đó có thể dùng Kubernetes Job.
5. Job dùng **đúng phiên bản input**, ghi params/metrics/artifacts vào MLflow; platform chạy được cả toy training lẫn mock prompt refinement.
6. Job có state định kỳ lưu **checkpoint đầy đủ**, cho phép tiếp tục khi bị gián đoạn.
7. Một research round nhóm hypothesis, baseline/champion, runs, budget, candidate và outcome.
8. Candidate được so với champion trên development set, rồi yêu cầu **trusted gate** kiểm tra bằng sealed test có budget.
9. Candidate PASS được release vào môi trường test, smoke test, xác nhận phiên bản thực chạy và diễn tập rollback.
10. Mỗi thay đổi đi qua feature branch, pull request, CI và merge vào `main`; image được build/publish theo commit và kiểm tra deploy trong lab.

**Điểm cốt lõi:** bạn đang tạo một **MLOps control plane thu nhỏ**. `hello` chỉ kiểm tra lifecycle container; CPU classifier là workload ML thật đầu tiên để học *software engineering, execution, data/version, metrics, artifacts, reliability, security, evaluation và delivery* trước khi dựng shared services.

### Kết quả cuối cùng cần demo được

```text
Feature branch -> PR + CI -> main -> image@digest -> lab deploy
                              |
                              v
                     exact source commit
                              |
                              v
     mini-ml CLI / API
            |
            v
 MLOps Controller (stateless API)
            |                 \
            |                  \--> PostgreSQL (job/run/gate state)
            v
       Job Launcher
        /        \
       v          v
 Docker Job    Kubernetes Job (milestone cuối)
       \          /
        v        v
     Generic job process (hello / CPU classifier / counter / PyTorch ML / mock prompt)
       |       |             |
       v       v             v
    MLflow   Dataset       Checkpoint
       |       |             |
       v       +------ SeaweedFS S3 ------+
  PostgreSQL
       |
       v
  Round -> Candidate -> Dev comparison -> Trusted gate -> PASS/FAIL
                                                    |
                                                    v
                                       Test release -> smoke -> rollback
```

> Lưu ý: sơ đồ biểu diễn **logical architecture**, không đồng nghĩa mỗi ô cần một server vật lý. MLflow dùng PostgreSQL làm backend store; file artifacts có thể lưu vào SeaweedFS. Job state của platform nên nằm ở schema hoặc database riêng với MLflow metadata.

---

## 1. Mục tiêu học tập

Sau khi hoàn thành, bạn phải có thể tự giải thích và chứng minh bằng code:

| Lĩnh vực | Bạn phải chứng minh được |
|---|---|
| Linux | Job command trở thành Python process ra sao; PID, exit code, signal, environment và file path hoạt động thế nào |
| Networking | Vì sao `localhost` khác giữa host/container/Pod; dịch vụ gọi nhau bằng IP, port, DNS và HTTP như thế nào |
| Python engineering | Module, package, `pyproject.toml`, entrypoint, `venv`, dependencies, CLI và reusable SDK |
| Git/GitHub | Mỗi feature có branch, commit, push, PR, CI checks, review, merge vào `main`, tag/release; tái chạy code của một commit cụ thể |
| Docker | Phân biệt Dockerfile/image/container; writable layer, bind mount, volume, runtime và source code |
| Docker Compose | Khởi tạo nhiều services, private networks, service DNS, healthchecks, volumes, env/secrets |
| Backend/API | FastAPI nhận request, validation, DB transaction, job state machine và idempotency |
| MLOps | Input/dataset version, round/run/candidate/champion, experiment tracking, evaluation, gate, release/rollback và reproducibility |
| Reliability | Retry khác resume, checkpoint hoàn chỉnh, run/attempt identity và recovery |
| Kubernetes | Pod/Job/Deployment/Service/namespace, ServiceAccount, Service DNS, NetworkPolicy; **không cần GPU thật** |
| Security | Tách trusted gate khỏi researcher code, least privilege, tránh lộ secrets, network policy khác storage permission |
| CI/CD | PR checks, build/publish image theo commit, deploy/smoke trên môi trường test, rollback, phân biệt platform release với candidate release |

### Nguyên tắc thiết kế xuyên suốt

- **Thin vertical slice trước**: dùng `hello` job để học logs/exit code, rồi train CPU classifier nhỏ ngay trong M1b; counter/PyTorch/mock prompt mở rộng cùng job contract ở các milestone sau.
- **Run identity khác execution attempt**: cùng một logical run có thể có nhiều lần chạy lại.
- **Dữ liệu bền vững nằm ngoài container**: job có thể biến mất, metrics/checkpoints vẫn còn.
- **Một job contract, nhiều workload**: platform chạy *một command được khai báo*, không hard-code một trainer hay algorithm cụ thể.
- **Round khác run; approval khác deployment**: một round có nhiều runs; candidate PASS gate chưa chứng minh phiên bản đó đang phục vụ request.
- **Mỗi feature đi qua PR**: `main` chỉ nhận thay đổi đã qua CI và review; CD dùng image/artifact bất biến theo digest.
- **Trusted code tách khỏi researcher code**: đặc biệt khi truy cập sealed test, secrets hoặc quyền release.
- **Làm xong từng milestone rồi mới mở rộng**: không xây Kubernetes/Rancher/frontend ở ngày đầu.

---

## 2. Phạm vi: bắt buộc, tùy chọn và không làm

### 2.1. MVP bắt buộc

1. Một generic `hello` job để học lifecycle; ngay sau đó train CPU classifier nhỏ trên dữ liệu tổng hợp, lưu metric/model artifact. Stateful counter học checkpoint ở M4; toy PyTorch MLP CPU và mock prompt/config refinement mở rộng ở M5.
2. Public GitHub repo có README, tests, `.gitignore`, hướng dẫn branch/PR, GitHub Actions và lịch sử PR đã merge vào `main`.
3. Docker image cho các jobs/controller; Docker Compose cho shared infrastructure.
4. PostgreSQL, MLflow Tracking Server, SeaweedFS S3-compatible object storage.
5. `mini-ml submit`, `mini-ml status`, `mini-ml logs` ở mức tối thiểu.
6. Experiment/job manifest dạng YAML được validate bằng Pydantic.
7. Ghi full Git commit, runtime image identifier/digest nếu có, config hash và dataset version vào run metadata.
8. Hai trạng thái độc lập: job lifecycle của platform và MLflow run tracking.
9. Checkpoint/resume qua object storage; chủ động kill container để kiểm chứng.
10. Research round có hypothesis, baseline/champion, giới hạn runs/gate calls và outcome; mọi run gắn `round_id`.
11. Evaluation contract có candidate/champion digest, dataset/evaluator version, primary và guard metrics; **trusted gate** dùng sealed-test budget bền vững trong PostgreSQL.
12. Test release và rollback sau gate; ghi riêng approved version và observed deployed version.
13. CI kiểm tra PR, CD build/publish image bất biến trên `main` và deploy/smoke trong môi trường test dạng lab; M3 dùng Compose lab, M6 mở rộng sang kind. Một smoke test chạy xuyên luồng từ submit tới gate/release.
14. Một local Kubernetes Job hoạt động bằng **kind** ở milestone cuối.

### 2.2. Tùy chọn — chỉ thêm khi MVP ổn

- Một workload loại khác, ví dụ **threshold tuner**, sau khi toy ML và mock prompt đã dùng chung job contract.
- FastAPI authentication đơn giản cho API local.
- Prometheus/Grafana, OpenTelemetry, structured logs.
- Paired bootstrap/superiority/non-inferiority ở mức học thuật sau khi evaluation contract cơ bản đã đúng; không suy diễn ý nghĩa thống kê từ tập synthetic quá nhỏ.
- Retry queue / quota / concurrency limits.
- Model registry dùng MLflow.
- Native sidecar hoặc init container nếu có nhu cầu rõ ràng.

### 2.3. Không làm trong phiên bản luyện tập

- Distributed multi-node GPU training, L40S thực, GPU scheduling nâng cao, MIG.
- Fine-tune LoRA cho LLM lớn trên laptop; mock prompt workflow chỉ kiểm tra platform contract, không thay thế bài học về chất lượng model thật.
- Public production inference endpoint hoặc vLLM serving cluster quy mô lớn.
- Multi-cluster Rancher management, tự dựng Kubernetes control plane production.
- Enterprise SSO/IAM, đầy đủ compliance/security audit.
- Frontend dashboard viết từ đầu (MLflow UI là đủ).
- Tự viết CNI, storage engine, model registry thay thế MLflow.
- Thử bất kỳ code/dataset/credential/tài liệu quy trình nội bộ nào lên GitHub cá nhân.

---

## 3. Kịch bản người dùng và Definition of Success

### Persona A — Researcher

- Có một command trong repo, bắt đầu bằng `hello` để kiểm tra Docker, tiếp theo là CPU classifier thật; sau đó thêm counter/PyTorch/mock prompt workload.
- Tạo `configs/exp01.yaml`.
- Submit; không cần SSH vào job container để train thủ công.
- Theo dõi trạng thái, log, metric, artifact và checkpoint khi workload có state.
- Gắn run vào round, so sánh candidate với champion, yêu cầu gate và quan sát release/rollback.

### Persona B — Platform Maintainer (bạn)

- Thay implementation `DockerLauncher` bằng `KubernetesLauncher` mà không sửa workload command.
- Biết request nào sinh ra Docker container/K8s Job nào.
- Debug thất bại từ log, status, exit code, metadata.
- Truy xuất exact code/data/runtime/config của một experiment.
- Hạn chế researcher không truy cập sealed test và privileged credentials.
- Review PR, đọc CI failure, theo dõi image digest đã publish và phiên bản thực deploy.

### Demo cuối được xem là **PASS** nếu

```text
[ ] Checkout GitHub repository từ máy mới, cấu hình local, chạy test được.
[ ] Một feature branch được push, tạo PR, CI pass, review/merge vào `main`; branch mới tách từ `main` đã cập nhật.
[ ] docker compose up khởi động PostgreSQL + MLflow + SeaweedFS.
[ ] CLI submit `hello` job tạo run_id, lưu DB, khởi chạy Docker job; status/log/exit code đúng.
[ ] CPU classifier train trên synthetic dataset bằng host và Docker, ghi validation metric và model artifact có thể dùng lại.
[ ] Training đọc dataset v1, ghi MLflow metric và artifact.
[ ] Xóa job container, metrics/artifact vẫn còn.
[ ] Kill stateful counter job giữa chừng và resume từ checkpoint đầy đủ gần nhất; sau đó thử toy ML.
[ ] Candidate dev evaluation lưu metric theo evaluation contract.
[ ] Round lưu hypothesis, baseline/champion, runs, budget và outcome; mock prompt job dùng cùng submit/status/logs contract.
[ ] Evaluation so candidate với champion trên cùng dataset/evaluator version, có primary/guard metrics.
[ ] Gate cho PASS/FAIL, ghi budget và không cho vượt budget khi submit đồng thời.
[ ] Candidate PASS được deploy test, smoke test xác nhận observed version; lỗi giả lập dẫn tới rollback về champion trước đó.
[ ] Training identity không đọc được sealed labels (trong phạm vi lab đã kiểm thử).
[ ] Chạy cùng toy training command bằng Kubernetes Job trên kind.
[ ] PR checks gồm format/lint, unit tests, build; integration/smoke được thêm theo milestone và chặn merge khi lỗi.
[ ] Merge vào `main` publish image theo commit SHA/digest tới GHCR và deploy/smoke trên lab staging; có bằng chứng rollback.
```

---

## 4. Stack công nghệ và trách nhiệm của từng công cụ

| Thành phần | Lựa chọn | Vì sao |
|---|---|---|
| OS | Ubuntu 24.04 | Máy cá nhân Linux, phù hợp Docker/K8s lab |
| Python | 3.11+ | Backend, CLI, SDK, training |
| Web API | FastAPI + Pydantic | Job submission, validation, OpenAPI |
| CLI | Typer (hoặc argparse ở phiên bản sớm) | `mini-ml submit/status/logs` |
| DB | PostgreSQL | Run/job/gate state bền vững và transaction |
| ORM/migration | SQLAlchemy + Alembic | Quản lý schema thay đổi có kiểm soát |
| Experiment tracking | MLflow | Runs, params, metrics, artifacts |
| Object storage | SeaweedFS S3 Gateway | Dataset snapshots, checkpoints, MLflow artifacts |
| S3 client | boto3 | List/download/upload/checksum verification |
| Workloads | Hello job, stateful counter, mock prompt, PyTorch MLP **CPU-only** | Học execution trước, rồi recovery và hai loại research workload |
| Docker | Docker Engine + Dockerfile | Reproducible runtime và job containers |
| Local services | Docker Compose | Start/stop infra và networking |
| CI | GitHub Actions | PR checks: format/lint, pytest, build, integration/smoke theo milestone |
| CD | GitHub Actions + GHCR + Compose/kind lab | Publish image theo commit/digest; deploy/smoke/rollback trong môi trường test, không cần production host |
| Kubernetes lab | kind + kubectl | Chạy Kubernetes trong Docker, không cần cluster công ty |
| K8s Python API | `kubernetes` Python client | Tạo/quan sát `batch/v1 Job` |
| Tests | pytest | Unit/integration/e2e |

**Chú ý:** không nhất thiết cài ngay mọi công cụ. Mỗi milestone chỉ bổ sung dependency khi sử dụng thật.

### Phân biệt các thành phần hay bị nhầm

- **GitHub** = lưu code + version + PR/CI/CD workflow; `git push` **không tự** tạo job process.
- **Docker image** = environment và có thể chứa app code; **container** = thực thể đang chạy.
- **Docker Compose** = điều phối services trên Docker Engine target; **Kubernetes** = cluster-level workload orchestration.
- **MLflow** = tracking API/metadata/artifacts; **PostgreSQL** = backend data; **SeaweedFS** = object storage.
- **MLOps Controller** (do bạn viết) = quyết định job nào cần chạy; **K8s Control Plane** (có sẵn) = quyết định workload chạy ở đâu.
- **Platform release** = phiên bản Controller/runtime được build/deploy; **candidate release** = artifact đã qua gate được chọn để phục vụ. Hai loại có lifecycle và rollback riêng.

---

## 5. Kiến trúc chi tiết

### 5.1. Component boundaries

**CLI (`mini_ml.cli`)**
- Đọc experiment config; gửi HTTP request vào Controller.
- Hiển thị run_id, trạng thái, logs; không giữ database credentials của platform.

**Controller API (`mini_ml.api`)**
- Validate input và quyền truy cập (lab local có thể đơn giản hóa authentication).
- Resolve/pin code, dataset, runtime, config; tạo logical run ID.
- Ghi DB; gọi JobLauncher; reconcile status.
- Không thực thi workload command trực tiếp bên trong web API process.

**JobLauncher (`mini_ml.launchers`)**
- Interface: `submit(job_spec) -> execution_ref`, `get_status(ref)`, `get_logs(ref)`, `cancel(ref)`.
- `DockerLauncher`: khởi tạo container với env/volume/resource config phù hợp.
- `KubernetesLauncher`: tạo K8s Job/Pod template.
- Launcher nhận **JobSpec** có validation, không tự quyết định model loss/metric.

**Research workload (`examples/...`)**
- `hello`, CPU classifier, counter, mock prompt và PyTorch toy ML tự implement logic; dùng common SDK cho tracking/storage/checkpoint khi cần.
- Không biết platform chạy bằng Docker hay Kubernetes.

**Round service (`mini_ml.rounds`)**
- Lưu hypothesis, baseline/champion, budget, run membership và outcome; một round có nhiều logical runs.
- Không dùng MLflow Experiment làm nguồn sự thật duy nhất cho round budget/outcome; ghi `round_id` vào MLflow tags để truy vết.

**MLflow**
- Lưu params, metrics, tags, experiments, model artifacts.
- Backend store PostgreSQL và artifact store SeaweedFS theo cấu hình server.

**Platform PostgreSQL DB**
- Lưu business state: rounds, logical runs, execution attempts, dataset/evaluation manifests, candidates, gate attempts/budget và releases/deployments.
- Dùng DB/schema logic riêng với MLflow backend để không trộn ownership.

**SeaweedFS**
- S3-compatible buckets cho dataset, checkpoints, MLflow artifacts, sealed-test data.
- Có policies/credentials riêng; **NetworkPolicy chỉ lọc network, không kiểm soát bucket ACL**.

**Trusted Gate**
- Chạy evaluator thuộc code đã review/trust; không đưa sealed labels hay gate credentials cho researcher job.
- Ghi PASS/FAIL/metrics và tiêu hao budget qua DB transaction.
- Candidate được gắn artifact digest và không thể bị thay âm thầm giữa các lần check.

**Lab release service**
- Chỉ nhận candidate đã PASS theo gate contract; ghi approved digest, target environment và deployment attempt.
- Smoke test đọc observed artifact/version từ workload thật; rollback về digest trước khi smoke thất bại.

**GitHub Actions**
- CI kiểm tra PR trước merge; workflow sau merge build/publish platform image và chạy lab deployment/smoke bằng chính image digest đó.
- Không thay thế gate đánh giá candidate; platform CI/CD và model candidate release là hai luồng khác nhau.

### 5.2. Hai loại workload

**Long-running services**: Controller API, MLflow, PostgreSQL, SeaweedFS (chạy/được quản lý bởi Compose hoặc deploy riêng).  
**Finite jobs**: hello, CPU classifier train, counter, PyTorch toy train, mock prompt, dev evaluation, gate evaluation (tạo theo request, kết thúc rồi biến mất).

Đừng đặt PostgreSQL/MLflow vào cùng một Pod/container với mỗi job run.

### 5.3. Stateless và stateful

- Controller API nên **stateless ở mức instance**: restart không mất business state.
- Database/object store là stateful và phải có volumes/backup phù hợp.
- Training **có state trong RAM/GPU trong lúc chạy**; durable checkpoint được đưa ra ngoài job.
- Kubernetes restart Pod **không tự động resume** PyTorch optimizer/model.

---

## 6. Mô hình networking

### 6.1. Khi chạy local bằng Compose

```text
Ubuntu Host
  |
  | localhost:8080 ---> controller (published host port)
  | localhost:5000 ---> mlflow UI (published host port)
  |
  +---- Docker network: platform_net -------------------+
  |   controller --> postgres:5432                       |
  |   controller --> mlflow:5000                         |
  |   mlflow     --> postgres:5432                       |
  |   mlflow     --> seaweedfs:8333                      |
  +-----------------------------------------------------+
  |
  +---- Docker network: jobs_net -----------------------+
  |   job --> mlflow endpoint                            |
  |   job --> SeaweedFS input/checkpoint endpoint         |
  +-----------------------------------------------------+

  Trusted gate có identity/credentials riêng, không đồng nhất với researcher job.
```

**Quy tắc địa chỉ:**

| Bên gọi | Endpoint MLflow ví dụ |
|---|---|
| Browser trên laptop | `http://localhost:5000` (nếu publish đúng host port) |
| Job trong Compose network | `http://mlflow:5000` (nếu cùng network và service name là `mlflow`) |
| Pod trong K8s | `http://mlflow.mlops-system.svc.cluster.local:5000` (nếu MLflow thực sự được expose bằng Service đó) |
| Workload truy cập MLflow ngoài cluster | Hostname nội bộ có thể route được, không dùng `localhost` |

**Đừng hard-code Pod IP/container IP trong Python**. Dùng env `MLFLOW_TRACKING_URI`, `S3_ENDPOINT_URL`, v.v.

### 6.2. Bảo mật mạng trong local lab

- Chỉ publish ports cần dùng lên `127.0.0.1` khi học local; không public PostgreSQL/S3 credentials.
- Chia `platform_net`, `jobs_net`, `gate_net` nếu phù hợp topology, nhưng nhớ Docker network **không thay thế** credential isolation.
- **Không** truyền privileged Docker socket, database admin password, sealed-test credentials vào researcher container.
- Local demo dùng Docker daemon/socket để khởi tạo job chỉ là giải pháp **lab-only**, vì quyền truy cập Docker socket có khả năng kiểm soát host rất cao. Không expose Controller như một public service khi đang dùng cách này.
- Training code tùy ý có thể độc hại: Docker thông thường không phải security boundary đủ mạnh cho multi-tenant untrusted research code.

### 6.3. Khi chuyển sang Kubernetes

- Tạo Pod/Job trong namespace `mlops-jobs`; shared Controller trong `mlops-system`; trusted gate trong `mlops-gate`.
- **Pod** là đơn vị network cơ bản; containers trong cùng Pod dùng chung network namespace/`localhost`.
- **Service + DNS** cho các API cần endpoint ổn định; không cần tạo Service cho mọi batch training Pod.
- **NetworkPolicy** để kiểm soát traffic Pod ingress/egress; thêm allow DNS/MLflow/storage cần thiết.
- S3 permissions vẫn là nhiệm vụ của S3 policy/credentials; NetworkPolicy không lọc bucket name ở cùng IP:port.
- `kind` **không mặc định đảm bảo NetworkPolicy được enforce**; để test isolation thực sự, cần cài và xác nhận một CNI hỗ trợ policy như Calico/Cilium, hoặc đánh dấu network-security test là chưa triển khai.
- `automountServiceAccountToken: false` cho researcher Pod trừ khi có lý do thực sự cần K8s API.

---

## 7. Hợp đồng dữ liệu và experiment

### 7.1. `ExperimentConfig` — YAML do researcher viết

Ví dụ `configs/exp01.yaml`:

```yaml
experiment:
  name: toy-classifier-v1

source:
  repository: https://github.com/Helooeverybody/AI-platform-pipeline.git
  commit: YOUR_FULL_COMMIT_SHA

execution:
  backend: docker              # docker | kubernetes
  runtime_image: mini-ml-runtime:dev
  command:
    - python
    - -m
    - examples.toy_classifier.train
  timeout_seconds: 1800

resources:
  cpu: 2
  memory: 2Gi
  gpu: 0

dataset:
  name: synthetic-classification
  version: v1

training:
  seed: 42
  epochs: 10
  batch_size: 32
  learning_rate: 0.001

checkpoint:
  every_n_steps: 50
  resume_policy: auto_if_compatible
```

**Đây là schema của project bạn tự xây**, không phải YAML chuẩn của Kubernetes/GitHub. Hãy validate các field này bằng Pydantic trước khi tạo job. Ở M1a, `configs/hello.yaml` chỉ cần `experiment` và `execution`. M1b thêm `configs/cpu_train.yaml` với cùng hai nhóm field và command chạy CPU classifier; seed/dataset-generator parameters ghi cùng artifact/metrics. Thêm `source/resources/dataset/training/checkpoint` vào schema khi các milestone tương ứng thật sự dùng chúng.

Mẫu tối thiểu cho `configs/cpu_train.yaml` ở M1b (image `:dev` chỉ dùng local; M3 pin image identity):

```yaml
experiment:
  name: cpu-classifier-v1
execution:
  backend: docker
  runtime_image: mini-ml-runtime:dev
  command: [python, examples/cpu_classifier/train.py, --seed, "42", --output-dir, /outputs]
  timeout_seconds: 120
```

`--output-dir /outputs` là đường dẫn **trong container**; khi chạy host dùng `--output-dir outputs/cpu_classifier`, còn Docker bind mount host directory vào `/outputs`. `model.json` chỉ là artifact số học/metadata của baseline binary classifier; trusted gate về sau parse schema này, không deserialize pickle/joblib không đáng tin.

**Lưu ý:** ví dụ đầy đủ này thuộc M5a, sau job `hello` và control plane cơ bản. Lệnh module `examples.toy_classifier.train` chỉ hoạt động khi thư mục được đóng gói/import đúng; lúc học entrypoint có thể dùng `python examples/toy_classifier/train.py` rồi chuyển sang `python -m`.

### 7.2. `JobSpec` — contract nội bộ đã validate

Sau validate, Controller biến config thành JobSpec bất biến theo run:

```json
{
  "run_id": "run_000172",
  "attempt": 1,
  "source_commit": "<full SHA>",
  "runtime_image": "mini-ml-runtime:dev",
  "dataset_version": "v1",
  "config_sha256": "<config digest>",
  "command": ["python", "examples/toy_classifier/train.py"],
  "resources": {"cpu": 2, "memory": "2Gi", "gpu": 0},
  "checkpoint_prefix": "s3://ml-checkpoints/run_000172/"
}
```

Trong version chính thức, dùng immutable image digest (`image@sha256:...`) hoặc bằng chứng runtime khác thay vì chỉ dùng mutable tag `:dev`.

### 7.3. Định danh cần tách

| ID | Ý nghĩa |
|---|---|
| `round_id` | Một vòng nghiên cứu có hypothesis, baseline/champion, budget và outcome; chứa nhiều runs |
| `logical_run_id` | Một experiment/job logic; giữ nguyên khi retry/resume |
| `attempt_id` | Một lần thực thi thực tế; tạo mới khi retry |
| `execution_ref` | Docker container ID hoặc K8s Job/Pod reference |
| `mlflow_run_id` | ID MLflow để truy vết metrics/artifacts |
| `candidate_id` | Phiên bản candidate đã freeze để evaluate/gate |
| `gate_request_id` | Mỗi yêu cầu sử dụng sealed test; phục vụ audit/idempotency |
| `release_id` | Quyết định đưa approved candidate tới một môi trường test |
| `deployment_id` | Một lần triển khai thực tế; có observed digest và smoke outcome |

Không dùng `GitHub Actions run ID`, `Docker container ID` hoặc `Kubernetes Pod name` làm ID logic duy nhất của experiment.

### 7.4. State machine tối thiểu

```text
CREATED -> VALIDATING -> QUEUED -> RUNNING -> SUCCEEDED
    \          \          \       \
     +----------+----------+-------> FAILED
                         \
                          +--------> CANCELLED
```

Bạn có thể dùng trạng thái ít hơn ở bản đầu; điểm quan trọng là:

- Trạng thái được lưu bền vững trong DB, không chỉ RAM của FastAPI.
- Mọi chuyển trạng thái có timestamp và người/thành phần thực hiện.
- Retry của cùng run tạo attempt mới và không vô tình tạo hai job do HTTP retry.

### 7.5. Research round contract — thêm sau M3

Ví dụ `configs/round01.yaml` dùng tên và dữ liệu giả:

```yaml
round:
  id: round-001
  hypothesis: "Cấu hình prompt B cải thiện độ hợp lệ JSON"
  baseline_candidate: candidate-v1
  budget:
    max_runs: 5
    max_gate_calls: 2
  primary_metric: json_valid_rate
```

- `round_id` được lưu trong platform DB và ghi vào tags của mọi MLflow run thuộc round.
- `max_runs` giới hạn số logical runs được tạo; `max_gate_calls` là giới hạn round, ngoài budget của sealed-test version ở gate. Cấp slot bằng DB transaction để hai requests đồng thời không vượt budget.
- Outcome ghi candidate được chọn, bằng chứng evaluation/gate và lý do dừng; không tự suy ra từ run có metric cao nhất.
- Chỉ thêm schema/API này khi submit/status/logs và tracking cơ bản đã chạy; không dựng toàn bộ round service ngay ở M0.

---

## 8. Dataset versioning và reproducibility

### 8.1. Cách tạo dataset demo

Dùng `sklearn.datasets.make_classification` hoặc PyTorch synthetic data, cố định seed; lưu dữ liệu ra CSV/NPZ/Parquet tùy mức độ học.

Dataset ban đầu:

```text
synthetic-classification/v1/
├── train.npz
├── dev.npz
├── manifest.json
└── README.md
```

`manifest.json` ví dụ:

```json
{
  "name": "synthetic-classification",
  "version": "v1",
  "seed": 42,
  "split": {"train": "train.npz", "dev": "dev.npz"},
  "checksums": {
    "train.npz": "sha256:<actual digest>",
    "dev.npz": "sha256:<actual digest>"
  }
}
```

- Version **v1 không được ghi đè âm thầm**; nếu đổi dữ liệu, tạo v2.
- Để tái lập, ghi file checksums và exact dataset manifest digest.
- **Sealed test phải có manifest/credential/lifecycle riêng**; researcher không được tải labels.
- Không tự động dùng sealed test để chọn hyperparameters hoặc tối ưu trực tiếp.
- Mock prompt workflow dùng synthetic documents/JSON labels có version, split dev/sealed và checksum tương tự; mock service phải deterministic để kiểm thử orchestration, không dùng metric giả để tuyên bố chất lượng LLM thật.

### 8.2. Reproducibility manifest

Mỗi run cần lưu tối thiểu:

```text
run_id
round_id (nếu thuộc round)
source_repo + full Git SHA
runtime_image_digest (hoặc xác định rõ fallback ở lab)
Python/ML dependency versions
experiment config + hash
dataset version + checksums
seed
execution backend (docker/kubernetes)
hardware information (CPU; optional GPU)
checkpoint/resume lineage
MLflow run ID
output artifact digest
evaluator/scorer version và evaluation suite digest khi có evaluation
approved candidate digest và observed deployed digest khi có release
```

**Lưu ý chính xác:** pin các thành phần giúp **reproducibility mạnh hơn**, nhưng không bảo đảm bit-for-bit identical trong mọi trường hợp do nondeterminism, hardware/backend và các nguồn ngẫu nhiên khác.

---

## 9. Storage: đặt dữ liệu nào ở đâu?

### 9.1. Buckets gợi ý

```text
SeaweedFS S3 Gateway
├── ml-datasets/          # immutable train/dev dataset snapshots
├── ml-checkpoints/       # training recovery checkpoints
├── mlflow-artifacts/     # MLflow large artifacts
├── ml-candidates/        # frozen candidate artifacts và evaluation reports
└── ml-testsets/          # sealed-test inputs/labels, trusted gate only
```

Các tên bucket là minh họa. Hãy tạo qua bootstrap script hoặc công cụ tương ứng của SeaweedFS trong local lab.

### 9.2. Database tables gợi ý

```text
platform_runs
  run_id (PK), experiment_name, source_sha, config_hash,
  dataset_version, status, mlflow_run_id, created_at, updated_at

run_attempts
  attempt_id (PK), run_id (FK), attempt_no, backend,
  execution_ref, status, started_at, ended_at, exit_code

research_rounds
  round_id (PK), hypothesis, baseline_candidate_id, max_runs,
  max_gate_calls, status, outcome, created_at, closed_at

round_runs
  round_id (FK), run_id (FK UNIQUE), created_at

dataset_versions
  dataset_id, version, manifest_uri, manifest_sha256, created_at

candidates
  candidate_id, source_run_id, artifact_uri,
  artifact_sha256, created_at

evaluation_reports
  evaluation_id (PK), candidate_id, champion_id, dataset_version,
  evaluator_version, report_uri, report_sha256, created_at

gate_budgets
  test_version (PK), max_uses, consumed_uses

gate_requests
  gate_request_id (PK), candidate_id, test_version,
  status, decision, created_at, completed_at

releases
  release_id (PK), candidate_id, approved_artifact_sha256,
  target_environment, status, created_at

deployments
  deployment_id (PK), release_id (FK), previous_artifact_sha256,
  observed_artifact_sha256, smoke_status, rollback_status, created_at
```

**Không** sửa schema nội bộ MLflow để lưu business state của platform. Bạn quản lý bảng của mình bằng migrations.

### 9.3. Checkpoint key convention

```text
s3://ml-checkpoints/
  step-counter/
    run_000172/
      step-000500/
        checkpoint.bin
        manifest.json
        COMPLETE
      step-001000/
        checkpoint.bin
        manifest.json
        COMPLETE
```

Manifest chứa run identity, step, code/config/dataset/runtime compatibility fields và checksum checkpoint.

Trình tự an toàn:

1. Serialize workload state vào file local tạm.
2. Upload file/checksum vào một object prefix mới; **không ghi đè checkpoint cũ**.
3. Verify kích thước/checksum sau upload nếu có thể.
4. Upload manifest và **publish COMPLETE cuối cùng**.
5. `latest_complete_checkpoint()` chỉ chọn prefix có COMPLETE và manifest hợp lệ.

Không giả định một S3 object multipart upload dở dang là checkpoint hoàn chỉnh.

---

## 10. Reliability: retry và resume là hai việc khác nhau

### 10.1. Phải lưu những gì trong checkpoint?

Trước tiên, stateful counter job lưu `step`, input/config/source hash và RNG state nếu có. Khi thêm PyTorch toy trainer, checkpoint phải chứa cả:

```python
{
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
    "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
    "epoch": epoch,
    "global_step": global_step,
    "rng_state": ...,
    "config_hash": ...,
    "dataset_version": ...,
    "source_commit": ...,
}
```

Nếu dùng AMP, distributed sampler hoặc shuffled dataloader, các trạng thái bổ sung có thể cần để resume chính xác. Với toy CPU training, hãy đặt mục tiêu trước là resume **đúng step/checkpoint** và thử nghiệm consistency, không tuyên bố bit-for-bit reproducibility khi chưa kiểm chứng.

### 10.2. Failure demo bắt buộc

```text
Job Attempt #1
  start step 0
  checkpoint at step 200
  checkpoint at step 400
  container killed at step 550

Job Attempt #2
  finds latest COMPLETE checkpoint = step 400
  verifies config/data/source compatibility
  loads durable state + global_step (toy ML: cả model/optimizer)
  resumes from step 400
  continues to completion
```

**Định nghĩa success:** counter job tiếp tục từ step 400 thay vì step 0; khi nâng cấp sang toy ML, attempt mới cũng phải restore model/optimizer thay vì khởi tạo weights mới. Logs/metadata thể hiện `resumed_from_step=400`.

### 10.3. Những lỗi phải thử

- Kill container bằng `docker kill` (không chỉ graceful SIGTERM).
- Crash ngay giữa upload checkpoint.
- Checkpoint checksum không khớp.
- Attempt mới dùng dataset v2 trong khi checkpoint từ v1.
- Controller nhận cùng submit request hai lần do HTTP retry.
- Workload process trả exit code khác 0.
- MLflow/SeaweedFS tạm thời unreachable.

Nguyên tắc: **job retry tạo execution mới; application code phải tự restore state từ durable checkpoint**.

---

## 11. Evaluation, sealed gate và test release

### 11.1. Development evaluation

- Chạy candidate và champion trên **cùng** dev split, evaluator/scorer version và điều kiện chạy; researcher có quyền xem dev split.
- Freeze candidate/champion bằng artifact digest. Dùng report contract chung cho mock prompt và toy ML, ví dụ:

```json
{
  "round_id": "round-001",
  "candidate": {"id": "candidate-v2", "artifact_sha256": "<digest>"},
  "champion": {"id": "candidate-v1", "artifact_sha256": "<digest>"},
  "dataset_version": "synthetic-docs-v1",
  "evaluator_version": "scorer-v1",
  "primary_metric": "json_valid_rate",
  "candidate_metrics": {"json_valid_rate": 0.86, "latency_ms": 120},
  "champion_metrics": {"json_valid_rate": 0.80, "latency_ms": 110},
  "guard_metrics": {"latency_ms_max": 150},
  "decision": "PASS"
}
```

- Các số trên chỉ minh họa schema, không phải kết quả thực nghiệm. Report thật phải được tính từ predictions/gold cùng version và có checksum.
- Lưu metric, report artifact và `round_id` vào MLflow; platform DB lưu đường dẫn/digest report và quyết định.
- Có ít nhất một case candidate tăng primary metric nhưng vi phạm guard metric và bị FAIL. Paired bootstrap/superiority/non-inferiority chỉ là bài mở rộng sau khi so sánh cơ bản đúng.

### 11.2. Sealed test gate — mô phỏng nghiêm túc, không overclaim security

MVP chỉ đánh giá artifact format **do platform tự kiểm soát** cho từng workload. Tránh nạp arbitrary researcher Python hoặc unsafe pickle vào privileged gate. Với mock prompt, gate đọc prompt/config dạng dữ liệu và gọi trusted mock evaluator; với toy ML, gate dùng trusted model architecture và format weights an toàn phù hợp. Gate nắm quyền đọc sealed labels.

Luồng:

```text
Candidate (artifact digest đã freeze)
           |
           v
Gate request + idempotency key
           |
           v
DB transaction: reserve one unit from test-version budget
           |
           v
Trusted evaluator đọc sealed test
           |
           v
Evaluate -> record outcome + audit entry
           |
           v
PASS / FAIL / ERROR
```

Định nghĩa budget: một lượt được tính khi gate đã cấp quyền truy cập sealed test; chính sách tính các lỗi sau khi reserve phải được quyết định minh bạch và ghi audit, tránh retry vô hạn để lấy feedback miễn phí.

### 11.3. Gate concurrency test

Giả sử test version `sealed-v1` có `max_uses=5`, `consumed_uses=4`.

Hai requests đến đồng thời. **Chỉ một request được cấp quota cuối**.

Không làm như sau:

```python
if consumed_uses < max_uses:
    consumed_uses += 1
```

vì hai processes có thể cùng đọc giá trị 4.

Nên dùng DB transaction/atomic conditional update và có unique idempotency key. Pseudocode SQL minh họa:

```sql
UPDATE gate_budgets
SET consumed_uses = consumed_uses + 1
WHERE test_version = :test_version
  AND consumed_uses < max_uses
RETURNING consumed_uses;
```

Nếu không trả về row, budget đã hết. Việc liên kết request ledger với budget reservation phải thực hiện trong một transaction phù hợp để không đếm hai lần hoặc cấp slot hai lần. Khi request thuộc round, cùng transaction phải reserve cả `round.max_gate_calls` và `gate_budgets`; nếu một giới hạn hết thì cả hai reservation đều rollback.

### 11.4. Security boundaries

- Researcher job: credential **read train/dev**, write chỉ checkpoint prefix của run và các output được cấp quyền.
- Gate: identity riêng, quyền đọc sealed test và cập nhật gate state; không chia sẻ với researcher.
- Controller: có quyền tạo workload nhưng không mang sealed-label credentials trong image của job.
- Không tin tưởng `namespace` hoặc NetworkPolicy một mình có thể chặn mọi loại code độc hại; demo local là bài tập nguyên lý, không phải chứng nhận multi-tenant isolation.
- Không đưa raw sealed labels vào MLflow artifacts hoặc training logs.

### 11.5. Test release và rollback — sau gate

```text
Candidate digest PASS gate -> approved release record
  -> test deployment pin đúng digest -> smoke test
  -> đọc observed digest/version từ workload đang phục vụ
  -> PASS: ghi deployed; FAIL: rollback về previous champion digest
```

- `approved_artifact_sha256` là quyết định của gate/release; `observed_artifact_sha256` là bằng chứng từ môi trường chạy, có thể khác nếu deploy sai hoặc chưa cập nhật.
- Bài lab dùng service/mock endpoint local hoặc kind, không cần public inference endpoint. Smoke test kiểm tra health, sample output/contract và observed version.
- Trước khi thử candidate mới, deploy champion đã biết hoạt động vào môi trường test; sau đó cố tình triển khai candidate lỗi để chứng minh rollback về champion. Lưu release/deployment attempts, thời điểm và kết quả smoke.
- **Model candidate release** ở đây khác **platform CI/CD** build/publish Controller/runtime image trong §15.

---

## 12. API và CLI contract

### API tối thiểu

| Method | Path | Ý nghĩa |
|---|---|---|
| `POST` | `/api/v1/runs` | Submit experiment; dùng idempotency key |
| `GET` | `/api/v1/runs/{run_id}` | Trạng thái logical run |
| `GET` | `/api/v1/runs/{run_id}/attempts` | Lịch sử attempts |
| `GET` | `/api/v1/runs/{run_id}/logs` | Lấy logs từ execution backend hoặc log store |
| `POST` | `/api/v1/runs/{run_id}/resume` | Tạo attempt mới sau verify compatibility |
| `POST` | `/api/v1/rounds` | Mở round với hypothesis/baseline/budget |
| `GET` | `/api/v1/rounds/{round_id}` | Runs, budget, candidate và outcome của round |
| `POST` | `/api/v1/candidates` | Freeze artifact digest thành candidate |
| `POST` | `/api/v1/evaluations` | So candidate và champion trên cùng eval contract |
| `POST` | `/api/v1/gate-requests` | Yêu cầu trusted gate theo budget |
| `POST` | `/api/v1/releases` | Tạo test release từ candidate PASS |
| `GET` | `/api/v1/releases/{release_id}` | Approved/observed version, smoke và rollback state |
| `GET` | `/health/live` | API process đang sống |
| `GET` | `/health/ready` | API sẵn sàng phục vụ theo điều kiện đã định nghĩa |

Tránh đưa API quyền cao ra internet. Ban đầu chỉ bind host `127.0.0.1`.

### CLI mẫu

```bash
mini-ml submit configs/exp01.yaml
mini-ml status run_000172
mini-ml logs run_000172
mini-ml resume run_000172
mini-ml round create configs/round01.yaml
mini-ml round status round-001
mini-ml candidate create run_000172
mini-ml evaluate candidate-v2 --against candidate-v1
mini-ml gate submit candidate_000042 --test-version sealed-v1
mini-ml release test candidate_000042
mini-ml release status release_000007
mini-ml release rollback release_000007
```

**CLI `mini-ml` là chương trình bạn tự xây**, không phải tool MLOps phổ biến có sẵn. Những command phụ có thể được thêm theo milestone.

### Ví dụ response của submit

```json
{
  "run_id": "run_000172",
  "status": "QUEUED",
  "source_commit": "<full SHA>",
  "dataset_version": "v1"
}
```

Không trả về thành công ở mức `SUCCEEDED` khi chỉ mới tạo job. Client có thể poll status hoặc dùng một cơ chế quan sát trạng thái khác.

---

## 13. Repository layout đích

```text
AI-platform-pipeline/
├── README.md
├── mini_research_mlops_project_spec.md  # file này
├── LICENSE
├── .gitignore
├── .dockerignore
├── .env.example                       # chỉ keys/mẫu, không có secret thật
├── pyproject.toml
├── compose.yaml
├── Dockerfile.controller
├── Dockerfile                          # runtime image; tên mặc định Docker sử dụng
├── Makefile                            # tùy chọn
│
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml
│       ├── publish.yml
│       └── deploy-lab.yml
│
├── configs/
│   ├── hello.yaml
│   ├── cpu_train.yaml
│   ├── round01.yaml
│   ├── exp01.yaml
│   └── prompt-v1.yaml
│
├── src/mini_ml/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── api/
│   │   ├── app.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── runs.py
│   │       └── gate.py
│   ├── domain/
│   │   ├── job_spec.py
│   │   ├── state_machine.py
│   │   └── identities.py
│   ├── rounds/
│   │   ├── models.py
│   │   └── service.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   ├── launchers/
│   │   ├── base.py
│   │   ├── docker.py
│   │   └── kubernetes.py
│   ├── storage/
│   │   ├── s3.py
│   │   └── datasets.py
│   ├── sdk/
│   │   ├── tracking.py
│   │   └── checkpoint.py
│   ├── evaluation/
│   │   ├── contracts.py
│   │   ├── dev_eval.py
│   │   └── compare.py
│   ├── gate/
│   │   ├── service.py
│   │   └── budget.py
│   └── release/
│       ├── service.py
│       └── observed_version.py
│
├── examples/
│   ├── hello_job/
│   │   └── run.py
│   ├── cpu_classifier/
│   │   ├── train.py
│   │   └── predict.py
│   ├── step_counter/
│   │   └── run.py
│   ├── mock_prompt/
│   │   ├── run.py
│   │   └── evaluator.py
│   ├── toy_classifier/
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   └── model.py
│   └── threshold_tuner/              # stretch goal
│       └── fit.py
│
├── infra/
│   ├── compose/
│   └── k8s/
│       ├── namespaces.yaml
│       ├── controller-deployment.yaml
│       ├── generic-job.yaml
│       ├── services.yaml
│       └── network-policies.yaml
│
├── scripts/
│   ├── generate_data.py
│   ├── bootstrap_buckets.py
│   ├── smoke_test.sh
│   ├── kill_and_resume_demo.sh
│   ├── deploy_kind.sh
│   └── rollback_kind.sh
│
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/
    ├── architecture.md
    ├── decisions/
    │   ├── ADR-001-job-contract.md
    │   └── ADR-002-checkpoint-storage.md
    ├── networking.md
    ├── security.md
    ├── git-workflow.md
    ├── ci-cd.md
    └── demos.md
```

> **Không tạo toàn bộ cây thư mục trong ngày đầu.** Đây là hình thái repository cuối. Chỉ thêm file khi có một task cụ thể cần nó.

---

## 14. Lộ trình triển khai theo milestone

Mỗi milestone gồm **kiến thức → việc xây → test → Definition of Done (DoD)**. Mỗi feature trong milestone đi qua branch → commit → push → PR → CI → review → merge vào `main` như §15. Không tạo tất cả services/files cùng lúc. Người học tự thao tác và giải thích được kết quả; trợ lý/AI chỉ hướng dẫn, đọc lỗi và review trừ khi được yêu cầu sửa một file cụ thể.

### M0 — Chuẩn hóa môi trường và GitHub repository

**Học:** Linux process/filesystem/env/permissions, `venv`, Git commit/branch/remote, PR/merge, SSH/HTTPS auth, `.gitignore`, CI căn bản.

**Làm:**

- Xác nhận Ubuntu, `python3`, Git, Docker/Compose, quyền truy cập Docker.
- Dùng public GitHub repo `AI-platform-pipeline`; README ghi rõ synthetic-only.
- Tạo `pyproject.toml`, `.venv`, `pytest`, `.gitignore`, `.env.example`.
- Tạo CI workflow đầu tiên: format/lint, unit tests; push branch, mở PR, tự review diff và merge sau khi checks pass.
- Sau khi CI check đã chạy thành công ít nhất một lần, bật branch protection/ruleset cho `main` yêu cầu PR và checks; solo learner không tự khóa mình bằng required reviewer khi không có cộng tác viên.

**DoD:** `python -m pytest` và CI pass; ít nhất một PR đã merge vào `main`; branch mới tách từ `main` cập nhật; repo không chứa secret/data nội bộ; giải thích được `commit`, `push`, PR và merge khác nhau.

### M1 — Docker hello rồi CPU classifier nhỏ

**Học:** Python package/import/entrypoint, Dockerfile image/container, PID/exit code, bind mount/env.

**M1a — Docker foundation (đã bắt đầu bằng `hello`):**

- Validate `configs/hello.yaml` bằng Pydantic, từ chối command/image/timeout sai.
- Chạy command `hello` bằng `docker run` thủ công; đọc container ID, status, logs, exit code và xóa container sau khi quan sát.
- Tạo Dockerfile runtime nhỏ và chạy cùng command từ image tự build; ghi Git commit SHA vào metadata/output.
- Thêm CI build validation cho image; mỗi bước code có branch/PR riêng khi đủ nhỏ để review.

**M1b — CPU training thật trước shared infrastructure:**

- Dùng `scikit-learn` để train `LogisticRegression` cho bài toán nhị phân từ `make_classification` nhỏ (khoảng 300 samples, 8 features). Dữ liệu hoàn toàn tổng hợp; đặt seed cho data generation và train/validation split (ví dụ 80/20, stratified). Chạy CPU trong vài giây; không tải dataset ngoài.
- Viết `examples/cpu_classifier/train.py` nhận `--output-dir` và seed; ghi `metrics.json` (ít nhất validation accuracy, số mẫu, seed, data-generator params và phiên bản scikit-learn) và `model.json` (class labels, coefficients, intercept, feature count) dưới `outputs/` local. Viết `predict.py` đọc model JSON và tạo prediction để chứng minh artifact dùng lại được. JSON chỉ chứa số/metadata; không nạp pickle/joblib do researcher cung cấp vào trusted gate.
- Tạo `configs/cpu_train.yaml` với `experiment`/`execution`, command gọi `python examples/cpu_classifier/train.py --output-dir /outputs`. Cập nhật `Dockerfile` để copy `examples/`, thêm dependency `scikit-learn`, và thêm `outputs/` vào `.gitignore`. Trên host dùng output dir local; trong Docker bind mount output dir để artifact còn sau khi container xóa.
- Thêm unit/smoke test có ý nghĩa: metric nằm trong `[0, 1]`, file artifact tồn tại, `predict.py` đọc model và dự đoán được, lệnh train chạy trên host và Docker. PR CI chạy training nhỏ bằng image mới và kiểm tra artifact/exit code; mỗi feature tiếp tục branch → PR → CI → merge.

**Tests:** M1a valid/invalid config, success/intentional failure exit code; M1b train/validation split không trộn dữ liệu, cùng seed tái tạo input, model artifact đọc lại được. Không assert accuracy đúng một số cố định giữa các phiên bản thư viện.

**DoD:** tự giải thích được image khác container và đọc logs/exit code; CPU classifier train trên host lẫn Docker, xuất metric và model artifact dùng lại được; PR CI pass. `hello` là smoke test rất nhỏ, CPU classifier là workload ML đầu tiên. PyTorch MLP phục vụ bài checkpoint nâng cao ở M5.

### M2 — Shared infrastructure: MLflow + PostgreSQL + SeaweedFS

**Học:** IP/port/DNS/localhost, Docker Compose services/networks/volumes/healthchecks; S3 concepts.

**Làm:**

- Compose chạy PostgreSQL, SeaweedFS, MLflow.
- Tạo buckets qua bootstrap script.
- Upload synthetic input/dataset `v1` (generator params/seed hoặc snapshot) với manifest/checksums.
- Cho CPU classifier M1b đọc đúng dataset v1 qua S3 client, log params/validation metric và `model.json` vào MLflow; không chỉ log một metric giả lập.
- Tách MLflow backend DB và platform DB/schema về mặt logical ownership.
- Thêm CI integration test dùng Compose và service DNS; giữ unit checks nhanh ở PR.

**Tests:** gọi `mlflow` bằng service DNS từ container; kill/remove job container; verify MLflow UI và S3 objects vẫn còn.

**DoD:** tracking không phụ thuộc sự tồn tại của job container; biết chính xác file nào lưu ở Postgres, file nào ở SeaweedFS; integration checks pass trên PR.

### M3 — Controller + CLI + job contract

**Học:** FastAPI/Pydantic, HTTP methods/status, DB transaction, Docker SDK, state machine, idempotency.

**Làm:**

- YAML schema → validated JobSpec.
- `POST /api/v1/runs`, `GET /runs/{id}`, `GET /runs/{id}/logs`.
- `mini-ml submit/status/logs`.
- Platform DB tables `platform_runs`, `run_attempts`.
- `DockerLauncher` tạo container từ trusted runtime và source snapshot/commit được pin.
- Lưu logical run ID vs attempt ID; validate image/source/config/dataset.
- Hoàn thiện platform CI/CD: PR checks → merge `main` → build/publish image theo SHA tới GHCR → deploy vào ephemeral Compose lab → smoke test cùng image digest. M6 thay/mở rộng lab staging bằng kind; cả hai không phải production deployment.

**Tests:** hai lần submit với cùng idempotency key không tạo hai logical runs; submit invalid YAML bị reject trước khi launch; CI smoke test dùng image mới publish.

**DoD:** từ CLI có thể tạo container chạy `hello` hoặc CPU classifier và theo dõi xuyên suốt mà không gõ `docker run` thủ công cho từng experiment; merge vào `main` tạo image digest và lab smoke pass.

**Cảnh báo lab-only:** nếu Controller truy cập Docker socket của host, coi đây là privileged development setup; chỉ bind API local, không đưa lên public internet và không chạy code lạ.

### M4 — Checkpoint/resume + failure recovery

**Học:** ephemeral container, durable object store, signals, retry, atomicity/checksum, resume compatibility.

**Làm:**

- `CheckpointManager.save/load/latest_complete`.
- Trước tiên dùng stateful counter job lưu step/config/input/source hash; CPU classifier M1b là one-shot training, không giả vờ hỗ trợ resume từng step. Khi thêm PyTorch toy ML phải lưu cả model/optimizer/RNG.
- Upload checkpoint theo unique prefix + COMPLETE marker.
- Kết thúc container đột ngột giữa counter job; retry attempt mới.
- Nếu code/config/data không tương thích thì từ chối auto resume.

**Tests:** kill ở step 550, verify resume từ step 400 hoặc checkpoint gần nhất; corrupted/incomplete checkpoint không được chọn.

**DoD:** demo được job recovery từ checkpoint hoàn chỉnh thay vì step 0; MLflow thấy provenance của các attempts. Khi nâng cấp toy ML, chứng minh model/optimizer cũng được restore.

### M5 — Research round, hai workload, evaluation, gate và test release

**Học:** round/run/candidate/champion, generic job contract, dev vs sealed test, leakage, service identity, transaction/concurrency, artifact immutability, approval khác deployment.

**M5a — Research workflow:**

- Tạo `round.yaml` có hypothesis, baseline/champion, max runs/gate calls, outcome; mọi run gắn `round_id` trong DB/MLflow.
- Mở rộng từ CPU classifier M1b sang toy PyTorch MLP CPU trên synthetic data để thực hành weight training/checkpoint; thêm mock prompt/config job trên synthetic document JSON. Mock service deterministic chỉ dùng để kiểm tra workflow, không đánh giá LLM thật.
- Cả hai workload dùng cùng `JobSpec`/submit/status/logs/tracking; không sửa Controller theo từng algorithm.

**M5b — Evaluation và gate:**

- Dev evaluator tạo report so candidate/champion trên cùng dataset/evaluator version, có primary và guard metrics.
- Freeze candidate bằng artifact digest, không chỉ mutable object path.
- Tạo gate DB ledger + budget theo sealed-test version.
- Gate chỉ dùng trusted evaluation implementation, đọc sealed dataset qua restricted credential.
- Kiểm tra budget transaction dưới concurrent requests.
- Test researcher job không có sealed-test credentials và không thể đọc sealed labels trong phạm vi lab.

**M5c — Test release/rollback:**

- Chỉ release candidate PASS tới môi trường test, pin đúng artifact digest, smoke test và đọc observed version.
- Cố ý làm smoke fail; rollback về champion trước, lưu deployment attempt và bằng chứng observed version sau rollback.

**Tests:** round vượt max runs; mock prompt v1/v2 tạo runs riêng; metric guard FAIL; budget hết; concurrent gate submits; artifact digest mismatch; candidate không có dev eval; release không PASS bị từ chối; rollback xác nhận digest cũ đang chạy.

**DoD:** một round đi từ hypothesis đến outcome, có hai workload dùng chung platform; gate không thể gọi unlimited và có audit trail; approved version và observed deployed version được phân biệt; rollback demo thành công.

### M6 — Kubernetes local bằng kind

**Học:** Cluster/Node/Pod/Job/Deployment/Service/namespace/ServiceAccount, Pod networking, Kubernetes API, NetworkPolicy.

**Làm:**

- Tạo kind cluster local, verify `kubectl get nodes`.
- Tạo `mlops-system`, `mlops-jobs`, `mlops-gate` namespaces.
- Tạo một `batch/v1 Job` chạy CPU classifier và stateful counter job; giữ `hello` làm diagnostic smoke, sau đó thử PyTorch toy ML CPU.
- Implement `KubernetesLauncher` từ cùng JobSpec.
- Cấu hình endpoints của MLflow/SeaweedFS reachable **từ cluster**, không giả định Compose DNS tự xuất hiện trong kind.
- Thử Job fail/retry và checkpoint resume.
- Test NetworkPolicy **chỉ khi đã chọn CNI có policy enforcement**.

**Tests:** `kubectl get jobs/pods`, logs, resource requests, Service DNS, Job retry; so sánh cùng config chạy Docker và K8s; lab deployment/smoke qua CI dùng immutable image digest.

**DoD:** thay `execution.backend` từ `docker` sang `kubernetes` mà không sửa workload code; cùng lifecycle/tracking/checkpoint contract được giữ.

### M7 — Polish cho GitHub portfolio (tùy chọn)

- Architecture diagram rõ ràng, ảnh MLflow UI, demo GIF/video tùy chọn.
- Script `make demo`, `make test`, `make infra-up`, `make infra-down`.
- ADR về lựa chọn design (tại sao external checkpoint, tại sao JobLauncher abstraction).
- GitHub Releases/Tags `v0.1.0`, `v0.2.0`; changelog.
- Security section công khai giới hạn của local demo.
- CI/CD dashboard/badges, release digest, PR history và test release/rollback evidence rõ ràng; không commit `.env`/tokens.

### Mốc tự đánh giá năng lực

- **Sau M0–M3:** có thể tự đọc một PR, chạy CI, giải thích source/config/image đi vào Docker job thế nào, debug status/log/exit code và truy vết MLflow/S3. Đây là nền tảng để nhận các task nhỏ có review; không cần chờ hoàn tất toàn bộ project mới bắt đầu công việc thực tế.
- **Sau M4–M6:** có thể giải thích retry/resume, round/candidate/champion, evaluation/gate/release và chạy cùng JobSpec trên kind. Đây là năng lực lab, chưa chứng minh một hệ thống production đã được harden.
- Tự đánh giá bằng demo và failure cases cụ thể, không quy đổi milestone thành điểm số hay cam kết sẵn sàng cho mọi nhiệm vụ của một tổ chức.

---

## 15. Git workflow, CI/CD và các lệnh khởi động

### 15.1. Kiểm tra máy

```bash
cat /etc/os-release
python3 --version
git --version
docker --version
docker compose version
```

Nếu Docker chưa có hoặc user không có quyền, hãy cài/cấu hình theo Docker documentation cho Ubuntu; không chạy các lệnh thay đổi group/daemon một cách mù quáng trên máy công ty.

### 15.2. Dùng repository hiện tại

```bash
git clone https://github.com/Helooeverybody/AI-platform-pipeline.git
cd AI-platform-pipeline
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Nếu repo đã được clone, chỉ `cd` vào thư mục hiện tại; không chạy lại `git init`/`git clone` bên trong thư mục không rỗng. Chỉ cài dependencies khi milestone dùng thật. Pin dependencies và lưu lock/constraints phù hợp trước khi yêu cầu tái lập CI/release.

### 15.3. Mỗi feature: branch → commit → push → PR → CI → merge

Trước khi bắt đầu feature mới, đảm bảo feature trước đã merge, working tree sạch và `main` local cập nhật:

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/hello-docker-job
```

Tên branch theo một thay đổi review được: `feature/...`, `fix/...`, `docs/...`; không gom nhiều milestone vào một PR. Người học tự viết code và chạy test, xem `git diff` để hiểu từng dòng thay đổi. Khi sẵn sàng:

```bash
python -m pytest -q
git diff --check
git add path/to/changed-file
git diff --cached
git commit -m "feat: add hello Docker job"
git push -u origin feature/hello-docker-job
```

Thay `path/to/changed-file` bằng các file thật; stage có chọn lọc để tránh commit `.env`, dữ liệu hoặc file sinh tự động. Trên GitHub mở PR **base `main` ← compare feature branch**, mô tả mục tiêu, cách test, bằng chứng kết quả và giới hạn; đọc lại Files changed. Sửa lỗi trên cùng branch và push lại. Chỉ merge khi required checks pass và review xong. Sau merge:

```bash
git switch main
git pull --ff-only origin main
git branch -d feature/hello-docker-job
```

Chỉ xóa branch local sau khi đã merge; xóa remote branch bằng nút GitHub hoặc `git push origin --delete ...` nếu muốn dọn dẹp. Feature kế tiếp lại tách từ `main` mới. Nếu feature trước chưa merge, không vô tình tạo branch mới từ branch cũ khiến PR chứa cả hai feature.

**Thiết lập bảo vệ `main`:** sau khi CI workflow đã chạy thành công và có tên check ổn định, bật GitHub branch protection/ruleset yêu cầu PR và status checks, chặn force push/delete. Solo repo nên tự review diff; không đặt required approval từ người khác nếu chưa có collaborator vì sẽ tự chặn merge. Mục tiêu là tự thực hành quy trình, không tự duyệt chất lượng bằng cách bỏ qua checks.

### 15.4. Docker workflow từ hello job đến CPU classifier

```bash
docker run --name mini-ml-hello python:3.12-slim python -c "print('hello from a job')"
docker ps -a --filter name=mini-ml-hello
docker logs mini-ml-hello
docker inspect --format '{{.State.ExitCode}}' mini-ml-hello
docker rm mini-ml-hello

# Khi đã viết Dockerfile ở thư mục gốc:
docker build --build-arg "GIT_SHA=$(git rev-parse HEAD)" -t mini-ml-runtime:dev .
docker run --rm mini-ml-runtime:dev
docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' mini-ml-runtime:dev
```

Lệnh manual đầu không cần Dockerfile; nếu image chưa có, Docker sẽ tải từ registry. Giữ container lại để inspect trước khi `docker rm`. Image tự build dùng `CMD` trong Dockerfile, còn label `org.opencontainers.image.revision` ghi commit SHA được truyền lúc build. Nếu source/Dockerfile chưa commit, SHA này chưa đại diện đầy đủ cho nội dung image; commit rồi build lại. Khi đã build image riêng, hiểu vì sao sửa source trên host không tự sửa image cũ.

### 15.5. Compose workflow khi tới M2

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs -f mlflow
```

- `docker compose down`: dừng và xóa containers/networks thuộc project, thường giữ named volumes.
- **Cẩn thận với `docker compose down -v`**: xóa cả named volumes được quản lý bởi Compose project, có thể mất PostgreSQL/SeaweedFS data local.

**Không giả định `compose.yaml` đã tồn tại ở M0:** các lệnh này chỉ dùng sau khi triển khai M2.

### 15.6. CI/CD platform theo từng milestone

**CI trên pull request** (`.github/workflows/ci.yml`):

1. M0: checkout, setup Python theo phiên bản project, cài dependencies, `ruff format --check`, `ruff check`, `pytest` unit. Thêm Ruff vào dev dependencies khi workflow được tạo.
2. M1a: build Docker image, chạy hello job success/failure và kiểm tra exit code. M1b: chạy CPU classifier nhỏ trong image, kiểm tra metric JSON, model JSON/prediction và artifact nằm ngoài container; giữ PR job đủ nhanh.
3. M2–M3: dùng Compose/service containers cho Postgres/MLflow/S3 integration; CPU classifier đọc dataset version v1 và ghi params/metric/model artifact vào MLflow; chạy smoke từ CLI submit tới trạng thái cuối và artifact. Đặt timeout và dọn volumes/containers của CI run.
4. M5–M6: thêm gate concurrency, release/rollback và kind checks có chọn lọc; giữ PR checks đủ nhanh, dời demo E2E dài sang workflow riêng nếu cần.

CI chạy trên PR vào `main` và push lên `main`. Check thất bại phải chặn merge; tên check phải rõ và không trùng giữa workflows. Không chạy deploy/publish bằng credentials trên PR từ code chưa review. Review `git diff`, test output và CI logs trước merge.

**Delivery sau merge** (`publish.yml`, chỉ khi M3 có image dùng được):

1. Trigger trên push vào `main` hoặc release tag; build từ exact commit đã merge, chạy lại checks tối thiểu và tạo image cho Controller/runtime.
2. Push GHCR với tag `sha-<commit>` (và tag semver khi release), ghi full image digest trong job output/release record. Runtime dùng digest để pin; không dựa vào tag mutable `latest` để chứng minh reproducibility.
3. `deploy-lab.yml` dùng chính digest vừa publish, deploy vào **ephemeral Compose staging** trên GitHub-hosted runner ở M3; M6 thêm **ephemeral kind staging**. Smoke test API/job, đọc observed image digest/version rồi lưu log/bằng chứng. Lab staging chỉ tồn tại trong thời gian workflow; đây không phải production environment bền vững.
4. Trong ephemeral lab, deploy một known-good digest trước, rồi thử image/job lỗi có kiểm soát, rollback về known-good digest và kiểm tra observed version. Nếu sau này có staging riêng thật, dùng GitHub Environment để giới hạn branch, secrets và approval trước deployment.

**Bảo mật workflow:** `permissions: contents: read` mặc định; chỉ publish job cần `packages: write` với `GITHUB_TOKEN`. Pin third-party actions theo full commit SHA hoặc workflow dependency lock khi hoàn thiện workflow; tránh secrets trong logs/PR, không dùng self-hosted runner có quyền nội bộ cho untrusted PR. Platform image CD ở đây tách khỏi candidate gate/release ở M5.

**Chuyển kiến thức sang CI khác:** GitHub workflow/job/runner/artifact/environment tương ứng về ý tưởng với pipeline/stage/runner/artifact/environment của GitLab CI, nhưng cú pháp và quyền truy cập khác nhau. Chỉ học mapping này bằng ví dụ public; không đưa cấu hình công ty vào repo.

**DoD CI/CD:** một PR lỗi lint/test không merge được; PR pass được merge; merge tạo image digest truy xuất được; lab deploy dùng đúng digest; smoke thất bại được phát hiện và rollback demo xác nhận phiên bản cũ. CI/CD được triển khai dần, không đòi đủ tất cả jobs ở M0.

---

## 16. Chiến lược kiểm thử

### Unit tests — chạy rất nhanh, không cần Docker

- Parse/validate YAML (missing fields, command invalid, negative resources).
- CPU classifier: synthetic data/split cố định theo seed, metric hữu hạn trong `[0, 1]`, JSON model được `predict.py` đọc lại; không assert một giá trị accuracy tuyệt đối qua nhiều phiên bản thư viện.
- Config digest ổn định khi canonicalize cùng một config.
- State machine không cho phép transition trái luật.
- Checkpoint manifest compatibility logic.
- Round max_runs/max_gate_calls và outcome transitions.
- Evaluation contract từ chối candidate/champion khác dataset/evaluator version; guard metric FAIL dù primary cải thiện.
- Gate decision logic không truy cập sealed test thật.
- Release từ candidate chưa PASS bị từ chối; approved digest và observed digest được lưu riêng.

### Integration tests — cần Compose

- Controller ↔ PostgreSQL CRUD/transactions.
- Generic job ↔ MLflow Tracking Server.
- S3 client ↔ SeaweedFS upload/list/download/checksum.
- JobLauncher ↔ Docker Engine; logs/exit codes.
- Atomic gate budget với nhiều concurrent workers.
- Test deployment đọc observed version và rollback về digest trước sau smoke fail.

### E2E tests — smoke test toàn đường

1. Bootstrap synthetic input/dataset v1 và mở round có hypothesis/baseline/budget.
2. Submit CPU classifier, rồi mock prompt/PyTorch toy ML experiment qua CLI; `hello` vẫn là diagnostic smoke, mọi research run có `round_id`.
3. Poll `SUCCEEDED` và MLflow params/metrics; verify output artifact, source/image/config/data digests.
4. Cố tình kill stateful job, tạo attempt mới và resume từ COMPLETE checkpoint.
5. Freeze candidate, so với champion trên cùng dev evaluation contract, submit gate.
6. Verify PASS/FAIL, ledger và budget, ghi round outcome.
7. Test release candidate PASS, smoke/observed digest; gây lỗi và rollback về champion trước.
8. Chạy cùng generic JobSpec tương đương trên kind (M6).
9. Chứng minh PR CI, merge `main`, image digest ở GHCR và lab deploy/smoke/rollback.

### Failure injection tests — bắt buộc có ít nhất 4

| Failure | Kết quả đúng cần chứng minh |
|---|---|
| Kill counter/toy training container | Attempt mới có thể resume từ COMPLETE checkpoint |
| Checkpoint upload dở dang | Không chọn checkpoint thiếu COMPLETE/checksum sai |
| Submit HTTP request 2 lần | Không tạo logical run trùng với cùng idempotency key |
| Concurrent gate requests ở budget cuối | Không cấp vượt quota |
| MLflow/SeaweedFS unavailable | Ghi lỗi rõ ràng, không báo job success giả |
| Researcher credential truy cập sealed bucket | Storage API từ chối truy cập |
| Candidate chính tốt hơn nhưng guard metric xấu | Evaluation/gate FAIL theo policy đã chốt trước |
| Deploy nhầm digest hoặc smoke fail | Không ghi deployed success; rollback và verify observed digest cũ |
| PR có test fail hoặc image build fail | Required checks chặn merge vào `main` |

---

## 17. Security checklist khi public GitHub

```text
[ ] Chỉ dùng synthetic/public-permitted data và code tự viết.
[ ] Không copy tài liệu, secrets, config, IP/hostname nội bộ công ty.
[ ] .env bị ignore; .env.example không có credential thật.
[ ] Không commit private SSH keys, cloud tokens, GitHub PATs.
[ ] CI secrets/environment secrets được cấu hình bằng GitHub Actions khi cần; PR untrusted không nhận publish/deploy credentials.
[ ] Workflow dùng quyền `GITHUB_TOKEN` tối thiểu; publish job mới có `packages: write`; actions được pin/lock theo mức hoàn thiện.
[ ] `main` yêu cầu PR và CI checks; không force push/bypass tùy tiện.
[ ] Container không chạy privileged và không mount Docker socket vào researcher workload.
[ ] Controller có Docker socket chỉ trong local lab; API không public.
[ ] Dataset/candidate artifacts được checksum và version.
[ ] Sealed-test credential không truyền vào researcher job, gồm mock prompt và toy train.
[ ] Gate không chạy arbitrary candidate code với privileged credentials.
[ ] Khi dùng K8s: RBAC/ServiceAccount tối thiểu; Pod security;
    NetworkPolicy chỉ được đánh dấu pass khi CNI thực sự enforce.
[ ] README ghi rõ: demo kiến trúc, KHÔNG phải hardened production platform.
[ ] Tất cả round/prompt/evaluation/release examples trong repo dùng dữ liệu tổng hợp; không chép quy trình hoặc benchmark nội bộ công ty.
```

Nếu đã lỡ commit credential, xóa file ở commit mới **không đủ** để bảo đảm credential được bảo vệ: cần rotate/revoke ngay và xử lý lịch sử repository khi phù hợp.

---

## 18. Những bài học kiến trúc cần trả lời được sau mỗi milestone

1. Linux process, Docker container, Kubernetes Pod và Kubernetes Job khác nhau thế nào?
2. Một file source ở laptop đi đến job process trong Docker hoặc Kubernetes bằng cách nào?
3. Ai có trách nhiệm checkout Git commit? Ai có trách nhiệm tạo container?
4. Vì sao Git branch name không đủ tái lập experiment?
5. Khi gọi `localhost:5000` trong container, nó trỏ tới đâu?
6. Vì sao MLflow metadata và artifact có thể ở hai storage khác nhau?
7. Nếu job container biến mất, file nào còn và tại sao?
8. `retry` khác `resume` thế nào?
9. Nếu Pod mới được schedule tới Node khác, checkpoint cũ còn truy cập được bằng cách nào?
10. Vì sao MLOps Controller phải lưu run state trong DB chứ không trong Python dict?
11. Vì sao training code không nên giữ gate credential?
12. NetworkPolicy có thể chặn quyền đọc bucket S3 riêng lẻ trên cùng endpoint không?
13. Hai gate requests đồng thời có thể vượt budget như thế nào và cách tránh?
14. Với `runtime image + Git commit`, làm thế nào xác định đúng code chạy bên trong container?
15. Vì sao Kubernetes Job failure/retry không tự động khôi phục optimizer state?
16. Nếu thêm một model threshold tuner, phần nào trong platform cần sửa, phần nào không?
17. Làm sao chứng minh một candidate đã PASS gate đúng là artifact đang được sử dụng?
18. Những thành phần nào platform của bạn thực sự viết, những thành phần nào do Docker/K8s/MLflow cung cấp?
19. Branch, PR, CI check, merge vào `main` và CD image digest khác nhau ở điểm nào?
20. Một round khác một run ra sao; vì sao MLflow run ID không thay thế round budget/outcome?
21. Vì sao mock prompt workflow giúp kiểm tra generic JobSpec nhưng không chứng minh chất lượng một LLM thật?
22. Candidate tăng primary metric nhưng vi phạm guard metric thì quyết định gì, trên dữ liệu/evaluator version nào?
23. Candidate đã PASS gate khác phiên bản thực sự đang deploy ra sao; quan sát và rollback bằng chứng nào?
24. Vì sao platform image release và candidate model release cần hai lifecycle riêng?

**Tiêu chí học sâu:** với mỗi câu, vẽ được execution flow; gọi tên tài nguyên (process/container/Pod/DB/object key) và giải thích ít nhất một failure mode.

---

## 19. Các quyết định kỹ thuật nên ghi thành ADR

Viết ngắn gọn trong `docs/decisions/` sau khi bạn thực sự gặp vấn đề:

- **ADR-001:** Vì sao interface chính là generic `JobSpec`/command, không phải một universal `BaseTrainer` bắt buộc.
- **ADR-002:** Vì sao checkpoint ở object storage, không chỉ trong container writable layer.
- **ADR-003:** Vì sao `run_id` khác `attempt_id` và K8s Job name.
- **ADR-004:** Vì sao Controller API stateless nhưng PostgreSQL stateful.
- **ADR-005:** Vì sao gate là trusted execution riêng, không chạy trong training Pod.
- **ADR-006:** Vì sao local dùng Compose, còn Kubernetes launcher chỉ thêm ở milestone cuối.
- **ADR-007:** Vì sao round state/budget ở platform DB, còn MLflow chỉ là tracking/linkage.
- **ADR-008:** Vì sao evaluation report pin candidate/champion/input/scorer versions và guard metrics.
- **ADR-009:** Vì sao approved candidate và observed deployed artifact cần hai record riêng.
- **ADR-010:** Vì sao platform CI/CD publish theo commit/image digest và không dùng mutable tag để chứng minh release.

Mỗi ADR có cấu trúc: `Context → Decision → Alternatives → Consequences`.

---

## 20. Hướng dẫn README GitHub sau khi hoàn thành

README nên có:

1. **Một câu mô tả rõ giá trị**: reproducible ML experiment execution & recovery.
2. **Architecture diagram** (source → control plane → jobs → tracking/storage → gate).
3. **Quick start** trên Ubuntu, các prerequisites và lệnh chạy.
4. **Demo commands** `mini-ml submit/status/logs` và MLflow UI.
5. **Checkpoint failure demo** kèm logs trước/sau.
6. **What is implemented / not implemented** minh bạch.
7. **Design decisions** và trade-offs.
8. **Screenshots/GIF** hữu ích; không có dữ liệu cá nhân/nội bộ.
9. **Tests/CI badge** và cách đóng góp.
10. **Git workflow**: branch naming, PR template, required checks, merge và cách đồng bộ `main`.
11. **CI/CD evidence**: commit → GHCR digest → lab deployment/smoke/rollback; phân biệt platform release và candidate release.
12. **Research demo**: round, mock prompt và toy ML, candidate/champion report, gate, test release/rollback.
13. **Security disclaimer**: không expose lab controller public; không coi isolation local là production-grade.

**Giá trị portfolio** không nằm ở việc có nhiều logo công nghệ nhất, mà ở chỗ bạn chứng minh được một luồng MLOps chạy từ đầu đến cuối và tự xử lý các failure modes quan trọng.

---

## 21. Nguồn học chính thức (tham khảo từng phần khi cần)

- GitHub Docs — Git & GitHub basics: https://docs.github.com/
- GitHub Actions: https://docs.github.com/en/actions
- GitHub protected branches/rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub Actions secure use: https://docs.github.com/en/actions/reference/security/secure-use
- GitHub Packages/GHCR from Actions: https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions
- GitHub Environments: https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments
- Python packaging: https://packaging.python.org/
- FastAPI: https://fastapi.tiangolo.com/
- Docker getting started: https://docs.docker.com/get-started/
- Docker Compose: https://docs.docker.com/compose/
- scikit-learn synthetic classification: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_classification.html
- scikit-learn train/validation split: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html
- scikit-learn LogisticRegression: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- scikit-learn model persistence và rủi ro pickle/joblib: https://scikit-learn.org/stable/model_persistence.html
- MLflow Tracking: https://mlflow.org/docs/latest/ml/tracking/
- PostgreSQL: https://www.postgresql.org/docs/
- SeaweedFS: https://github.com/seaweedfs/seaweedfs
- PyTorch saving/loading: https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html
- Kubernetes concepts: https://kubernetes.io/docs/concepts/
- Kubernetes Jobs: https://kubernetes.io/docs/concepts/workloads/controllers/job/
- Kubernetes NetworkPolicy: https://kubernetes.io/docs/concepts/services-networking/network-policies/
- kind: https://kind.sigs.k8s.io/

---

## 22. Việc đầu tiên bạn nên làm ngay

**M0 và bài Docker `hello` đã đặt nền. Bây giờ hoàn tất validation M1a rồi train CPU classifier ở M1b, trước khi dựng PostgreSQL/SeaweedFS/Kubernetes.** CPU classifier là workload ML thật đầu tiên; PyTorch MLP/checkpoint nâng cao vẫn ở M5.

```text
Step 1. Dùng repo public `AI-platform-pipeline`, tạo `.venv` và project Python tối thiểu.
Step 2. Tạo feature branch từ `main`, viết `configs/hello.yaml` và Pydantic validation, chạy test.
Step 3. Push branch, mở PR, xem diff; tạo CI format/lint/unit checks trước khi yêu cầu checks ở branch protection.
Step 4. Merge PR sau khi CI pass, pull `main`, tạo branch mới cho Docker hello job.
Step 5. Chạy hello job thủ công bằng Docker; inspect logs/status/exit code, rồi viết Dockerfile runtime.
Step 6. Thêm test success/failure và CI Docker build; push PR và merge khi pass.
Step 7. Trên branch `feature/hello-config-validation`, hoàn tất test và validator cho image/command/timeout; PR/CI/merge, rồi cập nhật `main`.
Step 8. Tạo branch `feature/cpu-classifier`; thêm scikit-learn và job train LogisticRegression trên synthetic data với seed/split cố định. Chạy host, xuất `metrics.json`/`model.json`, thử `predict.py` đọc lại artifact.
Step 9. Thêm `configs/cpu_train.yaml`, copy `examples/` vào Dockerfile, bind mount output dir; train cùng workload trong container và giữ artifact sau khi container kết thúc.
Step 10. Thêm test/CI CPU smoke, cập nhật README và `.gitignore`; push PR, yêu cầu check mới trong ruleset sau khi nó đã chạy, merge khi pass, pull `main`.
Step 11. Sang M2: Compose + MLflow + SeaweedFS; dùng CPU classifier ghi metric/model artifact và đọc dataset v1 đã version hóa.
```

Khi M1b hoàn tất, bắt đầu **M2: Compose + MLflow + SeaweedFS**. PyTorch training và mock prompt được thêm sau khi control plane cơ bản hoạt động ở M3; counter job ở M4 dùng để học checkpoint/resume trước.

### Câu tuyên bố hoàn thành toàn project

> Tôi có thể nhận một experiment config, đóng băng source/data/runtime identity, tạo generic job trong Docker hoặc Kubernetes, theo dõi run và round, resume stateful job từ checkpoint, so sánh candidate với champion, dùng trusted gate có budget, release/rollback trong lab và giải thích được Git PR → CI → merge → image digest → deployment cùng các security boundaries của hệ thống.

---

**Ghi chú cuối:** đây là **project description + implementation roadmap**, không phải một repository đã code sẵn. Mỗi feature nên được người học tự triển khai, kiểm thử, push PR và merge để hiểu *vì sao* hệ thống hoạt động. Trợ lý chỉ sửa code/tài liệu khi được yêu cầu rõ cho phần đó.
