# MINI RESEARCH MLOPS PLATFORM

> **Project specification / tài liệu định hướng triển khai**  
> Phiên bản: `v1.0` — 04/11/2026  
> Đối tượng: người mới học backend, Linux, networking, Docker và Kubernetes; đã có kiến thức cơ bản về Python/ML.  
> Môi trường chính: **Ubuntu 24.04, laptop CPU-only, Docker, GitHub**.  
> Mục tiêu: dự án **cá nhân, public trên GitHub**, dùng **dữ liệu tổng hợp**, không sử dụng tài nguyên hoặc dữ liệu nội bộ của công ty.

---

## 0. Đọc phần này trước: project này thực sự là gì?

**Mini Research MLOps Platform** là một nền tảng nhỏ mô phỏng cách nhóm nghiên cứu ML làm việc với hệ thống MLOps dùng chung:

1. Researcher viết code huấn luyện và một file YAML mô tả experiment.
2. Researcher chạy CLI `mini-ml submit configs/exp01.yaml`.
3. Platform kiểm tra config, gắn định danh cho run và chuẩn bị môi trường thực thi.
4. Platform khởi chạy một **job biệt lập** trong Docker (giai đoạn đầu), sau đó có thể dùng Kubernetes Job.
5. Job tải **đúng phiên bản dataset** từ object storage, train model, log params/metrics vào MLflow.
6. Job định kỳ lưu **checkpoint đầy đủ**, cho phép tiếp tục khi job bị gián đoạn.
7. Candidate được đánh giá trên development set, rồi yêu cầu **trusted gate** kiểm tra bằng sealed test có budget.
8. Kết quả và bằng chứng reproducibility có thể truy xuất dù job/container đã bị xóa.

**Điểm cốt lõi:** bạn đang tạo một **MLOps control plane thu nhỏ** chứ không phải xây model AI phức tạp. Model nên đơn giản để bạn dành thời gian học *software engineering, execution, storage, reliability, security và observability*.

### Kết quả cuối cùng cần demo được

```text
GitHub repository / exact commit
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
     Training process (CPU-only)
       |       |             |
       v       v             v
    MLflow   Dataset       Checkpoint
       |       |             |
       v       +------ SeaweedFS S3 ------+
  PostgreSQL
       |
       v
  Candidate --> Dev evaluation --> Trusted gate --> PASS/FAIL
```

> Lưu ý: sơ đồ biểu diễn **logical architecture**, không đồng nghĩa mỗi ô cần một server vật lý. MLflow dùng PostgreSQL làm backend store; file artifacts có thể lưu vào SeaweedFS. Job state của platform nên nằm ở schema hoặc database riêng với MLflow metadata.

---

## 1. Mục tiêu học tập

Sau khi hoàn thành, bạn phải có thể tự giải thích và chứng minh bằng code:

| Lĩnh vực | Bạn phải chứng minh được |
|---|---|
| Linux | `train.py` trở thành Python process ra sao; PID, exit code, signal, environment và file path hoạt động thế nào |
| Networking | Vì sao `localhost` khác giữa host/container/Pod; dịch vụ gọi nhau bằng IP, port, DNS và HTTP như thế nào |
| Python engineering | Module, package, `pyproject.toml`, entrypoint, `venv`, dependencies, CLI và reusable SDK |
| Git/GitHub | Branch, PR, commit SHA, tag, CI; tái chạy code của một commit cụ thể |
| Docker | Phân biệt Dockerfile/image/container; writable layer, bind mount, volume, runtime và source code |
| Docker Compose | Khởi tạo nhiều services, private networks, service DNS, healthchecks, volumes, env/secrets |
| Backend/API | FastAPI nhận request, validation, DB transaction, job state machine và idempotency |
| MLOps | Dataset version, experiment tracking, artifacts, evaluation, reproducibility và gate |
| Reliability | Retry khác resume, checkpoint hoàn chỉnh, run/attempt identity và recovery |
| Kubernetes | Pod/Job/Deployment/Service/namespace, ServiceAccount, Service DNS, NetworkPolicy; **không cần GPU thật** |
| Security | Tách trusted gate khỏi researcher code, least privilege, tránh lộ secrets, network policy khác storage permission |

### Nguyên tắc thiết kế xuyên suốt

