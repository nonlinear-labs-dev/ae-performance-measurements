import argparse
import pathlib
import sys
import os
from git import Repo
import subprocess
import statistics

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def assert_directory_exists(dir):
    if not os.path.exists(dir):
        eprint(f"{dir} does not exist!")
        exit(1)

def assert_ref_exists(ref, repo):
    assert ref != None

def do_command_in_dir(command, src_directory):
    ret = subprocess.run(command.split(" "), cwd=src_directory, capture_output=True)
    return ret

def get_commits_in_chronological_order(start_commit, source_dir):
    raw_ref_list = do_command_in_dir(f"git rev-list --ancestry-path {args.start_commit}..HEAD", args.source_directory).stdout.decode("utf-8")
    refs = raw_ref_list.split("\n")
    refs[:] = [x for x in refs if x]
    refs.reverse()
    return refs

def build_ae(build_dir):
    #todo check if we use ninja or make
    #print(do_command_in_dir("make audio-eninge", build_dir))
    do_command_in_dir("ninja audio-engine", build_dir)

def measure_performance_of_build(build_dir):
    ae_dir = os.path.join(build_dir, "package/audio-engine")
    ae_output = do_command_in_dir("./audio-engine -e", ae_dir)
    if ae_output.returncode != 0:
        eprint(ae_output.stderr.decode("utf-8"))
    
    performance_line = [line for line in ae_output.stdout.decode("utf-8").split("\n") if "Audio engine performs at " in line]
    if len(performance_line) > 0:
        performance_line = performance_line[0]

        start = 'Audio engine performs at '
        end = ' x realtime'
        num = performance_line[performance_line.find(start)+len(start):performance_line.rfind(end)]
        print(num)
        return num
    
    return -1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_commit", type=str)
    parser.add_argument("--branch", type=str)
    parser.add_argument("--build_directory", type=pathlib.Path)
    parser.add_argument("--source_directory", type=pathlib.Path)
    parser.add_argument("--num_runs_per_commit", type=int)
    args = parser.parse_args()

    assert_directory_exists(args.build_directory)
    assert_directory_exists(args.source_directory)

    repo = Repo(args.source_directory)

    assert not repo.bare
    assert not repo.is_dirty()

    assert_ref_exists(args.start_commit, repo)

    repo.git.checkout(args.branch)

    # this takes too long for debugging purposes
    #repo.remotes.origin.pull()
    refs = get_commits_in_chronological_order(args.start_commit, args.source_directory)
    print(f"found {len(refs)} commits to check")

    # create map to save results to
    total_results = {}

    for commit in refs:
        print(f"checking out {commit}")
        repo.git.checkout(commit)
        print(f"building audio-engine @{commit}")
        build_ae(args.build_directory)
        
        results = []
        for run in range(args.num_runs_per_commit):
            results.append(float(measure_performance_of_build(args.build_directory)))

        average_for_commit = statistics.mean(results)
        total_results[commit] = average_for_commit

    print(total_results)