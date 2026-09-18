"""
Disk Scheduling Algorithms Module
Implements FCFS, SSTF, SCAN, and C-SCAN algorithms.
"""

from typing import List, Dict, Any, Tuple


def fcfs(
    requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    direction: str = "UP"
) -> Dict[str, Any]:
    """
    First-Come, First-Served (FCFS) Disk Scheduling Algorithm.
    Requests are served in the exact order they arrive.
    """
    if not requests:
        return {
            "algorithm": "FCFS",
            "seek_order": [],
            "head_movement_sequence": [initial_head],
            "total_seek_distance": 0,
            "steps": []
        }

    seek_order = list(requests)
    head_movement_sequence = [initial_head] + seek_order
    
    total_seek_distance = 0
    steps = []
    current_head = initial_head
    cumulative_distance = 0

    for idx, req in enumerate(seek_order):
        dist = abs(req - current_head)
        total_seek_distance += dist
        cumulative_distance += dist
        steps.append({
            "step": idx + 1,
            "cylinder": req,
            "distance": dist,
            "cumulative_distance": cumulative_distance,
            "is_serviced": True,
            "event_type": "SERVICED",
            "label": f"Req #{idx + 1}: Cyl {req}"
        })
        current_head = req

    return {
        "algorithm": "FCFS",
        "seek_order": seek_order,
        "head_movement_sequence": head_movement_sequence,
        "total_seek_distance": total_seek_distance,
        "steps": steps
    }


def sstf(
    requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    direction: str = "UP"
) -> Dict[str, Any]:
    """
    Shortest Seek Time First (SSTF) Disk Scheduling Algorithm.
    Selects the request with minimum seek time from the current head position.
    """
    if not requests:
        return {
            "algorithm": "SSTF",
            "seek_order": [],
            "head_movement_sequence": [initial_head],
            "total_seek_distance": 0,
            "steps": []
        }

    unvisited = list(requests)
    current_head = initial_head
    seek_order = []
    head_movement_sequence = [initial_head]
    total_seek_distance = 0
    cumulative_distance = 0
    steps = []

    step_num = 1
    while unvisited:
        # Find closest cylinder
        closest_idx = 0
        min_dist = abs(unvisited[0] - current_head)
        
        for i in range(1, len(unvisited)):
            dist = abs(unvisited[i] - current_head)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
            elif dist == min_dist:
                # Tie-break in favored direction if applicable
                if direction == "UP" and unvisited[i] > current_head:
                    closest_idx = i
                elif direction == "DOWN" and unvisited[i] < current_head:
                    closest_idx = i

        chosen = unvisited.pop(closest_idx)
        dist = abs(chosen - current_head)
        total_seek_distance += dist
        cumulative_distance += dist
        seek_order.append(chosen)
        head_movement_sequence.append(chosen)

        steps.append({
            "step": step_num,
            "cylinder": chosen,
            "distance": dist,
            "cumulative_distance": cumulative_distance,
            "is_serviced": True,
            "event_type": "SERVICED",
            "label": f"SSTF #{step_num}: Cyl {chosen}"
        })
        current_head = chosen
        step_num += 1

    return {
        "algorithm": "SSTF",
        "seek_order": seek_order,
        "head_movement_sequence": head_movement_sequence,
        "total_seek_distance": total_seek_distance,
        "steps": steps
    }