- **Simple model, serious infrastructure**: dùng model nhỏ và dữ liệu giả, nhưng không bỏ qua việc lưu phiên bản và xử lý failure.
- **Run identity khác execution attempt**: cùng một logical training run có thể có nhiều lần chạy lại.
- **Dữ liệu bền vững nằm ngoài container**: job có thể biến mất, metrics/checkpoints vẫn còn.
- **Một job contract, nhiều model**: platform chạy *một command được khai báo*, không hard-code `DMSTrainer` hay một kiểu algorithm cụ thể.
- **Trusted code tách khỏi researcher code**: đặc biệt khi truy cập sealed test, secrets hoặc quyền release.
- **Làm xong từng milestone rồi mới mở rộng**: không xây Kubernetes/Rancher/frontend ở ngày đầu.

---

## 2. Phạm vi: bắt buộc, tùy chọn và không làm

### 2.1. MVP bắt buộc

1. Một model ML nhỏ (ví dụ PyTorch MLP trên synthetic classification data) train CPU.
2. Public GitHub repo có README, tests và GitHub Actions.
3. Docker image cho training; Docker Compose cho shared infrastructure.
4. PostgreSQL, MLflow Tracking Server, SeaweedFS S3-compatible object storage.
5. `mini-ml submit`, `mini-ml status`, `mini-ml logs` ở mức tối thiểu.
6. Experiment/job manifest dạng YAML được validate bằng Pydantic.
7. Ghi full Git commit, runtime image identifier/digest nếu có, config hash và dataset version vào run metadata.
8. Hai trạng thái độc lập: job lifecycle của platform và MLflow run tracking.
9. Checkpoint/resume qua object storage; chủ động kill container để kiểm chứng.
10. Evaluation và **trusted gate** dùng sealed-test budget bền vững trong PostgreSQL.
11. Một smoke test chạy xuyên luồng từ submit tới gate.
12. Một local Kubernetes Job hoạt động bằng **kind** ở milestone cuối.

### 2.2. Tùy chọn — chỉ thêm khi MVP ổn

- Một model loại khác, ví dụ **threshold tuner** không có neural-network training loop, để chứng minh generic job contract.
- GitHub Actions build/push image tới GHCR.
- FastAPI authentication đơn giản cho API local.
- Prometheus/Grafana, OpenTelemetry, structured logs.
- Simple release manifest và rollback mock.
- Retry queue / quota / concurrency limits.
- Model registry dùng MLflow.
- Native sidecar hoặc init container nếu có nhu cầu rõ ràng.

### 2.3. Không làm trong phiên bản luyện tập

- Distributed multi-node GPU training, L40S thực, GPU scheduling nâng cao, MIG.
- Public production inference endpoint hoặc vLLM serving cluster quy mô lớn.
- Multi-cluster Rancher management, tự dựng Kubernetes control plane production.
- Enterprise SSO/IAM, đầy đủ compliance/security audit.
- Frontend dashboard viết từ đầu (MLflow UI là đủ).
- Tự viết CNI, storage engine, model registry thay thế MLflow.
- Thử bất kỳ code/dataset/credential nội bộ nào lên GitHub cá nhân.

---

## 3. Kịch bản người dùng và Definition of Success

### Persona A — Researcher

- Có một repo/code train như `examples/toy_classifier/train.py`.
- Tạo `configs/exp01.yaml`.
- Submit; không cần SSH vào job container để train thủ công.
- Theo dõi trạng thái, log, metric, artifact và checkpoint.
- Có thể yêu cầu dev evaluation hoặc submit candidate tới gate.

### Persona B — Platform Maintainer (bạn)

- Thay implementation `DockerLauncher` bằng `KubernetesLauncher` mà không sửa training algorithm.
- Biết request nào sinh ra Docker container/K8s Job nào.
- Debug thất bại từ log, status, exit code, metadata.
- Truy xuất exact code/data/runtime/config của một experiment.
- Hạn chế researcher không truy cập sealed test và privileged credentials.

### Demo cuối được xem là **PASS** nếu

