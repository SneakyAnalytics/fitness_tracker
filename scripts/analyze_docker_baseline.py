#!/usr/bin/env python3
"""
Analyze Docker resource baseline logs to identify performance issues.
Usage: python scripts/analyze_docker_baseline.py logs/docker_baseline.log
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple


def parse_size(size_str: str) -> float:
    """Convert size string (e.g., '95.5MiB') to MB."""
    if not size_str or size_str == 'N/A':
        return 0.0
    
    size_str = size_str.strip()
    multipliers = {
        'B': 1 / (1024 * 1024),
        'KB': 1 / 1024,
        'KiB': 1 / 1024,
        'MB': 1,
        'MiB': 1,
        'GB': 1024,
        'GiB': 1024,
    }
    
    for unit, multiplier in multipliers.items():
        if size_str.endswith(unit):
            try:
                value = float(size_str[:-len(unit)])
                return value * multiplier
            except ValueError:
                return 0.0
    
    # Try parsing as plain number
    try:
        return float(size_str)
    except ValueError:
        return 0.0


def analyze_baseline(log_file: Path) -> None:
    """Analyze Docker baseline log file."""
    
    if not log_file.exists():
        print(f"ERROR: Log file not found: {log_file}")
        sys.exit(1)
    
    print(f"Analyzing: {log_file}")
    print("=" * 80)
    print()
    
    # Collect stats per container
    container_stats: Dict[str, List[Tuple[datetime, float, float]]] = defaultdict(list)
    
    with open(log_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                timestamp = datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S')
                container = row['Container']
                cpu_percent = float(row['CPU%'])
                mem_mb = parse_size(row['MemUsage'])
                
                container_stats[container].append((timestamp, cpu_percent, mem_mb))
            except (ValueError, KeyError) as e:
                continue  # Skip malformed rows
    
    if not container_stats:
        print("ERROR: No valid data found in log file")
        sys.exit(1)
    
    # Analyze each container
    for container, stats in container_stats.items():
        print(f"📦 {container}")
        print("-" * 80)
        
        # Extract metrics
        cpu_values = [s[1] for s in stats]
        mem_values = [s[2] for s in stats]
        
        # Calculate statistics
        cpu_avg = sum(cpu_values) / len(cpu_values)
        cpu_max = max(cpu_values)
        cpu_min = min(cpu_values)
        
        mem_avg = sum(mem_values) / len(mem_values)
        mem_max = max(mem_values)
        mem_min = min(mem_values)
        
        # Memory growth analysis (compare first hour to last hour)
        if len(stats) > 120:  # At least 2 hours of data
            first_hour = stats[:60]
            last_hour = stats[-60:]
            
            first_hour_avg = sum(s[2] for s in first_hour) / len(first_hour)
            last_hour_avg = sum(s[2] for s in last_hour) / len(last_hour)
            mem_growth = last_hour_avg - first_hour_avg
            mem_growth_pct = (mem_growth / first_hour_avg * 100) if first_hour_avg > 0 else 0
        else:
            mem_growth = 0
            mem_growth_pct = 0
        
        # Duration
        duration_hours = (stats[-1][0] - stats[0][0]).total_seconds() / 3600
        
        # Display results
        print(f"  Duration: {duration_hours:.1f} hours ({len(stats)} samples)")
        print()
        print(f"  CPU Usage:")
        print(f"    Average: {cpu_avg:.1f}%")
        print(f"    Min:     {cpu_min:.1f}%")
        print(f"    Max:     {cpu_max:.1f}%")
        
        # CPU analysis
        if cpu_avg > 25:
            print(f"    ⚠️  WARNING: High average CPU usage (>25%)")
        if cpu_max > 80:
            print(f"    ⚠️  WARNING: CPU spikes detected (>80%)")
        
        print()
        print(f"  Memory Usage:")
        print(f"    Average: {mem_avg:.1f} MB")
        print(f"    Min:     {mem_min:.1f} MB")
        print(f"    Max:     {mem_max:.1f} MB")
        
        if mem_growth_pct > 20:
            print(f"    ⚠️  WARNING: Memory growth of {mem_growth:.1f} MB ({mem_growth_pct:.1f}%)")
            print(f"       Potential memory leak detected")
        
        print()
        print(f"  Recommendations:")
        
        # Memory limit recommendation
        recommended_mem_limit = int(mem_max * 1.5)  # 50% buffer
        print(f"    mem_limit: {recommended_mem_limit}m  (1.5x max observed: {mem_max:.0f} MB)")
        
        # CPU limit recommendation
        if cpu_avg < 10:
            recommended_cpu_limit = 0.5
        elif cpu_avg < 25:
            recommended_cpu_limit = 1.0
        elif cpu_avg < 50:
            recommended_cpu_limit = 1.5
        else:
            recommended_cpu_limit = 2.0
        
        print(f"    cpus: {recommended_cpu_limit}  (based on avg CPU: {cpu_avg:.1f}%)")
        
        print()
        print()
    
    # Overall recommendations
    print("=" * 80)
    print("📊 OVERALL RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    total_containers = len(container_stats)
    high_cpu_containers = sum(1 for stats in container_stats.values() 
                               if sum(s[1] for s in stats) / len(stats) > 25)
    
    if high_cpu_containers > 0:
        print(f"⚠️  {high_cpu_containers}/{total_containers} containers have high CPU usage")
        print("   Consider:")
        print("   - Optimizing code (reduce unnecessary processing)")
        print("   - Identifying resource-intensive operations")
        print("   - Moving heavy tasks to background jobs")
        print()
    
    # WSL recommendations
    total_mem = sum(max(s[2] for s in stats) for stats in container_stats.values())
    print(f"Total peak memory usage: {total_mem:.0f} MB")
    print()
    print("Recommended .wslconfig settings:")
    wsl_mem = max(2048, int(total_mem * 2))  # At least 2GB or 2x peak usage
    wsl_cpu = max(2, total_containers)  # At least 2 or one per container
    print(f"  memory={wsl_mem}MB")
    print(f"  processors={wsl_cpu}")
    print()
    print("To apply: Create/edit C:\\Users\\<username>\\.wslconfig with above settings")
    print("Then run: wsl --shutdown")
    print()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/analyze_docker_baseline.py <log_file>")
        print("Example: python scripts/analyze_docker_baseline.py logs/docker_baseline.log")
        sys.exit(1)
    
    log_file = Path(sys.argv[1])
    analyze_baseline(log_file)
