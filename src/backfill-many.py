# backills many articles using a simple text file of paths to XML.
# paths may include globs.
# all paths are verified to exist before execution.
# see `/backfill-many.sh`

import glob, os, sys
import adhoc_backfill

def main(xml_repo_dir, backfill_file, dry_run):
    assert os.path.exists(xml_repo_dir), "path to XML repository doesn't exist: %s" % xml_repo_dir

    path_list = []
    for globbed_path in open("backfill.txt", 'r').read().splitlines():
        globbed_path = os.path.join(xml_repo_dir, globbed_path)
        globbed_path = os.path.abspath(globbed_path)
        result = glob.glob(globbed_path)
        assert result, "failed to find/expand path: %s" % globbed_path
        path_list.extend(result)

    for path in path_list:
        assert os.path.exists(path), "path does not exist: %s" % path

    # prompt

    path_list = sorted(path_list, reverse=True)
    for path in path_list:
        print(path)
    print()
    print("found %r articles to backfill" % (len(path_list),))
    try:
        input("any key to continue, ctrl-c to quit")
    except KeyboardInterrupt:
        print()
        return False

    # finally

    adhoc_backfill.do_paths(path_list, dry_run)

    # examine results for failures?

    return True

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--xml-repo-dir')
    parser.add_argument('--backfill-file')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    success = main(args.xml_repo_dir, args.backfill_file, args.dry_run)
    sys.exit(0 if success else 1)
