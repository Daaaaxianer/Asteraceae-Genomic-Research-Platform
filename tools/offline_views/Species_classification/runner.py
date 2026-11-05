import os
import sys


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: runner.py <place> <base_dir>")

    place = sys.argv[1]
    base_dir = sys.argv[2]

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from tools.offline_views.Species_classification import tools as species_tools

    species_tools.species_classification_run_tools(place=place, base_dir=base_dir)


if __name__ == "__main__":
    main()