```text
[ ] Checkout GitHub repository từ máy mới, cấu hình local, chạy test được.
[ ] docker compose up khởi động PostgreSQL + MLflow + SeaweedFS.
[ ] CLI submit tạo run_id, lưu DB, khởi chạy Docker job.
[ ] Training đọc dataset v1, ghi MLflow metric và artifact.
[ ] Xóa training container, metrics/artifact vẫn còn.
[ ] Kill training giữa chừng và resume từ checkpoint đầy đủ gần nhất.
[ ] Candidate dev evaluation lưu metric theo evaluation contract.
[ ] Gate cho PASS/FAIL, ghi budget và không cho vượt budget khi submit đồng thời.
[ ] Training identity không đọc được sealed labels (trong phạm vi lab đã kiểm thử).
[ ] Chạy cùng toy training command bằng Kubernetes Job trên kind.
[ ] GitHub Actions test thành công trên pull request/push.
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
| ML model | PyTorch MLP **CPU-only** | Đủ để thử optimizer/checkpoint và metrics |
| Docker | Docker Engine + Dockerfile | Reproducible runtime và job containers |
| Local services | Docker Compose | Start/stop infra và networking |
| CI | GitHub Actions | pytest, lint, build validation |
| Kubernetes lab | kind + kubectl | Chạy Kubernetes trong Docker, không cần cluster công ty |
| K8s Python API | `kubernetes` Python client | Tạo/quan sát `batch/v1 Job` |
| Tests | pytest | Unit/integration/e2e |

**Chú ý:** không nhất thiết cài ngay mọi công cụ. Mỗi milestone chỉ bổ sung dependency khi sử dụng thật.

### Phân biệt 5 thành phần hay bị nhầm

- **GitHub** = lưu code + version + CI; `git push` **không tự** tạo training process.
- **Docker image** = environment và có thể chứa app code; **container** = thực thể đang chạy.
- **Docker Compose** = điều phối services trên Docker Engine target; **Kubernetes** = cluster-level workload orchestration.
- **MLflow** = tracking API/metadata/artifacts; **PostgreSQL** = backend data; **SeaweedFS** = object storage.
- **MLOps Controller** (do bạn viết) = quyết định job nào cần chạy; **K8s Control Plane** (có sẵn) = quyết định workload chạy ở đâu.

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
- Không thực thi `train.py` trực tiếp bên trong web API process.

**JobLauncher (`mini_ml.launchers`)**
- Interface: `submit(job_spec) -> execution_ref`, `get_status(ref)`, `get_logs(ref)`, `cancel(ref)`.
- `DockerLauncher`: khởi tạo container với env/volume/resource config phù hợp.
- `KubernetesLauncher`: tạo K8s Job/Pod template.
- Launcher nhận **JobSpec** có validation, không tự quyết định model loss/metric.

**Research workload (`examples/...`)**
- Tự implement train/evaluate logic; dùng common SDK cho tracking/storage/checkpoint.
- Không biết platform chạy bằng Docker hay Kubernetes.

**MLflow**
- Lưu params, metrics, tags, experiments, model artifacts.
- Backend store PostgreSQL và artifact store SeaweedFS theo cấu hình server.

**Platform PostgreSQL DB**
- Lưu business state: logical run, execution attempts, dataset manifests, gate attempts/budget.
- Dùng DB/schema logic riêng với MLflow backend để không trộn ownership.

**SeaweedFS**
- S3-compatible buckets cho dataset, checkpoints, MLflow artifacts, sealed-test data.
- Có policies/credentials riêng; **NetworkPolicy chỉ lọc network, không kiểm soát bucket ACL**.

**Trusted Gate**
- Chạy evaluator thuộc code đã review/trust; không đưa sealed labels hay gate credentials cho researcher job.
- Ghi PASS/FAIL/metrics và tiêu hao budget qua DB transaction.
- Candidate được gắn artifact digest và không thể bị thay âm thầm giữa các lần check.

### 5.2. Hai loại workload

**Long-running services**: Controller API, MLflow, PostgreSQL, SeaweedFS (chạy/được quản lý bởi Compose hoặc deploy riêng).  
**Finite jobs**: train, dev evaluation, gate evaluation (tạo theo request, kết thúc rồi biến mất).

Đừng đặt PostgreSQL/MLflow vào cùng một Pod/container với mỗi training run.

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
  |   trainer --> mlflow endpoint                        |
  |   trainer --> SeaweedFS dataset/checkpoint endpoint  |
  +-----------------------------------------------------+

  Trusted gate có identity/credentials riêng, không đồng nhất với trainer.
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
- **Không** truyền privileged Docker socket, database admin password, sealed-test credentials vào training container.
- Local demo dùng Docker daemon/socket để khởi tạo job chỉ là giải pháp **lab-only**, vì quyền truy cập Docker socket có khả năng kiểm soát host rất cao. Không expose Controller như một public service khi đang dùng cách này.
- Training code tùy ý có thể độc hại: Docker thông thường không phải security boundary đủ mạnh cho multi-tenant untrusted research code.

### 6.3. Khi chuyển sang Kubernetes

- Tạo Pod/Job trong namespace `mlops-jobs`; shared Controller trong `mlops-system`; trusted gate trong `mlops-gate`.
- **Pod** là đơn vị network cơ bản; containers trong cùng Pod dùng chung network namespace/`localhost`.
- **Service + DNS** cho các API cần endpoint ổn định; không cần tạo Service cho mọi batch training Pod.
- **NetworkPolicy** để kiểm soát traffic Pod ingress/egress; thêm allow DNS/MLflow/storage cần thiết.
- S3 permissions vẫn là nhiệm vụ của S3 policy/credentials; NetworkPolicy không lọc bucket name ở cùng IP:port.
- `kind` **không mặc định đảm bảo NetworkPolicy được enforce**; để test isolation thực sự, cần cài và xác nhận một CNI hỗ trợ policy như Calico/Cilium, hoặc đánh dấu network-security test là chưa triển khai.
- `automountServiceAccountToken: false` cho training Pod trừ khi có lý do thực sự cần K8s API.

---

## 7. Hợp đồng dữ liệu và experiment

### 7.1. `ExperimentConfig` — YAML do researcher viết

Ví dụ `configs/exp01.yaml`:

```yaml
experiment:
  name: toy-classifier-v1