def scan(
    requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    direction: str = "UP"
) -> Dict[str, Any]:
    """
    SCAN (Elevator) Disk Scheduling Algorithm.
    The head moves in one direction servicing requests until reaching the boundary,
    then reverses direction to service requests in the opposite direction.
    """
    if not requests:
        return {
            "algorithm": "SCAN",
            "seek_order": [],
            "head_movement_sequence": [initial_head],
            "total_seek_distance": 0,
            "steps": []
        }

    dir_norm = direction.upper()
    max_cyl = disk_size - 1
    
    # Split requests into those above and below current head
    # Note: requests at exactly current_head will be serviced first in direction
    up_requests = sorted([r for r in requests if r >= initial_head])
    down_requests = sorted([r for r in requests if r < initial_head], reverse=True)

    seek_order = []
    head_movement_sequence = [initial_head]
    steps = []
    current_head = initial_head
    total_seek_distance = 0
    cumulative_distance = 0
    step_num = 1

    if dir_norm == "UP":
        # Service upwards
        for r in up_requests:
            dist = abs(r - current_head)
            total_seek_distance += dist
            cumulative_distance += dist
            seek_order.append(r)
            head_movement_sequence.append(r)
            steps.append({
                "step": step_num,
                "cylinder": r,
                "distance": dist,
                "cumulative_distance": cumulative_distance,
                "is_serviced": True,
                "event_type": "SERVICED",
                "label": f"SCAN UP: Cyl {r}"
            })
            current_head = r
            step_num += 1

        # If there are pending requests below, sweep to upper boundary and reverse
        if down_requests:
            if current_head != max_cyl:
                dist = abs(max_cyl - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                head_movement_sequence.append(max_cyl)
                steps.append({
                    "step": step_num,
                    "cylinder": max_cyl,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": False,
                    "event_type": "BOUNDARY_TURNAROUND",
                    "label": f"Boundary Turnaround: Cyl {max_cyl}"
                })
                current_head = max_cyl
                step_num += 1

            for r in down_requests:
                dist = abs(r - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                seek_order.append(r)
                head_movement_sequence.append(r)
                steps.append({
                    "step": step_num,
                    "cylinder": r,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": True,
                    "event_type": "SERVICED",
                    "label": f"SCAN DOWN: Cyl {r}"
                })
                current_head = r
                step_num += 1
    else:
        # Service downwards
        for r in down_requests:
            dist = abs(r - current_head)
            total_seek_distance += dist
            cumulative_distance += dist
            seek_order.append(r)
            head_movement_sequence.append(r)
            steps.append({
                "step": step_num,
                "cylinder": r,
                "distance": dist,
                "cumulative_distance": cumulative_distance,
                "is_serviced": True,
                "event_type": "SERVICED",
                "label": f"SCAN DOWN: Cyl {r}"
            })
            current_head = r
            step_num += 1

        # If there are pending requests above, sweep to lower boundary (0) and reverse
        if up_requests:
            if current_head != 0:
                dist = abs(0 - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                head_movement_sequence.append(0)
                steps.append({
                    "step": step_num,
                    "cylinder": 0,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": False,
                    "event_type": "BOUNDARY_TURNAROUND",
                    "label": "Boundary Turnaround: Cyl 0"
                })
                current_head = 0
                step_num += 1

            for r in up_requests:
                dist = abs(r - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                seek_order.append(r)
                head_movement_sequence.append(r)
                steps.append({
                    "step": step_num,
                    "cylinder": r,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": True,
                    "event_type": "SERVICED",
                    "label": f"SCAN UP: Cyl {r}"
                })
                current_head = r
                step_num += 1

    return {
        "algorithm": "SCAN",
        "seek_order": seek_order,
        "head_movement_sequence": head_movement_sequence,
        "total_seek_distance": total_seek_distance,
        "steps": steps
    }


def c_scan(
    requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    direction: str = "UP"
) -> Dict[str, Any]:
    """
    C-SCAN (Circular SCAN) Disk Scheduling Algorithm.
    The head moves in one direction to the end, then resets to the opposite end
    without servicing requests on the return trip, and resumes in the same direction.
    """
    if not requests:
        return {
            "algorithm": "C-SCAN",
            "seek_order": [],
            "head_movement_sequence": [initial_head],
            "total_seek_distance": 0,
            "steps": []
        }

    dir_norm = direction.upper()
    max_cyl = disk_size - 1

    up_requests = sorted([r for r in requests if r >= initial_head])
    down_requests = sorted([r for r in requests if r < initial_head])

    seek_order = []
    head_movement_sequence = [initial_head]
    steps = []
    current_head = initial_head
    total_seek_distance = 0
    cumulative_distance = 0
    step_num = 1

    if dir_norm == "UP":
        # Service upwards
        for r in up_requests:
            dist = abs(r - current_head)
            total_seek_distance += dist
            cumulative_distance += dist
            seek_order.append(r)
            head_movement_sequence.append(r)
            steps.append({
                "step": step_num,
                "cylinder": r,
                "distance": dist,
                "cumulative_distance": cumulative_distance,
                "is_serviced": True,
                "event_type": "SERVICED",
                "label": f"C-SCAN UP: Cyl {r}"
            })
            current_head = r
            step_num += 1

        # If there are pending requests below, go to boundary max_cyl, jump to 0, then continue UP
        if down_requests:
            if current_head != max_cyl:
                dist = abs(max_cyl - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                head_movement_sequence.append(max_cyl)
                steps.append({
                    "step": step_num,
                    "cylinder": max_cyl,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": False,
                    "event_type": "BOUNDARY",
                    "label": f"End Boundary: Cyl {max_cyl}"
                })
                current_head = max_cyl
                step_num += 1

            # Reset jump to cylinder 0
            jump_dist = abs(0 - current_head)
            total_seek_distance += jump_dist
            cumulative_distance += jump_dist
            head_movement_sequence.append(0)
            steps.append({
                "step": step_num,
                "cylinder": 0,
                "distance": jump_dist,
                "cumulative_distance": cumulative_distance,
                "is_serviced": False,
                "event_type": "CIRCULAR_RESET",
                "label": "Circular Reset Jump: Cyl 0"
            })
            current_head = 0
            step_num += 1

            # Continue UP through down_requests (in ascending order)
            for r in sorted(down_requests):
                dist = abs(r - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                seek_order.append(r)
                head_movement_sequence.append(r)
                steps.append({
                    "step": step_num,
                    "cylinder": r,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": True,
                    "event_type": "SERVICED",
                    "label": f"C-SCAN UP: Cyl {r}"
                })
                current_head = r
                step_num += 1
    else:
        # Service downwards
        down_rev = sorted(down_requests, reverse=True)
        for r in down_rev:
            dist = abs(r - current_head)
            total_seek_distance += dist
            cumulative_distance += dist
            seek_order.append(r)
            head_movement_sequence.append(r)
            steps.append({
                "step": step_num,
                "cylinder": r,
                "distance": dist,
                "cumulative_distance": cumulative_distance,
                "is_serviced": True,
                "event_type": "SERVICED",
                "label": f"C-SCAN DOWN: Cyl {r}"
            })
            current_head = r
            step_num += 1

        if up_requests:
            if current_head != 0:
                dist = abs(0 - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                head_movement_sequence.append(0)
                steps.append({
                    "step": step_num,
                    "cylinder": 0,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": False,
                    "event_type": "BOUNDARY",
                    "label": "End Boundary: Cyl 0"
                })
                current_head = 0
                step_num += 1

            # Reset jump to max_cyl
            jump_dist = abs(max_cyl - current_head)
            total_seek_distance += jump_dist
            cumulative_distance += jump_dist
            head_movement_sequence.append(max_cyl)
            steps.append({
                "step": step_num,
                "cylinder": max_cyl,
                "distance": jump_dist,
                "cumulative_distance": cumulative_distance,
                "is_serviced": False,
                "event_type": "CIRCULAR_RESET",
                "label": f"Circular Reset Jump: Cyl {max_cyl}"
            })
            current_head = max_cyl
            step_num += 1

            # Continue DOWN through up_requests (in descending order)
            up_rev = sorted(up_requests, reverse=True)
            for r in up_rev:
                dist = abs(r - current_head)
                total_seek_distance += dist
                cumulative_distance += dist
                seek_order.append(r)
                head_movement_sequence.append(r)
                steps.append({
                    "step": step_num,
                    "cylinder": r,
                    "distance": dist,
                    "cumulative_distance": cumulative_distance,
                    "is_serviced": True,
                    "event_type": "SERVICED",
                    "label": f"C-SCAN DOWN: Cyl {r}"
                })
                current_head = r
                step_num += 1

    return {
        "algorithm": "C-SCAN",
        "seek_order": seek_order,
        "head_movement_sequence": head_movement_sequence,
        "total_seek_distance": total_seek_distance,
        "steps": steps
    }


ALGORITHMS = {
    "FCFS": fcfs,
    "SSTF": sstf,
    "SCAN": scan,
    "C-SCAN": c_scan,
}


def run_algorithm(
    algorithm: str,
    requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    direction: str = "UP"
) -> Dict[str, Any]:
    """Dispatch helper for algorithms."""
    algo_key = algorithm.upper().replace("_", "-")
    if algo_key not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Choose from {list(ALGORITHMS.keys())}")
    return ALGORITHMS[algo_key](requests, initial_head, disk_size, direction)
