import os
import subprocess
import time


PROJECTS = [
    "caelum-stella",
    "cassandra", 
    "connectbot",
    "jdbi",
    "jdeb",
    "hive",
    "mongo-java-driver",
    "nutch",
    "scala-maven-plugin",
    "zookeeper"
]

N_SAMPLES = 100  # adjust as needed
OUTPUT_DIR = "ablation_results"


def run_project_ablation(project_name):
    print(f"\n{'='*60}")
    print(f"RUNNING ABLATION FOR: {project_name}")
    print(f"{'='*60}")
    
    output_file = os.path.join(OUTPUT_DIR, f"{project_name}_ablation.json")
    
    cmd = [
        "python", 
        "run_ablation_study.py", 
        project_name, 
        str(N_SAMPLES), 
        output_file
    ]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            elapsed = time.time() - start_time
            print(f"✅ {project_name} completed in {elapsed:.1f}s")
            print(f"   Output: {output_file}")
            return True
        else:
            print(f"❌ {project_name} failed:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {project_name} timed out after 1 hour")
        return False
    except Exception as e:
        print(f"💥 {project_name} crashed: {str(e)}")
        return False


def main():
    print("STARTING BATCH ABLATION STUDY")
    print(f"Projects: {len(PROJECTS)}")
    print(f"Samples per project: {N_SAMPLES}")
    
    # create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    successful = []
    failed = []
    total_start = time.time()
    
    for i, project in enumerate(PROJECTS):
        print(f"\nProgress: {i+1}/{len(PROJECTS)}")
        
        if run_project_ablation(project):
            successful.append(project)
        else:
            failed.append(project)
    
    total_elapsed = time.time() - total_start
    
    print(f"\n{'='*60}")
    print("BATCH ABLATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {total_elapsed/60:.1f} minutes")
    print(f"Successful: {len(successful)}/{len(PROJECTS)}")
    
    if successful:
        print(f"\n✅ Completed projects:")
        for project in successful:
            print(f"   - {project}")
    
    if failed:
        print(f"\n❌ Failed projects:")
        for project in failed:
            print(f"   - {project}")
    
    print(f"\nResults saved in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