source:
  repository: https://github.com/YOUR_USERNAME/mini-research-mlops.git
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

**Đây là schema của project bạn tự xây**, không phải YAML chuẩn của Kubernetes/GitHub. Hãy validate các field này bằng Pydantic trước khi tạo job.

**Lưu ý:** lệnh module `examples.toy_classifier.train` chỉ hoạt động khi thư mục được đóng gói/import đúng. Khi bắt đầu bạn có thể dùng `python examples/toy_classifier/train.py`, rồi chuyển sang `python -m` khi đã hiểu packaging.

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
| `logical_run_id` | Một training experiment logic; giữ nguyên khi retry/resume |
| `attempt_id` | Một lần thực thi thực tế; tạo mới khi retry |
| `execution_ref` | Docker container ID hoặc K8s Job/Pod reference |
| `mlflow_run_id` | ID MLflow để truy vết metrics/artifacts |
| `candidate_id` | Phiên bản candidate đã freeze để evaluate/gate |
| `gate_request_id` | Mỗi yêu cầu sử dụng sealed test; phục vụ audit/idempotency |

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

### 8.2. Reproducibility manifest

Mỗi run cần lưu tối thiểu:

```text
run_id
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

dataset_versions
  dataset_id, version, manifest_uri, manifest_sha256, created_at

candidates
  candidate_id, source_run_id, artifact_uri,
  artifact_sha256, created_at

gate_budgets
  test_version (PK), max_uses, consumed_uses

gate_requests
  gate_request_id (PK), candidate_id, test_version,
  status, decision, created_at, completed_at
```

**Không** sửa schema nội bộ MLflow để lưu business state của platform. Bạn quản lý bảng của mình bằng migrations.

### 9.3. Checkpoint key convention

```text
s3://ml-checkpoints/
  toy-classifier/
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

1. Serialize training state vào file local tạm.
2. Upload file/checksum vào một object prefix mới; **không ghi đè checkpoint cũ**.
3. Verify kích thước/checksum sau upload nếu có thể.
4. Upload manifest và **publish COMPLETE cuối cùng**.
5. `latest_complete_checkpoint()` chỉ chọn prefix có COMPLETE và manifest hợp lệ.

Không giả định một S3 object multipart upload dở dang là checkpoint hoàn chỉnh.

---

## 10. Reliability: retry và resume là hai việc khác nhau

### 10.1. Phải lưu những gì trong checkpoint?

Đối với PyTorch toy trainer:

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
  loads model + optimizer + global_step
  resumes from step 400
  continues to completion
```

**Định nghĩa success:** Attempt #2 **không khởi tạo lại weights ngẫu nhiên**, và logs/metadata thể hiện `resumed_from_step=400`.

### 10.3. Những lỗi phải thử

- Kill container bằng `docker kill` (không chỉ graceful SIGTERM).
- Crash ngay giữa upload checkpoint.
- Checkpoint checksum không khớp.
- Attempt mới dùng dataset v2 trong khi checkpoint từ v1.
- Controller nhận cùng submit request hai lần do HTTP retry.
- Training process trả exit code khác 0.
- MLflow/SeaweedFS tạm thời unreachable.

