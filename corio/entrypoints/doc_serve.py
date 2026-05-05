from corio.infrastructure_tools.project import Project
from corio.infrastructure_tools.releaser import ReleaseDocumentation
from corio.path_tools import PackagePaths, Path


def main():
    paths = PackagePaths(Path.cwd())
    project = Project(paths.name_ns)
    release = ReleaseDocumentation(project.releaser)

    with paths.repo.chdir:
        release.serve(
            host='0.0.0.0',
            port=8180 + paths.metadata.port,
        )


if __name__ == "__main__":
    main()
