# Disk Scheduling Simulator & AI Workload Classifier

A full-stack interactive Operating Systems Disk Scheduling Simulator with a Flask Python backend and a responsive Vanilla CSS & JavaScript frontend powered by Chart.js.

## 🚀 Features

### Backend
- **Core Algorithms**:
  - **FCFS** (First-Come, First-Served): Services requests in arrival order.
  - **SSTF** (Shortest Seek Time First): Greedily visits the closest request to the current head.
  - **SCAN** (Elevator): Sweeps unidirectionally to the boundary, reverses, and services tracks on the return.
  - **C-SCAN** (Circular SCAN): Sweeps in one direction to the boundary, executes a circular reset jump, and resumes in the same direction.
  - **Adaptive**: Statistical classifier predicting and executing the optimal seek-minimizing algorithm.
- **Workload Generator**:
  - `random`: Uniform distribution across disk cylinders.
  - `sequential`: Contiguous track runs simulating streaming file operations.
  - `clustered`: Dense hotspots around database index and metadata cylinders.
  - `bursty`: Spatial/temporal bursts interspersed with sudden cross-disk seeks.
- **Classifier Module**:
  - Extracts queue features: `spread`, `density`, `clustering`, and `direction_bias`.
  - Classifies pattern into random, sequential, clustered, or bursty.
  - Predicts the seek-distance minimizing algorithm with an explainable OS rationale.
- **Metrics Module**:
  - `seek_distance`: Total head movement (cylinders).
  - `service_time`: Modeled on enterprise 7,200 RPM drive physics (seek overhead + track seek time + rotational latency + sector transfer).
  - `throughput`: Serviced requests per second.
  - `fairness`: Variance ($\sigma^2$) and standard deviation of request waiting times.
  - `response_time`: Mean waiting time across the queue.

### Frontend
- **Dark Glassmorphism Design System**: Modern aesthetic with glowing indicators, customized tokens, and smooth micro-animations.
- **Interactive Platter Strip**: Physical depiction of disk cylinders with live head pointer and serviced request pips.
- **Dynamic Head Movement Chart**: Chart.js line graph depicting step-by-step head trajectory, servicing markers, and optional 4-algorithm overlay.
- **Multi-Algorithm Comparison**: Grouped bar chart comparing FCFS, SSTF, SCAN, and C-SCAN across all 5 metrics with interactive metric filters.
- **4-Workload Multi-Benchmark**: Matrix evaluating all 4 algorithms on Random, Sequential, Clustered, and Bursty workloads simultaneously, complete with OS theoretical insights.

---

## 🛠️ Installation & Running

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Flask application**:
   ```bash
   python app.py
   ```

3. **Open in your browser**:
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 🧪 Running Automated Tests

Run the comprehensive unit test suite:
```bash
python -m pytest tests/ -v
```
Verifies textbook canonical examples (Galvin 53 head, 640/236/331/382 seek distances), edge cases, generators, classifier features, and REST API endpoints.