Nguyên tắc: **job retry tạo execution mới; application code phải tự restore state từ durable checkpoint**.

---

## 11. Evaluation và sealed gate

### 11.1. Development evaluation

- Chạy trên dev split mà researcher có quyền xem.
- Trả `metrics.json` theo common contract, ví dụ:

```json
{
  "model_type": "toy-classifier",
  "dataset_version": "v1",
  "metrics": {"accuracy": 0.87, "loss": 0.33},
  "artifact_sha256": "<actual digest>"
}
```

- Lưu metric vào MLflow kèm metadata của evaluator và dataset.

### 11.2. Sealed test gate — mô phỏng nghiêm túc, không overclaim security

MVP chỉ đánh giá một artifact format/model architecture **do platform tự kiểm soát**. Tránh nạp arbitrary researcher Python hoặc unsafe pickle vào privileged gate. Ví dụ gate nhận model weights dạng format an toàn phù hợp, dùng **trusted evaluation code** của platform và nắm quyền đọc sealed labels.

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

Nếu không trả về row, budget đã hết. Việc liên kết request ledger với budget reservation phải thực hiện trong một transaction phù hợp để không đếm hai lần hoặc cấp slot hai lần.

### 11.4. Security boundaries

- Researcher job: credential **read train/dev**, write chỉ checkpoint prefix của run và các output được cấp quyền.
- Gate: identity riêng, quyền đọc sealed test và cập nhật gate state; không chia sẻ với researcher.
- Controller: có quyền tạo workload nhưng không mang sealed-label credentials trong image của job.
- Không tin tưởng `namespace` hoặc NetworkPolicy một mình có thể chặn mọi loại code độc hại; demo local là bài tập nguyên lý, không phải chứng nhận multi-tenant isolation.
- Không đưa raw sealed labels vào MLflow artifacts hoặc training logs.

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
| `POST` | `/api/v1/candidates` | Freeze artifact digest thành candidate |
| `POST` | `/api/v1/gate-requests` | Yêu cầu trusted gate theo budget |
| `GET` | `/health/live` | API process đang sống |
| `GET` | `/health/ready` | API sẵn sàng phục vụ theo điều kiện đã định nghĩa |

Tránh đưa API quyền cao ra internet. Ban đầu chỉ bind host `127.0.0.1`.

### CLI mẫu

```bash
mini-ml submit configs/exp01.yaml
mini-ml status run_000172
mini-ml logs run_000172
mini-ml resume run_000172
mini-ml candidate create run_000172
mini-ml gate submit candidate_000042 --test-version sealed-v1
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
mini-research-mlops/
├── README.md
├── PROJECT_SPEC.md                    # file này
├── LICENSE
├── .gitignore
├── .env.example                       # chỉ keys/mẫu, không có secret thật
├── pyproject.toml
├── compose.yaml
├── Dockerfile.controller
├── Dockerfile.runtime
├── Makefile                            # tùy chọn
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── configs/
│   ├── exp01.yaml
│   └── exp02.yaml
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
│   │   └── dev_eval.py
│   └── gate/
│       ├── service.py
│       └── budget.py
│
├── examples/
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
│       ├── training-job.yaml
│       ├── services.yaml
│       └── network-policies.yaml
│
├── scripts/
│   ├── generate_data.py
│   ├── bootstrap_buckets.py
│   ├── smoke_test.sh
│   └── kill_and_resume_demo.sh
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
    └── demos.md
```

> **Không tạo toàn bộ cây thư mục trong ngày đầu.** Đây là hình thái repository cuối. Chỉ thêm file khi có một task cụ thể cần nó.

---

## 14. Lộ trình triển khai theo milestone

Mỗi milestone gồm **kiến thức → việc xây → test → Definition of Done (DoD)**. Chỉ chuyển milestone khi DoD đạt.

### M0 — Chuẩn hóa môi trường và GitHub repository

**Học:** Linux process/filesystem/env/permissions, `venv`, Git commit/branch/remote, SSH/HTTPS auth, `.gitignore`.

**Làm:**

- Xác nhận Ubuntu, `python3`, Git, Docker/Compose, quyền truy cập Docker.
- Tạo public GitHub repo `mini-research-mlops`; README ghi rõ synthetic-only.
- Tạo `pyproject.toml`, `.venv`, `pytest`, `.gitignore`, `.env.example`.
- Tạo PR đầu tiên rồi merge sau khi tests pass.

