def main():
    """

    Encrypt secrets from repo root

    """
    from corio import secrets
    for path in secrets.SecretsDefinitions.from_cwd():
        print(str(path))


if __name__ == '__main__':
    main()
