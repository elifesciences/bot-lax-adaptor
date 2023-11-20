import sys
import main
import generate_article_json

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    main_subparser = subparsers.add_parser('main') # todo: rename
    main_subparser = main.cli_args(main_subparser)

    gaj_subparser = subparsers.add_parser('generate-article-json')
    gaj_subparser = generate_article_json.cli_args(gaj_subparser)

    args = parser.parse_args()

    command_map = {
        'main': main.__main__,
        'generate-article-json': generate_article_json.__main__,
        # ...
    }

    if args.command not in command_map:
        print('unknown command: %s' % args.command)
        sys.exit(1)

    command_map[args.command](args)
