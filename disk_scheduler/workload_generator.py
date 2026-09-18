"""
Workload Generator Module
Generates 4 types of disk request patterns: random, sequential, clustered, and bursty.
"""

import random
from typing import List, Optional, Dict, Any


def generate_random_workload(
    count: int = 20,
    disk_size: int = 200,
    seed: Optional[int] = None
) -> List[int]:
    """
    Uniformly distributed random cylinder requests across [0, disk_size - 1].
    """
    rng = random.Random(seed)
    return [rng.randint(0, disk_size - 1) for _ in range(count)]


def generate_sequential_workload(
    count: int = 20,
    disk_size: int = 200,
    seed: Optional[int] = None,
    stride: int = 1
) -> List[int]:
    """
    Sequential request patterns mimicking streaming reads/writes.
    Generates ordered, consecutive cylinder requests in a streaming progression.
    """
    rng = random.Random(seed)
    requests: List[int] = []

    direction_sign = 1 if rng.random() > 0.3 else -1
    span_needed = count * stride
    if direction_sign == 1:
        start_cyl = rng.randint(5, max(5, disk_size - span_needed - 5))
    else:
        start_cyl = rng.randint(min(disk_size - 6, span_needed + 5), disk_size - 6)

    curr = start_cyl
    for _ in range(count):
        jitter = rng.choice([0, 0, 0, 1]) if rng.random() < 0.2 else 0
        val = max(0, min(disk_size - 1, curr + jitter))
        requests.append(val)
        curr += direction_sign * stride
        if curr < 0 or curr >= disk_size:
            direction_sign *= -1
            curr += direction_sign * (stride * 2)
            curr = max(0, min(disk_size - 1, curr))

    return requests[:count]


