token_hex = None  # FastAPI tries to import this?


def main():
    """

    Encrypt secrets from repo root

    """
    from corio import secrets
    config = secrets.Config()
    config.run()


if __name__ == '__main__':
    import sys

    from corio import Path

    with Path('/opt/dev/repo/ia.core').chdir:
        sys.argv = [
            '/opt/dev/repo/corio/corio/secrets_tools.py',
            #'decrypt',
            'encrypt',
            #'--context=+',
            '--context=web,vpn',
        ]
        main()
    main()