**DoD:** `python -m pytest` pass; GitHub repo không chứa secret/data nội bộ; giải thích được `git commit` khác `git push`.

### M1 — Toy model chạy bằng Python và Docker

**Học:** Python package/import/entrypoint, Dockerfile image/container, PID/exit code, bind mount/env.

**Làm:**

- Generate synthetic classification data bằng seed cố định.
- Viết PyTorch MLP train CPU, có accuracy/loss và seed.
- Tạo Dockerfile runtime và lệnh `docker run` chạy train.
- Tạo GitHub Actions chạy lint + pytest; build Docker image trong CI nếu phù hợp.

**Tests:** local Python vs Docker; test invalid config; exit code khi training cố tình lỗi.

**DoD:** cùng training script chạy cả host và Docker; commit SHA ghi vào output; CI pass.

### M2 — Shared infrastructure: MLflow + PostgreSQL + SeaweedFS

**Học:** IP/port/DNS/localhost, Docker Compose services/networks/volumes/healthchecks; S3 concepts.

**Làm:**

- Compose chạy PostgreSQL, SeaweedFS, MLflow.
- Tạo buckets qua bootstrap script.
- Upload synthetic dataset `v1` với manifest/checksums.
- Training tải dataset qua S3 client, log MLflow params/metrics và artifact.
- Tách MLflow backend DB và platform DB/schema về mặt logical ownership.

**Tests:** gọi `mlflow` bằng service DNS từ container; kill/remove training container; verify MLflow UI và S3 objects vẫn còn.

**DoD:** tracking không phụ thuộc sự tồn tại của trainer container; biết chính xác file nào lưu ở Postgres, file nào ở SeaweedFS.

### M3 — Controller + CLI + job contract

**Học:** FastAPI/Pydantic, HTTP methods/status, DB transaction, Docker SDK, state machine, idempotency.

**Làm:**

- YAML schema → validated JobSpec.
- `POST /api/v1/runs`, `GET /runs/{id}`, `GET /runs/{id}/logs`.
- `mini-ml submit/status/logs`.
- Platform DB tables `platform_runs`, `run_attempts`.
- `DockerLauncher` tạo container từ trusted runtime và source snapshot/commit được pin.
- Lưu logical run ID vs attempt ID; validate image/source/config/dataset.

**Tests:** hai lần submit với cùng idempotency key không tạo hai logical runs; submit invalid YAML bị reject trước khi launch.

**DoD:** từ CLI có thể tạo một container chạy training và theo dõi xuyên suốt mà không cần bạn gõ `docker run` thủ công cho từng experiment.

**Cảnh báo lab-only:** nếu Controller truy cập Docker socket của host, coi đây là privileged development setup; chỉ bind API local, không đưa lên public internet và không chạy code lạ.

### M4 — Checkpoint/resume + failure recovery

**Học:** ephemeral container, durable object store, signals, retry, atomicity/checksum, resume compatibility.

**Làm:**

- `CheckpointManager.save/load/latest_complete`.
- Lưu model/optimizer/step/RNG và metadata tối thiểu.
- Upload checkpoint theo unique prefix + COMPLETE marker.
- Kết thúc container đột ngột giữa training; retry attempt mới.
- Nếu code/config/data không tương thích thì từ chối auto resume.

**Tests:** kill ở step 550, verify resume từ step 400 hoặc checkpoint gần nhất; corrupted/incomplete checkpoint không được chọn.

**DoD:** demo được job recovery mà không mất toàn bộ tiến trình training; MLflow thấy provenance của các attempts.

### M5 — Evaluation + trusted gate + budget

**Học:** dev vs sealed test, leakage, service identity, privilege separation, transaction/concurrency, artifact immutability.

**Làm:**

- Dev evaluator với metric contract.
- Freeze candidate bằng artifact digest, không chỉ mutable object path.
- Tạo gate DB ledger + budget theo sealed-test version.
- Gate chỉ dùng trusted evaluation implementation, đọc sealed dataset qua restricted credential.
- Kiểm tra budget transaction dưới concurrent requests.
- Test training job không có sealed-test credentials và không thể đọc sealed labels trong phạm vi lab.

**Tests:** PASS/FAIL; budget hết; concurrent gate submits; artifact digest mismatch; candidate không có dev eval.

**DoD:** gate không thể được gọi unlimited; decision gắn với đúng candidate/test version; kết quả có audit trail.

### M6 — Kubernetes local bằng kind

