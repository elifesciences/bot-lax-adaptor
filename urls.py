from glob import glob
import json
import sys

def all(folder_json):
    files = glob("%s/elife-*.json" % folder_json)
    urls = []
    for f in files:
        article = json.load(open(f))
        urls.append("/content/%d/e%s" % (article['snippet']['volume'], article['snippet']['id']))
    return urls

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: %s folder_json\n" % sys.argv[0]
        sys.exit(1)
    for url in all(sys.argv[1]):
        print url


