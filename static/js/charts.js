/**
 * charts.js
 * Modern Light-Theme Charts for Disk Scheduling Simulator
 * Typography: Plus Jakarta Sans
 * Canvas: Clean White with Subtle Slate Gridlines
 */

const ChartManager = (function() {
    let headMovementChart = null;
    let compareAllChart = null;
    let workloadsBenchmarkChart = null;
    let arrivalBenchmarkChart = null;

    // Modern Light Theme Defaults
    if (window.Chart) {
        Chart.defaults.color = '#64748b';
        Chart.defaults.font.family = "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
        Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
        Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
        Chart.defaults.plugins.tooltip.borderColor = '#334155';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 6;
        Chart.defaults.elements.bar.borderRadius = 4;
    }

    // High-Contrast Multi-Algorithm Palette
    const ALGO_COLORS = {
        'FCFS': {
            border: '#f43f5e',
            bar: '#f43f5e',
            point: '#f43f5e'
        },
        'SSTF': {
            border: '#f59e0b',
            bar: '#f59e0b',
            point: '#f59e0b'
        },
        'SCAN': {
            border: '#10b981',
            bar: '#10b981',
            point: '#10b981'
        },
        'C-SCAN': {
            border: '#8b5cf6',
            bar: '#8b5cf6',
            point: '#8b5cf6'
        },
        'Adaptive': {
            border: '#0284c7',
            bar: '#0284c7',
            point: '#0284c7'
        }
    };

    /**
     * Renders or updates the Head Movement Oscillogram Line Chart
     * @param {Object} singleRunData - Data from /api/simulate
     * @param {Object|null} multiAlgoData - Optional comparison map from /api/compare if overlaying
     * @param {boolean} overlayAll - Whether to overlay all 4 algorithms
     * @param {number} diskSize - Total cylinder count (default 200)
     */
    function renderHeadMovementChart(singleRunData, multiAlgoData = null, overlayAll = false, diskSize = 200) {
        const canvas = document.getElementById('headMovementChart');
        if (!canvas) return;

        let datasets = [];

        if (overlayAll && multiAlgoData) {
            // Distinct colored lines for all 4 algorithms
            const configs = [
                { name: 'FCFS', color: '#f43f5e', dash: [4, 4] },
                { name: 'SSTF', color: '#f59e0b', dash: [] },
                { name: 'SCAN', color: '#10b981', dash: [6, 4] },
                { name: 'C-SCAN', color: '#8b5cf6', dash: [2, 2] }
            ];

            configs.forEach(cfg => {
                const algoRes = multiAlgoData[cfg.name]?.result;
                if (!algoRes) return;

                const seq = algoRes.head_movement_sequence || [];

                datasets.push({
                    label: `${cfg.name} (${algoRes.total_seek_distance} cyl)`,
                    data: seq.map((cyl, idx) => ({ x: idx, y: cyl })),
                    borderColor: cfg.color,
                    borderWidth: 2.2,
                    borderDash: cfg.dash,
                    pointRadius: 3.5,
                    pointHoverRadius: 6,
                    pointBackgroundColor: cfg.color,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1.5,
                    tension: 0,
                    fill: false,
                    clip: false
                });
            });
        } else {
            // Single run: bold amber/orange stroke with white-bordered nodes
            const algoName = singleRunData.algorithm || 'Algorithm';
            const steps = singleRunData.steps || [];
            const seq = singleRunData.head_movement_sequence || [];

            // Point markers: Serviced dot, Turnaround diamond, Circular reset triangle
            const pointRadii = [5]; // initial head
            const pointStyles = ['rect'];
            const pointBgColors = ['#0f172a'];

            steps.forEach(step => {
                const evType = step.event_type || '';
                if (step.is_serviced) {
                    pointRadii.push(4.5);
                    pointStyles.push('circle');
                    pointBgColors.push('#ea580c');
                } else if (evType === 'CIRCULAR_RESET' || step.label.includes('Circular')) {
                    pointRadii.push(5.5);
                    pointStyles.push('triangle');
                    pointBgColors.push('#8b5cf6');
                } else {
                    pointRadii.push(5.5);
                    pointStyles.push('rectRot');
                    pointBgColors.push('#0f172a');
                }
            });

            datasets.push({
                label: `${algoName} Trajectory (${singleRunData.total_seek_distance} cyl seek)`,
                data: seq.map((cyl, idx) => ({ x: idx, y: cyl })),
                borderColor: '#ea580c',
                borderWidth: 2.5,
                pointRadius: pointRadii,
                pointStyle: pointStyles,
                pointBackgroundColor: pointBgColors,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 1.5,
                pointHoverRadius: 7,
                tension: 0,
                fill: false,
                clip: false
            });
        }

        if (headMovementChart) {
            headMovementChart.destroy();
        }

        headMovementChart = new Chart(canvas, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                clip: false,
                layout: {
                    padding: {
                        top: 16,
                        bottom: 10,
                        left: 10,
                        right: 14
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Step Sequence (Order of Head Traversal)',
                            color: '#475569',
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                        },
                        grid: { color: '#f1f5f9' },
                        ticks: {
                            stepSize: 1,
                            color: '#64748b',
                            font: { family: "'JetBrains Mono', monospace", size: 10 },
                            callback: function(value) {
                                return `#${value}`;
                            }
                        }
                    },
                    y: {
                        min: 0,
                        max: diskSize - 1,
                        title: {
                            display: true,
                            text: `Cylinder Track [0 .. ${diskSize - 1}]`,
                            color: '#475569',
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                        },
                        grid: { color: '#f1f5f9' },
                        ticks: {
                            color: '#64748b',
                            font: { family: "'JetBrains Mono', monospace", size: 10 }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#0f172a',
                            boxWidth: 14,
                            padding: 14,
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            title: function(items) {
                                return `Step #${items[0].parsed.x}`;
                            },
                            label: function(item) {
                                return ` Cylinder: ${item.parsed.y}`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Renders or updates the "Compare All" Bar Chart across algorithms (including Adaptive)
     * @param {Object} compareData - Data from /api/compare
     * @param {string} filterMetric - 'all' or specific metric key
     */
    function renderCompareAllChart(compareData, filterMetric = 'all') {
        const canvas = document.getElementById('compareAllChart');
        if (!canvas) return;

        const comp = compareData.comparison || {};
        const algos = ['FCFS', 'SSTF', 'SCAN', 'C-SCAN'];
        if (comp['Adaptive']) {
            algos.push('Adaptive');
        }

        let labels = algos;
        let datasets = [];

        if (filterMetric === 'all') {
            // Normalized metrics comparison
            const seekDistances = algos.map(a => comp[a]?.metrics.seek_distance || 0);
            const serviceTimes = algos.map(a => comp[a]?.metrics.service_time_ms || 0);
            const throughputs = algos.map(a => comp[a]?.metrics.throughput_req_per_sec || 0);
            const fairnesses = algos.map(a => comp[a]?.metrics.fairness_variance || 0);
            const responseTimes = algos.map(a => comp[a]?.metrics.mean_response_time_ms || 0);

            const maxSeek = Math.max(...seekDistances, 1);
            const maxServ = Math.max(...serviceTimes, 1);
            const maxThrough = Math.max(...throughputs, 1);
            const maxFair = Math.max(...fairnesses, 1);
            const maxResp = Math.max(...responseTimes, 1);

            datasets = [
                {
                    label: 'Seek Distance (%)',
                    data: seekDistances.map(v => Math.round((v / maxSeek) * 100)),
                    rawValues: seekDistances,
                    unit: 'cyl',
                    backgroundColor: '#f59e0b',
                    borderRadius: 4
                },
                {
                    label: 'Service Time (%)',
                    data: serviceTimes.map(v => Math.round((v / maxServ) * 100)),
                    rawValues: serviceTimes,
                    unit: 'ms',
                    backgroundColor: '#8b5cf6',
                    borderRadius: 4
                },
                {
                    label: 'Throughput (%)',
                    data: throughputs.map(v => Math.round((v / maxThrough) * 100)),
                    rawValues: throughputs,
                    unit: 'req/s',
                    backgroundColor: '#10b981',
                    borderRadius: 4
                },
                {
                    label: 'Fairness Var (%)',
                    data: fairnesses.map(v => Math.round((v / maxFair) * 100)),
                    rawValues: fairnesses,
                    unit: 'ms²',
                    backgroundColor: '#f43f5e',
                    borderRadius: 4
                },
                {
                    label: 'Avg Response (%)',
                    data: responseTimes.map(v => Math.round((v / maxResp) * 100)),
                    rawValues: responseTimes,
                    unit: 'ms',
                    backgroundColor: '#0f172a',
                    borderRadius: 4
                }
            ];
        } else {
            // Single metric view
            const metricLabels = {
                'seek_distance': { name: 'Seek Distance', unit: 'cylinders' },
                'service_time_ms': { name: 'Service Time', unit: 'ms' },
                'throughput_req_per_sec': { name: 'Throughput', unit: 'req/sec' },
                'fairness_variance': { name: 'Fairness Variance (σ²)', unit: 'ms²' },
                'mean_response_time_ms': { name: 'Average Response Time', unit: 'ms' }
            };

            const info = metricLabels[filterMetric] || { name: filterMetric, unit: '' };
            const values = algos.map(a => comp[a]?.metrics[filterMetric] || 0);

            datasets = [
                {
                    label: `${info.name} (${info.unit})`,
                    data: values,
                    rawValues: values,
                    unit: info.unit,
                    backgroundColor: ['#f43f5e', '#f59e0b', '#10b981', '#8b5cf6', '#0284c7'],
                    borderRadius: 4
                }
            ];
        }

        if (compareAllChart) {
            compareAllChart.destroy();
        }

        compareAllChart = new Chart(canvas, {
            type: 'bar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: {
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#0f172a', font: { family: "'Plus Jakarta Sans', sans-serif", weight: '700', size: 12 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f1f5f9' },
                        title: {
                            display: true,
                            text: filterMetric === 'all' ? 'Relative Normalized Score [0 - 100%]' : datasets[0]?.label || '',
                            color: '#475569',
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                        },
                        ticks: {
                            color: '#64748b',
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: filterMetric === 'all',
                        position: 'top',
                        labels: { color: '#0f172a', boxWidth: 12, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const dataset = context.dataset;
                                const raw = dataset.rawValues ? dataset.rawValues[context.dataIndex] : context.parsed.y;
                                const unit = dataset.unit || '';
                                if (filterMetric === 'all') {
                                    return `${dataset.label}: ${context.parsed.y}% (Raw: ${raw} ${unit})`;
                                }
                                return `${dataset.label}: ${raw} ${unit}`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Renders or updates the 4-Workloads Technical Benchmark Chart
     * @param {Object} benchmarkData - Data from /api/compare-all-workloads
     */
    function renderWorkloadsBenchmarkChart(benchmarkData) {
        const canvas = document.getElementById('workloadsBenchmarkChart');
        if (!canvas) return;

        const patterns = ['random', 'sequential', 'clustered', 'bursty'];
        const algos = ['FCFS', 'SSTF', 'SCAN', 'C-SCAN', 'Adaptive'];
        const benchmarks = benchmarkData.workload_benchmarks || {};

        const barColors = {
            'FCFS': '#f43f5e',
            'SSTF': '#f59e0b',
            'SCAN': '#10b981',
            'C-SCAN': '#8b5cf6',
            'Adaptive': '#0284c7'
        };

        const datasets = algos.map(algo => {
            const data = patterns.map(pat => {
                return benchmarks[pat]?.comparison[algo]?.metrics.seek_distance || 0;
            });

            return {
                label: algo,
                data: data,
                backgroundColor: barColors[algo] || '#f59e0b',
                borderRadius: 4
            };
        });

        if (workloadsBenchmarkChart) {
            workloadsBenchmarkChart.destroy();
        }

        workloadsBenchmarkChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Random Workload', 'Sequential Workload', 'Clustered Workload', 'Bursty Workload'],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: {
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#0f172a', font: { family: "'Plus Jakarta Sans', sans-serif", weight: '700', size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Total Seek Distance (Cylinders) — Lower is Optimal',
                            color: '#475569',
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                        },
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#64748b', font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#0f172a', boxWidth: 12, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ` ${ctx.dataset.label}: ${ctx.parsed.y} cylinders seek`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Renders or updates the Arrival Pattern Benchmark Chart
     * @param {Object} arrivalData - Data from /api/compare-arrival-patterns
     */
    function renderArrivalBenchmarkChart(arrivalData) {
        const canvas = document.getElementById('arrivalBenchmarkChart');
        if (!canvas) return;

        const patterns = ['all_at_once', 'sequential', 'random', 'bursty', 'continuous'];
        const displayLabels = ['All-at-Once', 'Sequential', 'Random', 'Bursty', 'Continuous'];
        const algos = ['FCFS', 'SSTF', 'SCAN', 'C-SCAN', 'Adaptive'];
        const benchmarks = arrivalData.arrival_benchmarks || {};

        const barColors = {
            'FCFS': '#f43f5e',
            'SSTF': '#f59e0b',
            'SCAN': '#10b981',
            'C-SCAN': '#8b5cf6',
            'Adaptive': '#0284c7'
        };

        const datasets = algos.map(algo => {
            const data = patterns.map(pat => {
                return benchmarks[pat]?.summary[algo]?.mean_response_time_ms || 0;
            });

            return {
                label: algo,
                data: data,
                backgroundColor: barColors[algo] || '#f59e0b',
                borderRadius: 4
            };
        });

        if (arrivalBenchmarkChart) {
            arrivalBenchmarkChart.destroy();
        }

        arrivalBenchmarkChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: displayLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: {
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#0f172a', font: { family: "'Plus Jakarta Sans', sans-serif", weight: '700', size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Mean Response Time (ms) Across Arrival Patterns',
                            color: '#475569',
                            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' }
                        },
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#64748b', font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#0f172a', boxWidth: 12, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ` ${ctx.dataset.label}: ${ctx.parsed.y} ms avg response`;
                            }
                        }
                    }
                }
            }
        });
    }

    function clearHeadMovementChart() {
        if (headMovementChart) {
            headMovementChart.destroy();
            headMovementChart = null;
        }
    }

    return {
        renderHeadMovementChart,
        renderCompareAllChart,
        renderWorkloadsBenchmarkChart,
        renderArrivalBenchmarkChart,
        clearHeadMovementChart
    };
})();
