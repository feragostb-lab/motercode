"""Auto-configuration script - Detect hardware and generate optimal config."""
import psutil
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_config


def detect_hardware():
    """
    Detect system hardware capabilities.
    
    Returns:
        Dictionary with hardware info
    """
    print("🔍 Detecting hardware...")
    
    # CPU info
    cpu_count_physical = psutil.cpu_count(logical=False)
    cpu_count_logical = psutil.cpu_count(logical=True)
    
    # Memory info
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024 ** 3)
    
    # TODO: GPU detection via llama-cpp probe
    # Try to detect GPU VRAM
    gpu_available = False
    gpu_vram_gb = 0
    gpu_layers = 0
    
    try:
        # TODO: Probe GPU with llama-cpp
        # This would require loading a small model to check GPU support
        pass
    except:
        pass
    
    hardware_info = {
        'cpu_physical_cores': cpu_count_physical,
        'cpu_logical_cores': cpu_count_logical,
        'ram_gb': memory_gb,
        'gpu_available': gpu_available,
        'gpu_vram_gb': gpu_vram_gb,
    }
    
    print(f"  ✓ CPU: {cpu_count_physical} physical cores ({cpu_count_logical} logical)")
    print(f"  ✓ RAM: {memory_gb:.1f} GB")
    if gpu_available:
        print(f"  ✓ GPU: Available ({gpu_vram_gb:.1f} GB VRAM)")
    else:
        print(f"  ℹ GPU: Not detected (will use CPU only)")
    
    # Calculate and display maximum theoretical capacities
    print(f"\n🚀 Maximum Capacities:")
    max_threads = cpu_count_logical
    max_ram_available = memory_gb * 0.95  # Reserve 5% for OS
    print(f"  • Max Threads: {max_threads} (100% of logical cores)")
    print(f"  • Max RAM Available: {max_ram_available:.1f} GB (95% of total)")
    if gpu_available:
        print(f"  • Max GPU Layers: ~{min(80, int(gpu_vram_gb * 10))} (based on VRAM)")
    
    return hardware_info


def calculate_optimal_settings(hardware_info):
    """
    Calculate optimal processor settings based on hardware.
    
    Args:
        hardware_info: Hardware information dictionary
        
    Returns:
        Dictionary with optimal settings
    """
    print("\n⚙️  Calculating optimal settings...")
    
    # Thread calculation (70% of logical cores for normal mode)
    threads_normal = max(1, int(hardware_info['cpu_logical_cores'] * 0.7))
    threads_boost = max(1, int(hardware_info['cpu_logical_cores'] * 0.95))
    
    # RAM calculation (70% of total RAM for normal mode)
    ram_normal_gb = hardware_info['ram_gb'] * 0.7
    ram_boost_gb = hardware_info['ram_gb'] * 0.95
    
    # Batch size calculation (based on available RAM)
    # Rough heuristic: 2048 batch size per 8GB RAM
    batch_size = min(4096, max(512, int(ram_normal_gb / 8 * 2048)))
    
    # GPU layers (if GPU available, offload most layers)
    gpu_layers = 0
    if hardware_info['gpu_available']:
        # Estimate layers based on VRAM
        # Qwen2.5-VL-7B has ~80 layers, each ~100MB
        gpu_layers = min(80, int(hardware_info['gpu_vram_gb'] * 10))
    
    settings = {
        'threads': threads_normal,
        'batch_size': batch_size,
        'gpu_layers': gpu_layers,
        'max_cpu_percent': 70,
        'max_ram_percent': 70,
        'idle_cpu_percent': 95,
        'idle_ram_percent': 95,
    }
    
    print(f"  ✓ Threads (normal): {threads_normal}")
    print(f"  ✓ Threads (boost): {threads_boost}")
    print(f"  ✓ Batch size: {batch_size}")
    print(f"  ✓ GPU layers: {gpu_layers}")
    print(f"  ✓ Max CPU (normal): 70%")
    print(f"  ✓ Max RAM (normal): 70%")
    print(f"  ✓ Max CPU (boost): 95%")
    print(f"  ✓ Max RAM (boost): 95%")
    
    return settings


def update_config(settings):
    """
    Update config.yaml with optimal settings.
    
    Args:
        settings: Settings dictionary
    """
    print("\n💾 Updating configuration...")
    
    config = get_config()
    
    # Update processor settings
    config.set('processor.threads', settings['threads'])
    config.set('processor.batch_size', settings['batch_size'])
    config.set('processor.gpu_layers', settings['gpu_layers'])
    config.set('processor.max_cpu_percent', settings['max_cpu_percent'])
    config.set('processor.max_ram_percent', settings['max_ram_percent'])
    config.set('processor.idle_cpu_percent', settings['idle_cpu_percent'])
    config.set('processor.idle_ram_percent', settings['idle_ram_percent'])
    
    # Save configuration
    config.save()
    
    print(f"  ✓ Configuration saved to config.yaml")


def main():
    """Main setup process."""
    print("=" * 60)
    print("Receipt Processor - Auto Configuration Setup")
    print("=" * 60)
    print()
    print("This tool will detect your hardware and configure")
    print("optimal settings for background receipt processing.")
    print()
    
    # Detect hardware
    hardware_info = detect_hardware()
    
    # Calculate optimal settings
    settings = calculate_optimal_settings(hardware_info)
    
    # Confirm with user
    print()
    response = input("Apply these settings to config.yaml? (y/n): ")
    
    if response.lower() == 'y':
        update_config(settings)
        print()
        print("=" * 60)
        print("✅ Configuration completed successfully!")
        print("=" * 60)
        print()
        print("You can now:")
        print("  1. Run 'python app_processor.py' to start the processor")
        print("  2. Run 'python app_dashboard.py' to open the dashboard")
        print()
        print("Settings can be manually adjusted in config.yaml if needed.")
    else:
        print("\n❌ Configuration cancelled.")


if __name__ == "__main__":
    main()
