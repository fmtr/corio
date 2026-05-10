from pydantic_settings import CliSubCommand

from corio import dm
from corio import sec
from corio import sets
from corio.path import Path


class DocServe(dm.Base):
    def run(self):
        from corio.infra.project import Project
        from corio.infra.releaser import ReleaseDocumentation
        from corio.path import PackagePaths, Path

        paths = PackagePaths(Path.cwd())
        project = Project(paths.name_ns)
        release = ReleaseDocumentation(project.releaser)

        with paths.repo.chdir:
            return release.serve(
                host="0.0.0.0",
                port=8180 + paths.metadata.port,
            )


class Docs(dm.Base):
    serve: CliSubCommand[DocServe]


class Pyproject(dm.Base):
    def run(self):
        from corio.infra.incrementor_pyproject import IncrementorPyproject
        from corio.infra.project import Project
        from corio.paths import paths

        project = Project(paths.name_ns)
        project.versions.pinned = project.versions.new
        return IncrementorPyproject(project.releaser).apply()


class EpTest(dm.Base):
    def run(self):
        print("Ran test entrypoint.")


class Test(dm.Base):
    name: str = Path.cwd().name

    def run(self):
        from corio.infra.project import Project

        project = Project(self.name)
        is_passed = project.releaser.tester.run()
        return int(not is_passed)


class ShellDebug(dm.Base):
    def run(self):
        from corio import debug

        return debug.debug_shell()


class CacheHfh(dm.Base):
    def run(self):
        import corio

        return corio.hfh.main()


class Infra(dm.Base):
    def run(self):
        from corio.infra.api import Api

        return Api.launch()


class InstallYamlscript(dm.Base):
    def run(self):
        from corio import yml

        return yml.install()


class RemoteDebugTest(dm.Base):
    def run(self):
        from corio import debug

        return debug.trace(is_debug=True)


class Cli(sets.Base, cli_parse_args=True):
    secrets: CliSubCommand[sec.Cli]
    docs: CliSubCommand[Docs]
    pyproject: CliSubCommand[Pyproject]
    test: CliSubCommand[Test]
    ep_test: CliSubCommand[EpTest]
    shell_debug: CliSubCommand[ShellDebug]
    cache_hfh: CliSubCommand[CacheHfh]
    infra: CliSubCommand[Infra]
    install_yamlscript: CliSubCommand[InstallYamlscript]
    remote_debug_test: CliSubCommand[RemoteDebugTest]


def main():
    config = Cli()
    config.run()


if __name__ == "__main__":
    main()
