/**
 * app.js
 * Mission Control & Adaptive Simulator State Engine
 * Single Source of Truth for Simulation Kinematics, Initial Head State, and Arrival Timing
 */

document.addEventListener('DOMContentLoaded', () => {
    // Engine State
    const state = {
        requests: [],
        arrivalTimes: [],
        arrivalPattern: 'all_at_once',
        initialHead: 0,
        diskSize: 200,
        direction: 'UP',
        algorithm: 'ADAPTIVE',
        currentSingleRun: null,
        currentComparison: null,
        currentWorkloadBenchmarks: null,
        currentArrivalBenchmarks: null,
        activeCompareMetric: 'all'
    };

    // DOM References
    const elements = {
        // Inputs
        requestQueueInput: document.getElementById('requestQueueInput'),
        queueCountBadge: document.getElementById('queueCountBadge'),
        queueRangeBadge: document.getElementById('queueRangeBadge'),
        queueArrivalBadge: document.getElementById('queueArrivalBadge'),
        arrivalPatternSelect: document.getElementById('arrivalPatternSelect'),
        diskSizeInput: document.getElementById('diskSizeInput'),
        initialHeadInput: document.getElementById('initialHeadInput'),
        headValueDisplay: document.getElementById('headValueDisplay'),
        headSlider: document.getElementById('headSlider'),
        sliderMid: document.getElementById('sliderMid'),
        sliderMax: document.getElementById('sliderMax'),
        btnDirUp: document.getElementById('btnDirUp'),
        btnDirDown: document.getElementById('btnDirDown'),
        algoSelect: document.getElementById('algoSelect'),
        genCountInput: document.getElementById('genCountInput'),
        genSeedInput: document.getElementById('genSeedInput'),
        
        // Buttons
        btnSimulate: document.getElementById('btnSimulate'),
        btnRunAdaptive: document.getElementById('btnRunAdaptive'),
        btnCompareAll: document.getElementById('btnCompareAll') || document.getElementById('btnCompare'),
        btnBenchmarkWorkloads: document.getElementById('btnBenchmarkWorkloads') || document.getElementById('btnMatrix'),
        btnResetAll: document.getElementById('btnResetAll'),
        btnApplyAdaptive: document.getElementById('btnApplyAdaptive'),
        btnApplyMl: document.getElementById('btnApplyMl'),
        btnRefreshWorkloadBenchmark: document.getElementById('btnRefreshWorkloadBenchmark'),
        btnRunArrivalBenchmark: document.getElementById('btnRunArrivalBenchmark'),
        
        // Viva Modal
        btnVivaModalOpen: document.getElementById('btnVivaModalOpen'),
        btnVivaModalClose: document.getElementById('btnVivaModalClose'),
        vivaModalBackdrop: document.getElementById('vivaModalBackdrop'),
        
        // Platter
        trackHeadMarker: document.getElementById('trackHeadMarker'),
        trackHeadTooltip: document.getElementById('trackHeadTooltip'),
        trackRequestsLayer: document.getElementById('trackRequestsLayer'),
        platterMaxCyl: document.getElementById('platterMaxCyl'),
        
        // Tabs
        tabButtons: document.querySelectorAll('.tab-btn'),
        tabContents: document.querySelectorAll('.tab-content'),
        
        // AI / Classification / Adaptive
        workloadTypeVal: document.getElementById('workloadTypeVal'),
        workloadConfVal: document.getElementById('workloadConfVal'),
        simStatusBadge: document.getElementById('simStatusBadge'),
        featSpreadVal: document.getElementById('featSpreadVal'),
        featSpreadBar: document.getElementById('featSpreadBar'),
        featSpreadDetail: document.getElementById('featSpreadDetail'),
        featDensityVal: document.getElementById('featDensityVal'),
        featDensityBar: document.getElementById('featDensityBar'),
        featDensityDetail: document.getElementById('featDensityDetail'),
        featClusterVal: document.getElementById('featClusterVal'),
        featClusterBar: document.getElementById('featClusterBar'),
        featClusterDetail: document.getElementById('featClusterDetail'),
        featDirVal: document.getElementById('featDirVal'),
        featDirBar: document.getElementById('featDirBar'),
        featDirDetail: document.getElementById('featDirDetail'),
        recAlgoName: document.getElementById('recAlgoName'),
        recAlgoReason: document.getElementById('recAlgoReason'),
        mlAlgoName: document.getElementById('mlAlgoName'),
        mlAlgoConf: document.getElementById('mlAlgoConf'),
        mlAlgoReason: document.getElementById('mlAlgoReason'),
        mlRecBox: document.getElementById('mlRecBox'),
        adaptiveDecisionBanner: document.getElementById('adaptiveDecisionBanner'),
        adaptiveSelectedAlgo: document.getElementById('adaptiveSelectedAlgo'),
        adaptiveSelectedBasis: document.getElementById('adaptiveSelectedBasis'),
        adaptiveSelectedReason: document.getElementById('adaptiveSelectedReason'),
        
        // Metric Scorecards
        metricSeekDist: document.getElementById('metricSeekDist'),
        metricSeekDistSub: document.getElementById('metricSeekDistSub'),
        metricServiceTime: document.getElementById('metricServiceTime'),
        metricThroughput: document.getElementById('metricThroughput'),
        metricFairness: document.getElementById('metricFairness'),
        metricFairnessSub: document.getElementById('metricFairnessSub'),
        metricResponseTime: document.getElementById('metricResponseTime'),
        metricResponseTimeSub: document.getElementById('metricResponseTimeSub'),
        activeAlgoBadge: document.getElementById('activeAlgoBadge'),
        
        // Tables & Charts
        chkOverlayAll: document.getElementById('chkOverlayAll'),
        stepsTableBody: document.getElementById('stepsTableBody'),
        stepCountBadge: document.getElementById('stepCountBadge'),
        compareRankingBody: document.getElementById('compareRankingBody'),
        workloadBenchmarkGrid: document.getElementById('workloadBenchmarkGrid'),
        arrivalBenchmarkGrid: document.getElementById('arrivalBenchmarkGrid'),
        filterPills: document.querySelectorAll('.filter-pill')
    };

    // Standard Technical Presets
    const PRESETS = {
        'canonical': {
            requests: [98, 183, 37, 122, 14, 124, 65, 67],
            head: 53,
            size: 200,
            dir: 'UP',
            arrivalPattern: 'all_at_once'
        },
        'ascending': {
            requests: [10, 14, 25, 29, 32, 65, 78, 85, 110, 140, 175],
            head: 12,
            size: 200,
            dir: 'UP',
            arrivalPattern: 'sequential'
        },
        'dual-cluster': {
            requests: [15, 18, 22, 19, 25, 20, 145, 150, 152, 148, 160],
            head: 80,
            size: 200,
            dir: 'UP',
            arrivalPattern: 'bursty'
        },
        'erratic': {
            requests: [5, 195, 12, 180, 24, 165, 30, 150],
            head: 100,
            size: 200,
            dir: 'DOWN',
            arrivalPattern: 'random'
        }
    };

    /* -------------------------------------------------------------
       Parsing & Geometry Synchronization
    ------------------------------------------------------------- */

    function parseInputRequests() {
        const text = elements.requestQueueInput.value.trim();
        if (!text) return [];
        return text.replace(/,/g, ' ')
                   .split(/\s+/)
                   .map(t => parseInt(t, 10))
                   .filter(n => !isNaN(n));
    }

    function generateArrivalTimesForQueue(count, pattern) {
        if (pattern === 'all_at_once') {
            return new Array(count).fill(0.0);
        } else if (pattern === 'sequential') {
            return Array.from({ length: count }, (_, i) => +(i * 5.0).toFixed(2));
        } else if (pattern === 'random') {
            let curr = 0;
            const res = [0.0];
            for (let i = 1; i < count; i++) {
                curr += (2.0 + Math.random() * 7.0);
                res.push(+curr.toFixed(2));
            }
            return res;
        } else if (pattern === 'bursty') {
            const res = [];
            let epoch = 0;
            let i = 0;
            while (i < count) {
                const bSize = 3 + Math.floor(Math.random() * 3);
                for (let b = 0; b < bSize && i < count; b++, i++) {
                    res.push(+(epoch + Math.random() * 1.5).toFixed(2));
                }
                epoch += (30 + Math.random() * 30);
            }
            return res.slice(0, count);
        } else if (pattern === 'continuous') {
            return Array.from({ length: count }, (_, i) => +(i * 2.0).toFixed(2));
        }
        return new Array(count).fill(0.0);
    }

    function updateQueueMetadata() {
        const reqs = parseInputRequests();
        state.requests = reqs;
        elements.queueCountBadge.textContent = `${reqs.length} requests`;

        if (reqs.length > 0) {
            const minCyl = Math.min(...reqs);
            const maxCyl = Math.max(...reqs);
            elements.queueRangeBadge.textContent = `Range: [${minCyl} .. ${maxCyl}]`;
            
            // Sync arrival times
            if (!state.arrivalTimes || state.arrivalTimes.length !== reqs.length) {
                state.arrivalTimes = generateArrivalTimesForQueue(reqs.length, state.arrivalPattern);
            }
        } else {
            elements.queueRangeBadge.textContent = 'Range: N/A';
            state.arrivalTimes = [];
        }

        const patDisplay = state.arrivalPattern.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        if (elements.queueArrivalBadge) {
            elements.queueArrivalBadge.textContent = `Timing: ${patDisplay}`;
        }

        updatePlatterTrack(state.initialHead);
    }

    /**
     * Unified Platter Track Updater
     */
    function updatePlatterTrack(actualHead = null, servicedCylinders = [], targetDiskSize = null) {
        const diskSize = targetDiskSize || parseInt(elements.diskSizeInput.value, 10) || 200;
        let head;
        if (actualHead !== null && actualHead !== undefined && !isNaN(actualHead)) {
            head = parseInt(actualHead, 10);
        } else {
            head = parseInt(elements.initialHeadInput.value, 10);
            if (isNaN(head)) {
                head = parseInt(elements.headSlider.value, 10) || 0;
            }
        }

        head = Math.max(0, Math.min(diskSize - 1, head));
        state.diskSize = diskSize;
        state.initialHead = head;

        // Synchronize inputs
        elements.diskSizeInput.value = diskSize;
        elements.initialHeadInput.value = head;
        elements.headSlider.max = diskSize - 1;
        elements.headSlider.value = head;
        elements.headValueDisplay.textContent = head;
        elements.sliderMax.textContent = diskSize - 1;
        elements.sliderMid.textContent = Math.floor(diskSize / 2);

        if (elements.platterMaxCyl) {
            elements.platterMaxCyl.textContent = (diskSize - 1);
        }
        document.querySelectorAll('.maxCylFootnote').forEach(el => el.textContent = (diskSize - 1));

        // Move head needle and set tooltip text
        const headPct = Math.max(0, Math.min(100, (head / (diskSize - 1)) * 100));
        elements.trackHeadMarker.style.left = `${headPct}%`;
        elements.trackHeadTooltip.textContent = `Head: ${head}`;

        // Render request pips on track
        elements.trackRequestsLayer.innerHTML = '';
        const servicedSet = new Set(servicedCylinders);

        state.requests.forEach((cyl, idx) => {
            const pct = Math.max(0, Math.min(100, (cyl / (diskSize - 1)) * 100));
            const pip = document.createElement('div');
            pip.className = 'req-pip' + (servicedSet.has(cyl) ? ' serviced' : '');
            pip.style.left = `${pct}%`;
            const arrT = (state.arrivalTimes && state.arrivalTimes[idx] !== undefined) ? state.arrivalTimes[idx] : 0.0;
            pip.title = `Request #${idx + 1}: Cylinder ${cyl} (Arrival: ${arrT} ms)`;
            elements.trackRequestsLayer.appendChild(pip);
        });
    }

    function switchTab(tabId) {
        elements.tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        elements.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === tabId);
        });
    }

    /* -------------------------------------------------------------
       End-to-End Simulation Execution Flow
    ------------------------------------------------------------- */

    async function runSimulation(algo = null, basis = null) {
        const algorithmChoice = algo || elements.algoSelect.value;
        let reqs = parseInputRequests();

        // If user clicks simulate on empty input, automatically populate canonical textbook queue
        if (reqs.length === 0) {
            elements.requestQueueInput.value = '98, 183, 37, 122, 14, 124, 65, 67';
            elements.initialHeadInput.value = 53;
            elements.headSlider.value = 53;
            elements.headValueDisplay.textContent = 53;
            updateQueueMetadata();
            reqs = parseInputRequests();
        }

        const diskSize = parseInt(elements.diskSizeInput.value, 10) || 200;
        let headVal = parseInt(elements.initialHeadInput.value, 10);
        if (isNaN(headVal)) {
            headVal = parseInt(elements.headSlider.value, 10) || 0;
        }
        headVal = Math.max(0, Math.min(diskSize - 1, headVal));

        state.requests = reqs;
        state.diskSize = diskSize;
        state.initialHead = headVal;
        state.algorithm = algorithmChoice;

        // Keep UI synchronized before sending
        elements.initialHeadInput.value = headVal;
        elements.headSlider.value = headVal;
        elements.headValueDisplay.textContent = headVal;

        elements.btnSimulate.disabled = true;
        elements.btnSimulate.textContent = 'Simulating...';

        try {
            const payload = {
                requests: state.requests,
                initial_head: headVal,
                disk_size: diskSize,
                direction: state.direction,
                algorithm: algorithmChoice,
                arrival_pattern: state.arrivalPattern,
                arrival_times: state.arrivalTimes,
                adaptive_basis: basis || "HYBRID",
                _timestamp: Date.now()
            };

            const resp = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await resp.json();
            if (!result.success) {
                console.error('Simulation error:', result.error);
                return;
            }

            const data = result.data;
            state.currentSingleRun = data;

            // Re-render UI using single source of truth returned by the run
            updateSimulationUI(data);

            // Synchronize comparison data in background
            fetchComparisonData();

        } catch (err) {
            console.error('API Error during simulation:', err);
        } finally {
            elements.btnSimulate.disabled = false;
            elements.btnSimulate.textContent = '▶ Simulate Trajectory';
        }
    }

    async function fetchComparisonData() {
        if (!state.requests || state.requests.length === 0) {
            return;
        }

        try {
            const payload = {
                requests: state.requests,
                initial_head: state.initialHead,
                disk_size: state.diskSize,
                direction: state.direction,
                arrival_pattern: state.arrivalPattern,
                arrival_times: state.arrivalTimes,
                _timestamp: Date.now()
            };

            const resp = await fetch('/api/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const res = await resp.json();
            if (res.success) {
                state.currentComparison = res.data;
                updateCompareAllUI(res.data);

                // If overlay is checked, re-render head movement chart with overlay
                if (elements.chkOverlayAll.checked && state.currentSingleRun) {
                    ChartManager.renderHeadMovementChart(
                        state.currentSingleRun,
                        state.currentComparison.comparison,
                        true,
                        state.diskSize
                    );
                }
            }
        } catch (e) {
            console.error('Error fetching comparison:', e);
        }
    }

    async function generateWorkloadPattern(pattern) {
        const count = parseInt(elements.genCountInput.value, 10) || 20;
        const seed = elements.genSeedInput.value ? parseInt(elements.genSeedInput.value, 10) : null;
        const diskSize = parseInt(elements.diskSizeInput.value, 10) || 200;
        const arrPat = elements.arrivalPatternSelect ? elements.arrivalPatternSelect.value : state.arrivalPattern;

        try {
            const resp = await fetch('/api/generate-workload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pattern, count, disk_size: diskSize, seed, arrival_pattern: arrPat })
            });
            const res = await resp.json();
            if (res.success) {
                const reqs = res.data.requests;
                state.arrivalPattern = res.data.arrival_pattern || arrPat;
                state.arrivalTimes = res.data.arrival_times || [];
                elements.requestQueueInput.value = reqs.join(', ');
                updateQueueMetadata();
                // Immediately execute simulation on generated workload
                runSimulation();
            }
        } catch (e) {
            console.error('Generate error:', e);
        }
    }

    async function run4WorkloadBenchmark() {
        elements.btnBenchmarkWorkloads.disabled = true;
        elements.btnBenchmarkWorkloads.textContent = 'Benchmarking Matrix...';
        switchTab('workloads-tab');

        try {
            const payload = {
                count: parseInt(elements.genCountInput.value, 10) || 25,
                disk_size: parseInt(elements.diskSizeInput.value, 10) || 200,
                initial_head: state.initialHead,
                direction: state.direction,
                arrival_pattern: state.arrivalPattern,
                seed: elements.genSeedInput.value ? parseInt(elements.genSeedInput.value, 10) : 42,
                _timestamp: Date.now()
            };

            const resp = await fetch('/api/compare-all-workloads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const res = await resp.json();
            if (res.success) {
                state.currentWorkloadBenchmarks = res.data;
                updateWorkloadBenchmarkUI(res.data);
            }
        } catch (e) {
            console.error('Benchmark error:', e);
        } finally {
            elements.btnBenchmarkWorkloads.disabled = false;
            elements.btnBenchmarkWorkloads.textContent = '⚡ 4-Workload Matrix';
        }
    }

    async function runArrivalBenchmark() {
        if (elements.btnRunArrivalBenchmark) {
            elements.btnRunArrivalBenchmark.disabled = true;
            elements.btnRunArrivalBenchmark.textContent = 'Evaluating Patterns...';
        }

        try {
            let reqs = parseInputRequests();
            if (reqs.length === 0) {
                reqs = [98, 183, 37, 122, 14, 124, 65, 67];
            }

            const payload = {
                requests: reqs,
                initial_head: state.initialHead,
                disk_size: state.diskSize,
                direction: state.direction,
                _timestamp: Date.now()
            };

            const resp = await fetch('/api/compare-arrival-patterns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const res = await resp.json();
            if (res.success) {
                state.currentArrivalBenchmarks = res.data;
                updateArrivalBenchmarkUI(res.data);
            }
        } catch (e) {
            console.error('Arrival benchmark error:', e);
        } finally {
            if (elements.btnRunArrivalBenchmark) {
                elements.btnRunArrivalBenchmark.disabled = false;
                elements.btnRunArrivalBenchmark.textContent = 'Run Arrival Pattern Benchmark';
            }
        }
    }

    /* -------------------------------------------------------------
       UI Re-Rendering Logic (Single Source of Truth)
    ------------------------------------------------------------- */

    function updateSimulationUI(data) {
        const m = data.metrics;
        const cls = data.classification;
        const f = cls.features;

        const actualHead = (data.config && data.config.initial_head !== undefined)
            ? data.config.initial_head
            : data.head_movement_sequence[0];
        const actualDiskSize = (data.config && data.config.disk_size) || state.diskSize || 200;
        const actualDirection = (data.config && data.config.direction) || state.direction || 'UP';

        // Synchronize internal state
        state.initialHead = actualHead;
        state.diskSize = actualDiskSize;
        state.direction = actualDirection;

        // Synchronize control widgets to match actual run
        elements.initialHeadInput.value = actualHead;
        elements.headSlider.value = actualHead;
        elements.headValueDisplay.textContent = actualHead;
        elements.diskSizeInput.value = actualDiskSize;

        // Synchronize direction toggle buttons
        elements.btnDirUp.classList.toggle('active', actualDirection === 'UP');
        elements.btnDirDown.classList.toggle('active', actualDirection === 'DOWN');

        // Status Badge
        if (elements.simStatusBadge) {
            elements.simStatusBadge.textContent = 'Status: Complete';
            elements.simStatusBadge.style.background = 'var(--green-light)';
            elements.simStatusBadge.style.color = 'var(--green-text)';
        }

        // Active Algorithm Badge
        elements.activeAlgoBadge.textContent = data.algorithm + (data.is_adaptive ? ' (Adaptive Policy)' : '');

        // Adaptive Decision Banner
        if (data.is_adaptive && data.adaptive_info) {
            elements.adaptiveDecisionBanner.style.display = 'flex';
            elements.adaptiveSelectedAlgo.textContent = data.adaptive_info.selected_algorithm;
            elements.adaptiveSelectedBasis.textContent = data.adaptive_info.selection_basis || 'Adaptive Policy';
            elements.adaptiveSelectedReason.textContent = data.adaptive_info.reason || 'Workload analysis complete.';
        } else {
            elements.adaptiveDecisionBanner.style.display = 'none';
        }

        // Metric 1: Seek Distance
        elements.metricSeekDist.innerHTML = `${m.seek_distance}<span class="unit">cyl</span>`;
        elements.metricSeekDistSub.textContent = `Head: ${actualHead} • Dir: ${actualDirection}`;
        
        // Metric 2: Service Time (7200 RPM physical model)
        elements.metricServiceTime.innerHTML = `${m.service_time_ms}<span class="unit">ms</span>`;
        
        // Metric 3: Throughput
        elements.metricThroughput.innerHTML = `${m.throughput_req_per_sec}<span class="unit">req/s</span>`;
        
        // Metric 4: Fairness (Jain's & Variance)
        const jainsVal = (m.jains_fairness_index !== undefined) ? m.jains_fairness_index : 1.0;
        elements.metricFairness.innerHTML = `${jainsVal}<span class="unit">J</span>`;
        elements.metricFairnessSub.textContent = `σ² = ${m.fairness_variance} ms² • σ = ${m.fairness_std_dev} ms`;

        // Metric 5: Response Time
        elements.metricResponseTime.innerHTML = `${m.mean_response_time_ms}<span class="unit">ms</span>`;
        elements.metricResponseTimeSub.textContent = `Min: ${m.min_response_time_ms} ms | Max: ${m.max_response_time_ms} ms`;

        // Classification & Feature Meters
        elements.workloadTypeVal.textContent = cls.workload_type;
        elements.workloadConfVal.textContent = `(${Math.round(cls.confidence * 100)}% conf)`;

        elements.featSpreadVal.textContent = f.spread.toFixed(2);
        elements.featSpreadBar.style.width = `${Math.min(100, Math.round(f.spread * 100))}%`;
        elements.featSpreadDetail.textContent = `Span: ${f.details.span} cyl • σ: ${f.details.std_dev}`;

        elements.featDensityVal.textContent = f.density.toFixed(2);
        elements.featDensityBar.style.width = `${Math.min(100, Math.round(f.density * 100))}%`;
        elements.featDensityDetail.textContent = `${f.details.mean_consecutive_diff} avg step`;

        elements.featClusterVal.textContent = f.clustering.toFixed(2);
        elements.featClusterBar.style.width = `${Math.min(100, Math.round(f.clustering * 100))}%`;
        elements.featClusterDetail.textContent = `Diff CV: ${f.details.cv_diff}`;

        elements.featDirVal.textContent = f.direction_bias.toFixed(2);
        elements.featDirBar.style.width = `${Math.min(100, Math.round(f.direction_bias * 100))}%`;
        elements.featDirDetail.textContent = `Net Flow: ${f.details.net_flow}`;

        // Rule-Based Recommendation Box
        const ruleInfo = data.rule_based || (data.adaptive_info?.rule_based_choice ? { recommended_algorithm: data.adaptive_info.rule_based_choice, reason: data.adaptive_info.reason } : null);
        if (ruleInfo) {
            elements.recAlgoName.textContent = ruleInfo.recommended_algorithm;
            elements.recAlgoReason.textContent = ruleInfo.reason;
        } else {
            predictAdaptiveRecommendation();
        }

        // ML Decision Tree Prediction Box
        const mlData = data.ml_prediction || data.classification?.ml_prediction;
        if (mlData && mlData.ml_predicted_algorithm && elements.mlAlgoName) {
            elements.mlAlgoName.textContent = mlData.ml_predicted_algorithm;
            elements.mlAlgoConf.textContent = mlData.confidence ? `(${Math.round(mlData.confidence * 100)}% conf)` : '';
            const probs = mlData.probabilities ? Object.entries(mlData.probabilities).map(([k, v]) => `${k}: ${Math.round(v * 100)}%`).join(' • ') : '';
            elements.mlAlgoReason.textContent = probs ? `Decision Tree Probabilities: ${probs}` : 'Evaluated [spread, density, clustering, direction_bias].';
        }

        // Oscilloscope Trajectory Chart
        ChartManager.renderHeadMovementChart(
            data,
            state.currentComparison?.comparison || null,
            elements.chkOverlayAll.checked,
            actualDiskSize
        );

        // Platter Cylinder Map
        updatePlatterTrack(actualHead, data.seek_order, actualDiskSize);

        // Servicing Event Log
        elements.stepCountBadge.textContent = `${data.steps.length} steps`;
        elements.stepsTableBody.innerHTML = '';

        // Step #00: Explicit Initial Head Position
        const trStart = document.createElement('tr');
        trStart.style.backgroundColor = 'var(--bg-subtle, #f8fafc)';
        trStart.innerHTML = `
            <td><strong>#00</strong></td>
            <td><strong style="color: var(--amber-primary, #d97706);">Cyl ${actualHead} (Start)</strong></td>
            <td>0 cyl</td>
            <td>0 cyl</td>
            <td><span class="status-chip chip-boundary">Initial Head</span></td>
            <td>Simulation Origin: Read/Write Head starting at Cylinder ${actualHead}</td>
        `;
        elements.stepsTableBody.appendChild(trStart);

        // Step #01 onwards
        data.steps.forEach(s => {
            const tr = document.createElement('tr');
            let chipHtml = '';
            const evType = s.event_type || '';
            if (s.is_serviced) {
                chipHtml = `<span class="status-chip chip-serviced">Serviced</span>`;
            } else if (evType === 'CIRCULAR_RESET' || s.label.includes('Circular')) {
                chipHtml = `<span class="status-chip chip-jump">Circular Reset</span>`;
            } else {
                chipHtml = `<span class="status-chip chip-boundary">Turnaround</span>`;
            }

            tr.innerHTML = `
                <td><strong>#${String(s.step).padStart(2, '0')}</strong></td>
                <td><span style="font-weight: 700;">Cyl ${s.cylinder}</span></td>
                <td>+${s.distance} cyl</td>
                <td>${s.cumulative_distance} cyl</td>
                <td>${chipHtml}</td>
                <td>${s.label}</td>
            `;
            elements.stepsTableBody.appendChild(tr);
        });
    }

    async function predictAdaptiveRecommendation() {
        if (!state.requests || state.requests.length === 0) {
            return;
        }
        try {
            const resp = await fetch('/api/classify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    requests: state.requests,
                    initial_head: state.initialHead,
                    disk_size: state.diskSize,
                    direction: state.direction,
                    arrival_pattern: state.arrivalPattern,
                    arrival_times: state.arrivalTimes
                })
            });
            const res = await resp.json();
            if (res.success) {
                const rule = res.data.rule_based || res.data.prediction;
                if (rule && elements.recAlgoName) {
                    elements.recAlgoName.textContent = rule.recommended_algorithm || rule.predicted_algorithm;
                    elements.recAlgoReason.textContent = rule.reason;
                }
                const ml = res.data.ml_prediction || res.data.classification?.ml_prediction;
                if (ml && elements.mlAlgoName) {
                    elements.mlAlgoName.textContent = ml.ml_predicted_algorithm || '-';
                    elements.mlAlgoConf.textContent = ml.confidence ? `(${Math.round(ml.confidence * 100)}% conf)` : '';
                    const probs = ml.probabilities ? Object.entries(ml.probabilities).map(([k, v]) => `${k}: ${Math.round(v * 100)}%`).join(' • ') : '';
                    elements.mlAlgoReason.textContent = probs ? `Decision Tree Probabilities: ${probs}` : 'Evaluated [spread, density, clustering, direction_bias].';
                }
            }
        } catch (e) {
            console.error('Classification error:', e);
        }
    }

    function updateCompareAllUI(data) {
        ChartManager.renderCompareAllChart(data, state.activeCompareMetric);

        elements.compareRankingBody.innerHTML = '';
        const rankings = data.ranking || [];

        const bestForMap = {
            'SSTF': 'Min seek on localized clusters',
            'SCAN': 'Starvation bounded boundary sweep',
            'C-SCAN': 'Uniform wait time distribution',
            'FCFS': 'Strict arrival-order FIFO determinism',
            'Adaptive': 'Dynamically optimized by AI policy'
        };

        rankings.forEach((item, idx) => {
            const tr = document.createElement('tr');
            const isAdaptive = (item.algorithm === 'Adaptive');
            if (isAdaptive) {
                tr.style.backgroundColor = '#eff6ff';
                tr.style.fontWeight = '600';
            }

            const algoLabel = isAdaptive ? 'Adaptive (AI Policy)' : item.algorithm;
            const jVal = (item.jains_fairness_index !== undefined) ? item.jains_fairness_index : '-';

            tr.innerHTML = `
                <td><span class="rank-badge rank-${idx + 1}">${idx + 1}</span></td>
                <td><strong style="color: ${isAdaptive ? '#2563eb' : 'var(--text-primary)'};">${algoLabel}</strong></td>
                <td><span style="color: var(--amber-primary); font-weight: 800;">${item.seek_distance}</span> cyl</td>
                <td>${item.service_time_ms} ms</td>
                <td>${item.throughput_req_per_sec} req/s</td>
                <td><span style="color: #10b981; font-weight: 700;">${jVal}</span></td>
                <td>${item.fairness_variance} ms²</td>
                <td>${item.mean_response_time_ms} ms</td>
                <td style="color: var(--text-secondary); font-size: 0.8rem;">${bestForMap[item.algorithm] || 'General profile'}</td>
            `;
            elements.compareRankingBody.appendChild(tr);
        });
    }

    function updateWorkloadBenchmarkUI(data) {
        const benchmarks = data.workload_benchmarks || {};
        elements.workloadBenchmarkGrid.innerHTML = '';

        for (const [pat, details] of Object.entries(benchmarks)) {
            const card = document.createElement('div');
            card.className = `workload-bench-card bench-card-${pat}`;

            const comp = details.comparison;
            const winner = details.winner;
            const algos = ['FCFS', 'SSTF', 'SCAN', 'C-SCAN', 'Adaptive'];

            let rowsHtml = '';
            algos.forEach(a => {
                const dist = comp[a]?.metrics.seek_distance;
                const isWinner = (a === winner.algorithm);
                const isAdaptive = (a === 'Adaptive');
                rowsHtml += `
                    <tr class="${isWinner ? 'winner-row' : ''}" style="${isAdaptive ? 'color: #2563eb; font-weight: 700;' : ''}">
                        <td>${isWinner ? '★ ' : (isAdaptive ? '🧠 ' : '  ')}${a}</td>
                        <td style="text-align: right;">${dist} cyl</td>
                    </tr>
                `;
            });

            card.innerHTML = `
                <div class="bench-card-header">
                    <span class="bench-pattern-title">${pat.charAt(0).toUpperCase() + pat.slice(1)}</span>
                    <span class="bench-winner-badge">Winner: ${winner.algorithm}</span>
                </div>
                <div style="font-size: 0.76rem; color: var(--text-muted); line-height: 1.45; min-height: 48px;">
                    ${details.description || details.classification?.reason || ''}
                </div>
                <table class="bench-mini-table">
                    <tbody>${rowsHtml}</tbody>
                </table>
            `;

            elements.workloadBenchmarkGrid.appendChild(card);
        }

        ChartManager.renderWorkloadsBenchmarkChart(data);
    }

    function updateArrivalBenchmarkUI(data) {
        if (!elements.arrivalBenchmarkGrid) return;
        const benchmarks = data.arrival_benchmarks || {};
        elements.arrivalBenchmarkGrid.innerHTML = '';

        const namesMap = {
            'all_at_once': 'All-at-Once (Batch)',
            'sequential': 'Sequential Arrival',
            'random': 'Random Arrival',
            'bursty': 'Bursty Arrival',
            'continuous': 'Continuous Stream'
        };

        for (const [patKey, details] of Object.entries(benchmarks)) {
            const card = document.createElement('div');
            card.className = 'arrival-bench-card';

            const summary = details.summary || {};
            const adaptiveChoice = details.adaptive_choice || 'SSTF';

            let rowsHtml = '';
            ['FCFS', 'SSTF', 'SCAN', 'C-SCAN', 'Adaptive'].forEach(algo => {
                const s = summary[algo] || {};
                const isAdaptive = (algo === 'Adaptive');
                rowsHtml += `
                    <tr style="${isAdaptive ? 'color: #2563eb; font-weight: 700;' : ''}">
                        <td>${isAdaptive ? '🧠 ' : ''}${algo}</td>
                        <td style="text-align: right;">${s.seek_distance || 0} cyl</td>
                        <td style="text-align: right;">${s.mean_response_time_ms || 0} ms</td>
                    </tr>
                `;
            });

            card.innerHTML = `
                <div class="arrival-card-title">
                    <span>${namesMap[patKey] || patKey}</span>
                    <span class="timing-badge">Adaptive: ${adaptiveChoice}</span>
                </div>
                <table class="bench-mini-table">
                    <thead>
                        <tr style="color: var(--text-muted); font-size: 0.72rem;">
                            <th>Policy</th>
                            <th style="text-align: right;">Seek</th>
                            <th style="text-align: right;">Avg Resp</th>
                        </tr>
                    </thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            `;

            elements.arrivalBenchmarkGrid.appendChild(card);
        }

        ChartManager.renderArrivalBenchmarkChart(data);
    }

    function resetToEmptyState() {
        elements.activeAlgoBadge.textContent = 'Standby';
        if (elements.simStatusBadge) {
            elements.simStatusBadge.textContent = 'Status: Standby';
            elements.simStatusBadge.style.background = 'var(--bg-subtle)';
            elements.simStatusBadge.style.color = 'var(--text-muted)';
        }

        elements.metricSeekDist.innerHTML = `-<span class="unit">cyl</span>`;
        elements.metricSeekDistSub.textContent = `Head: 0 • Standby`;
        elements.metricServiceTime.innerHTML = `-<span class="unit">ms</span>`;
        elements.metricThroughput.innerHTML = `-<span class="unit">req/s</span>`;
        elements.metricFairness.innerHTML = `-<span class="unit">J</span>`;
        elements.metricFairnessSub.textContent = `Variance: - ms² • σ: - ms`;
        elements.metricResponseTime.innerHTML = `-<span class="unit">ms</span>`;
        elements.metricResponseTimeSub.textContent = `Standby`;

        elements.workloadTypeVal.textContent = 'Awaiting Input';
        elements.workloadConfVal.textContent = '';

        elements.featSpreadVal.textContent = '-';
        elements.featSpreadBar.style.width = '0%';
        elements.featSpreadDetail.textContent = 'No data';

        elements.featDensityVal.textContent = '-';
        elements.featDensityBar.style.width = '0%';
        elements.featDensityDetail.textContent = 'No data';

        elements.featClusterVal.textContent = '-';
        elements.featClusterBar.style.width = '0%';
        elements.featClusterDetail.textContent = 'No data';

        elements.featDirVal.textContent = '-';
        elements.featDirBar.style.width = '0%';
        elements.featDirDetail.textContent = 'No data';

        elements.recAlgoName.textContent = '-';
        elements.recAlgoReason.textContent = "Awaiting workload input. Enter requests or trigger synthetic generator to analyze kinematics.";

        if (elements.mlAlgoName) elements.mlAlgoName.textContent = '-';
        if (elements.mlAlgoConf) elements.mlAlgoConf.textContent = '';
        if (elements.mlAlgoReason) elements.mlAlgoReason.textContent = "Awaiting workload features for ML decision tree inference.";

        if (elements.adaptiveDecisionBanner) {
            elements.adaptiveDecisionBanner.style.display = 'none';
        }

        ChartManager.clearHeadMovementChart();

        elements.stepCountBadge.textContent = '0 steps';
        elements.stepsTableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No telemetry recorded. Enter a queue or generate a synthetic workload and click <strong>Simulate Trajectory</strong>.
                </td>
            </tr>
        `;
    }

    /* -------------------------------------------------------------
       Interactive Event Listeners
    ------------------------------------------------------------- */

    // Tab Navigation
    elements.tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            switchTab(tabId);
            if (tabId === 'compare-tab' && !state.currentComparison) {
                fetchComparisonData();
            } else if (tabId === 'workloads-tab' && !state.currentWorkloadBenchmarks) {
                run4WorkloadBenchmark();
            } else if (tabId === 'arrival-tab' && !state.currentArrivalBenchmarks) {
                runArrivalBenchmark();
            }
        });
    });

    // Request queue input live typing
    elements.requestQueueInput.addEventListener('input', () => {
        updateQueueMetadata();
    });

    // Arrival Pattern Select
    if (elements.arrivalPatternSelect) {
        elements.arrivalPatternSelect.addEventListener('change', (e) => {
            state.arrivalPattern = e.target.value;
            if (state.requests.length > 0) {
                state.arrivalTimes = generateArrivalTimesForQueue(state.requests.length, state.arrivalPattern);
                updateQueueMetadata();
                runSimulation();
            }
        });
    }

    // Head slider and input synchronization
    elements.headSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        elements.initialHeadInput.value = val;
        state.initialHead = val;
        updatePlatterTrack(val);
    });

    elements.initialHeadInput.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10) || 0;
        elements.headSlider.value = val;
        state.initialHead = val;
        updatePlatterTrack(val);
    });

    elements.diskSizeInput.addEventListener('change', (e) => {
        state.diskSize = parseInt(e.target.value, 10) || 200;
        updatePlatterTrack(state.initialHead);
    });

    // Direction Toggle
    elements.btnDirUp.addEventListener('click', () => {
        elements.btnDirUp.classList.add('active');
        elements.btnDirDown.classList.remove('active');
        state.direction = 'UP';
        if (state.requests.length > 0) {
            runSimulation();
        }
    });

    elements.btnDirDown.addEventListener('click', () => {
        elements.btnDirDown.classList.add('active');
        elements.btnDirUp.classList.remove('active');
        state.direction = 'DOWN';
        if (state.requests.length > 0) {
            runSimulation();
        }
    });

    // Algorithm selection
    elements.algoSelect.addEventListener('change', (e) => {
        state.algorithm = e.target.value;
        if (parseInputRequests().length > 0) {
            runSimulation(e.target.value);
        }
    });

    // Quick Presets
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.dataset.preset;
            const p = PRESETS[key];
            if (p) {
                elements.requestQueueInput.value = p.requests.join(', ');
                elements.initialHeadInput.value = p.head;
                elements.headSlider.value = p.head;
                elements.headValueDisplay.textContent = p.head;
                elements.diskSizeInput.value = p.size;
                state.diskSize = p.size;
                state.initialHead = p.head;
                state.direction = p.dir;
                state.arrivalPattern = p.arrivalPattern || 'all_at_once';
                if (elements.arrivalPatternSelect) {
                    elements.arrivalPatternSelect.value = state.arrivalPattern;
                }
                elements.btnDirUp.classList.toggle('active', p.dir === 'UP');
                elements.btnDirDown.classList.toggle('active', p.dir === 'DOWN');
                updateQueueMetadata();
                runSimulation();
            }
        });
    });

    // Workload Generator Buttons
    document.querySelectorAll('.gen-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const pat = btn.dataset.pattern;
            generateWorkloadPattern(pat);
        });
    });

    // Simulate Button
    elements.btnSimulate.addEventListener('click', () => {
        runSimulation();
    });

    // Run Adaptive Scheduler Button
    if (elements.btnRunAdaptive) {
        elements.btnRunAdaptive.addEventListener('click', () => {
            elements.algoSelect.value = 'ADAPTIVE';
            state.algorithm = 'ADAPTIVE';
            runSimulation('ADAPTIVE');
        });
    }

    // Compare All Button
    elements.btnCompareAll?.addEventListener('click', () => {
        switchTab('compare-tab');
        if (parseInputRequests().length === 0) {
            elements.requestQueueInput.value = '98, 183, 37, 122, 14, 124, 65, 67';
            elements.initialHeadInput.value = 53;
            elements.headSlider.value = 53;
            elements.headValueDisplay.textContent = 53;
            updateQueueMetadata();
        }
        fetchComparisonData();
    });

    // Benchmark 4 Workloads Button
    elements.btnBenchmarkWorkloads?.addEventListener('click', () => {
        run4WorkloadBenchmark();
    });

    elements.btnRefreshWorkloadBenchmark?.addEventListener('click', () => {
        run4WorkloadBenchmark();
    });

    if (elements.btnRunArrivalBenchmark) {
        elements.btnRunArrivalBenchmark.addEventListener('click', () => {
            runArrivalBenchmark();
        });
    }

    // Viva Guide Modal Open / Close
    if (elements.btnVivaModalOpen && elements.vivaModalBackdrop) {
        elements.btnVivaModalOpen.addEventListener('click', () => {
            elements.vivaModalBackdrop.style.display = 'flex';
        });
    }

    if (elements.btnVivaModalClose && elements.vivaModalBackdrop) {
        elements.btnVivaModalClose.addEventListener('click', () => {
            elements.vivaModalBackdrop.style.display = 'none';
        });
    }

    if (elements.vivaModalBackdrop) {
        elements.vivaModalBackdrop.addEventListener('click', (e) => {
            if (e.target === elements.vivaModalBackdrop) {
                elements.vivaModalBackdrop.style.display = 'none';
            }
        });
    }

    // Reset Defaults / Clear State
    elements.btnResetAll.addEventListener('click', () => {
        elements.requestQueueInput.value = '';
        elements.initialHeadInput.value = 0;
        elements.headSlider.value = 0;
        elements.headValueDisplay.textContent = 0;
        state.initialHead = 0;
        state.requests = [];
        state.arrivalTimes = [];
        state.currentSingleRun = null;
        state.currentComparison = null;
        state.currentWorkloadBenchmarks = null;
        state.currentArrivalBenchmarks = null;
        updateQueueMetadata();
        resetToEmptyState();
        updatePlatterTrack(0);
    });

    // Apply Rule-Based choice
    elements.btnApplyAdaptive.addEventListener('click', () => {
        const rec = elements.recAlgoName.textContent.trim();
        if (rec && rec !== '-') {
            elements.algoSelect.value = rec;
            state.algorithm = rec;
            runSimulation(rec, 'RULE');
        }
    });

    // Apply ML Decision Tree recommendation
    elements.btnApplyMl?.addEventListener('click', () => {
        const mlRec = elements.mlAlgoName.textContent.trim();
        if (mlRec && mlRec !== '-') {
            elements.algoSelect.value = mlRec;
            state.algorithm = mlRec;
            runSimulation(mlRec, 'ML');
        }
    });

    // Overlay All checkbox
    elements.chkOverlayAll.addEventListener('change', () => {
        if (state.currentSingleRun) {
            ChartManager.renderHeadMovementChart(
                state.currentSingleRun,
                state.currentComparison?.comparison || null,
                elements.chkOverlayAll.checked,
                state.diskSize
            );
        }
    });

    // Metric Filter Pills on Compare Tab
    elements.filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            elements.filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            state.activeCompareMetric = pill.dataset.metric;
            if (state.currentComparison) {
                ChartManager.renderCompareAllChart(state.currentComparison, state.activeCompareMetric);
            }
        });
    });

    /* -------------------------------------------------------------
       Initial Startup
    ------------------------------------------------------------- */
    updateQueueMetadata();
    resetToEmptyState();
    updatePlatterTrack(0);
});
