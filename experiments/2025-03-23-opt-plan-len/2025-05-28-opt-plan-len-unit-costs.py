#! /usr/bin/env python
import json
import os

from downward.suites import Task

import custom_parser
import project

from downward import suites
from downward.cached_revision import CachedFastDownwardRevision
from downward.experiment import FastDownwardAlgorithm, FastDownwardRun
from lab.experiment import Experiment

REPO = project.get_repo_base()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
SCP_LOGIN = "myname@myserver.com"
REMOTE_REPOS_DIR = "/infai/username/projects"
REVISION_CACHE = (
        os.environ.get("DOWNWARD_REVISION_CACHE") or project.DIR / "data" / "revision-cache"
)
REVISION_CACHE = (
        project.DIR / "data" / "revision-cache"
)
SUITE = project.SUITE_OPTIMAL_STRIPS
if project.BaselSlurmEnvironment.is_present():
    ENV = project.BaselSlurmEnvironment(
        email="jendrik.seipp@unibas.ch",
        partition="infai_2",
        memory_per_cpu="9G",  # leave some space for the scripts
    )
elif project.TetralithEnvironment.is_present():
    ENV = project.TetralithEnvironment(
        memory_per_cpu="9G",  # leave some space for the scripts
        email="jendrik.seipp@liu.se",
        extra_options="#SBATCH --account=naiss2024-5-421",
    )
else:
    ENV = project.LocalEnvironment(processes=2)
    SUITE = ["miconic:s1-0.pddl"]

CONFIGS = [
    ("scorpion-unit-cost", [
    "--search", """astar(scp_online([
        projections(sys_scp(max_time=100, max_time_per_restart=10)),
        cartesian()],
        saturator=perimstar, max_time=1000, interval=10K, orders=greedy_orders(), transform=adapt_costs(one)),
        pruning=limited_pruning(pruning=atom_centric_stubborn_sets(), min_required_pruning_ratio=0.2), cost_type=one)""",]),
]
BUILD_OPTIONS = []
DRIVER_OPTIONS = [
    "--overall-memory-limit", "8G",
    "--overall-time-limit", "1h",
    "--transform-task", "preprocess-h2"]
# Pairs of revision identifier and optional revision nick.
REV_NICKS = [
    ("scorpion", ""),
]
ATTRIBUTES = [
    "error",
    "run_dir",
    "search_start_time",
    "search_start_memory",
    "total_time",
    "h_values",
    "coverage",
    "expansions",
    "memory",
    "plan_length",
    project.EVALUATIONS_PER_TIME,
]
exp = Experiment(environment=ENV)
for rev, rev_nick in REV_NICKS:
    cached_rev = CachedFastDownwardRevision(REVISION_CACHE, REPO, rev, BUILD_OPTIONS)
    cached_rev.cache()
    exp.add_resource("", cached_rev.path, cached_rev.get_relative_exp_path())
    for config_nick, config in CONFIGS:
        algo_name = f"{rev_nick}-{config_nick}" if rev_nick else config_nick
        task: Task
        for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
            algo = FastDownwardAlgorithm(
                algo_name,
                cached_rev,
                DRIVER_OPTIONS,
                config,
            )
            run = FastDownwardRun(exp, algo, task)
            exp.add_run(run)

exp.add_parser(project.FastDownwardExperiment.EXITCODE_PARSER)
exp.add_parser(project.FastDownwardExperiment.TRANSLATOR_PARSER)
exp.add_parser(project.FastDownwardExperiment.SINGLE_SEARCH_PARSER)
exp.add_parser(custom_parser.get_parser())
exp.add_parser(project.FastDownwardExperiment.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp,
    attributes=ATTRIBUTES,
    filter=[project.add_evaluations_per_time, project.group_domains],
)

exp.run_steps()
