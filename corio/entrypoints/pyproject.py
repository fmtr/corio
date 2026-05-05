from corio.infra.incrementor_pyproject import IncrementorPyproject
from corio.infra.project import Project
from corio.paths import paths


def main():
    project = Project(paths.name_ns)
    project.versions.pinned = project.versions.old
    IncrementorPyproject(project.releaser).apply()


if __name__ == "__main__":
    main()
