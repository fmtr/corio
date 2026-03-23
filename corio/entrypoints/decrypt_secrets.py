def main():
    """

    Decrypt secrets from repo root

    """
    from corio import secrets
    for path in secrets.decrypt():
        print(str(path))


if __name__ == '__main__':
    main()