**Học:** Cluster/Node/Pod/Job/Deployment/Service/namespace/ServiceAccount, Pod networking, Kubernetes API, NetworkPolicy.

**Làm:**

- Tạo kind cluster local, verify `kubectl get nodes`.
- Tạo `mlops-system`, `mlops-jobs`, `mlops-gate` namespaces.
- Tạo một `batch/v1 Job` chạy toy training CPU.
- Implement `KubernetesLauncher` từ cùng JobSpec.
- Cấu hình endpoints của MLflow/SeaweedFS reachable **từ cluster**, không giả định Compose DNS tự xuất hiện trong kind.
- Thử Job fail/retry và checkpoint resume.
- Test NetworkPolicy **chỉ khi đã chọn CNI có policy enforcement**.

**Tests:** `kubectl get jobs/pods`, logs, resource requests, Service DNS, Job retry; so sánh cùng config chạy Docker và K8s.

**DoD:** thay `execution.backend` từ `docker` sang `kubernetes` mà không sửa model algorithm; cùng lifecycle/tracking/checkpoint contract được giữ.

### M7 — Polish cho GitHub portfolio (tùy chọn)

- Architecture diagram rõ ràng, ảnh MLflow UI, demo GIF/video tùy chọn.
- Script `make demo`, `make test`, `make infra-up`, `make infra-down`.
- ADR về lựa chọn design (tại sao external checkpoint, tại sao JobLauncher abstraction).
- GitHub Releases/Tags `v0.1.0`, `v0.2.0`; changelog.
- Security section công khai giới hạn của local demo.
- GitHub Actions test unit/integration hợp lý; không commit `.env`/tokens.

---

## 15. Thứ tự thực hành và các lệnh khởi động (M0–M1)

### 15.1. Kiểm tra máy

```bash
cat /etc/os-release
python3 --version
git --version
docker --version
docker compose version
```

Nếu Docker chưa có hoặc user không có quyền, hãy cài/cấu hình theo Docker documentation cho Ubuntu; không chạy các lệnh thay đổi group/daemon một cách mù quáng trên máy công ty.

### 15.2. Tạo workspace cá nhân

```bash
mkdir -p ~/projects/mini-research-mlops
cd ~/projects/mini-research-mlops
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Chỉ cài dependencies khi milestone yêu cầu. Python packages nên được pin theo phiên bản/lockfile khi mục tiêu chuyển sang reproducibility.

### 15.3. Git workflow đề xuất

```bash
git init -b main
git switch -c feature/toy-training
# edit files, test
git add .
git commit -m "feat: add toy CPU training"
```

Trên GitHub tạo repository rỗng theo tên phù hợp; kết nối remote và push qua SSH/HTTPS theo hướng dẫn GitHub. Không dán token vào command/README được public.

### 15.4. Docker workflow sau khi có Dockerfile

```bash
docker build -t mini-ml-runtime:dev -f Dockerfile.runtime .
docker run --rm mini-ml-runtime:dev \
  python examples/toy_classifier/train.py
