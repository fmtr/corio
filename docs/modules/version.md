# version
`from corio import version`

Semantic version parsing helpers. `semver` is installed as a core Corio dependency.

Use `PackagePaths.metadata.version` for the declared version and `PackagePaths.metadata.version_dev` for the runtime version. The latter adds a development suffix and timestamp for repository checkouts, and returns the declared version for installed packages.