def generate_clustered_workload(
    count: int = 20,
    disk_size: int = 200,
    seed: Optional[int] = None,
    num_clusters: int = 3
) -> List[int]:
    """
    Clustered workload where requests concentrate heavily in 2-4 localized hotspots
    (e.g., file system metadata, database index, active data tables).
    Generates requests in localized groups around cluster centers.
    """
    rng = random.Random(seed)
    num_clusters = min(num_clusters, max(2, count // 6))
    
    step = disk_size // (num_clusters + 1)
    centers = [step * (i + 1) + rng.randint(-max(1, step // 6), max(1, step // 6)) for i in range(num_clusters)]
    centers = [max(10, min(disk_size - 11, c)) for c in centers]

    cluster_std = max(2.0, disk_size * 0.025)  # tightly grouped
    requests: List[int] = []

    # Generate requests in localized groups (batches) per cluster
    while len(requests) < count:
        center = rng.choice(centers)
        batch_size = rng.randint(4, 7)
        for _ in range(batch_size):
            if len(requests) >= count:
                break
            val = int(round(rng.gauss(center, cluster_std)))
            val = max(0, min(disk_size - 1, val))
            requests.append(val)

    return requests[:count]


def generate_bursty_workload(
    count: int = 20,
    disk_size: int = 200,
    seed: Optional[int] = None
) -> List[int]:
    """
    Bursty workload characterized by tight bursts of requests within a small locality,
    punctuated by sudden large jumps across distant sectors of the disk.
    """
    rng = random.Random(seed)
    requests: List[int] = []
    
    current_locality = rng.randint(10, disk_size - 11)
    
    while len(requests) < count:
        burst_size = rng.randint(3, 5)
        locality_width = max(2, int(disk_size * 0.03))  # narrow locality for the burst
        
        for _ in range(burst_size):
            if len(requests) >= count:
                break
            val = current_locality + rng.randint(-locality_width, locality_width)
            val = max(0, min(disk_size - 1, val))
            requests.append(val)

        # After the burst, jump to an entirely different, distant region
        if len(requests) < count:
            jump_min_dist = max(25, int(disk_size * 0.25))
            lower_max = current_locality - jump_min_dist
            upper_min = current_locality + jump_min_dist
            candidates = []
            if lower_max > 0:
                candidates.append((0, lower_max))
            if upper_min < disk_size - 1:
                candidates.append((upper_min, disk_size - 1))
            
            if candidates:
                chosen_range = rng.choice(candidates)
                current_locality = rng.randint(chosen_range[0], chosen_range[1])
            else:
                current_locality = (current_locality + disk_size // 2) % disk_size

    return requests[:count]


GENERATORS = {
    "random": generate_random_workload,
    "sequential": generate_sequential_workload,
    "clustered": generate_clustered_workload,
    "bursty": generate_bursty_workload,
}



ARRIVAL_PATTERNS = [
    "all_at_once",
    "sequential",
    "random",
    "bursty",
    "continuous"
]


def generate_arrival_times(
    count: int = 20,
    arrival_pattern: str = "all_at_once",
    seed: Optional[int] = None
) -> List[float]:
    """
    Generates arrival times (in milliseconds) based on arrival pattern:
      - all_at_once: All requests arrive at t = 0.0 ms.
      - sequential: Arrive at regular increments (e.g. 0, 5, 10, 15 ms).
      - random: Stochastic inter-arrival times (uniform / exponential jitter).
      - bursty: Arrive in temporal clusters (e.g. 4 requests at t=0, 4 at t=35, etc.).
      - continuous: High-rate streaming arrivals (0, 2, 4, 6 ms).
    """
    pattern_norm = (arrival_pattern or "all_at_once").lower().replace("-", "_").strip()
    rng = random.Random(seed)

    if pattern_norm == "all_at_once":
        return [0.0] * count

    elif pattern_norm == "sequential":
        interval = 5.0
        return [round(i * interval, 2) for i in range(count)]

    elif pattern_norm == "random":
        times = [0.0]
        curr = 0.0
        for _ in range(1, count):
            curr += rng.uniform(1.5, 9.0)
            times.append(round(curr, 2))
        return times

    elif pattern_norm == "bursty":
        times = []
        curr_batch_time = 0.0
        i = 0
        while i < count:
            batch_size = rng.randint(3, 6)
            batch = []
            for _ in range(batch_size):
                if i >= count:
                    break
                # Requests within the same burst arrive within 0-1.5 ms of each other
                jitter = round(rng.uniform(0.0, 1.5), 2)
                batch.append(round(curr_batch_time + jitter, 2))
                i += 1
            batch.sort()
            times.extend(batch)
            # Interval between bursts
            curr_batch_time = (times[-1] if times else curr_batch_time) + rng.uniform(25.0, 50.0)
        times.sort()
        return times[:count]

    elif pattern_norm == "continuous":
        interval = 2.0
        return [round(i * interval, 2) for i in range(count)]

    else:
        # Default fallback to all-at-once
        return [0.0] * count


def generate_workload(
    pattern: str = "random",
    count: int = 20,
    disk_size: int = 200,
    seed: Optional[int] = None,
    arrival_pattern: str = "all_at_once"
) -> Dict[str, Any]:
    """
    Unified generator returning the cylinder requests, arrival times, and structured request objects.
    Supports both Request Spatial Distribution and Request Arrival Pattern.
    """
    pattern_key = pattern.lower().strip()
    if pattern_key not in GENERATORS:
        raise ValueError(f"Unknown workload pattern '{pattern}'. Choose from {list(GENERATORS.keys())}")
    
    generator_fn = GENERATORS[pattern_key]
    requests = generator_fn(count=count, disk_size=disk_size, seed=seed)
    arrival_times = generate_arrival_times(count=len(requests), arrival_pattern=arrival_pattern, seed=seed)

    request_objects = [
        {
            "id": f"R{i + 1}",
            "cylinder": cyl,
            "arrival_time": arrival_times[i]
        }
        for i, cyl in enumerate(requests)
    ]

    return {
        "pattern": pattern_key,
        "arrival_pattern": (arrival_pattern or "all_at_once").lower().replace("-", "_").strip(),
        "count": len(requests),
        "disk_size": disk_size,
        "seed": seed,
        "requests": requests,
        "arrival_times": arrival_times,
        "request_objects": request_objects
    }