```

Đường dẫn/entrypoint thực tế phụ thuộc Dockerfile và packaging bạn tạo. Sau khi hoàn thành, cần hiểu vì sao sửa source trên host không tự sửa image cũ đã build.

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

---

## 16. Chiến lược kiểm thử

### Unit tests — chạy rất nhanh, không cần Docker

- Parse/validate YAML (missing fields, command invalid, negative resources).
- Config digest ổn định khi canonicalize cùng một config.
- State machine không cho phép transition trái luật.
- Checkpoint manifest compatibility logic.
- Gate decision logic không truy cập sealed test thật.

### Integration tests — cần Compose

- Controller ↔ PostgreSQL CRUD/transactions.
- Trainer ↔ MLflow Tracking Server.
- S3 client ↔ SeaweedFS upload/list/download/checksum.
- JobLauncher ↔ Docker Engine; logs/exit codes.
- Atomic gate budget với nhiều concurrent workers.

### E2E tests — smoke test toàn đường

1. Bootstrap synthetic dataset v1.
2. Submit experiment qua CLI.
3. Poll `SUCCEEDED` và MLflow params/metrics.
4. Verify output artifact + metadata.
5. Cố tình kill job thử lại checkpoint/resume.
6. Freeze candidate, chạy dev eval, submit gate.
7. Verify PASS/FAIL, ledger và budget.
8. Chạy tương đương trên kind (M6).

### Failure injection tests — bắt buộc có ít nhất 4

| Failure | Kết quả đúng cần chứng minh |
|---|---|
| Kill training container | Attempt mới có thể resume từ COMPLETE checkpoint |
| Checkpoint upload dở dang | Không chọn checkpoint thiếu COMPLETE/checksum sai |
| Submit HTTP request 2 lần | Không tạo logical run trùng với cùng idempotency key |
| Concurrent gate requests ở budget cuối | Không cấp vượt quota |
| MLflow/SeaweedFS unavailable | Ghi lỗi rõ ràng, không báo job success giả |
| Training credential truy cập sealed bucket | Storage API từ chối truy cập |

---

## 17. Security checklist khi public GitHub

```text
[ ] Chỉ dùng synthetic/public-permitted data và code tự viết.
[ ] Không copy tài liệu, secrets, config, IP/hostname nội bộ công ty.
[ ] .env bị ignore; .env.example không có credential thật.
[ ] Không commit private SSH keys, cloud tokens, GitHub PATs.
[ ] CI secrets được cấu hình bằng GitHub Actions Secrets khi cần.
[ ] Container không chạy privileged và không mount Docker socket vào researcher workload.
[ ] Controller có Docker socket chỉ trong local lab; API không public.
[ ] Dataset/candidate artifacts được checksum và version.
[ ] Sealed-test credential không truyền vào train job.
[ ] Gate không chạy arbitrary candidate code với privileged credentials.
[ ] Khi dùng K8s: RBAC/ServiceAccount tối thiểu; Pod security;
    NetworkPolicy chỉ được đánh dấu pass khi CNI thực sự enforce.
[ ] README ghi rõ: demo kiến trúc, KHÔNG phải hardened production platform.
```

Nếu đã lỡ commit credential, xóa file ở commit mới **không đủ** để bảo đảm credential được bảo vệ: cần rotate/revoke ngay và xử lý lịch sử repository khi phù hợp.

---

## 18. Những bài học kiến trúc cần trả lời được sau mỗi milestone

1. Linux process, Docker container, Kubernetes Pod và Kubernetes Job khác nhau thế nào?
2. Một file source ở laptop đi đến training process trên server bằng cách nào?
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
10. **Security disclaimer**: không expose lab controller public; không coi isolation local là production-grade.

**Giá trị portfolio** không nằm ở việc có nhiều logo công nghệ nhất, mà ở chỗ bạn chứng minh được một luồng MLOps chạy từ đầu đến cuối và tự xử lý các failure modes quan trọng.

---

## 21. Nguồn học chính thức (tham khảo từng phần khi cần)

- GitHub Docs — Git & GitHub basics: https://docs.github.com/
- GitHub Actions: https://docs.github.com/en/actions
- Python packaging: https://packaging.python.org/
- FastAPI: https://fastapi.tiangolo.com/
- Docker getting started: https://docs.docker.com/get-started/
- Docker Compose: https://docs.docker.com/compose/
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

**Chỉ làm M0 và M1 trước.** Chưa dựng PostgreSQL/SeaweedFS/Kubernetes khi bạn chưa tự chạy được `train.py` trong Docker.

```text
Step 1. Tạo repo public GitHub mini-research-mlops.
Step 2. Tạo môi trường .venv và project Python tối thiểu.
Step 3. Viết PyTorch toy classifier chạy CPU với seed cố định.
Step 4. Viết Dockerfile để chạy đúng file train đó.
Step 5. Viết pytest cho dữ liệu/model/training entrypoint.
Step 6. Thiết lập GitHub Actions chạy tests khi push/PR.
Step 7. Ghi README: làm gì, chạy như thế nào, đã học gì.
```

Khi cả 7 bước hoàn tất, bắt đầu **M2: Compose + MLflow + SeaweedFS**.

### Câu tuyên bố hoàn thành toàn project

> Tôi có thể nhận một experiment config, đóng băng source/data/runtime identity, tạo training job trong Docker hoặc Kubernetes, theo dõi run, lưu checkpoint bền vững, resume sau khi job chết, đánh giá candidate bằng một trusted gate có budget và giải thích được mỗi component, network connection và security boundary trong hệ thống.

---

**Ghi chú cuối:** đây là **project description + implementation roadmap**, không phải một repository đã code sẵn. Mỗi milestone nên được triển khai, kiểm thử và commit riêng để bạn học được *vì sao* hệ thống hoạt động, chứ không chỉ chạy được bằng cách sao chép một stack lớn.
