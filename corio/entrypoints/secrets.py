token_hex = None


def main():
    """

    Encrypt secrets from repo root

    """
    from corio import secrets
    config = secrets.Config()
    config.run()


if __name__ == '__main__':
    main()
